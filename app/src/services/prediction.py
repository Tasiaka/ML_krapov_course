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


@dataclass(frozen=True)
class RowError:
    row_index: int
    field: str
    message: str


class PredictionService:
    def __init__(self) -> None:
        self._models = MLModelRepository()
        self._billing = BillingRepository()
        self._history = PredictionHistoryRepository()

    def _validate_rows(self, rows: Iterable[Any]) -> tuple[list[dict[str, Any]], list[RowError]]:
        valid: list[dict[str, Any]] = []
        errors: list[RowError] = []

        for i, r in enumerate(rows):
            if not isinstance(r, dict):
                errors.append(RowError(row_index=i, field="row", message="row must be an object"))
                continue
            if not r:
                errors.append(RowError(row_index=i, field="row", message="row must not be empty"))
                continue
            if not all(isinstance(k, str) for k in r.keys()):
                errors.append(RowError(row_index=i, field="row", message="all keys must be strings"))
                continue
            valid.append(r)

        return valid, errors

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

        valid_rows, errors = self._validate_rows(rows)
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
            charged=charged,
        )
        self._history.add(session, item)
        return item


