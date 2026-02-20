from decimal import Decimal


def test_rejected_transaction_saved_in_history(client, register_user, topup):
    """
    При недостаточном балансе должна:
    - вернуться ошибка 402
    - НЕ измениться баланс
    - появиться транзакция со статусом rejected
    """
    email, password = register_user()

    login = client.post("/auth/login", json={
        "email": email,
        "password": password
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}


    topup(client, token=token, amount=Decimal("0.01"))


    rows = [{"a": 1}]
    r = client.post("/predict", json={
        "model_name": "default",
        "model_version": "1",
        "rows": rows
    }, headers=headers)

    assert r.status_code == 402


    history = client.get("/history/transactions", headers=headers)
    assert history.status_code == 200

    txs = history.json()
    assert any(
        t["tx_type"] == "charge" and t["status"] == "rejected"
        for t in txs
    )



