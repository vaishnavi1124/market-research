# Market Research/app_state.py
from typing import Optional

# Single, process-wide global (simple, not multi-user safe)
GLOBAL_USER_ID: Optional[int] = None

def set_global_user_id(user_id: int) -> None:
    global GLOBAL_USER_ID
    GLOBAL_USER_ID = user_id

def get_global_user_id() -> Optional[int]:
    return GLOBAL_USER_ID
