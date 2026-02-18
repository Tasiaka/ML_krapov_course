from __future__ import annotations

import base64
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any
from uuid import UUID


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode((s + pad).encode("ascii"))


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _get_secret() -> bytes:
    return os.getenv("API_SECRET_KEY", "dev-secret-change-me").encode("utf-8")


@dataclass(frozen=True)
class TokenPayload:
    sub: UUID
    email: str
    exp: datetime


class TokenError(Exception):
    pass


def create_access_token(*, user_id: UUID, email: str, ttl_minutes: int = 60) -> str:
    exp = _now_utc() + timedelta(minutes=ttl_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "exp": int(exp.timestamp()),
        "iat": int(_now_utc().timestamp()),
        "typ": "access",
    }
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    body_b64 = _b64url_encode(body)

    sig = hmac.new(_get_secret(), body_b64.encode("ascii"), sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{body_b64}.{sig_b64}"


def decode_access_token(token: str) -> TokenPayload:
    try:
        body_b64, sig_b64 = token.split(".", 1)
    except ValueError:
        raise TokenError("bad token format")

    expected_sig = hmac.new(_get_secret(), body_b64.encode("ascii"), sha256).digest()
    if not hmac.compare_digest(_b64url_encode(expected_sig), sig_b64):
        raise TokenError("bad token signature")

    try:
        payload = json.loads(_b64url_decode(body_b64))
        user_id = UUID(payload["sub"])
        email = str(payload["email"])
        exp_ts = int(payload["exp"])
    except Exception:
        raise TokenError("bad token payload")

    exp = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
    if _now_utc() >= exp:
        raise TokenError("token expired")

    return TokenPayload(sub=user_id, email=email, exp=exp)



