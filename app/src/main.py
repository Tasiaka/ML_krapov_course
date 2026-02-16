from __future__ import annotations

import argparse

from sqlmodel import select

from src.db.models import MLModelDB, UserDB
from src.db.session import make_engine, session_scope
from src.init_db import main as init_db_main


def cmd_init_db() -> None:
    init_db_main()


def cmd_show_demo() -> None:
    engine = make_engine(echo=False)
    with session_scope(engine) as s:
        users = s.exec(select(UserDB).order_by(UserDB.email)).all()
        print("Users:")
        for u in users:
            print(f" - {u.email} (role={u.role}, balance={u.balance})")

        models = s.exec(select(MLModelDB).order_by(MLModelDB.name, MLModelDB.version)).all()
        print("ML models:")
        for m in models:
            print(f" - {m.name}:{m.version} price={m.price_per_row} active={m.is_active}")


def cmd_run_api() -> None:
    import uvicorn

    uvicorn.run("src.api.app:app", host="0.0.0.0", port=8000, reload=True)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ml-service", description="Local entrypoint for the ML service project")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init-db", help="Create DB tables and load demo data.").set_defaults(func=lambda _: cmd_init_db())
    sub.add_parser("show-demo", help="Print demo users and ML models.").set_defaults(func=lambda _: cmd_show_demo())
    sub.add_parser("run-api", help="Run FastAPI app (dev mode). ").set_defaults(func=lambda _: cmd_run_api())
    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()


