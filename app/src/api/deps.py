from __future__ import annotations

import os
from typing import Generator

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from ..db.session import make_engine
from ..db.models import UserDB
from ..repositories.users import UserRepository
from ..security.tokens import TokenError, decode_access_token


_engine = make_engine(echo=False)
_bearer = HTTPBearer(auto_error=False)


def get_session() -> Generator[Session, None, None]:
    with Session(_engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: Session = Depends(get_session),
) -> UserDB:
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    try:
        payload = decode_access_token(creds.credentials)
    except TokenError as e:
        raise HTTPException(status_code=401, detail=str(e))

    repo = UserRepository()
    user = repo.get(session, payload.sub)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def get_token_ttl_minutes() -> int:
    try:
        return int(os.getenv("ACCESS_TOKEN_TTL_MINUTES", "60"))
    except ValueError:
        return 60



