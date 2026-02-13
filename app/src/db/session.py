from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine

from .config import load_db_config


def make_engine(*, echo: bool = False):
    cfg = load_db_config()
    return create_engine(cfg.database_url, echo=echo, pool_pre_ping=True)


@contextmanager
def session_scope(engine) -> Iterator[Session]:
    """Единая точка для транзакций"""
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def create_db_and_tables(engine) -> None:
    SQLModel.metadata.create_all(engine)


