# routes/feedback_router.py (only the handler changed; keep the rest of the file)
# import os, json
# from datetime import datetime
# from typing import Optional, Literal

# from fastapi import APIRouter, HTTPException, Request
# from pydantic import BaseModel, Field, ValidationError
# import mysql.connector
# from mysql.connector import pooling, Error as MySQLError

# router = APIRouter(prefix="", tags=["feedback"])

# _DB_POOL: Optional[pooling.MySQLConnectionPool] = None
# def _get_pool() -> pooling.MySQLConnectionPool:
#     global _DB_POOL
#     if _DB_POOL is None:
#         _DB_POOL = pooling.MySQLConnectionPool(
#             pool_name="feedback_pool",
#             pool_size=5,
#             host=os.getenv("DB_HOST", "127.0.0.1"),
#             user=os.getenv("DB_USER", "root"),
#             password=os.getenv("DB_PASSWORD", ""),
#             database=os.getenv("DB_NAME", "your_db_name"),
#             autocommit=True,
#         )
#     return _DB_POOL

# class FeedbackIn(BaseModel):
#     type: Literal["chat", "topic"] = Field(default="chat")
#     id: int
#     feedback: Literal["like", "dislike"]
#     note: Optional[str] = None
#     append: bool = True

# def _coerce_bool(v, default=True):
#     if v is None:
#         return default
#     if isinstance(v, bool):
#         return v
#     if isinstance(v, (int, float)):
#         return bool(v)
#     if isinstance(v, str):
#         return v.strip().lower() in {"1", "true", "yes", "y", "on"}
#     return default

# async def _parse_feedback(request: Request) -> FeedbackIn:
#     """Accept application/json, multipart/form-data, or x-www-form-urlencoded."""
#     ctype = (request.headers.get("content-type") or "").lower()
#     data = {}
#     try:
#         if "application/json" in ctype:
#             data = await request.json()
#         elif "multipart/form-data" in ctype or "application/x-www-form-urlencoded" in ctype:
#             form = await request.form()
#             data = dict(form)
#         else:
#             # Try JSON as a fallback
#             data = await request.json()
#     except Exception:
#         # If body cannot be parsed, raise a clean 400
#         raise HTTPException(status_code=400, detail="Invalid request body")

#     # Coerce types defensively
#     if "id" in data:
#         try:
#             data["id"] = int(data["id"])
#         except Exception:
#             raise HTTPException(status_code=422, detail="Field 'id' must be an integer")
#     if "append" in data:
#         data["append"] = _coerce_bool(data.get("append"), True)

#     try:
#         return FeedbackIn(**data)
#     except ValidationError as e:
#         # Surface pydantic errors in a friendly way
#         raise HTTPException(status_code=422, detail=e.errors())

# @router.post("/feedback")
# async def submit_feedback(request: Request):
#     # Get user_id from cookie
#     user_id = request.cookies.get("user_id")
#     if not user_id:
#         raise HTTPException(status_code=401, detail="Not authenticated")
#     try:
#         user_id = int(user_id)
#     except ValueError:
#         raise HTTPException(status_code=400, detail="Invalid user_id cookie")

#     payload = await _parse_feedback(request)
#     table = "chat_history" if payload.type == "chat" else "research_topics"

#     remark_obj = {
#         "feedback": payload.feedback,
#         "note": payload.note or "",
#         "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
#         "source": "api:/feedback",
#         "user_id": user_id,   # keep track of which user gave the feedback
#     }
#     remark_str = json.dumps(remark_obj, ensure_ascii=False)

#     try:
#         cnx = _get_pool().get_connection()
#         cur = cnx.cursor()
#         try:
#             cur.execute(f"SELECT id FROM {table} WHERE id=%s", (payload.id,))
#             if not cur.fetchone():
#                 raise HTTPException(status_code=404, detail=f"{table} id {payload.id} not found")

#             if payload.append:
#                 cur.execute(
#                     f"""
#                     UPDATE {table}
#                     SET remark = CASE
#                         WHEN remark IS NULL OR remark = '' THEN %s
#                         ELSE CONCAT(remark, ';', %s)
#                     END
#                     WHERE id = %s
#                     """,
#                     (remark_str, remark_str, payload.id),
#                 )
#             else:
#                 cur.execute(
#                     f"UPDATE {table} SET remark=%s WHERE id=%s",
#                     (remark_str, payload.id),
#                 )

#             cnx.commit()
#             return {
#                 "ok": True,
#                 "table": table,
#                 "id": payload.id,
#                 "user_id": user_id,
#                 "saved": remark_obj,
#                 "mode": "append" if payload.append else "overwrite",
#             }
#         finally:
#             try:
#                 cur.close()
#             except Exception:
#                 pass
#             try:
#                 cnx.close()
#             except Exception:
#                 pass
#     except MySQLError as e:
#         raise HTTPException(status_code=500, detail=f"MySQL error: {e.msg}")


# @router.options("/feedback")
# def feedback_options():
#     return {"ok": True}

# Market Research\routes\feedback_router.py
from fastapi import APIRouter, Request, Body, HTTPException
from fastapi.responses import JSONResponse
import mysql.connector
from mysql.connector import pooling
import os

# Database Config
_DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "market_research"),
}

# MySQL Connection Pool
db_pool = pooling.MySQLConnectionPool(pool_name="mypool", pool_size=5, **_DB_CONFIG)

router = APIRouter()

@router.post("/feedback")
async def save_feedback(request: Request, payload: dict = Body(...)):
    """
    Save like/dislike feedback for a chatbot response in chat_history.remark.
    """
    try:
        feedback = payload.get("feedback", "").strip().lower()
        message = payload.get("message", "").strip()
        topic = payload.get("topic", "").strip() if payload.get("topic") else None

        if feedback not in ("like", "dislike"):
            raise HTTPException(status_code=400, detail="feedback must be 'like' or 'dislike'")
        if not message:
            raise HTTPException(status_code=400, detail="message is required")

        conn = db_pool.get_connection()
        cursor = conn.cursor()

        # Find the chat_history ID for the assistant's message
        query = """
            SELECT id FROM chat_history
            WHERE role = 'assistant' AND message = %s
            {topic_filter}
            ORDER BY created_at DESC
            LIMIT 1
        """.format(topic_filter="AND topic = %s" if topic else "")
        params = (message, topic) if topic else (message,)
        cursor.execute(query, params)
        row = cursor.fetchone()

        if not row:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Message not found in chat history")

        chat_id = row[0]

        # Update remark column
        update_query = "UPDATE chat_history SET remark = %s WHERE id = %s"
        cursor.execute(update_query, (feedback, chat_id))
        conn.commit()

        cursor.close()
        conn.close()

        return JSONResponse(status_code=200, content={
            "success": True,
            "message": f"Feedback saved: {feedback}",
            "chat_id": chat_id
        })

    except mysql.connector.Error as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
