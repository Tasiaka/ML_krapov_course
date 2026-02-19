from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlmodel import Session

from ..api.deps import get_session
from fastapi import HTTPException
from ..db.enums import UserRole
from ..db.models import UserDB
from ..repositories.ml_models import MLModelRepository
from ..repositories.transactions import TransactionRepository
from ..repositories.history import PredictionHistoryRepository
from ..security.tokens import create_access_token
from ..services.auth import AuthService
from ..services.balance import BalanceService
from ..services.prediction import PredictionService
from .deps import get_current_user_web, get_optional_user_web


router = APIRouter(include_in_schema=False)


_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_jinja = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def _render(request: Request, name: str, **ctx: Any) -> HTMLResponse:
    tpl = _jinja.get_template(name)
    html = tpl.render(request=request, **ctx)
    return HTMLResponse(html)


def _redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url=url, status_code=303)


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    user: UserDB | None = Depends(get_optional_user_web),
):
    return _render(request, "index.html", user=user)


@router.get("/register", response_class=HTMLResponse)
def register_page(
    request: Request,
    user: UserDB | None = Depends(get_optional_user_web),
):
    return _render(request, "register.html", user=user, error=None)


@router.post("/register")
def register_action(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    try:
        svc = AuthService()
        svc.register(session, email=email, password=password)
    except HTTPException as e:
        return _render(request, "register.html", user=None, error=str(e.detail))
    except Exception as e:
        return _render(request, "register.html", user=None, error=str(e))

    return _redirect("/login?registered=1")


@router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    registered: int | None = None,
    user: UserDB | None = Depends(get_optional_user_web),
):
    return _render(request, "login.html", user=user, error=None, registered=bool(registered))


@router.post("/login")
def login_action(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_session),
):
    try:
        svc = AuthService()
        user = svc.authenticate(session, email=email, password=password)
    except HTTPException as e:
        return _render(request, "login.html", user=None, error=str(e.detail), registered=False)
    except Exception as e:
        return _render(request, "login.html", user=None, error=str(e), registered=False)

    token = create_access_token(user_id=user.id, email=user.email)
    resp = _redirect("/cabinet")
    resp.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
    )
    return resp


@router.get("/logout")
def logout():
    resp = _redirect("/")
    resp.delete_cookie("access_token")
    return resp


def _parse_rows(rows_json: str | None, rows_file: UploadFile | None) -> tuple[list[dict[str, Any]] | None, str | None]:
    raw: str | None = None
    if rows_file is not None and rows_file.filename:
        raw = (rows_file.file.read() or b"").decode("utf-8")
    elif rows_json is not None:
        raw = rows_json

    if not raw or not raw.strip():
        return None, "Нужно передать данные: вставьте JSON в поле или загрузите файл"

    try:
        data = json.loads(raw)
    except Exception:
        return None, "Невалидный JSON"

    if isinstance(data, dict):
        return [data], None
    if isinstance(data, list):
        return data, None

    return None, "Ожидается JSON-объект или массив объектов"


@router.get("/cabinet", response_class=HTMLResponse)
def cabinet(
    request: Request,
    user: UserDB = Depends(get_current_user_web),
    session: Session = Depends(get_session),
):
    models = MLModelRepository().get_active(session)
    return _render(
        request,
        "cabinet.html",
        user=user,
        models=models,
        predict_result=None,
        error=None,
        topup_ok=False,
    )


@router.get("/requests/{request_id}", response_class=HTMLResponse)
def request_status_page(
    request: Request,
    request_id: str,
    user: UserDB = Depends(get_current_user_web),
    session: Session = Depends(get_session),
):
    """Страница статуса/результата конкретного ML‑запроса"""

    from uuid import UUID

    try:
        rid = UUID(request_id)
    except Exception:
        return _render(request, "request.html", user=user, item=None, error="Некорректный идентификатор")

    item = PredictionHistoryRepository().get(session, rid)
    if item is None:
        return _render(request, "request.html", user=user, item=None, error="Запрос не найден")

    if user.role != UserRole.ADMIN and item.user_id != user.id:
        return _render(request, "request.html", user=user, item=None, error="Запрос не найден")

    session.refresh(user)
    return _render(request, "request.html", user=user, item=item, error=None)


@router.post("/cabinet/topup", response_class=HTMLResponse)
def cabinet_topup(
    request: Request,
    amount: str = Form(...),
    user: UserDB = Depends(get_current_user_web),
    session: Session = Depends(get_session),
):
    models = MLModelRepository().get_active(session)
    try:
        try:
            amt = Decimal(amount)
        except Exception:
            raise HTTPException(status_code=400, detail="Введите корректную сумму")

        if amt <= 0:
            raise HTTPException(status_code=400, detail="Сумма пополнения должна быть больше нуля")

        svc = BalanceService()
        svc.top_up(session, user_id=user.id, amount=amt)
        session.refresh(user)
        return _render(
            request,
            "cabinet.html",
            user=user,
            models=models,
            predict_result=None,
            error=None,
            topup_ok=True,
        )
    except HTTPException as e:
        session.refresh(user)
        return _render(
            request,
            "cabinet.html",
            user=user,
            models=models,
            predict_result=None,
            error=str(e.detail),
            topup_ok=False,
        )
    except Exception as e:
        session.refresh(user)
        return _render(
            request,
            "cabinet.html",
            user=user,
            models=models,
            predict_result=None,
            error=str(e),
            topup_ok=False,
        )


@router.post("/cabinet/predict", response_class=HTMLResponse)
def cabinet_predict(
    request: Request,
    model_key: str = Form(...),
    rows_json: str | None = Form(default=None),
    rows_file: UploadFile | None = None,
    user: UserDB = Depends(get_current_user_web),
    session: Session = Depends(get_session),
):
    models = MLModelRepository().get_active(session)

    try:
        model_name, model_version = model_key.split("|", 1)
    except ValueError:
        session.refresh(user)
        return _render(
            request,
            "cabinet.html",
            user=user,
            models=models,
            predict_result=None,
            error="Некорректный выбор модели",
            topup_ok=False,
        )

    rows, parse_err = _parse_rows(rows_json, rows_file)
    if parse_err:
        session.refresh(user)
        return _render(
            request,
            "cabinet.html",
            user=user,
            models=models,
            predict_result=None,
            error=parse_err,
            topup_ok=False,
        )

    try:
        svc = PredictionService()
        item = svc.enqueue(
            session,
            user=user,
            model_name=model_name,
            model_version=model_version,
            rows=rows or [],
        )
        session.refresh(user)
        return _render(
            request,
            "cabinet.html",
            user=user,
            models=models,
            predict_result=item,
            error=None,
            topup_ok=False,
        )
    except HTTPException as e:
        session.refresh(user)
        return _render(
            request,
            "cabinet.html",
            user=user,
            models=models,
            predict_result=None,
            error=str(e.detail),
            topup_ok=False,
        )
    except Exception as e:
        session.refresh(user)
        return _render(
            request,
            "cabinet.html",
            user=user,
            models=models,
            predict_result=None,
            error=str(e),
            topup_ok=False,
        )


@router.get("/history", response_class=HTMLResponse)
def history(
    request: Request,
    user: UserDB = Depends(get_current_user_web),
    session: Session = Depends(get_session),
):
    txs = TransactionRepository().list_by_user(session, user.id, limit=200)
    preds = PredictionHistoryRepository().list_by_user(session, user.id, limit=200)
    return _render(request, "history.html", user=user, transactions=txs, predictions=preds)


@router.get("/admin/users", response_class=HTMLResponse)
def admin_users(
    request: Request,
    user: UserDB = Depends(get_current_user_web),
    session: Session = Depends(get_session),
):
    if user.role != UserRole.ADMIN:
        return _redirect("/cabinet")

    users = AuthService().list_users(session)
    return _render(request, "admin_users.html", user=user, users=users, error=None, ok=False)


@router.post("/admin/users/topup", response_class=HTMLResponse)
def admin_users_topup(
    request: Request,
    target_email: str = Form(...),
    amount: str = Form(...),
    user: UserDB = Depends(get_current_user_web),
    session: Session = Depends(get_session),
):
    if user.role != UserRole.ADMIN:
        return _redirect("/cabinet")

    ok = False
    err: str | None = None
    try:
        auth = AuthService()
        target = auth.get_user_by_email(session, email=target_email)
        if target is None:
            raise RuntimeError("User not found")
        BalanceService().top_up(session, user_id=target.id, amount=Decimal(amount))
        ok = True
    except Exception as e:
        err = str(e)

    users = AuthService().list_users(session)
    return _render(request, "admin_users.html", user=user, users=users, error=err, ok=ok)



