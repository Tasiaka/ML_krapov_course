from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import Session
from sqlmodel import select

from ..db.models import UserDB
from ..db.enums import UserRole
from ..repositories.users import UserRepository
from ..security.passwords import hash_password, verify_password


class AuthService:
    def __init__(self) -> None:
        self._users = UserRepository()

    def register(self, session: Session, *, email: str, password: str) -> UserDB:
        existing = self._users.get_by_email(session, email=email)
        if existing is not None:
            raise HTTPException(status_code=409, detail="User already exists")

        user = UserDB(email=email, role=UserRole.USER, password_hash=hash_password(password))
        return self._users.add(session, user)

    def authenticate(self, session: Session, *, email: str, password: str) -> UserDB:
        user = self._users.get_by_email(session, email=email)
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        return user

    def get_user_by_email(self, session: Session, *, email: str) -> UserDB | None:
        return self._users.get_by_email(session, email=email)

    def list_users(self, session: Session, *, limit: int = 200) -> list[UserDB]:
        stmt = select(UserDB).order_by(UserDB.created_at.desc()).limit(limit)
        return list(session.exec(stmt).all())



