from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DBConfig:
    database_url: str


def load_db_config() -> DBConfig:
    """
    Если DATABASE_URL нет, то URL берется из DB_* переменных (удобно для docker-compose).
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return DBConfig(database_url=database_url)


    # Fallback для переменных из docker-compose (.env.example часто содержит POSTGRES_*).
    if not os.getenv("DB_HOST") and os.getenv("POSTGRES_HOST"):
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        db = os.getenv("POSTGRES_DB", "postgres")
        return DBConfig(database_url=f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}")

    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASS", "postgres")
    db = os.getenv("DB_NAME", "postgres")

    return DBConfig(database_url=f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}")

