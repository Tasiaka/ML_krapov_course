from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import HTTPException
from sqlmodel import Session

from ..repositories.billing import BillingRepository


class BalanceService:
    def __init__(self) -> None:
        self._billing = BillingRepository()

    def top_up(self, session: Session, *, user_id, amount: Any):
        """Пополнение баланса

        В реальных запросах `amount` может прийти как Decimal/float/int
        Приводим к Decimal и возвращаем корректную 4xx-ошибку вместо 500
        """
        try:
            amount_dec = amount if isinstance(amount, Decimal) else Decimal(str(amount))
        except (InvalidOperation, ValueError, TypeError):
            raise HTTPException(status_code=400, detail="amount must be a valid number")

        try:
            return self._billing.top_up(session, user_id, amount_dec)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except TypeError:
            raise HTTPException(status_code=400, detail="amount must be a valid number")
        


