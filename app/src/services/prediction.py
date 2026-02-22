from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable
from uuid import uuid4

from fastapi import HTTPException
from sqlmodel import Session

from ..db.enums import PredictionStatus
from ..db.models import MLModelDB, PredictionHistoryDB, UserDB
from ..repositories.billing import BillingRepository
from ..repositories.history import PredictionHistoryRepository
from ..repositories.ml_models import MLModelRepository
from ..rabbitmq.client import publish_task


@dataclass(frozen=True)
class RowError:
    row_index: int
    field: str
    message: str


def _safe_json_row(value: Any) -> Any:
    """Гарантируем, что значение можно сериализовать в JSON"""
    try:
        import json

        json.dumps(value, ensure_ascii=False)
        return value
    except Exception:
        return str(value)


class PredictionService:
    def __init__(self) -> None:
        self._models = MLModelRepository()
        self._billing = BillingRepository()
        self._history = PredictionHistoryRepository()

    def _validate_rows(self, rows: Iterable[Any]) -> tuple[list[dict[str, Any]], list[RowError], list[dict[str, Any]]]:
        valid: list[dict[str, Any]] = []
        errors: list[RowError] = []
        rejected: list[dict[str, Any]] = []

        for i, r in enumerate(rows):
            if not isinstance(r, dict):
                msg = "row must be an object"
                errors.append(RowError(row_index=i, field="row", message=msg))
                rejected.append({"row_index": i, "row": _safe_json_row(r), "field": "row", "message": msg})
                continue
            if not r:
                msg = "row must not be empty"
                errors.append(RowError(row_index=i, field="row", message=msg))
                rejected.append({"row_index": i, "row": _safe_json_row(r), "field": "row", "message": msg})
                continue
            if not all(isinstance(k, str) for k in r.keys()):
                msg = "all keys must be strings"
                errors.append(RowError(row_index=i, field="row", message=msg))
                rejected.append({"row_index": i, "row": _safe_json_row(r), "field": "row", "message": msg})
                continue
            valid.append(r)

        return valid, errors, rejected

    def predict(
        self,
        session: Session,
        *,
        user: UserDB,
        model_name: str,
        model_version: str,
        rows: list[dict[str, Any]],
    ) -> PredictionHistoryDB:
        model: MLModelDB | None = self._models.get_by_name_version(session, name=model_name, version=model_version)
        if model is None:
            raise HTTPException(status_code=404, detail="Model not found")
        if not model.is_active:
            raise HTTPException(status_code=409, detail="Model is disabled")

        valid_rows, errors, rejected_rows = self._validate_rows(rows)
        valid_count = len(valid_rows)
        invalid_count = len(errors)

        predictions: list[dict[str, Any]] = []
        for row in valid_rows:
            predictions.append({"prediction": float(abs(hash(str(sorted(row.items())))) % 1000) / 1000.0})

        charged = Decimal("0")
        status = PredictionStatus.FAILED

        if valid_count > 0:
            charged = Decimal(model.price_per_row) * Decimal(valid_count)
            try:
                self._billing.charge(session, user.id, charged)
            except RuntimeError:
                session.commit()
                raise HTTPException(status_code=402, detail="Not enough credits")

            status = PredictionStatus.APPLIED

        item = PredictionHistoryDB(
            user_id=user.id,
            model_id=model.id,
            job_id=uuid4(),
            upload_id=None,
            status=status,
            valid_rows=valid_count,
            invalid_rows=invalid_count,
            errors=[e.__dict__ for e in errors],
            predictions=predictions,
            input_rows=rows,
            valid_data=valid_rows,
            rejected_rows=rejected_rows,
            charged=charged,
        )
        self._history.add(session, item)
        return item

    def enqueue(
        self,
        session: Session,
        *,
        user: UserDB,
        model_name: str,
        model_version: str,
        rows: list[dict[str, Any]],
    ) -> PredictionHistoryDB:
        """Асинхронный сценарий (задание №5 + требования задания №6)

        Publisher:
        - проверяет, что модель существует и активна;
        - валидирует входные данные (чтобы UI/API мог вернуть пользователю список ошибок);
        - выполняет проверку баланса ДО постановки задачи в очередь;
        - создает запись истории и отправляет задачу в RabbitMQ.

        Воркеры:
        - выполняют предикт;
        - списывают кредиты только при успешном выполнении.
        """

        model: MLModelDB | None = self._models.get_by_name_version(session, name=model_name, version=model_version)
        if model is None:
            raise HTTPException(status_code=404, detail="Model not found")
        if not model.is_active:
            raise HTTPException(status_code=409, detail="Model is disabled")

        valid_rows, row_errors, rejected_rows = self._validate_rows(rows)
        valid_count = len(valid_rows)
        invalid_count = len(row_errors)

        if valid_count == 0:
            item = PredictionHistoryDB(
                user_id=user.id,
                model_id=model.id,
                job_id=uuid4(),
                upload_id=None,
                status=PredictionStatus.FAILED,
                valid_rows=0,
                invalid_rows=invalid_count,
                errors=[e.__dict__ for e in row_errors],
                predictions=[],
                input_rows=rows,
                valid_data=[],
                rejected_rows=rejected_rows,
                charged=Decimal("0"),
            )
            self._history.add(session, item)
            return item

        estimated = Decimal(model.price_per_row) * Decimal(valid_count)
        fresh_user = session.get(UserDB, user.id)
        balance = Decimal(getattr(fresh_user, "balance", user.balance))
        if balance <= 0 or balance < estimated:
            raise HTTPException(status_code=402, detail="Not enough credits")

        task_id = uuid4()
        item = PredictionHistoryDB(
            id=task_id,
            user_id=user.id,
            model_id=model.id,
            job_id=task_id,
            upload_id=None,
            status=PredictionStatus.QUEUED,
            valid_rows=valid_count,
            invalid_rows=invalid_count,
            errors=[e.__dict__ for e in row_errors],
            predictions=[],
            input_rows=rows,
            valid_data=valid_rows,
            rejected_rows=rejected_rows,
            charged=Decimal("0"),
        )
        self._history.add(session, item)

        features: dict[str, Any] = {"rows": valid_rows}
        publish_task(
            {
                "task_id": str(task_id),
                "user_id": str(user.id),
                "model": {"name": model_name, "version": model_version},
                "features": features,
                "timestamp": item.created_at.isoformat(),
            }
        )

        return item


