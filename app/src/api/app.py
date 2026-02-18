from __future__ import annotations

from fastapi import FastAPI

from .errors import setup_exception_handlers
from .routers.auth import router as auth_router
from .routers.balance import router as balance_router
from .routers.history import router as history_router
from .routers.predict import router as predict_router
from .routers.system import router as system_router
from .routers.users import router as users_router
from ..web.router import router as web_router


def create_app() -> FastAPI:
    app = FastAPI(title="ML Service API", version="0.1.0")

    setup_exception_handlers(app)

    app.include_router(system_router)
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(users_router, prefix="/users", tags=["users"])
    app.include_router(balance_router, prefix="/balance", tags=["balance"])
    app.include_router(predict_router, prefix="/predict", tags=["predict"])
    app.include_router(history_router, prefix="/history", tags=["history"])

    # Web UI
    app.include_router(web_router)

    return app


app = create_app()


