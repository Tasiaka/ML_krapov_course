from decimal import Decimal

from src.tests_e2e.conftest import get_balance, get_transactions, predict_sync, topup


MODEL_NAME = "catboost-churn"
MODEL_VERSION = "1.0"


def test_rejected_charge_is_saved_when_not_enough_credits(client, user):
    """
    При недостаточном балансе:
    - /predict должен вернуть 402
    - баланс не изменяется
    - в истории транзакций должна появиться charge со статусом rejected
    """
    topup(client, token=user.token, amount=Decimal("0.01"))
    before = get_balance(client, token=user.token)

    rows = [{"a": 1}]
    r = predict_sync(
        client,
        token=user.token,
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        rows=rows,
    )
    assert r.status_code == 402, r.text

    after = get_balance(client, token=user.token)
    assert after == before

    txs = get_transactions(client, token=user.token)
    assert any(
        t.get("tx_type") == "charge" and t.get("status") == "rejected"
        for t in txs
    ), txs



