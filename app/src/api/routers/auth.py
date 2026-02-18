from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..deps import get_session, get_token_ttl_minutes
from ..schemas import LoginIn, RegisterIn, TokenOut, UserOut
from ...security.tokens import create_access_token
from ...services.auth import AuthService


router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: RegisterIn, session: Session = Depends(get_session)):
    svc = AuthService()
    user = svc.register(session, email=payload.email, password=payload.password)
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, session: Session = Depends(get_session)):
    svc = AuthService()
    user = svc.authenticate(session, email=payload.email, password=payload.password)
    token = create_access_token(user_id=user.id, email=user.email, ttl_minutes=get_token_ttl_minutes())
    return TokenOut(access_token=token)


