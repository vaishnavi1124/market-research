# backend/auth/config.py
import os

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = os.getenv("JWT_ALG", "HS256")

ACCESS_EXPIRE_MIN = int(os.getenv("ACCESS_EXPIRE_MIN", "30"))
REFRESH_EXPIRE_DAYS = int(os.getenv("REFRESH_EXPIRE_DAYS", "14"))

# cookie lifetimes in seconds
ACCESS_MAX_AGE = int(os.getenv("ACCESS_MAX_AGE", str(ACCESS_EXPIRE_MIN * 60)))
REFRESH_MAX_AGE = int(os.getenv("REFRESH_MAX_AGE", str(REFRESH_EXPIRE_DAYS * 86400)))

# cookies
COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN")  # usually None in dev
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"  # False in dev (http)
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax").lower()  # 'lax' in dev
