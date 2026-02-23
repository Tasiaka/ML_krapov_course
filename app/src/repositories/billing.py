from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlmodel import Session, select

from ..db.models import TransactionDB, UserDB
from ..db.enums import TransactionType, TransactionStatus
from ..common import metrics



class BillingRepository:
    def _dialect(self, session: Session) -> str:
        bind = session.get_bind()
        return getattr(getattr(bind, "dialect", None), "name", "") if bind is not None else ""

    def top_up(self, session: Session, user_id: UUID, amount: Decimal) -> TransactionDB:
        if amount <= 0:
            raise ValueError("amount must be > 0")

        stmt = select(UserDB).where(UserDB.id == user_id)
        if self._dialect(session) == "postgresql":
            stmt = stmt.with_for_update()

        user = session.exec(stmt).one()

        tx = TransactionDB(user_id=user_id, amount=amount, tx_type=TransactionType.TOP_UP, status=TransactionStatus.APPLIED)
        user.balance = Decimal(user.balance) + amount

        session.add(tx)
        session.add(user)
        session.flush()
        session.refresh(tx)
        metrics.BILLING_TOPUPS_TOTAL.inc()
        metrics.REVENUE_TOTAL.inc(float(amount))
        return tx

    def charge(self, session: Session, user_id: UUID, amount: Decimal) -> TransactionDB:
        if amount <= 0:
            raise ValueError("amount must be > 0")

        stmt = select(UserDB).where(UserDB.id == user_id)
        if self._dialect(session) == "postgresql":
            stmt = stmt.with_for_update()

        user = session.exec(stmt).one()

        if Decimal(user.balance) < amount:
            tx = TransactionDB(user_id=user_id, amount=amount, tx_type=TransactionType.CHARGE, status=TransactionStatus.REJECTED)
            session.add(tx)
            session.flush()
            session.refresh(tx)
            metrics.BILLING_CHARGES_TOTAL.labels(result="rejected").inc()
            raise RuntimeError("not enough credits")

        tx = TransactionDB(user_id=user_id, amount=amount, tx_type=TransactionType.CHARGE, status=TransactionStatus.APPLIED)
        user.balance = Decimal(user.balance) - amount

        session.add(tx)
        session.add(user)
        session.flush()
        session.refresh(tx)
        metrics.BILLING_CHARGES_TOTAL.labels(result="applied").inc()
        return tx


