def test_token_can_be_reused_multiple_times(client, user):
    """
    Повторное использование токена:
    - несколько запросов подряд с одним и тем же Bearer token
    """
    headers = {"Authorization": f"Bearer {user.token}"}

    r1 = client.get("/balance", headers=headers)
    assert r1.status_code == 200, r1.text

    r2 = client.get("/history/transactions", headers=headers)
    assert r2.status_code == 200, r2.text

    r3 = client.get("/history/predictions", headers=headers)
    assert r3.status_code == 200, r3.text


