from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select, col

from ..db.models import PredictionHistoryDB


class PredictionHistoryRepository:
    def add(self, session: Session, item: PredictionHistoryDB) -> PredictionHistoryDB:
        session.add(item)
        session.flush()
        session.refresh(item)
        return item

    def list_by_user(self, session: Session, user_id: UUID, limit: int = 50) -> list[PredictionHistoryDB]:
        stmt = (
            select(PredictionHistoryDB)
            .where(PredictionHistoryDB.user_id == user_id)
            .order_by(col(PredictionHistoryDB.created_at).desc())
            .limit(limit)
        )
        return session.exec(stmt).all()

    def get(self, session: Session, item_id: UUID) -> PredictionHistoryDB | None:
        return session.get(PredictionHistoryDB, item_id)

    def save(self, session: Session, item: PredictionHistoryDB) -> PredictionHistoryDB:
        """Сохранить изменения (для воркера)"""
        session.add(item)
        session.flush()
        session.refresh(item)
        return item



