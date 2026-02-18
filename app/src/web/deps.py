from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException
from sqlmodel import Session

from ..api.deps import get_session
from ..db.models import UserDB
from ..repositories.users import UserRepository
from ..security.tokens import TokenError, decode_access_token


def get_current_user_web(
    access_token: str | None = Cookie(default=None),
    session: Session = Depends(get_session),
) -> UserDB:
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = decode_access_token(access_token)
    except TokenError as e:
        raise HTTPException(status_code=401, detail=str(e))

    repo = UserRepository()
    user = repo.get(session, payload.sub)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user



