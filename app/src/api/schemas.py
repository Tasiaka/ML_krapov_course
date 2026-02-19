from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: str
    balance: Decimal
    created_at: datetime



class RegisterIn(BaseModel):
    email: str
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class BalanceOut(BaseModel):
    balance: Decimal


class TopUpIn(BaseModel):
    amount: Decimal = Field(gt=0)


class TransactionOut(BaseModel):
    id: UUID
    amount: Decimal
    tx_type: str
    status: str
    created_at: datetime


class PredictIn(BaseModel):
    model_name: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    rows: list[dict[str, Any]] = Field(min_length=1)


class RowErrorOut(BaseModel):
    row_index: int
    field: str
    message: str


class RejectedRowOut(BaseModel):
    row_index: int
    row: Any
    field: str
    message: str


class PredictOut(BaseModel):
    request_id: UUID
    status: str
    charged: Decimal
    valid_rows: int
    invalid_rows: int
    errors: list[RowErrorOut]
    valid_data: list[dict[str, Any]] = []
    rejected_rows: list[RejectedRowOut] = []
    predictions: list[dict[str, Any]]
    created_at: datetime


class PredictionHistoryOut(BaseModel):
    id: UUID
    model_id: UUID
    job_id: UUID
    upload_id: UUID | None
    status: str
    valid_rows: int
    invalid_rows: int
    charged: Decimal
    created_at: datetime



