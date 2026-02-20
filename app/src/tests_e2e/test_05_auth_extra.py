from decimal import Decimal
import pytest


def test_repeat_authorization_returns_new_token(client, register_user):
    """
    Повторная авторизация должна быть успешной
    и возвращать валидный access token
    """
    email, password = register_user()


    r1 = client.post("/auth/login", json={
        "email": email,
        "password": password
    })
    assert r1.status_code == 200
    token1 = r1.json()["access_token"]


    r2 = client.post("/auth/login", json={
        "email": email,
        "password": password
    })
    assert r2.status_code == 200
    token2 = r2.json()["access_token"]

    assert token1 is not None
    assert token2 is not None



