from __future__ import annotations

from decimal import Decimal

from .conftest import get_balance, get_transactions, predict_sync, topup


MODEL_NAME = "catboost-churn"
MODEL_VERSION = "1.0"


def test_transactions_include_topup_and_charge_after_success_predict(user, client):
    topup(client, token=user.token, amount=Decimal("5"))
    before = get_balance(client, token=user.token)

    r = predict_sync(
        client,
        token=user.token,
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        rows=[{"age": 30, "country": "RU"}],
    )
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["status"] == "applied"
    charged = Decimal(str(payload["charged"]))
    assert charged > 0

    after = get_balance(client, token=user.token)
    assert after == before - charged

    txs = get_transactions(client, token=user.token)
    assert any(t["tx_type"] == "top_up" for t in txs)
    assert any(t["tx_type"] == "charge" and t["status"] == "applied" for t in txs)


def test_unknown_model_does_not_charge_and_does_not_write_applied_charge(user, client):
    topup(client, token=user.token, amount=Decimal("5"))
    before = get_balance(client, token=user.token)

    r = predict_sync(client, token=user.token, model_name="unknown", model_version="9.9", rows=[{"a": 1}])
    assert r.status_code == 404

    after = get_balance(client, token=user.token)
    assert after == before

    txs = get_transactions(client, token=user.token)
    assert not any(t["tx_type"] == "charge" and t["status"] == "applied" for t in txs)



