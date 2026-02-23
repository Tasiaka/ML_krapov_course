from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..common import metrics
from ..common.logging import setup_logging
from ..web.router import router as web_router
from .errors import setup_exception_handlers
from .routers.auth import router as auth_router
from .routers.balance import router as balance_router
from .routers.history import router as history_router
from .routers.predict import router as predict_router
from .routers.system import router as system_router
from .routers.users import router as users_router


setup_logging("api")
logger = logging.getLogger("api")


def _init_db_on_startup() -> None:
    """Ensure DB schema + demo data exist.

    Делает запуск через docker-compose полностью воспроизводимым: достаточно
    `docker compose up`, без ручного шага `python -m src.main init-db`.
    """

    from ..db.session import create_db_and_tables, make_engine, session_scope
    from ..db.init_data import init_demo_data

    engine = make_engine(echo=False)
    create_db_and_tables(engine)
    with session_scope(engine) as session:
        init_demo_data(session)


def create_app() -> FastAPI:
    app = FastAPI(title="ML Service API", version="0.1.0")

    @app.middleware("http")
    async def _metrics_and_logging(request: Request, call_next):
        start = time.perf_counter()
        route = request.scope.get("route")
        path_tmpl = getattr(route, "path", request.url.path)

        try:
            response = await call_next(request)
        except Exception as e:
            metrics.APP_ERRORS_TOTAL.labels(kind=type(e).__name__).inc()
            logger.exception("Unhandled error on %s %s", request.method, path_tmpl)
            raise

        elapsed = time.perf_counter() - start
        metrics.HTTP_REQUESTS_TOTAL.labels(request.method, path_tmpl, str(response.status_code)).inc()
        metrics.HTTP_REQUEST_DURATION_SECONDS.labels(request.method, path_tmpl).observe(elapsed)

        if response.status_code >= 500:
            metrics.APP_ERRORS_TOTAL.labels(kind=f"http_{response.status_code}").inc()

        logger.info("%s %s -> %s (%.3fs)", request.method, path_tmpl, response.status_code, elapsed)
        return response

    @app.get("/metrics", include_in_schema=False)
    def internal_metrics():
        """In-process metrics in JSON.

        Используем вместо Prometheus/Grafana (если их невозможно поднять локально).
        """

        return JSONResponse(content=metrics.snapshot())

    setup_exception_handlers(app)

    app.include_router(system_router, prefix="/api")
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(users_router, prefix="/users", tags=["users"])
    app.include_router(balance_router, prefix="/balance", tags=["balance"])
    app.include_router(predict_router, prefix="/predict", tags=["predict"])
    app.include_router(history_router, prefix="/history", tags=["history"])

    # Web UI
    app.include_router(web_router)

    @app.on_event("startup")
    def _startup() -> None:
        _init_db_on_startup()

    return app


app = create_app()
