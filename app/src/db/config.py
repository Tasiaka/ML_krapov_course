from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DBConfig:
    database_url: str


def load_db_config() -> DBConfig:
    """
    Для подключения к БД:

    1) DATABASE_URL (если задан)
    2) POSTGRES_* (host/port/user/password/db)

    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return DBConfig(database_url=database_url)

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    db = os.getenv("POSTGRES_DB", "postgres")

    return DBConfig(database_url=f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}")

