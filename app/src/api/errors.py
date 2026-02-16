from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _error(code: str, message: str, *, details=None) -> dict:
    payload = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    return payload


def setup_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exc_handler(_: Request, exc: HTTPException):
        code = "http_error"
        if exc.status_code == 401:
            code = "unauthorized"
        elif exc.status_code == 403:
            code = "forbidden"
        elif exc.status_code == 404:
            code = "not_found"
        elif 400 <= exc.status_code < 500:
            code = "bad_request"
        return JSONResponse(status_code=exc.status_code, content=_error(code, str(exc.detail)))

    @app.exception_handler(RequestValidationError)
    async def validation_exc_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=_error("validation_error", "Invalid request", details=exc.errors()),
        )

    @app.exception_handler(Exception)
    async def unhandled_exc_handler(_: Request, exc: Exception):
        return JSONResponse(status_code=500, content=_error("internal_error", "Internal server error"))


