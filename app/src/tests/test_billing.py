from decimal import Decimal

import pytest

from src.db.models import UserDB
from src.repositories.billing import BillingRepository


def test_top_up_and_charge(session):
    user = UserDB(email="anastasia@karpov.ru", role="user", balance=Decimal("0"))
    session.add(user)
    session.commit()
    session.refresh(user)

    billing = BillingRepository()

    billing.top_up(session, user.id, Decimal("100"))
    session.commit()
    session.refresh(user)
    assert user.balance == Decimal("100")

    billing.charge(session, user.id, Decimal("30"))
    session.commit()
    session.refresh(user)
    assert user.balance == Decimal("70")


def test_charge_fail(session):
    user = UserDB(email="anastasia@karpov.ru", role="user", balance=Decimal("10"))
    session.add(user)
    session.commit()
    session.refresh(user)

    billing = BillingRepository()

    with pytest.raises(RuntimeError):
        billing.charge(session, user.id, Decimal("30"))

    session.refresh(user)
    assert user.balance == Decimal("10")


