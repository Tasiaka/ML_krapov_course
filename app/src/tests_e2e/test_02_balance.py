from __future__ import annotations

from decimal import Decimal

import pytest

from .conftest import get_balance, get_transactions, topup


def test_balance_get_and_topup(user, client):
    start = get_balance(client, token=user.token)
    assert start >= 0

    new_balance = topup(client, token=user.token, amount=Decimal("25"))
    assert new_balance == start + Decimal("25")

    txs = get_transactions(client, token=user.token)
    assert any(t["tx_type"] == "top_up" and Decimal(str(t["amount"])) == Decimal("25") for t in txs)


@pytest.mark.parametrize("amount", [Decimal("0"), Decimal("-10")])
def test_topup_validation(user, client, amount: Decimal):
    r = client.post(
        "/balance/topup",
        json={"amount": float(amount)},
        headers={"Authorization": f"Bearer {user.token}"},
    )
    assert r.status_code == 400



