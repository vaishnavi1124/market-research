# # backend/auth/router.py
# from datetime import datetime
# from fastapi import APIRouter, HTTPException, Response, Request, Form
# from pydantic import BaseModel, Field
# from .db import exec_sql
# from .security import hash_password, verify_password, create_token, decode_token
# from .config import (
#     ACCESS_EXPIRE_MIN, REFRESH_EXPIRE_DAYS,
#     ACCESS_MAX_AGE, REFRESH_MAX_AGE,
#     COOKIE_DOMAIN, COOKIE_SECURE, COOKIE_SAMESITE,
# )

# router = APIRouter(tags=["Auth"])

# # ---------- helpers ----------
# def set_auth_cookies(resp: Response, access: str, refresh: str):
#     cookie_kwargs = dict(httponly=True, samesite=COOKIE_SAMESITE, secure=COOKIE_SECURE)
#     if COOKIE_DOMAIN:
#         cookie_kwargs["domain"] = COOKIE_DOMAIN
#     resp.set_cookie("access_token", access, max_age=ACCESS_MAX_AGE, **cookie_kwargs)
#     resp.set_cookie("refresh_token", refresh, max_age=REFRESH_MAX_AGE, **cookie_kwargs)

# def clear_auth_cookies(resp: Response):
#     cookie_kwargs = dict(httponly=True, samesite=COOKIE_SAMESITE, secure=COOKIE_SECURE)
#     if COOKIE_DOMAIN:
#         cookie_kwargs["domain"] = COOKIE_DOMAIN
#     resp.delete_cookie("access_token", **cookie_kwargs)
#     resp.delete_cookie("refresh_token", **cookie_kwargs)

# def set_user_cookie(resp: Response, user_id: int):
#     # Not HttpOnly so frontend JS can read if needed; flip to HttpOnly if you prefer backend-only access.
#     cookie_kwargs = dict(samesite=COOKIE_SAMESITE, secure=COOKIE_SECURE)
#     if COOKIE_DOMAIN:
#         cookie_kwargs["domain"] = COOKIE_DOMAIN
#     resp.set_cookie("user_id", str(user_id), max_age=ACCESS_MAX_AGE, **cookie_kwargs)

# def clear_user_cookie(resp: Response):
#     cookie_kwargs = dict(samesite=COOKIE_SAMESITE, secure=COOKIE_SECURE)
#     if COOKIE_DOMAIN:
#         cookie_kwargs["domain"] = COOKIE_DOMAIN
#     resp.delete_cookie("user_id", **cookie_kwargs)

# # ---------- models ----------
# class RegisterIn(BaseModel):
#     email: str
#     password: str = Field(min_length=8)
#     full_name: str | None = None
#     plan_type: str = Field(default="FREE", pattern="^(FREE|BASIC|PRO)$")

# class PublicUser(BaseModel):
#     id: int  # we will alias user_id AS id in SQL
#     email: str
#     full_name: str | None
#     status: str
#     last_login: datetime | None
#     register_date: datetime
#     plan_type: str

# # ---------- endpoints ----------
# @router.post("/register", status_code=201)
# def register(payload: RegisterIn):
#     # normalize & validate
#     email = (payload.email or "").strip().lower()
#     if not email:
#         raise HTTPException(400, detail="Email is required")
#     if len(payload.password or "") < 8:
#         raise HTTPException(400, detail="Password must be at least 8 characters")

#     plan = (payload.plan_type or "FREE").strip().upper()
#     if plan not in ("FREE", "BASIC", "PRO"):
#         plan = "FREE"

#     # conflict?  (use user_id, not id)
#     row = exec_sql("SELECT user_id FROM users WHERE email=%s", (email,), fetch=True)
#     if row:
#         # clearer signal for frontend
#         raise HTTPException(status_code=409, detail="Email already registered. Please sign in.")

#     pw_hash = hash_password(payload.password)
#     exec_sql(
#         "INSERT INTO users (email, password_hash, full_name, plan_type) VALUES (%s,%s,%s,%s)",
#         (email, pw_hash, payload.full_name, plan),
#     )
#     return {"message": "Registered successfully"}

# @router.post("/login")
# def login(
#     response: Response,
#     username: str = Form(...),  # OAuth2 form field name
#     password: str = Form(...)
# ):
#     email = (username or "").strip().lower()
#     user_rows = exec_sql("SELECT * FROM users WHERE email=%s", (email,), fetch=True) or []
#     if not user_rows or not verify_password(password, user_rows[0]["password_hash"]):
#         raise HTTPException(status_code=401, detail="Invalid email or password")
#     user = user_rows[0]
#     if user["status"] != "ACTIVE":
#         raise HTTPException(status_code=403, detail=f"Account status is {user['status']}")

#     # update last_login (use user_id)
#     exec_sql("UPDATE users SET last_login=%s WHERE user_id=%s", (datetime.utcnow(), user["user_id"]))

#     # create tokens & set cookies
#     access = create_token(user["email"], minutes=ACCESS_EXPIRE_MIN)
#     refresh = create_token(user["email"], days=REFRESH_EXPIRE_DAYS)
#     set_auth_cookies(response, access, refresh)

#     # also set user_id cookie for convenient session use
#     set_user_cookie(response, user["user_id"])

#     return {"message": "Login successful", "user_id": user["user_id"]}

# @router.post("/refresh")
# def refresh(request: Request, response: Response):
#     rt = request.cookies.get("refresh_token")
#     if not rt:
#         raise HTTPException(status_code=401, detail="Missing refresh token")
#     try:
#         data = decode_token(rt)
#         if data.get("type") != "refresh":
#             raise ValueError("Not a refresh token")
#         email = data.get("sub")
#     except Exception:
#         raise HTTPException(status_code=401, detail="Invalid refresh token")

#     access = create_token(email, minutes=ACCESS_EXPIRE_MIN)
#     cookie_kwargs = dict(httponly=True, samesite=COOKIE_SAMESITE, secure=COOKIE_SECURE)
#     if COOKIE_DOMAIN:
#         cookie_kwargs["domain"] = COOKIE_DOMAIN
#     response.set_cookie("access_token", access, max_age=ACCESS_MAX_AGE, **cookie_kwargs)
#     return {"message": "Refreshed"}

# @router.post("/logout")
# def logout(response: Response):
#     clear_auth_cookies(response)
#     clear_user_cookie(response)
#     return {"message": "Logged out"}

# @router.get("/me", response_model=PublicUser)
# def me(request: Request):
#     at = request.cookies.get("access_token")
#     if not at:
#         raise HTTPException(status_code=401, detail="Not authenticated")
#     try:
#         data = decode_token(at)  # or decode_token(at, expected_type="access") if you enforce type there
#         if data.get("type") != "access":
#             raise ValueError("Not an access token")
#         email = data.get("sub")
#     except Exception:
#         raise HTTPException(status_code=401, detail="Invalid/expired token")

#     # IMPORTANT: alias user_id AS id so the PublicUser schema (and frontend) remain unchanged
#     rows = exec_sql(
#         """
#         SELECT
#           user_id AS id,
#           email,
#           full_name,
#           status,
#           last_login,
#           register_date,
#           plan_type
#         FROM users
#         WHERE email=%s
#         """,
#         (email,), fetch=True
#     ) or []
#     if not rows:
#         raise HTTPException(404, detail="User not found")
#     return rows[0]

# backend/auth/router.py

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Response, Request, Form
from pydantic import BaseModel, Field

from .db import exec_sql
from .security import hash_password, verify_password, create_token, decode_token
from .config import (
    ACCESS_EXPIRE_MIN, REFRESH_EXPIRE_DAYS,
    ACCESS_MAX_AGE, REFRESH_MAX_AGE,
    COOKIE_DOMAIN, COOKIE_SECURE, COOKIE_SAMESITE,
)

# ---- GLOBAL user_id support (process-wide; single-worker dev only) ----
# Requires app_state.py with set_global_user_id(Optional[int]) -> None
try:
    from app_state import set_global_user_id  # type: ignore
except Exception:
    # Fallback no-op if app_state.py is not present (prevents import crash)
    def set_global_user_id(_: Optional[int]) -> None:  # type: ignore
        return

router = APIRouter(tags=["Auth"])

# ---------- helpers ----------
def set_auth_cookies(resp: Response, access: str, refresh: str):
    cookie_kwargs = dict(httponly=True, samesite=COOKIE_SAMESITE, secure=COOKIE_SECURE)
    if COOKIE_DOMAIN:
        cookie_kwargs["domain"] = COOKIE_DOMAIN
    resp.set_cookie("access_token", access, max_age=ACCESS_MAX_AGE, **cookie_kwargs)
    resp.set_cookie("refresh_token", refresh, max_age=REFRESH_MAX_AGE, **cookie_kwargs)

def clear_auth_cookies(resp: Response):
    cookie_kwargs = dict(httponly=True, samesite=COOKIE_SAMESITE, secure=COOKIE_SECURE)
    if COOKIE_DOMAIN:
        cookie_kwargs["domain"] = COOKIE_DOMAIN
    resp.delete_cookie("access_token", **cookie_kwargs)
    resp.delete_cookie("refresh_token", **cookie_kwargs)

def set_user_cookie(resp: Response, user_id: int):
    # Not HttpOnly so frontend JS can read if needed; flip to HttpOnly if you prefer backend-only access.
    cookie_kwargs = dict(samesite=COOKIE_SAMESITE, secure=COOKIE_SECURE)
    if COOKIE_DOMAIN:
        cookie_kwargs["domain"] = COOKIE_DOMAIN
    resp.set_cookie("user_id", str(user_id), max_age=ACCESS_MAX_AGE, **cookie_kwargs)

def clear_user_cookie(resp: Response):
    cookie_kwargs = dict(samesite=COOKIE_SAMESITE, secure=COOKIE_SECURE)
    if COOKIE_DOMAIN:
        cookie_kwargs["domain"] = COOKIE_DOMAIN
    resp.delete_cookie("user_id", **cookie_kwargs)

# ---------- models ----------
class RegisterIn(BaseModel):
    email: str
    password: str = Field(min_length=8)
    full_name: str | None = None
    plan_type: str = Field(default="FREE", pattern="^(FREE|BASIC|PRO)$")

class PublicUser(BaseModel):
    id: int  # we will alias user_id AS id in SQL
    email: str
    full_name: str | None
    status: str
    last_login: datetime | None
    register_date: datetime
    plan_type: str

# ---------- endpoints ----------
@router.post("/register", status_code=201)
def register(payload: RegisterIn):
    # normalize & validate
    email = (payload.email or "").strip().lower()
    if not email:
        raise HTTPException(400, detail="Email is required")
    if len(payload.password or "") < 8:
        raise HTTPException(400, detail="Password must be at least 8 characters")

    plan = (payload.plan_type or "FREE").strip().upper()
    if plan not in ("FREE", "BASIC", "PRO"):
        plan = "FREE"

    # conflict?  (use user_id, not id)
    row = exec_sql("SELECT user_id FROM users WHERE email=%s", (email,), fetch=True)
    if row:
        raise HTTPException(status_code=409, detail="Email already registered. Please sign in.")

    pw_hash = hash_password(payload.password)
    exec_sql(
        "INSERT INTO users (email, password_hash, full_name, plan_type) VALUES (%s,%s,%s,%s)",
        (email, pw_hash, payload.full_name, plan),
    )
    return {"message": "Registered successfully"}

@router.post("/login")
def login(
    response: Response,
    username: str = Form(...),  # OAuth2 form field name
    password: str = Form(...)
):
    email = (username or "").strip().lower()
    user_rows = exec_sql("SELECT * FROM users WHERE email=%s", (email,), fetch=True) or []
    if not user_rows or not verify_password(password, user_rows[0]["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user = user_rows[0]
    if user["status"] != "ACTIVE":
        raise HTTPException(status_code=403, detail=f"Account status is {user['status']}")

    # update last_login (use user_id)
    exec_sql("UPDATE users SET last_login=%s WHERE user_id=%s", (datetime.utcnow(), user["user_id"]))

    # create tokens & set cookies
    access = create_token(user["email"], minutes=ACCESS_EXPIRE_MIN)
    refresh = create_token(user["email"], days=REFRESH_EXPIRE_DAYS)
    set_auth_cookies(response, access, refresh)

    # also set user_id cookie for convenient session use
    set_user_cookie(response, user["user_id"])

    # === SET GLOBAL USER ID (process-wide) ===
    set_global_user_id(int(user["user_id"]))

    return {"message": "Login successful", "user_id": user["user_id"]}

@router.post("/refresh")
def refresh(request: Request, response: Response):
    rt = request.cookies.get("refresh_token")
    if not rt:
        raise HTTPException(status_code=401, detail="Missing refresh token")
    try:
        data = decode_token(rt)
        if data.get("type") != "refresh":
            raise ValueError("Not a refresh token")
        email = data.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    access = create_token(email, minutes=ACCESS_EXPIRE_MIN)
    cookie_kwargs = dict(httponly=True, samesite=COOKIE_SAMESITE, secure=COOKIE_SECURE)
    if COOKIE_DOMAIN:
        cookie_kwargs["domain"] = COOKIE_DOMAIN
    response.set_cookie("access_token", access, max_age=ACCESS_MAX_AGE, **cookie_kwargs)
    return {"message": "Refreshed"}

@router.post("/logout")
def logout(response: Response):
    clear_auth_cookies(response)
    clear_user_cookie(response)
    # Clear global user id
    set_global_user_id(None)
    return {"message": "Logged out"}

@router.get("/me", response_model=PublicUser)
def me(request: Request):
    # Validate via access token (authoritative check)
    at = request.cookies.get("access_token")
    if not at:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        data = decode_token(at)  # ensure it's an access token
        if data.get("type") != "access":
            raise ValueError("Not an access token")
        email = data.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid/expired token")

    # IMPORTANT: alias user_id AS id so PublicUser matches frontend expectations
    rows = exec_sql(
        """
        SELECT
          user_id AS id,
          email,
          full_name,
          status,
          last_login,
          register_date,
          plan_type
        FROM users
        WHERE email=%s
        """,
        (email,), fetch=True
    ) or []
    if not rows:
        raise HTTPException(404, detail="User not found")
    return rows[0]
