from __future__ import annotations

from decimal import Decimal

from sqlmodel import Session

from .models import MLModelDB, UserDB
from ..repositories.ml_models import MLModelRepository
from ..repositories.users import UserRepository


DEMO_ADMIN_EMAIL = "admin@demo.local"
DEMO_USER_EMAIL = "user@demo.local"


def _get_or_create_user(session: Session, repo: UserRepository, *, email: str, role: str, initial_balance: Decimal) -> UserDB:
    user = repo.get_by_email(session, email=email)
    if user:
        return user

    user = UserDB(email=email, role=role, balance=initial_balance)
    return repo.add(session, user)


def _get_or_create_model(session: Session, repo: MLModelRepository, *, name: str, version: str, price_per_row: Decimal, is_active: bool = True) -> MLModelDB:
    model = repo.get_by_name_version(session, name=name, version=version)
    if model:
        return model

    model = MLModelDB(name=name, version=version, price_per_row=price_per_row, is_active=is_active)
    return repo.add(session, model)


def init_demo_data(session: Session) -> None:
    user_repo = UserRepository()
    model_repo = MLModelRepository()

    _get_or_create_user(session, user_repo, email=DEMO_ADMIN_EMAIL, role="admin", initial_balance=Decimal("10000"))
    _get_or_create_user(session, user_repo, email=DEMO_USER_EMAIL, role="user", initial_balance=Decimal("100"))

    _get_or_create_model(session, model_repo, name="catboost-churn", version="1.0", price_per_row=Decimal("0.10"))
    _get_or_create_model(session, model_repo, name="xgb-fraud", version="1.0", price_per_row=Decimal("0.50"))
    _get_or_create_model(session, model_repo, name="bert-sentiment", version="2.1", price_per_row=Decimal("0.20"))


