# # backend/auth/__init__.py
# from .router import router
# from .db import ensure_users_table


# backend/auth/__init__.py
from .router import router
from .db import ensure_users_table

__all__ = ["router", "ensure_users_table"]
