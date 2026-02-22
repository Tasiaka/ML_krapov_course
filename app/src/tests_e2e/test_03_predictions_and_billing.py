from __future__ import annotations

from decimal import Decimal

import pytest

from .conftest import get_balance, get_predictions, get_transactions, predict_sync, topup


MODEL_NAME = "catboost-churn"
MODEL_VERSION = "1.0"
PRICE_PER_ROW = Decimal("0.10")


def test_predict_sync_success_charges_credits_and_saves_history(user, client):
    topup(client, token=user.token, amount=Decimal("10"))

    before = get_balance(client, token=user.token)
    rows = [{"age": 25, "country": "RU"}, {"age": 40, "country": "NL"}, {"age": 18, "country": "DE"}]

    r = predict_sync(client, token=user.token, model_name=MODEL_NAME, model_version=MODEL_VERSION, rows=rows)
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["status"] == "applied"
    assert payload["valid_rows"] == 3
    assert payload["invalid_rows"] == 0

    expected_charge = PRICE_PER_ROW * Decimal("3")
    assert Decimal(str(payload["charged"])) == expected_charge
    assert len(payload["predictions"]) == 3

    after = get_balance(client, token=user.token)
    assert after == before - expected_charge

    txs = get_transactions(client, token=user.token)
    assert any(t["tx_type"] == "charge" and Decimal(str(t["amount"])) == expected_charge and t["status"] == "applied" for t in txs)

    preds = get_predictions(client, token=user.token)
    assert any(p["status"] == "applied" and Decimal(str(p["charged"])) == expected_charge for p in preds)


def test_predict_sync_no_charge_on_invalid_rows(user, client):
    topup(client, token=user.token, amount=Decimal("10"))
    before = get_balance(client, token=user.token)

    rows = [{}, {}]
    r = predict_sync(client, token=user.token, model_name=MODEL_NAME, model_version=MODEL_VERSION, rows=rows)
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["status"] == "failed"
    assert Decimal(str(payload["charged"])) == Decimal("0")
    assert payload["valid_rows"] == 0
    assert payload["invalid_rows"] > 0
    assert payload["predictions"] == []
    assert payload["errors"], "ожидаем ошибки валидации"

    after = get_balance(client, token=user.token)
    assert after == before

    txs = get_transactions(client, token=user.token)
    assert not any(t["tx_type"] == "charge" and t["status"] == "applied" for t in txs)


def test_predict_sync_not_enough_credits_forbids_charge(user, client):
    topup(client, token=user.token, amount=Decimal("0.05"))
    before = get_balance(client, token=user.token)

    rows = [{"a": 1}]
    r = predict_sync(client, token=user.token, model_name=MODEL_NAME, model_version=MODEL_VERSION, rows=rows)
    assert r.status_code == 402

    after = get_balance(client, token=user.token)
    assert after == before

    txs = get_transactions(client, token=user.token)
    assert any(t["tx_type"] == "charge" and t["status"] == "rejected" for t in txs)


def test_predict_sync_unknown_model_returns_404(user, client):
    topup(client, token=user.token, amount=Decimal("10"))
    r = predict_sync(client, token=user.token, model_name="unknown", model_version="9.9", rows=[{"a": 1}])
    assert r.status_code == 404




