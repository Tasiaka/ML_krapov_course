from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserDB(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(index=True, nullable=False, unique=True)
    role: str = Field(default="user", nullable=False)
    balance: Decimal = Field(default=Decimal("0"), nullable=False, max_digits=18, decimal_places=2)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)

    transactions: list["TransactionDB"] = Relationship(back_populates="user")
    predictions: list["PredictionHistoryDB"] = Relationship(back_populates="user")


class MLModelDB(SQLModel, table=True):
    __tablename__ = "ml_models"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, nullable=False)
    version: str = Field(index=True, nullable=False)
    price_per_row: Decimal = Field(default=Decimal("1"), nullable=False, max_digits=18, decimal_places=2)
    is_active: bool = Field(default=True, nullable=False)

    predictions: list["PredictionHistoryDB"] = Relationship(back_populates="model")


class TransactionDB(SQLModel, table=True):
    __tablename__ = "transactions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)

    amount: Decimal = Field(nullable=False, max_digits=18, decimal_places=2)
    tx_type: str = Field(nullable=False, index=True)
    status: str = Field(default="pending", nullable=False, index=True)
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)

    user: Optional[UserDB] = Relationship(back_populates="transactions")


class PredictionHistoryDB(SQLModel, table=True):
    __tablename__ = "prediction_history"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    user_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    model_id: UUID = Field(foreign_key="ml_models.id", index=True, nullable=False)

    job_id: UUID = Field(index=True, nullable=False)
    upload_id: Optional[UUID] = Field(default=None, nullable=True)

    status: str = Field(default="queued", nullable=False, index=True)
    valid_rows: int = Field(default=0, nullable=False)
    invalid_rows: int = Field(default=0, nullable=False)

    errors: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON().with_variant(JSONB, "postgresql"), nullable=False))
    predictions: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON().with_variant(JSONB, "postgresql"), nullable=False))

    charged: Decimal = Field(default=Decimal("0"), nullable=False, max_digits=18, decimal_places=2)
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)

    user: Optional[UserDB] = Relationship(back_populates="predictions")
    model: Optional[MLModelDB] = Relationship(back_populates="predictions")


