from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..deps import get_current_user, get_session
from ..schemas import PredictIn, PredictOut, RowErrorOut, RejectedRowOut
from ...db.models import UserDB
from ...db.enums import UserRole
from ...repositories.history import PredictionHistoryRepository
from ...services.prediction import PredictionService


router = APIRouter()


@router.get("/{request_id}", response_model=PredictOut)
def get_prediction_status(
    request_id: UUID,
    session: Session = Depends(get_session),
    user: UserDB = Depends(get_current_user),
):
    """Получить статус/результат ML‑запроса по его идентификатору."""

    item = PredictionHistoryRepository().get(session, request_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Request not found")

    if user.role != UserRole.ADMIN and item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Request not found")

    errors = [RowErrorOut(**e) for e in (item.errors or [])]
    rejected = [RejectedRowOut(**e) for e in (getattr(item, "rejected_rows", None) or [])]
    return PredictOut(
        request_id=item.id,
        status=item.status.value,
        charged=item.charged,
        valid_rows=item.valid_rows,
        invalid_rows=item.invalid_rows,
        errors=errors,
        valid_data=getattr(item, "valid_data", None) or [],
        rejected_rows=rejected,
        predictions=item.predictions or [],
        created_at=item.created_at,
    )


@router.post("/", response_model=PredictOut)
def predict(
    payload: PredictIn,
    session: Session = Depends(get_session),
    user: UserDB = Depends(get_current_user),
):
    svc = PredictionService()
    item = svc.enqueue(
        session,
        user=user,
        model_name=payload.model_name,
        model_version=payload.model_version,
        rows=payload.rows,
    )

    errors = [RowErrorOut(**e) for e in (item.errors or [])]
    rejected = [RejectedRowOut(**e) for e in (getattr(item, "rejected_rows", None) or [])]
    return PredictOut(
        request_id=item.id,
        status=item.status.value,
        charged=item.charged,
        valid_rows=item.valid_rows,
        invalid_rows=item.invalid_rows,
        errors=errors,
        valid_data=getattr(item, "valid_data", None) or [],
        rejected_rows=rejected,
        predictions=item.predictions or [],
        created_at=item.created_at,
    )


@router.post("/sync", response_model=PredictOut)
def predict_sync(
    payload: PredictIn,
    session: Session = Depends(get_session),
    user: UserDB = Depends(get_current_user),
):
    """Синхронный предикт

    Нужен для Web UI: сразу возвращает результат, валидацию строк
    и списание кредитов (только за валидные строки)
    """
    svc = PredictionService()
    item = svc.predict(
        session,
        user=user,
        model_name=payload.model_name,
        model_version=payload.model_version,
        rows=payload.rows,
    )

    errors = [RowErrorOut(**e) for e in (item.errors or [])]
    rejected = [RejectedRowOut(**e) for e in (getattr(item, "rejected_rows", None) or [])]
    return PredictOut(
        request_id=item.id,
        status=item.status.value,
        charged=item.charged,
        valid_rows=item.valid_rows,
        invalid_rows=item.invalid_rows,
        errors=errors,
        valid_data=getattr(item, "valid_data", None) or [],
        rejected_rows=rejected,
        predictions=item.predictions or [],
        created_at=item.created_at,
    )


