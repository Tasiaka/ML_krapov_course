import pytest
from sqlmodel import Session, SQLModel, create_engine

from src.db.models import UserDB, MLModelDB


@pytest.fixture()
def engine():
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture()
def session(engine):
    with Session(engine) as session:
        yield session


