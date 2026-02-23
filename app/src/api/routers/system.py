from __future__ import annotations

from fastapi import APIRouter

from ...db.session import make_engine, session_scope
from ...rabbitmq.config import get_rabbitmq_dsn


def _check_db() -> tuple[str, str | None]:
    try:
        from sqlalchemy import text

        engine = make_engine(echo=False)
        with session_scope(engine) as s:
            s.exec(text("SELECT 1"))
        return "ok", None
    except Exception as e:
        return "error", str(e)


def _check_rabbitmq() -> tuple[str, str | None]:
    try:
        import pika

        cfg = get_rabbitmq_dsn()
        params = pika.ConnectionParameters(
            host=cfg["host"],
            port=cfg["port"],
            virtual_host=cfg["vhost"],
            credentials=pika.PlainCredentials(username=cfg["user"], password=cfg["password"]),
            heartbeat=30,
            blocked_connection_timeout=2,
            socket_timeout=2,
            connection_attempts=1,
            retry_delay=0,
        )
        conn = pika.BlockingConnection(params)
        conn.close()
        return "ok", None
    except Exception as e:
        return "error", str(e)


router = APIRouter()


@router.get("/", tags=["system"])
def root():
    return {"message": "ML Service API"}


@router.get("/health", tags=["system"])
def health():
    db_status, db_err = _check_db()
    mq_status, mq_err = _check_rabbitmq()

    overall = "ok" if db_status == "ok" and mq_status == "ok" else "degraded"

    payload = {
        "status": overall,
        "database": {"status": db_status, "error": db_err},
        "rabbitmq": {"status": mq_status, "error": mq_err},
    }
    return payload


@router.get("/healthz", include_in_schema=False)
def healthz():
    return health()


