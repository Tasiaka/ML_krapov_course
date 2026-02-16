from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from ..fundament import Credits, Role, User, Wallet, MLModel, Transaction, TxStatus, TxType, PredictionHistory, JobStatus, RowError
from ..db.models import UserDB, MLModelDB, TransactionDB, PredictionHistoryDB


def userdb_to_domain(u: UserDB) -> User:
    user = User(id=u.id, email=u.email, role=Role(u.role))
    user.wallet.top_up(Credits(Decimal(u.balance)))
    return user


def apply_domain_user_to_userdb(domain: User, db: UserDB) -> None:
    db.email = domain.email
    db.role = domain.role.value
    db.balance = domain.wallet.balance.amount


def mldb_to_domain(m: MLModelDB) -> MLModel:
    return MLModel(id=m.id, name=m.name, version=m.version, price_per_row=Credits(Decimal(m.price_per_row)), is_active=m.is_active)


def txdb_to_domain(t: TransactionDB) -> Transaction:
    return Transaction(
        id=t.id,
        user_id=t.user_id,
        amount=Credits(Decimal(t.amount)),
        tx_type=TxType(t.tx_type),
        status=TxStatus(t.status),
        created_at=t.created_at,
    )


def historydb_to_domain(h: PredictionHistoryDB) -> PredictionHistory:
    errors = [RowError(**e) for e in (h.errors or [])]
    return PredictionHistory(
        id=h.id,
        user_id=h.user_id,
        model_id=h.model_id,
        job_id=h.job_id,
        upload_id=h.upload_id,
        status=JobStatus(h.status),
        valid_rows=h.valid_rows,
        invalid_rows=h.invalid_rows,
        errors=errors,
        predictions=h.predictions or [],
        charged=Credits(Decimal(h.charged)),
        created_at=h.created_at,
    )


def history_domain_to_db(domain: PredictionHistory, db: PredictionHistoryDB) -> None:
    db.user_id = domain.user_id
    db.model_id = domain.model_id
    db.job_id = domain.job_id
    db.upload_id = domain.upload_id
    db.status = domain.status.value
    db.valid_rows = domain.valid_rows
    db.invalid_rows = domain.invalid_rows
    db.errors = [e.__dict__ for e in domain.errors]
    db.predictions = domain.predictions
    db.charged = domain.charged.amount


