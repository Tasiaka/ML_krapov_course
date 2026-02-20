from __future__ import annotations

import os
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest


try:
    import httpx
except Exception as e:
    raise RuntimeError("httpx is required for e2e tests") from e


DEFAULT_BASE_URL = os.getenv("BASE_URL", "http://localhost")


@dataclass(frozen=True)
class TestUser:
    email: str
    password: str
    token: str


@pytest.fixture(scope="session")
def base_url() -> str:
    return DEFAULT_BASE_URL.rstrip("/")


@pytest.fixture(scope="session")
def client(base_url: str):
    with httpx.Client(base_url=base_url, timeout=10.0, follow_redirects=True) as c:
        yield c


def _wait_for_health(client: "httpx.Client", *, retries: int = 60, sleep_s: float = 1.0) -> None:
    last_err: str | None = None
    for _ in range(retries):
        try:
            r = client.get("/api/health")
            if r.status_code == 200 and r.json().get("status") == "ok":
                return
            last_err = f"status={r.status_code} body={r.text[:200]}"
        except Exception as e:
            last_err = str(e)
        time.sleep(sleep_s)
    raise RuntimeError(f"Service is not healthy: {last_err}")


@pytest.fixture(scope="session", autouse=True)
def wait_for_system(client):
    _wait_for_health(client)


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register_user(client: "httpx.Client", *, email: str, password: str) -> None:
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text


def login_user(client: "httpx.Client", *, email: str, password: str) -> str:
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    token = r.json().get("access_token")
    assert token
    return token


@pytest.fixture()
def user(client) -> TestUser:
    email = f"e2e_{uuid4().hex[:10]}@example.local"
    password = "StrongPass_123"
    register_user(client, email=email, password=password)
    token = login_user(client, email=email, password=password)
    return TestUser(email=email, password=password, token=token)


def get_balance(client: "httpx.Client", *, token: str) -> Decimal:
    r = client.get("/balance/", headers=_auth_headers(token))
    assert r.status_code == 200, r.text
    return Decimal(str(r.json()["balance"]))


def topup(client: "httpx.Client", *, token: str, amount: Decimal) -> Decimal:
    r = client.post("/balance/topup", json={"amount": float(amount)}, headers=_auth_headers(token))
    assert r.status_code == 200, r.text
    return Decimal(str(r.json()["balance"]))


def predict_sync(
    client: "httpx.Client",
    *,
    token: str,
    model_name: str,
    model_version: str,
    rows: list[Any],
):
    r = client.post(
        "/predict/sync",
        json={"model_name": model_name, "model_version": model_version, "rows": rows},
        headers=_auth_headers(token),
    )
    return r


def get_transactions(client: "httpx.Client", *, token: str, limit: int = 50) -> list[dict[str, Any]]:
    r = client.get(f"/history/transactions?limit={limit}", headers=_auth_headers(token))
    assert r.status_code == 200, r.text
    return r.json()


def get_predictions(client: "httpx.Client", *, token: str, limit: int = 50) -> list[dict[str, Any]]:
    r = client.get(f"/history/predictions?limit={limit}", headers=_auth_headers(token))
    assert r.status_code == 200, r.text
    return r.json()



