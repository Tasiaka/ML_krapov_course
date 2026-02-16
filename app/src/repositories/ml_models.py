from __future__ import annotations

from sqlmodel import Session, select

from ..db.models import MLModelDB


class MLModelRepository:
    def get_active(self, session: Session):
        return session.exec(select(MLModelDB).where(MLModelDB.is_active == True)).all()

    def get_by_name_version(self, session: Session, name: str, version: str) -> MLModelDB | None:
        return session.exec(select(MLModelDB).where(MLModelDB.name == name, MLModelDB.version == version)).first()

    def add(self, session: Session, model: MLModelDB) -> MLModelDB:
        session.add(model)
        session.flush()
        session.refresh(model)
        return model


