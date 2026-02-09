from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional, Sequence
from uuid import UUID, uuid4
from datetime import datetime, timezone
from decimal import Decimal


# -----------------------
#  хелперы
# -----------------------

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# -----------------------
# статусы/роли
# -----------------------

class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"


class JobStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    OK = "ok"
    PARTIAL_OK = "partial_ok"
    FAILED = "failed"


class TxType(str, Enum):
    TOP_UP = "top_up"
    CHARGE = "charge"


class TxStatus(str, Enum):
    PENDING = "pending"
    APPLIED = "applied"
    REJECTED = "rejected"


# -----------------------
# ошибки
# -----------------------

class DomainError(Exception):
    pass


class NotEnoughCredits(DomainError):
    pass


class Forbidden(DomainError):
    pass


@dataclass(frozen=True)
class RowError:
    """Ошибка валидации на одной строке"""
    row_index: int
    field: str
    message: str


# -----------------------
# основной каркас
# -----------------------

@dataclass(frozen=True)
class Credits:
    """Кредиты (условная валюта)."""
    amount: Decimal

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("credits must be >= 0")


@dataclass
class Wallet:
    """
    Кошелёк. Баланс нельзя менять напрямую
    Только через методы top_up / charge.
    """
    __balance: Credits = field(default_factory=lambda: Credits(Decimal("0")))

    @property
    def balance(self) -> Credits:
        return self.__balance

    def top_up(self, amount: Credits) -> None:
        self.__balance = Credits(self.__balance.amount + amount.amount)

    def charge(self, amount: Credits) -> None:
        if self.__balance.amount < amount.amount:
            raise NotEnoughCredits("not enough credits")
        self.__balance = Credits(self.__balance.amount - amount.amount)


@dataclass
class User:
    id: UUID
    email: str
    role: Role = Role.USER
    wallet: Wallet = field(default_factory=Wallet)
    created_at: datetime = field(default_factory=utc_now)

    def is_admin(self) -> bool:
        return self.role == Role.ADMIN


@dataclass
class MLModel:
    """ML модель"""
    id: UUID
    name: str
    version: str
    price_per_row: Credits
    is_active: bool = True

    def calc_cost(self, rows_count: int) -> Credits:
        """Цена = цена за строку * количество строк"""
        return Credits(self.price_per_row.amount * Decimal(rows_count))


# -----------------------
# транзакции
# -----------------------

@dataclass
class Transaction:
    """
    Транзакция пополнения или списания.
    Применяется billing-сервисом (не самим объектом).
    """
    id: UUID
    user_id: UUID
    amount: Credits
    tx_type: TxType
    status: TxStatus = TxStatus.PENDING
    created_at: datetime = field(default_factory=utc_now)

    def mark_applied(self) -> None:
        self.status = TxStatus.APPLIED

    def mark_rejected(self) -> None:
        self.status = TxStatus.REJECTED


# ---------------------
# события с моделью
# ---------------------

@dataclass
class Upload:
    id: UUID
    user_id: UUID
    filename: str
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class MLJob:
    """
    ML задача (потом в RabbitMQ)
    payload: сюда пока кидаем строки
    """
    id: UUID
    user_id: UUID
    model_id: UUID
    upload_id: Optional[UUID]
    payload: dict[str, Any]

    status: JobStatus = JobStatus.CREATED
    created_at: datetime = field(default_factory=utc_now)

    def to_queue(self) -> None:
        self.status = JobStatus.QUEUED

    def start(self) -> None:
        self.status = JobStatus.RUNNING

    def finish(self, status: JobStatus) -> None:
        self.status = status


@dataclass
class PredictionHistory:
    """
    История предсказаний для личного кабинета:
    - ошибки валидации показываем пользователю
    - предикты только по валидным строкам
    - charged — сколько списали
    """
    id: UUID
    user_id: UUID
    model_id: UUID
    job_id: UUID
    upload_id: Optional[UUID]

    status: JobStatus = JobStatus.QUEUED
    valid_rows: int = 0
    invalid_rows: int = 0
    errors: list[RowError] = field(default_factory=list)
    predictions: list[dict[str, Any]] = field(default_factory=list)
    charged: Credits = field(default_factory=lambda: Credits(Decimal("0")))
    created_at: datetime = field(default_factory=utc_now)


@dataclass
class ValidationReport:
    valid_rows: list[Mapping[str, Any]]
    errors: list[RowError]


# -----------------------------
# сервисы / наброски логики
# -----------------------------

class BillingService:
    """
    Пополнение и списание:
    - создаём Transaction
    - применяем к кошельку
    - выставляем статус
    """

    def create_top_up_request(self, user: User, amount: Credits) -> Transaction:
        return Transaction(
            id=uuid4(),
            user_id=user.id,
            amount=amount,
            tx_type=TxType.TOP_UP,
            status=TxStatus.PENDING,
        )

    def approve_top_up(self, admin: User, tx: Transaction, user: User) -> None:
        if not admin.is_admin():
            raise Forbidden("admin only")

        # идемпотентность
        if tx.status != TxStatus.PENDING:
            return

        if tx.tx_type != TxType.TOP_UP:
            raise DomainError("wrong tx type for approve_top_up")

        user.wallet.top_up(tx.amount)
        tx.mark_applied()

    def charge_user(self, user: User, amount: Credits) -> Transaction:
        tx = Transaction(
            id=uuid4(),
            user_id=user.id,
            amount=amount,
            tx_type=TxType.CHARGE,
            status=TxStatus.PENDING,
        )

        user.wallet.charge(amount)  # может бросить NotEnoughCredits
        tx.mark_applied()
        return tx


class MLFlowService:
    """
    Основная логика:
    - submit: проверка модели и баланса, создание job и history
    - finalize: записать ошибки/предикты и списать деньги только если valid_rows > 0
    """

    def submit(
        self,
        user: User,
        model: MLModel,
        rows: Sequence[Mapping[str, Any]],
        upload: Optional[Upload],
    ) -> tuple[MLJob, PredictionHistory]:
        if not model.is_active:
            raise DomainError("model disabled")

        estimated = model.calc_cost(len(rows))
        if user.wallet.balance.amount < estimated.amount:
            raise NotEnoughCredits("need enough balance for estimated cost")

        job = MLJob(
            id=uuid4(),
            user_id=user.id,
            model_id=model.id,
            upload_id=upload.id if upload else None,
            payload={"rows": list(rows)},
        )
        job.to_queue()

        history = PredictionHistory(
            id=uuid4(),
            user_id=user.id,
            model_id=model.id,
            job_id=job.id,
            upload_id=job.upload_id,
            status=JobStatus.QUEUED,
        )
        return job, history

    def finalize(
        self,
        user: User,
        model: MLModel,
        history: PredictionHistory,
        report: ValidationReport,
        predictions: list[dict[str, Any]],
        billing: BillingService,
    ) -> PredictionHistory:
        history.valid_rows = len(report.valid_rows)
        history.invalid_rows = len(report.errors)
        history.errors = report.errors
        history.predictions = predictions

        if history.valid_rows > 0:
            history.status = JobStatus.PARTIAL_OK if history.invalid_rows > 0 else JobStatus.OK
            cost = model.calc_cost(history.valid_rows)

            billing.charge_user(user, cost)  # если не хватит — упадёт исключением
            history.charged = cost
        else:
            history.status = JobStatus.FAILED
            history.charged = Credits(Decimal("0"))

        return history


