from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..deps import get_current_user, get_session
from ..schemas import PredictIn, PredictOut, RowErrorOut
from ...db.models import UserDB
from ...services.prediction import PredictionService


router = APIRouter()


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
    return PredictOut(
        request_id=item.id,
        status=item.status.value,
        charged=item.charged,
        valid_rows=item.valid_rows,
        invalid_rows=item.invalid_rows,
        errors=errors,
        predictions=item.predictions or [],
        created_at=item.created_at,
    )


