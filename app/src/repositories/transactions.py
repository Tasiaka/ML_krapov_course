from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select, col

from ..db.models import TransactionDB


class TransactionRepository:
    def list_by_user(self, session: Session, user_id: UUID, limit: int = 50) -> list[TransactionDB]:
        stmt = (
            select(TransactionDB)
            .where(TransactionDB.user_id == user_id)
            .order_by(col(TransactionDB.created_at).desc())
            .limit(limit)
        )
        return session.exec(stmt).all()

