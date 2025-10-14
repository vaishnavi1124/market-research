# Market Research\auth\auth_helpers.py
from fastapi import Request, HTTPException

def get_user_id_from_cookies(request: Request) -> int:
    """Extract user_id from cookies and return as int."""
    user_id = request.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated (no user_id cookie)")
    try:
        return int(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id cookie")
