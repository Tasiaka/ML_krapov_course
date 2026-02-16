from __future__ import annotations

import hashlib
import hmac
import os


_DEFAULT_ITERATIONS = 210_000  #рекомендация для PBKDF2


def _b64e(raw: bytes) -> str:
    # urlsafe base64 без "=" чтобы токены/строки были короче
    import base64

    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(s: str) -> bytes:
    import base64

    pad = "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode((s + pad).encode("ascii"))


def hash_password(password: str, *, iterations: int = _DEFAULT_ITERATIONS) -> str:
    """PBKDF2-HMAC-SHA256.

    Формат: pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>
    """
    if not password:
        raise ValueError("password must not be empty")

    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${_b64e(salt)}${_b64e(dk)}"


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False

    try:
        algo, it_s, salt_s, dk_s = password_hash.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False

        iterations = int(it_s)
        salt = _b64d(salt_s)
        expected = _b64d(dk_s)
    except Exception:
        return False

    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(dk, expected)


