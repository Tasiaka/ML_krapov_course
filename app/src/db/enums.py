from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class TransactionType(str, Enum):
    TOP_UP = "top_up"
    CHARGE = "charge"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    APPLIED = "applied"
    REJECTED = "rejected"


class PredictionStatus(str, Enum):
    QUEUED = "queued"
    APPLIED = "applied"
    FAILED = "failed"
