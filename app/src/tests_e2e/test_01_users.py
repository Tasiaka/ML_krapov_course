from __future__ import annotations

from uuid import uuid4

import pytest

from .conftest import login_user, register_user


def _new_email(prefix: str = "user") -> str:
    return f"{prefix}_{uuid4().hex[:10]}@example.local"


def test_register_user_success(client):
    email = _new_email("reg")
    password = "StrongPass_123"
    register_user(client, email=email, password=password)


def test_login_user_success(client):
    email = _new_email("login")
    password = "StrongPass_123"
    register_user(client, email=email, password=password)

    token = login_user(client, email=email, password=password)
    assert isinstance(token, str) and len(token) > 10


def test_relogin_user_success(client):
    email = _new_email("relogin")
    password = "StrongPass_123"
    register_user(client, email=email, password=password)

    token1 = login_user(client, email=email, password=password)
    token2 = login_user(client, email=email, password=password)
    assert isinstance(token1, str) and len(token1) > 10
    assert isinstance(token2, str) and len(token2) > 10


@pytest.mark.parametrize(
    "payload",
    [
{},
{"password": "StrongPass_123"},
{"email": _new_email("missingpw")},
{"email": _new_email("badpw"), "password": "123"},
    ],
)
def test_register_invalid_payload_returns_error(client, payload):
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 422, r.text


@pytest.mark.parametrize(
    "email,password",
    [
        ("no-such-user@example.local", "whatever"),
        (_new_email("never-registered"), "WrongPass_999"),
    ],
)
def test_login_invalid_credentials(client, email: str, password: str):
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 401


def test_register_duplicate_user(client):
    email = _new_email("dup")
    password = "StrongPass_123"

    register_user(client, email=email, password=password)
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 409


