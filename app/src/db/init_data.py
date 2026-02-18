from __future__ import annotations

from decimal import Decimal

from sqlmodel import Session

from .models import MLModelDB, UserDB
from ..repositories.ml_models import MLModelRepository
from ..repositories.users import UserRepository
from .enums import UserRole



DEMO_ADMIN_EMAIL = "admin@demo.local"
DEMO_USER_EMAIL = "user@demo.local"

DEMO_ADMIN_PASSWORD = "admin"
DEMO_USER_PASSWORD = "user"


def _get_or_create_user(
    session: Session,
    repo: UserRepository,
    *,
    email: str,
    role: str,
    initial_balance: Decimal,
    password_hash: str = "",
) -> UserDB:
    user = repo.get_by_email(session, email=email)
    if user:
        return user

    user = UserDB(email=email, role=role, balance=initial_balance, password_hash=password_hash)
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

    # password_hash заполняем в init_db (через сервис хэширования),
    # но пока кладём сразу
    from ..security.passwords import hash_password

    _get_or_create_user(
        session,
        user_repo,
        email=DEMO_ADMIN_EMAIL,
        role=UserRole.ADMIN,
        initial_balance=Decimal("10000"),
        password_hash=hash_password(DEMO_ADMIN_PASSWORD),
    )
    _get_or_create_user(
        session,
        user_repo,
        email=DEMO_USER_EMAIL,
        role=UserRole.USER,
        initial_balance=Decimal("100"),
        password_hash=hash_password(DEMO_USER_PASSWORD),
    )

    _get_or_create_model(session, model_repo, name="catboost-churn", version="1.0", price_per_row=Decimal("0.10"))
    _get_or_create_model(session, model_repo, name="xgb-fraud", version="1.0", price_per_row=Decimal("0.50"))
    _get_or_create_model(session, model_repo, name="bert-sentiment", version="2.1", price_per_row=Decimal("0.20"))


