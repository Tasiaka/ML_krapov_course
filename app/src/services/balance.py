from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException
from sqlmodel import Session

from ..repositories.billing import BillingRepository


class BalanceService:
    def __init__(self) -> None:
        self._billing = BillingRepository()

    def top_up(self, session: Session, *, user_id, amount: Decimal):
        try:
            return self._billing.top_up(session, user_id, amount)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))


