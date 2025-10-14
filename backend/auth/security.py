# backend/auth/security.py
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
import jwt
from passlib.context import CryptContext
from .config import JWT_SECRET, JWT_ALG, ACCESS_EXPIRE_MIN

# ---------------- Password hashing ----------------
# Switch between argon2 (recommended) and bcrypt via env:
#   AUTH_HASH_SCHEME=argon2   -> uses Argon2 (install: passlib[argon2])
#   AUTH_HASH_SCHEME=bcrypt   -> uses bcrypt (default)
_HASH_SCHEME = (os.getenv("AUTH_HASH_SCHEME") or "bcrypt").lower().strip()
if _HASH_SCHEME == "argon2":
    pwdctx = CryptContext(schemes=["argon2"], deprecated="auto")
else:
    pwdctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(pw: str) -> str:
    return pwdctx.hash(pw)

def verify_password(pw: str, hashed: str) -> bool:
    try:
        return pwdctx.verify(pw, hashed)
    except Exception:
        return False

# ---------------- JWT helpers ----------------
# Optional hardening via env
_JWT_ISSUER = os.getenv("JWT_ISSUER") or None          # e.g. "mr-backend"
_JWT_LEEWAY = int(os.getenv("JWT_LEEWAY_SECONDS", "30"))  # clock skew tolerance

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

def create_token(sub: str, minutes: int | None = None, days: int | None = None) -> str:
    """
    Create an access token (minutes) or refresh token (days).
    If 'days' is provided -> refresh token; otherwise access.
    """
    now = _utcnow()
    if minutes is not None:
        exp = now + timedelta(minutes=minutes)
        token_type = "access"
    elif days is not None:
        exp = now + timedelta(days=days)
        token_type = "refresh"
    else:
        exp = now + timedelta(minutes=ACCESS_EXPIRE_MIN)
        token_type = "access"

    payload = {
        "sub": sub,
        "type": token_type,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    if _JWT_ISSUER:
        payload["iss"] = _JWT_ISSUER

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def decode_token(token: str, expected_type: str | None = None) -> dict:
    """
    Decode & validate a token. Optionally assert the 'type' claim.
    - Enforces exp/iat/nbf, optional issuer, and small leeway for clock skew.
    """
    options = {"require": ["exp", "iat", "nbf", "sub", "type"]}
    kwargs = {"leeway": _JWT_LEEWAY}
    if _JWT_ISSUER:
        kwargs["issuer"] = _JWT_ISSUER

    data = jwt.decode(
        token,
        JWT_SECRET,
        algorithms=[JWT_ALG],
        options=options,
        **kwargs,
    )
    if expected_type and data.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"Unexpected token type: {data.get('type')}")
    return data
