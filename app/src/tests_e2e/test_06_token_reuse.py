def test_token_can_be_reused_multiple_times(client, register_user):
    """
    Один и тот же токен можно использовать
    для нескольких запросов подряд.
    """
    email, password = register_user()

    login = client.post("/auth/login", json={
        "email": email,
        "password": password
    })
    token = login.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}

    r1 = client.get("/balance", headers=headers)
    r2 = client.get("/history/transactions", headers=headers)

    assert r1.status_code == 200
    assert r2.status_code == 200



