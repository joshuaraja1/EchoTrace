"""Local password hashing and signed bearer tokens for the MVP backend."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from typing import Dict


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 310_000
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${_encode(salt)}${_encode(derived)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), _decode(salt), int(iterations)
        )
        return hmac.compare_digest(actual, _decode(expected))
    except (ValueError, TypeError):
        return False


class TokenError(ValueError):
    """Raised when an authentication token is invalid or expired."""


class TokenService:
    def __init__(self, secret: bytes, lifetime_seconds: int = 8 * 60 * 60) -> None:
        self.secret = secret
        self.lifetime_seconds = lifetime_seconds

    @classmethod
    def from_data_dir(cls, data_dir: Path) -> TokenService:
        configured = os.environ.get("ECHOTRACE_JWT_SECRET")
        if configured:
            return cls(configured.encode("utf-8"))
        path = data_dir / ".jwt_secret"
        if not path.exists():
            path.write_bytes(secrets.token_bytes(32))
            path.chmod(0o600)
        return cls(path.read_bytes())

    def issue(self, user_id: str) -> str:
        header = _encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode("utf-8"))
        payload = _encode(
            json.dumps(
                {"sub": user_id, "exp": int(time.time()) + self.lifetime_seconds},
                separators=(",", ":"),
            ).encode("utf-8")
        )
        signature = _encode(hmac.new(self.secret, f"{header}.{payload}".encode(), hashlib.sha256).digest())
        return f"{header}.{payload}.{signature}"

    def verify(self, token: str) -> Dict[str, object]:
        try:
            header, payload, signature = token.split(".")
            expected = hmac.new(
                self.secret, f"{header}.{payload}".encode(), hashlib.sha256
            ).digest()
            if not hmac.compare_digest(expected, _decode(signature)):
                raise TokenError("Invalid token signature")
            claims = json.loads(_decode(payload))
            if int(claims["exp"]) <= int(time.time()):
                raise TokenError("Token expired")
            if not claims.get("sub"):
                raise TokenError("Token subject missing")
            return claims
        except (KeyError, ValueError, json.JSONDecodeError) as error:
            if isinstance(error, TokenError):
                raise
            raise TokenError("Invalid token") from error
