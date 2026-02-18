from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from ..deps import get_current_user, get_session
from ..schemas import PredictionHistoryOut, TransactionOut
from ...db.models import UserDB
from ...repositories.history import PredictionHistoryRepository
from ...repositories.transactions import TransactionRepository


router = APIRouter()


@router.get("/predictions", response_model=list[PredictionHistoryOut])
def prediction_history(
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
    user: UserDB = Depends(get_current_user),
):
    repo = PredictionHistoryRepository()
    items = repo.list_by_user(session, user.id, limit=limit)
    return [
        PredictionHistoryOut(
            id=i.id,
            model_id=i.model_id,
            job_id=i.job_id,
            upload_id=i.upload_id,
            status=i.status.value,
            valid_rows=i.valid_rows,
            invalid_rows=i.invalid_rows,
            charged=i.charged,
            created_at=i.created_at,
        )
        for i in items
    ]


@router.get("/transactions", response_model=list[TransactionOut])
def transaction_history(
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
    user: UserDB = Depends(get_current_user),
):
    repo = TransactionRepository()
    items = repo.list_by_user(session, user.id, limit=limit)
    return [
        TransactionOut(
            id=i.id,
            amount=i.amount,
            tx_type=i.tx_type.value,
            status=i.status.value,
            created_at=i.created_at,
        )
        for i in items
    ]


