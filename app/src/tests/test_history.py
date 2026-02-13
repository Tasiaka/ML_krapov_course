from decimal import Decimal
from uuid import uuid4

from src.db.models import MLModelDB, PredictionHistoryDB, UserDB
from src.repositories.history import PredictionHistoryRepository


def test_prediction_history_list(session):
    user = UserDB(email="anastasia@karpov.ru", role="user", balance=Decimal("0"))
    model = MLModelDB(name="m", version="1", price_per_row=Decimal("1.0"), is_active=True)
    session.add(user)
    session.add(model)
    session.commit()
    session.refresh(user)
    session.refresh(model)

    repo = PredictionHistoryRepository()

    h1 = PredictionHistoryDB(user_id=user.id, model_id=model.id, job_id=uuid4(), status="ok", valid_rows=1, invalid_rows=0, charged=Decimal("1"))
    h2 = PredictionHistoryDB(user_id=user.id, model_id=model.id, job_id=uuid4(), status="failed", valid_rows=0, invalid_rows=2, charged=Decimal("0"))
    repo.add(session, h1)
    repo.add(session, h2)
    session.commit()

    items = repo.list_by_user(session, user.id)
    assert len(items) == 2
    assert items[0].created_at >= items[1].created_at


