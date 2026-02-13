from __future__ import annotations

from sqlmodel import Session, select

from ..db.models import UserDB


class UserRepository:
    def get_by_email(self, session: Session, email: str) -> UserDB | None:
        return session.exec(select(UserDB).where(UserDB.email == email)).first()

    def get(self, session: Session, user_id) -> UserDB | None:
        return session.get(UserDB, user_id)

    def add(self, session: Session, user: UserDB) -> UserDB:
        session.add(user)
        session.flush()
        session.refresh(user)
        return user
