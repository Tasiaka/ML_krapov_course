from __future__ import annotations

from decimal import Decimal

import pytest

from .conftest import get_balance


@pytest.mark.parametrize("amount", [0, -1, -10])
def test_topup_invalid_amount_does_not_change_balance(user, client, amount):
    before = get_balance(client, token=user.token)
    r = client.post(
        "/balance/topup",
        json={"amount": float(amount)},
        headers={"Authorization": f"Bearer {user.token}"},
    )
    assert r.status_code == 400, r.text
    after = get_balance(client, token=user.token)
    assert after == before



