from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..deps import get_current_user, get_session
from ..schemas import BalanceOut, TopUpIn
from ...db.models import UserDB
from ...services.balance import BalanceService


router = APIRouter()


@router.get("/", response_model=BalanceOut)
def get_balance(user: UserDB = Depends(get_current_user)):
    return BalanceOut(balance=user.balance)


@router.post("/topup", response_model=BalanceOut)
def top_up(
    payload: TopUpIn,
    session: Session = Depends(get_session),
    user: UserDB = Depends(get_current_user),
):
    if payload.amount is None or payload.amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be > 0")

    svc = BalanceService()
    svc.top_up(session, user_id=user.id, amount=payload.amount)
    session.refresh(user)
    return BalanceOut(balance=user.balance)


