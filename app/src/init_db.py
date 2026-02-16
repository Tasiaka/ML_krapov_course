from __future__ import annotations

from src.db.session import create_db_and_tables, make_engine, session_scope
from src.db.init_data import init_demo_data


def main() -> None:
    engine = make_engine(echo=False)
    create_db_and_tables(engine)
    with session_scope(engine) as session:
        init_demo_data(session)
    print("DB initialized")


if __name__ == "__main__":
    main()


