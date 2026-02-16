from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, Enum as SAEnum, Index
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from .enums import (
    UserRole,
    TransactionType,
    TransactionStatus,
    PredictionStatus,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserDB(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(index=True, nullable=False, unique=True)
    role: UserRole = Field(
    default=UserRole.USER,
    sa_column=Column(SAEnum(UserRole, name="user_role_enum"), nullable=False),)
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

    __table_args__ = (
    Index("ix_transactions_user_id_created_at", "user_id", "created_at"),
    Index("ix_transactions_tx_type", "tx_type"),
    Index("ix_transactions_status", "status"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)

    amount: Decimal = Field(nullable=False, max_digits=18, decimal_places=2)
    tx_type: TransactionType = Field(
    sa_column=Column(SAEnum(TransactionType, name="transaction_type_enum"), nullable=False),)
    status: TransactionStatus = Field(
        default=TransactionStatus.PENDING,
        sa_column=Column(SAEnum(TransactionStatus, name="transaction_status_enum"), nullable=False),)
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)

    user: Optional[UserDB] = Relationship(back_populates="transactions")




class PredictionHistoryDB(SQLModel, table=True):
    __tablename__ = "prediction_history"

    __table_args__ = (
    Index("ix_prediction_history_user_id_created_at", "user_id", "created_at"),
    Index("ix_prediction_history_status", "status"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    user_id: UUID = Field(foreign_key="users.id", index=True, nullable=False)
    model_id: UUID = Field(foreign_key="ml_models.id", index=True, nullable=False)

    job_id: UUID = Field(index=True, nullable=False)
    upload_id: Optional[UUID] = Field(default=None, nullable=True)

    status: PredictionStatus = Field(
        default=PredictionStatus.QUEUED,
        sa_column=Column(SAEnum(PredictionStatus, name="prediction_status_enum"), nullable=False),
    )
    valid_rows: int = Field(default=0, nullable=False)
    invalid_rows: int = Field(default=0, nullable=False)

    errors: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON().with_variant(JSONB, "postgresql"), nullable=False))
    predictions: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON().with_variant(JSONB, "postgresql"), nullable=False))

    charged: Decimal = Field(default=Decimal("0"), nullable=False, max_digits=18, decimal_places=2)
    created_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)

    user: Optional[UserDB] = Relationship(back_populates="predictions")
    model: Optional[MLModelDB] = Relationship(back_populates="predictions")




