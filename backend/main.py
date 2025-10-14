# # ----------------------------------------------------------------------
# # Market Research\main.py
# # ----------------------------------------------------------------------
# import os
# os.environ["CREWAI_TELEMETRY_DISABLED"] = "1"  # Disable CrewAI telemetry
# import logging
# import re
# from typing import List, Dict, Any, Optional
# import secrets
# from datetime import datetime

# from fastapi import FastAPI, Request, Form, WebSocket, Body, HTTPException
# from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
# from fastapi.templating import Jinja2Templates
# from fastapi.staticfiles import StaticFiles
# from fastapi.middleware.cors import CORSMiddleware
# from dotenv import load_dotenv

# # CrewAI
# from crewai import Crew, Task

# # Your modules
# from main_crewai import (
#     llm, research_agent, research_analyst, research_writer,
#     chat_agent, router_agent, build_research_tasks,
# )
# from app_state import get_global_user_id
# from auth.auth_helpers import get_user_id_from_cookies
# # MCP / utils
# from mcp_server import tavily_search, get_tavily_schema, rag_mcp_tool, rag_upsert, save_to_pdf
# from mcp_server import db_insert_writer_report, db_get_reports

# # Gemini
# from langchain_google_genai import ChatGoogleGenerativeAI

# # MySQL
# import mysql.connector
# from mysql.connector import pooling, Error as MySQLError

# # Auth router & users table ensure
# from auth import router as auth_router
# from auth import ensure_users_table
# from database_setup import _ensure_tables
# from routes import sectors, feedback_router
# from mcp_server import send_email_to_user

# # WebSocket disconnect (quiet)
# try:
#     from starlette.websockets import WebSocketDisconnect
# except Exception:
#     WebSocketDisconnect = Exception

# # ----------------------------------------------------------------------
# # App setup
# # ----------------------------------------------------------------------
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
# load_dotenv()

# app = FastAPI()

# # ✅ include the routers
# app.include_router(sectors.router)
# app.include_router(auth_router, prefix="/auth")
# app.include_router(feedback_router.router) # Correctly named based on import

# templates = Jinja2Templates(directory="templates")
# app.mount("/static", StaticFiles(directory="static"), name="static")
# app.add_middleware(
#     CORSMiddleware,
#     allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# os.makedirs("Docs", exist_ok=True)

# # ----------------------------------------------------------------------
# # Globals
# # ----------------------------------------------------------------------
# previous_topic: Optional[str] = None
# active_websockets: List[WebSocket] = []
# chat_history_mem: List[Dict[str, Any]] = []  # runtime cache (reports + chats)

# # ----------------------------------------------------------------------
# # DB
# # ----------------------------------------------------------------------
# _DB_CONFIG = {
#     "host": os.getenv("DB_HOST", "127.0.0.1"),
#     "port": int(os.getenv("DB_PORT", "3306")),
#     "user": os.getenv("DB_USER", "root"),
#     "password": os.getenv("DB_PASSWORD", ""),
#     "database": os.getenv("DB_NAME", "market_research"),
# }

# _db_pool = None

# def _get_pool():
#     global _db_pool
#     if _db_pool is None:
#         _db_pool = pooling.MySQLConnectionPool(
#             pool_name="mr_web_pool",
#             pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
#             **_DB_CONFIG
#         )
#     return _db_pool

# def _exec_sql(q, params=None, fetch=False):
#     cnx = cur = None
#     try:
#         cnx = _get_pool().get_connection()
#         cur = cnx.cursor(dictionary=True)
#         cur.execute(q, params or ())
#         if fetch:
#             return cur.fetchall()
#         cnx.commit()
#     except MySQLError as e:
#         raise RuntimeError(f"MySQL error: {e}")
#     finally:
#         try:
#             if cur: cur.close()
#             if cnx: cnx.close()
#         except Exception:
#             pass


# def _latest_report_topic() -> Optional[str]:
#     rows = _exec_sql(
#         "SELECT topic FROM research_topics WHERE archived=0 "
#         "ORDER BY id DESC LIMIT 1",
#         fetch=True
#     ) or []
#     return rows[0]['topic'] if rows else None

# def _effective_topic(passed: Optional[str]) -> str:
#     # Prefer explicit topic, else prior topic, else latest report topic, else "General"
#     return passed or previous_topic or _latest_report_topic() or "General"



# def _resolve_uid(request: Request, user_id: Optional[int] = None) -> int:
#     """
#     Prefer explicit ?user_id=..., else use global, else cookie.
#     Raises 401 if none available.
#     """
#     if isinstance(user_id, int):
#         return user_id

#     uid = get_global_user_id()
#     if isinstance(uid, int):
#         return uid

#     try:
#         uid = get_user_id_from_cookies(request)
#         if isinstance(uid, int):
#             return uid
#     except HTTPException:
#         pass

#     raise HTTPException(status_code=401, detail="Not authenticated (no user_id)")

# # ----------------------------------------------------------------------
# # Startup
# # ---------------------------------------------------------------------- 

# @app.on_event("startup")
# def _warmup():
#     try:
#         _ensure_tables()
#         logger.info("Tables ensured.")
#     except Exception as e:
#         logger.warning(f"table init failed: {e}")

# # ----------------------------------------------------------------------
# # Pages / WebSocket
# # ----------------------------------------------------------------------
# @app.get("/", response_class=HTMLResponse)
# async def home(request: Request):
#     return templates.TemplateResponse("index.html", {"request": request})

# @app.websocket("/ws/progress")
# async def websocket_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     active_websockets.append(websocket)
#     try:
#         while True:
#             await websocket.receive_text()
#     except WebSocketDisconnect:
#         logger.debug("WebSocket disconnected")
#     except Exception as e:
#         logger.error(f"WebSocket error: {str(e)}")
#     finally:
#         if websocket in active_websockets:
#             active_websockets.remove(websocket)

# async def broadcast_progress(message: str):
#     stale = []
#     for ws in active_websockets:
#         try:
#             await ws.send_json({"message": message})
#         except Exception:
#             stale.append(ws)
#     for ws in stale:
#         if ws in active_websockets:
#             active_websockets.remove(ws)

# # ----------------------------------------------------------------------
# # Generate report
# # ----------------------------------------------------------------------
# @app.post("/generate-report")
# async def generate_report(
#     request: Request,
#     sector: str = Form(...),
#     category: str = Form(...),
#     research_type: str = Form(...),
#     brief_details: str = Form(...),
#     goals: str = Form(...),
#     client_name: str = Form(...),
#     scope: str = Form(...),
#     product_details: str = Form(""),
#     other_comments: str = Form("")
# ):
#     global previous_topic, chat_history_mem
    
#     uid = _resolve_uid(request)
    
#     print("\n======== /generate-report DEBUG ========")
#     print(f"Resolved_user_id: {uid}")
#     print(f"Method={request.method}  path={request.url.path}")
#     print(f"Research_type={research_type}")
#     print(f"sector={sector!r} - Category_name={category!r}")
#     print(f"goals={goals!r}  scope_raw={scope!r}")
#     print(f"client_name={client_name!r}")
#     print(f"brief_details(len={len(brief_details or '')}")
#     print(f"product_details(len={len(product_details or '')}")
#     print(f"other_comments(len={len(other_comments or '')}")
#     print("========================================")
#     try:
#         current_date_str = datetime.now().strftime("%B %d, %Y")
#         query_parts = [
#             f"Sector: {sector}",
#             F"Product Category: {category},",
#             f"Research Type: {research_type}",
#             f"Brief Details: {brief_details}",
#             f"Goals: {goals}",
#             f"Client name:{client_name}",
#             f"Geographic Scope: {scope}",
#             f"Product Details: {product_details}" if product_details.strip() else "",
#             f"Other Comments: {other_comments}" if other_comments.strip() else "",
#         ]
#         query = "\n".join([p for p in query_parts if p])

#         await broadcast_progress("Starting agents…")
#         await broadcast_progress("Router Agent working…")

#         route_task = Task(
#             description=f"""Analyze the following query:
# {query}

# Previous topic: {previous_topic if previous_topic else 'None'}

# Determine if this is a new research topic or a follow-up/related to the previous topic.
# Output ONLY 'new' or the related topic without any additional text.""",
#             agent=router_agent,
#             expected_output="'new' or the related topic",
#         )
#         decision = (await Crew(agents=[router_agent], tasks=[route_task], verbose=True).kickoff_async()).raw.strip().lower()
#         await broadcast_progress("Router Agent task completed")
#         logger.info(f"Routing decision: {decision}")

#         topic_key = f"{sector} - {research_type}"
#         safe_topic = topic_key.replace(" ", "_").replace("/", "_").replace(":", "_")[:50]

#         async def run_full_research_and_return():
#             await broadcast_progress("Research Agents working…")
#             tasks = build_research_tasks(query)
#             research_crew = Crew(agents=[research_agent, research_analyst, research_writer], tasks=tasks, verbose=True)
#             result = await research_crew.kickoff_async({"input": query})
#             await broadcast_progress("Research Agents tasks completed")
            
#             writer_pdf = "" # Initialize variable

#             # (Optional) save PDFs locally for download—NOT stored in DB or sidebar
#             try:
#                 analyst_pdf = f"Docs/{safe_topic}_analyst_report.pdf"
#                 if hasattr(tasks[1], "output") and tasks[1].output:
#                     save_to_pdf(str(tasks[1].output), analyst_pdf)
                
#                 # Assign the writer's PDF path
#                 writer_pdf = f"Docs/{safe_topic}_writer_report.pdf"
#                 if hasattr(tasks[2], "output") and tasks[2].output:
#                     save_to_pdf(str(tasks[2].output), writer_pdf)
#             except Exception as e:
#                 logger.warning(f"PDF save warning: {e}")


#             # Upsert to RAG + persist ONLY in research_topics (single source of truth)
#             try:
#                 if hasattr(tasks[2], "output") and tasks[2].output:
#                     rag_upsert(str(tasks[2].output), query)
#                     db_insert_writer_report(uid,topic=topic_key, research=str(tasks[2].output))
#                     try:
#                         email_subject = f"Your Market Research Report is Ready: {topic_key}"
#                         email_body = (
#                             f"Hello {client_name},\n\n"
#                             f"Your requested market research report on '{topic_key}' has been successfully generated.\n\n"
#                             "Please find the full report attached to this email.\n\n"
#                             "You can also view the report by logging into your dashboard.\n\n"
#                             "Thank you."
#                         )
                        
#                         # --- MODIFIED: Call the email tool with the PDF path ---
#                         email_status = send_email_to_user(
#                             user_id=uid, 
#                             subject=email_subject, 
#                             body=email_body, 
#                             pdf_path=writer_pdf  # Pass the path to the generated PDF
#                         )
#                         logger.info(email_status) # Log the result

#                     except Exception as email_e:
#                         logger.warning(f"Failed to send email notification: {email_e}")
#             except Exception as db_e:
#                 logger.warning(f"DB insert writer report failed: {db_e}")

#             # update topic trackers (for subsequent chats)
#             global previous_topic
#             previous_topic = topic_key

#             # runtime cache for quick UI
#             chat_history_mem.append({
#                 "type": "report",
#                 "topic": topic_key,
#                 "report": str(result)
#             })

#             # --- NEW: Generate follow-up suggestions ---
#             await broadcast_progress("Generating follow-up suggestions…")
#             llm_chat = ChatGoogleGenerativeAI(
#                 model="gemini-2.5-flash",
#                 google_api_key=os.getenv("GEMINI_API_KEY"),
#                 temperature=0.5,
#             )
#             suggestions = await _generate_follow_up_suggestions(llm_chat, str(result))
            
#             # --- MODIFIED: Return report with suggestions ---
#             return JSONResponse(content={"report": str(result), "suggestions": suggestions})

#         return await run_full_research_and_return()

#     except Exception as e:
#         logger.error(f"Error in generate_report: {e}")
#         await broadcast_progress(f"Error: {e}")
#         return JSONResponse(status_code=500, content={"error": str(e)})

# # ----------------------------------------------------------------------
# # Files (still available if you kept save_to_pdf)
# # ----------------------------------------------------------------------
# @app.get("/download-pdf/{filename}")
# async def download_pdf(filename: str):
#     pdf_path = os.path.join("Docs", filename)
#     if os.path.exists(pdf_path):
#         return FileResponse(pdf_path, media_type="application/pdf", filename=filename)
#     return JSONResponse(status_code=404, content={"error": "File not found"})


# # ----------------------------------------------------------------------
# # Helpers for chatbot
# # ----------------------------------------------------------------------
# def _fetch_report_for_topic(topic: str) -> Optional[str]:
#     rows = _exec_sql(
#         "SELECT research FROM research_topics WHERE archived=0 AND topic=%s ORDER BY id DESC LIMIT 1",
#         (topic,), fetch=True
#     ) or []
#     if rows:
#         return rows[0].get("research") or ""
#     return None

# def _make_context_block(topic: str) -> str:
#     """Build the context block from latest report + last 20 chat messages for the topic."""
#     chunks: List[str] = []
#     report_text = _fetch_report_for_topic(topic)
#     if report_text:
#         chunks.append(f"- (report) {report_text[:2000]}")

#     rows = _exec_sql(
#         "SELECT role, message FROM chat_history WHERE archived=0 AND topic=%s ORDER BY id DESC LIMIT 20",
#         (topic,), fetch=True
#     ) or []
#     for r in rows:
#         msg = (r["message"] or "")[:1200]
#         if not msg:
#             continue
#         role = "user" if r["role"] == "user" else "assistant"
#         chunks.append(f"- ({role}) {msg}")
#     return "\n".join(chunks) if chunks else "- No prior context found for this topic."

# def _looks_thin_or_generic(ans: str) -> bool:
#     """Heuristics to trigger tavily fallback when the LLM answer is low-signal."""
#     if not ans:
#         return True
#     a = ans.lower()
#     if len(ans.split()) < 40:
#         return True
#     generic_flags = [
#         "does not mention", "not available in the provided context",
#         "no prior context", "not enough context", "insufficient information",
#         "cannot find", "i couldn't derive"
#     ]
#     return any(flag in a for flag in generic_flags)

# def _normalize_tavily_payload(raw: Any) -> List[Dict[str, Any]]:
#     """
#     Make tavily results consistent.
#     Accepts list or dict and returns a list of items with title/snippet/link keys if possible.
#     """
#     if not raw:
#         return []
#     # If it's already a list of dicts
#     if isinstance(raw, list):
#         return raw

#     # If it's a dict, try common fields
#     if isinstance(raw, dict):
#         # Typical shapes to try
#         for key in ("results", "organic", "items", "news"):
#             if isinstance(raw.get(key), list):
#                 return raw.get(key) or []
#         # If dict has single result fields
#         return [raw]

#     return []

# def _tavily_results(question: str, limit: int = 6) -> List[Dict[str, str]]:
#     """
#     Robust wrapper around tavily_search() that DOES NOT pass unsupported kwargs.
#     It normalizes output into a list of {title, snippet, link}.
#     """
#     try:
#         # IMPORTANT: don't pass n= since your tavily_search doesn't accept it.
#         raw = tavily_search(question)
#     except TypeError:
#         # Some implementations require only the query; retry without any other params
#         raw = tavily_search(question)
#     except Exception as e:
#         logger.warning(f"tavily call failed: {e}")
#         return []

#     items = _normalize_tavily_payload(raw)[:limit]
#     normd: List[Dict[str, str]] = []
#     for r in items:
#         if not isinstance(r, dict):
#             continue
#         title = (r.get("title") or r.get("name") or r.get("headline") or "").strip()
#         snippet = (r.get("snippet") or r.get("description") or r.get("summary") or "").strip()
#         link = (r.get("link") or r.get("url") or r.get("source") or "").strip()
#         if title or snippet or link:
#             normd.append({"title": title, "snippet": snippet, "link": link})
#     return normd

# def _synthesize_from_web(llm_chat: ChatGoogleGenerativeAI, question: str) -> Optional[str]:
#     """Run tavily, then synthesize a grounded answer."""
#     results = _tavily_results(question, limit=6)
#     if not results:
#         return None

#     evidence_lines = []
#     for r in results:
#         t = r.get("title", "")
#         s = r.get("snippet", "")
#         l = r.get("link", "")
#         if t or s:
#             evidence_lines.append(f"- {t} — {s} ({l})")
#     evidence = "\n".join(evidence_lines) if evidence_lines else "No web results."

#     prompt = f"""SYSTEM:
# You are a concise market-research assistant. Answer ONLY using the WEB RESULTS below.
# Write crisp, factual bullets and avoid speculation. Add a 'Sources' section listing 3-5 items
# as 'Title — domain'.

# QUESTION: {question}

# WEB RESULTS:
# {evidence}

# FORMAT:
# - One-line summary
# - 3–8 bullets with specifics grounded in results
# - Sources (3–5 bullets)
# """
#     try:
#         synthesized = (llm_chat.invoke(prompt).content or "").strip()
#         return synthesized or None
#     except Exception as e:
#         logger.warning(f"LLM synthesize error: {e}")
#         return None

# # ----------------------------------------------------------------------
# # Chatbot (DB-first, Serper fallback)
# # ----------------------------------------------------------------------

# SENTINEL = "__NEEDS_OPEN_QA__"

# def _needs_open_qa(text: str) -> bool:
#     """
#     Decide if we should fall back to open-domain:
#     - No text at all
#     - Model returned the exact sentinel (or included it)
#     - Output looks thin or generic per your heuristic
#     """
#     if not text:
#         return True
#     t = (text or "").strip()
#     # Exact or substring match for robustness
#     if t.upper() == SENTINEL or SENTINEL in t:
#         return True
#     # Keep your heuristic (assumes you have this helper)
#     return _looks_thin_or_generic(t)

# def _prompt_context_first(eff_topic: str, context_block: str, user_query: str) -> str:
#     # Tell the model to answer only from CONTEXT; if insufficient, output ONLY the sentinel.
#     return f"""SYSTEM:
# You are a concise market-research assistant.
# Use ONLY the CONTEXT below. If the CONTEXT is insufficient to answer the USER QUESTION,
# OUTPUT EXACTLY this token and nothing else: {SENTINEL}.

# Prefer bullet points and crisp phrasing. Do not invent references.

# TOPIC: {eff_topic}

# CONTEXT:
# {context_block}

# USER QUESTION:
# {user_query}

# RESPONSE FORMAT:
# - If sufficient context: brief one-line summary, then 3–8 bullet points with specifics.
# - If insufficient context: output ONLY {SENTINEL} (no other text).
# """

# def _prompt_open_domain(eff_topic: str,user_query: str) -> str:
#     # Free the model to use its general knowledge (no external browsing here)
#     return f"""SYSTEM:
# You are a concise market-research assistant. Answer using your general knowledge based on the topic (no external browsing).
# Be factual, avoid speculation, and prefer crisp bullets.

# TOPIC: {eff_topic}

# USER QUESTION:
# {user_query}

# RESPONSE FORMAT:
# - One-line summary
# - 3–8 bullets with specifics
# - (Optional) What to check next
# """

# async def _generate_follow_up_suggestions(llm_chat: ChatGoogleGenerativeAI, text: str) -> List[str]:
#     """Generate follow-up questions based on a report or chat answer."""
#     if not text or len(text.strip()) < 50:
#         return []

#     prompt = f"""
# Based on the provided market research text, generate 2 distinct and actionable follow-up questions in 10 words.
# Format the output as a numbered list. Do not include any introductory or concluding sentences.

# TEXT:
# {text[:4000]}

# FOLLOW-UP QUESTIONS:
# """
#     try:
#         # Using ainvoke for async operation
#         response = await llm_chat.ainvoke(prompt)
#         content = getattr(response, "content", "") or ""

#         # Split by newline and filter out empty lines
#         lines = [line.strip() for line in content.split('\n') if line.strip()]

#         # Clean up leading numbers/bullets (e.g., "1. ", "- ", "* ")
#         suggestions = [re.sub(r'^\s*[\d\.\-\*]+\s*', '', line) for line in lines]

#         # Return only non-empty, cleaned suggestions
#         return [s for s in suggestions if s]

#     except Exception as e:
#         logger.warning(f"Follow-up suggestion generation failed: {e}")
#         return []

# @app.post("/chatbot")
# async def chatbot_rag(request: Request, query: str = Form(...), topic: Optional[str] = Form(None)):
#     global previous_topic, chat_history_mem

#     uid = _resolve_uid(request)

#     print("\n======== /chatbot DEBUG ========")
#     print(f"Resolved_user_id: {uid}")
#     print(f"Query='{query}' Topic='{topic}'")
#     print("==============================")

#     try:
#         await broadcast_progress("Chatbot retrieving context…")

#         eff_topic = _effective_topic(topic)
#         context_block = _make_context_block(eff_topic)

#         llm_chat = ChatGoogleGenerativeAI(
#             model="gemini-2.5-flash",
#             google_api_key=os.getenv("GEMINI_API_KEY"),
#             temperature=0.3,
#         )

#         # ---------- Pass 1: Context-first ----------
#         await broadcast_progress("Composing from local context…")
#         answer_ctx = ""
#         try:
#             raw = llm_chat.invoke(
#                 _prompt_context_first(eff_topic, context_block or "", query)
#             )
#             answer_ctx = (getattr(raw, "content", "") or "").strip()
#         except Exception as e:
#             logger.warning(f"Context-first LLM error: {e}")

#         # Decide if we need open-domain (strict sentinel + heuristic)
#         need_open = _needs_open_qa(answer_ctx)

#         # ---------- Pass 2: Open-domain (general knowledge) ----------
#         answer_open = ""
#         if need_open:
#             await broadcast_progress("Context insufficient — answering from general knowledge…")
#             try:
#                 raw = llm_chat.invoke(_prompt_open_domain(eff_topic,query))
#                 answer_open = (getattr(raw, "content", "") or "").strip()
#             except Exception as e:
#                 logger.warning(f"Open-domain LLM error: {e}")

#         # Pick best so far
#         answer = answer_open if need_open else answer_ctx

#         # ---------- Optional Pass 3: Web synth fallback (only if still thin) ----------
#         if _looks_thin_or_generic(answer):
#             await broadcast_progress("Searching the web…")
#             try:
#                 synthesized = _synthesize_from_web(llm_chat, query)
#                 if synthesized:
#                     answer = synthesized.strip()
#             except Exception as e:
#                 logger.warning(f"Web synth fallback failed: {e}")

#         # runtime cache
#         try:
#             chat_history_mem.append({
#                 "type": "chat", "topic": eff_topic, "query": query, "response": answer
#             })
#         except Exception as e:
#             logger.debug(f"chat_history_mem append failed: {e}")

    
#         # persist (user + assistant only)
#         try:
#             _exec_sql("INSERT INTO chat_history (user_id, topic, role, message) VALUES (%s,%s,'user',%s)",
#                   (uid, eff_topic, query))
#             _exec_sql("INSERT INTO chat_history (user_id, topic, role, message) VALUES (%s,%s,'assistant',%s)",
#                   (uid, eff_topic, answer))
#         except Exception as e:
#             logger.warning(f"Persist chat messages failed: {e}")

#         # --- NEW: Generate follow-up suggestions ---
#         await broadcast_progress("Generating follow-up suggestions…")
#         suggestions = await _generate_follow_up_suggestions(llm_chat, answer)

#         # --- MODIFIED: Return response with suggestions ---
#         return JSONResponse(content={"response": answer, "suggestions": suggestions})

#     except Exception as e:
#         logger.error(f"/chatbot error: {e}")
#         return JSONResponse(status_code=500, content={"error": str(e)})



# # ----------------------------------------------------------------------
# # History / read endpoints
# # ----------------------------------------------------------------------

# @app.get("/api/report/{rid}")
# def api_report_read(rid: int, request: Request, user_id: int | None = None):
#     try:
#         uid = _resolve_uid(request, user_id)
#         rows = _exec_sql(
#             "SELECT id, topic, research, created_at, archived, share_token "
#             "FROM research_topics WHERE id=%s AND user_id=%s",
#             (rid, uid), fetch=True
#         ) or []
#         if not rows:
#             return JSONResponse(status_code=404, content={"error": "not found"})
#         r = rows[0]
#         if int(r.get("archived", 0) or 0) == 1:
#             return JSONResponse(status_code=410, content={"error": "archived"})
#         return JSONResponse(content={
#             "id": r["id"],
#             "topic": r["topic"],
#             "client_name": r.get("client_name", ""),
#             "research": r["research"] or "",
#             "created_at": str(r["created_at"]),
#             "share_token": r.get("share_token"),
#         })
#     except Exception as e:
#         return JSONResponse(status_code=500, content={"error": str(e)})

# @app.get("/api/report-by-topic")
# def api_report_by_topic(request: Request, topic: str, user_id: int | None = None):
#     """Latest report for a topic and client  for this user."""
#     try:
#         uid = _resolve_uid(request, user_id)
#         rows = _exec_sql(
#             """
#             SELECT id, topic,client name, research, created_at, archived, share_token
#             FROM research_topics
#             WHERE user_id=%s AND topic=%s AND archived=0
#             ORDER BY id DESC LIMIT 1
#             """,
#             (uid, topic), fetch=True
#         ) or []
#         if not rows:
#             return JSONResponse(status_code=404, content={"error": "not found"})
#         r = rows[0]
#         return JSONResponse(content={
#             "id": r["id"],
#             "topic": r["topic"],
#             "client_name": r.get("client_name", ""),
#             "research": r["research"] or "",
#             "created_at": str(r["created_at"]),
#             "share_token": r.get("share_token"),
#         })
#     except Exception as e:
#         return JSONResponse(status_code=500, content={"error": str(e)})

# @app.get("/api/report-history")
# def api_report_history(request: Request, user_id: int | None = None):
#     try:
#         uid = _resolve_uid(request, user_id)
#         rows = _exec_sql(
#             "SELECT id, topic, LEFT(research, 200) AS research_snippet, created_at, archived, share_token "
#             "FROM research_topics WHERE user_id=%s "
#             "ORDER BY id DESC LIMIT 50",
#             (uid,), fetch=True
#         ) or []
#         data = [{
#             "id": r["id"],
#             "topic": r["topic"],
#             "client_name": r.get("client_name", ""),
#             "snippet": r["research_snippet"] or "",
#             "created_at": str(r["created_at"]),
#             "archived": int(r.get("archived", 0) or 0),
#             "share_token": r.get("share_token"),
#         } for r in rows if int(r.get("archived", 0) or 0) == 0]
#         return JSONResponse(content=data)
#     except Exception as e:
#         return JSONResponse(status_code=500, content={"error": str(e)})


# @app.get("/api/chat-history")
# def api_chat_history(request: Request, user_id: int | None = None):
#     try:
#         uid = _resolve_uid(request, user_id)
#         if uid is None:
#             return JSONResponse(status_code=401, content={"error": "Authentication required"})

#         rows = _exec_sql(
#             """
#             SELECT topic, MAX(created_at) AS last_at, COUNT(*) AS cnt
#             FROM (
#                 SELECT topic, created_at FROM chat_history WHERE archived=0 AND user_id=%s
#                 UNION ALL
#                 SELECT topic, created_at FROM research_topics WHERE archived=0 AND user_id=%s
#             ) t
#             GROUP BY topic
#             ORDER BY last_at DESC
#             LIMIT 200
#             """,
#             (uid, uid), fetch=True
#         ) or []

#         topics = [{
#             "topic": r["topic"] or "General",
#             "last_at": str(r["last_at"]),
#             "count": int(r["cnt"] or 0),
#         } for r in rows]
#         return JSONResponse(content=topics)
#     except Exception as e:
#         return JSONResponse(status_code=500, content={"error": str(e)})


# @app.get("/api/chat-by-id/{cid}")
# def api_chat_by_id(cid: int, request: Request, user_id: int | None = None):
#     try:
#         uid = _resolve_uid(request, user_id)
#         rows = _exec_sql(
#             "SELECT id, topic, role, message, created_at, archived, share_token "
#             "FROM chat_history WHERE id=%s AND user_id=%s",
#             (cid, uid), fetch=True
#         ) or []
#         if not rows:
#             return JSONResponse(status_code=404, content={"error": "not found"})
#         r = rows[0]
#         if int(r.get("archived", 0) or 0) == 1:
#             return JSONResponse(status_code=410, content={"error": "archived"})
#         return JSONResponse(content={
#             "id": r["id"],
#             "topic": r["topic"] or "General",
#             "client_name": r.get("client_name", ""),
#             "role": r["role"],
#             "message": r["message"] or "",
#             "created_at": str(r["created_at"]),
#             "share_token": r.get("share_token"),
#         })
#     except Exception as e:
#         return JSONResponse(status_code=500, content={"error": str(e)})


# @app.get("/api/chat-thread")
# def api_chat_thread(request: Request, topic: str, user_id: int | None = None):
#     """Full thread (user + assistant only) for a topic, ordered asc, scoped to user."""
#     try:
#         uid = _resolve_uid(request, user_id)
#         rows = _exec_sql(
#             "SELECT id, topic,client_name, role, message, created_at "
#             "FROM chat_history "
#             "WHERE user_id=%s AND topic=%s AND archived=0 AND role!='report' "
#             "ORDER BY id ASC LIMIT 500",
#             (uid, topic), fetch=True
#         ) or []
#         data = [{
#             "id": r["id"],
#             "role": r["role"],
#             "message": r["message"] or "",
#             "created_at": str(r["created_at"]),
#         } for r in rows]
#         return JSONResponse(content=data)
#     except Exception as e:
#         return JSONResponse(status_code=500, content={"error": str(e)})


# # ----------------------------------------------------------------------
# # Actions
# # ----------------------------------------------------------------------

# @app.post("/api/history/action")
# def api_history_action(payload: dict = Body(...)):
#     try:
#         kind = payload.get("kind")              # "report" | "chat" | "topic"
#         action = payload.get("action")          # "share" | "rename" | "archive" | "delete"
#         item_id = payload.get("id")
#         value = payload.get("value")            # for topic name / rename

#         if kind not in ("report", "chat", "topic"):
#             return JSONResponse(status_code=400, content={"error": "invalid kind"})

#         # ---------- TOPIC-WIDE ACTIONS (affect both research_topics & chat_history) ----------
#         if kind == "topic":
#             if not isinstance(value, str) or not value.strip():
#                 return JSONResponse(status_code=400, content={"error": "topic value required"})
#             topic = value.strip()

#             if action == "delete":
#                 _exec_sql("DELETE FROM chat_history WHERE topic=%s", (topic,))
#                 _exec_sql("DELETE FROM research_topics WHERE topic=%s", (topic,))
#                 return JSONResponse(content={"ok": True})

#             if action == "archive":
#                 _exec_sql("UPDATE chat_history SET archived=1 WHERE topic=%s", (topic,))
#                 _exec_sql("UPDATE research_topics SET archived=1 WHERE topic=%s", (topic,))
#                 return JSONResponse(content={"ok": True})

#             if action == "rename":
#                 new_name = payload.get("new_name") or payload.get("newTopic") or payload.get("value_new")
#                 if not isinstance(new_name, str) or not new_name.strip():
#                     return JSONResponse(status_code=400, content={"error": "new topic name required"})
#                 new_name = new_name.strip()
#                 _exec_sql("UPDATE chat_history SET topic=%s WHERE topic=%s", (new_name, topic))
#                 _exec_sql("UPDATE research_topics SET topic=%s WHERE topic=%s", (new_name, topic))
#                 return JSONResponse(content={"ok": True})

#             return JSONResponse(status_code=400, content={"error": "invalid action for topic"})

#         # ---------- PER-ROW ACTIONS (existing) ----------
#         if not isinstance(item_id, int):
#             try:
#                 item_id = int(item_id)
#             except Exception:
#                 return JSONResponse(status_code=400, content={"error": "invalid id"})

#         if action == "rename":
#             if kind == "report":
#                 _exec_sql("UPDATE research_topics SET topic=%s WHERE id=%s", (value, item_id))
#             else:
#                 _exec_sql("UPDATE chat_history SET topic=%s WHERE id=%s", (value, item_id))
#             return JSONResponse(content={"ok": True})

#         if action == "archive":
#             if kind == "report":
#                 _exec_sql("UPDATE research_topics SET archived=1 WHERE id=%s", (item_id,))
#             else:
#                 _exec_sql("UPDATE chat_history SET archived=1 WHERE id=%s", (item_id,))
#             return JSONResponse(content={"ok": True})

#         if action == "delete":
#             if kind == "report":
#                 # Cascade: delete report and all chats for same topic
#                 row = _exec_sql("SELECT topic FROM research_topics WHERE id=%s", (item_id,), fetch=True) or []
#                 _exec_sql("DELETE FROM research_topics WHERE id=%s", (item_id,))
#                 if row:
#                     _exec_sql("DELETE FROM chat_history WHERE topic=%s", (row[0]["topic"],))
#                 return JSONResponse(content={"ok": True})

#             else:  # kind == "chat"
#                 # Cascade: delete whole chat thread for that topic and any reports for that topic
#                 row = _exec_sql("SELECT topic FROM chat_history WHERE id=%s", (item_id,), fetch=True) or []
#                 _exec_sql("DELETE FROM chat_history WHERE id=%s", (item_id,))
#                 if row:
#                     topic = row[0]["topic"]
#                     _exec_sql("DELETE FROM chat_history WHERE topic=%s", (topic,))
#                     _exec_sql("DELETE FROM research_topics WHERE topic=%s", (topic,))
#                 return JSONResponse(content={"ok": True})

#         if action == "share":
#             token = secrets.token_urlsafe(16)
#             if kind == "report":
#                 _exec_sql("UPDATE research_topics SET share_token=%s WHERE id=%s", (token, item_id))
#             else:
#                 _exec_sql("UPDATE chat_history SET share_token=%s WHERE id=%s", (token, item_id))
#             return JSONResponse(content={"ok": True, "share_url": f"/share/{token}"})

#         return JSONResponse(status_code=400, content={"error": "invalid action"})
#     except Exception as e:
#         return JSONResponse(status_code=500, content={"error": str(e)})


# @app.get("/share/{token}", response_class=HTMLResponse)
# def share_view(token: str):
#     try:
#         r = _exec_sql(
#             "SELECT 'report' AS kind, id, topic, research AS content, created_at "
#             "FROM research_topics WHERE share_token=%s",
#             (token,), fetch=True
#         )
#         if r:
#             row = r[0]
#             html = f"""
#             <html><head><title>Shared Report</title></head>
#             <body style="font-family:Arial;padding:20px;max-width:900px;margin:auto;">
#               <h2>{row['topic']}</h2>
#               <div style="white-space:pre-wrap;border:1px solid #ddd;padding:12px;border-radius:6px;">{row['content']}</div>
#               <p style="color:#666">Shared report • Created at {row['created_at']}</p>
#             </body></html>"""
#             return HTMLResponse(content=html)

#         c = _exec_sql(
#             "SELECT 'chat' AS kind, id, topic, role, message AS content, created_at "
#             "FROM chat_history WHERE share_token=%s",
#             (token,), fetch=True
#         )
#         if c:
#             row = c[0]
#             html = f"""
#             <html><head><title>Shared Chat</title></head>
#             <body style="font-family:Arial;padding:20px;max-width:900px;margin:auto;">
#               <h2>Conversation: {row['topic'] or 'General'}</h2>
#               <p><b>{row['role']}:</b></p>
#               <div style="white-space:pre-wrap;border:1px solid #ddd;padding:12px;border-radius:6px;">{row['content']}</div>
#               <p style="color:#666">Shared message • Created at {row['created_at']}</p>
#             </body></html>"""
#             return HTMLResponse(content=html)

#         return HTMLResponse("<h3>Invalid or expired share link.</h3>", status_code=404)
#     except Exception as e:
#         return HTMLResponse(f"<h3>Error: {e}</h3>", status_code=500)

# # ----------------------------------------------------------------------
# # Run
# # ----------------------------------------------------------------------
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)










# ----------------------------------------------------------------------
# Market Research\main.py
# ----------------------------------------------------------------------
import os
os.environ["CREWAI_TELEMETRY_DISABLED"] = "1"  # Disable CrewAI telemetry
import logging
import re
from typing import List, Dict, Any, Optional
import secrets
from datetime import datetime
import io  # Required for in-memory file handling
import PyPDF2 # Required for PDF text extraction

from fastapi import FastAPI, Request, Form, WebSocket, Body, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# CrewAI
from crewai import Crew, Task

# Your modules
from main_crewai import (
    llm, research_agent, research_analyst, research_writer,
    chat_agent, router_agent, build_research_tasks,
)
from app_state import get_global_user_id
from auth.auth_helpers import get_user_id_from_cookies
# MCP / utils
from mcp_server import tavily_search, get_tavily_schema, rag_mcp_tool, rag_upsert, save_to_pdf
from mcp_server import db_insert_writer_report, db_get_reports

# Gemini
from langchain_google_genai import ChatGoogleGenerativeAI

# MySQL
import mysql.connector
from mysql.connector import pooling, Error as MySQLError

# Auth router & users table ensure
from auth import router as auth_router
from auth import ensure_users_table
from database_setup import _ensure_tables
from routes import sectors, feedback_router
from mcp_server import send_email_to_user

# WebSocket disconnect (quiet)
try:
    from starlette.websockets import WebSocketDisconnect
except Exception:
    WebSocketDisconnect = Exception

# ----------------------------------------------------------------------
# App setup
# ----------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

app = FastAPI()

# ✅ include the routers
app.include_router(sectors.router)
app.include_router(auth_router, prefix="/auth")
app.include_router(feedback_router.router) # Correctly named based on import

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("Docs", exist_ok=True)

# ----------------------------------------------------------------------
# Globals
# ----------------------------------------------------------------------
previous_topic: Optional[str] = None
active_websockets: List[WebSocket] = []
chat_history_mem: List[Dict[str, Any]] = []  # runtime cache (reports + chats)

# ----------------------------------------------------------------------
# DB
# ----------------------------------------------------------------------
_DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "market_research"),
}

_db_pool = None

def _get_pool():
    global _db_pool
    if _db_pool is None:
        _db_pool = pooling.MySQLConnectionPool(
            pool_name="mr_web_pool",
            pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
            **_DB_CONFIG
        )
    return _db_pool

def _exec_sql(q, params=None, fetch=False):
    cnx = cur = None
    try:
        cnx = _get_pool().get_connection()
        cur = cnx.cursor(dictionary=True)
        cur.execute(q, params or ())
        if fetch:
            return cur.fetchall()
        cnx.commit()
    except MySQLError as e:
        raise RuntimeError(f"MySQL error: {e}")
    finally:
        try:
            if cur: cur.close()
            if cnx: cnx.close()
        except Exception:
            pass


def _latest_report_topic() -> Optional[str]:
    rows = _exec_sql(
        "SELECT topic FROM research_topics WHERE archived=0 "
        "ORDER BY id DESC LIMIT 1",
        fetch=True
    ) or []
    return rows[0]['topic'] if rows else None

def _effective_topic(passed: Optional[str]) -> str:
    # Prefer explicit topic, else prior topic, else latest report topic, else "General"
    return passed or previous_topic or _latest_report_topic() or "General"



def _resolve_uid(request: Request, user_id: Optional[int] = None) -> int:
    """
    Prefer explicit ?user_id=..., else use global, else cookie.
    Raises 401 if none available.
    """
    if isinstance(user_id, int):
        return user_id

    uid = get_global_user_id()
    if isinstance(uid, int):
        return uid

    try:
        uid = get_user_id_from_cookies(request)
        if isinstance(uid, int):
            return uid
    except HTTPException:
        pass

    raise HTTPException(status_code=401, detail="Not authenticated (no user_id)")

# ----------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------- 

@app.on_event("startup")
def _warmup():
    try:
        _ensure_tables()
        logger.info("Tables ensured.")
    except Exception as e:
        logger.warning(f"table init failed: {e}")

# ----------------------------------------------------------------------
# PDF Helper
# ----------------------------------------------------------------------
async def extract_text_from_pdf(file: io.BytesIO) -> str:
    """Extracts text content from an in-memory PDF file."""
    try:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {e}")
        return ""

# ----------------------------------------------------------------------
# Pages / WebSocket
# ----------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws/progress")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.debug("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        if websocket in active_websockets:
            active_websockets.remove(websocket)

async def broadcast_progress(message: str):
    stale = []
    for ws in active_websockets:
        try:
            await ws.send_json({"message": message})
        except Exception:
            stale.append(ws)
    for ws in stale:
        if ws in active_websockets:
            active_websockets.remove(ws)

# ----------------------------------------------------------------------
# Generate report
# ----------------------------------------------------------------------
@app.post("/generate-report")
async def generate_report(
    request: Request,
    sector: str = Form(...),
    category: str = Form(...),
    research_type: str = Form(...),
    brief_details: str = Form(...),
    goals: str = Form(...),
    client_name: str = Form(...),
    scope: str = Form(...),
    product_details: str = Form(""),
    other_comments: str = Form(""),
    pdf_file: UploadFile = File(None)
):
    global previous_topic, chat_history_mem
    
    uid = _resolve_uid(request)
    
    print("\n======== /generate-report DEBUG ========")
    print(f"Resolved_user_id: {uid}")
    print(f"Method={request.method}  path={request.url.path}")
    print(f"Research_type={research_type}")
    print(f"sector={sector!r} - Category_name={category!r}")
    print(f"goals={goals!r}  scope_raw={scope!r}")
    print(f"client_name={client_name!r}")
    print(f"brief_details(len={len(brief_details or '')}")
    print(f"product_details(len={len(product_details or '')}")
    print(f"other_comments(len={len(other_comments or '')}")
    if pdf_file:
        print(f"pdf_file='{pdf_file.filename}' content_type='{pdf_file.content_type}'")
    print("========================================")
    try:
        # --- PDF Processing Logic ---
        pdf_content = ""
        if pdf_file and pdf_file.filename:
            await broadcast_progress("Processing uploaded PDF…")
            if pdf_file.content_type != "application/pdf":
                raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PDF.")
            
            pdf_bytes = await pdf_file.read()
            pdf_buffer = io.BytesIO(pdf_bytes)
            
            pdf_content = await extract_text_from_pdf(pdf_buffer)
            if not pdf_content:
                await broadcast_progress("Warning: Could not extract text from the PDF.")
            else:
                await broadcast_progress("PDF content extracted successfully.")

        current_date_str = datetime.now().strftime("%B %d, %Y")
        query_parts = [
            f"Sector: {sector}",
            F"Product Category: {category},",
            f"Research Type: {research_type}",
            f"Brief Details: {brief_details}",
            f"Goals: {goals}",
            f"Client name:{client_name}",
            f"Geographic Scope: {scope}",
            f"Product Details: {product_details}" if product_details.strip() else "",
            f"Other Comments: {other_comments}" if other_comments.strip() else "",
        ]
        
        form_query = "\n".join([p for p in query_parts if p])
        
        # --- Combine PDF content with form query ---
        query = form_query
        if pdf_content:
            query = (
                "Primary analysis based on the user-provided document below, supplemented by web research.\n\n"
                "--- User Document Content ---\n"
                f"{pdf_content}\n"
                "--- End of User Document ---\n\n"
                "--- User Research Request ---\n"
                f"{form_query}"
            )

        await broadcast_progress("Starting agents…")
        await broadcast_progress("Router Agent working…")

        route_task = Task(
            description=f"""Analyze the following query:
{query}

Previous topic: {previous_topic if previous_topic else 'None'}

Determine if this is a new research topic or a follow-up/related to the previous topic.
Output ONLY 'new' or the related topic without any additional text.""",
            agent=router_agent,
            expected_output="'new' or the related topic",
        )
        decision = (await Crew(agents=[router_agent], tasks=[route_task], verbose=True).kickoff_async()).raw.strip().lower()
        await broadcast_progress("Router Agent task completed")
        logger.info(f"Routing decision: {decision}")

        topic_key = f"{sector} - {research_type}"
        safe_topic = topic_key.replace(" ", "_").replace("/", "_").replace(":", "_")[:50]

        async def run_full_research_and_return():
            await broadcast_progress("Research Agents working…")
            tasks = build_research_tasks(query)
            research_crew = Crew(agents=[research_agent, research_analyst, research_writer], tasks=tasks, verbose=True)
            result = await research_crew.kickoff_async({"input": query})
            await broadcast_progress("Research Agents tasks completed")
            
            writer_pdf = "" # Initialize variable

            # (Optional) save PDFs locally for download—NOT stored in DB or sidebar
            try:
                analyst_pdf = f"Docs/{safe_topic}_analyst_report.pdf"
                if hasattr(tasks[1], "output") and tasks[1].output:
                    save_to_pdf(str(tasks[1].output), analyst_pdf)
                
                # Assign the writer's PDF path
                writer_pdf = f"Docs/{safe_topic}_writer_report.pdf"
                if hasattr(tasks[2], "output") and tasks[2].output:
                    save_to_pdf(str(tasks[2].output), writer_pdf)
            except Exception as e:
                logger.warning(f"PDF save warning: {e}")


            # Upsert to RAG + persist ONLY in research_topics (single source of truth)
            try:
                if hasattr(tasks[2], "output") and tasks[2].output:
                    rag_upsert(str(tasks[2].output), query)
                    db_insert_writer_report(
                        user_id=uid,
                        topic=topic_key, 
                        research=str(tasks[2].output),
                        client_name=client_name,      # Add this
                        pdf_extract=pdf_content       # Add this
                    )
                    try:
                        email_subject = f"Your Market Research Report is Ready: {topic_key}"
                        email_body = (
                            f"Hello {client_name},\n\n"
                            f"Your requested market research report on '{topic_key}' has been successfully generated.\n\n"
                            "Please find the full report attached to this email.\n\n"
                            "You can also view the report by logging into your dashboard.\n\n"
                            "Thank you."
                        )
                        
                        # --- MODIFIED: Call the email tool with the PDF path ---
                        email_status = send_email_to_user(
                            user_id=uid, 
                            subject=email_subject, 
                            body=email_body, 
                            pdf_path=writer_pdf  # Pass the path to the generated PDF
                        )
                        logger.info(email_status) # Log the result

                    except Exception as email_e:
                        logger.warning(f"Failed to send email notification: {email_e}")
            except Exception as db_e:
                logger.warning(f"DB insert writer report failed: {db_e}")

            # update topic trackers (for subsequent chats)
            global previous_topic
            previous_topic = topic_key

            # runtime cache for quick UI
            chat_history_mem.append({
                "type": "report",
                "topic": topic_key,
                "report": str(result)
            })

            # --- NEW: Generate follow-up suggestions ---
            await broadcast_progress("Generating follow-up suggestions…")
            llm_chat = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                google_api_key=os.getenv("GEMINI_API_KEY"),
                temperature=0.5,
            )
            suggestions = await _generate_follow_up_suggestions(llm_chat, str(result))
            
            # --- MODIFIED: Return report with suggestions ---
            return JSONResponse(content={"report": str(result), "suggestions": suggestions})

        return await run_full_research_and_return()

    except Exception as e:
        logger.error(f"Error in generate_report: {e}")
        await broadcast_progress(f"Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# ----------------------------------------------------------------------
# Files (still available if you kept save_to_pdf)
# ----------------------------------------------------------------------
@app.get("/download-pdf/{filename}")
async def download_pdf(filename: str):
    pdf_path = os.path.join("Docs", filename)
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, media_type="application/pdf", filename=filename)
    return JSONResponse(status_code=404, content={"error": "File not found"})


# ----------------------------------------------------------------------
# Helpers for chatbot
# ----------------------------------------------------------------------
def _fetch_report_for_topic(topic: str) -> Optional[str]:
    rows = _exec_sql(
        "SELECT research FROM research_topics WHERE archived=0 AND topic=%s ORDER BY id DESC LIMIT 1",
        (topic,), fetch=True
    ) or []
    if rows:
        return rows[0].get("research") or ""
    return None

def _make_context_block(topic: str) -> str:
    """Build the context block from latest report + last 20 chat messages for the topic."""
    chunks: List[str] = []
    report_text = _fetch_report_for_topic(topic)
    if report_text:
        chunks.append(f"- (report) {report_text[:2000]}")

    rows = _exec_sql(
        "SELECT role, message FROM chat_history WHERE archived=0 AND topic=%s ORDER BY id DESC LIMIT 20",
        (topic,), fetch=True
    ) or []
    for r in rows:
        msg = (r["message"] or "")[:1200]
        if not msg:
            continue
        role = "user" if r["role"] == "user" else "assistant"
        chunks.append(f"- ({role}) {msg}")
    return "\n".join(chunks) if chunks else "- No prior context found for this topic."

def _looks_thin_or_generic(ans: str) -> bool:
    """Heuristics to trigger tavily fallback when the LLM answer is low-signal."""
    if not ans:
        return True
    a = ans.lower()
    if len(ans.split()) < 40:
        return True
    generic_flags = [
        "does not mention", "not available in the provided context",
        "no prior context", "not enough context", "insufficient information",
        "cannot find", "i couldn't derive"
    ]
    return any(flag in a for flag in generic_flags)

def _normalize_tavily_payload(raw: Any) -> List[Dict[str, Any]]:
    """
    Make tavily results consistent.
    Accepts list or dict and returns a list of items with title/snippet/link keys if possible.
    """
    if not raw:
        return []
    # If it's already a list of dicts
    if isinstance(raw, list):
        return raw

    # If it's a dict, try common fields
    if isinstance(raw, dict):
        # Typical shapes to try
        for key in ("results", "organic", "items", "news"):
            if isinstance(raw.get(key), list):
                return raw.get(key) or []
        # If dict has single result fields
        return [raw]

    return []

def _tavily_results(question: str, limit: int = 6) -> List[Dict[str, str]]:
    """
    Robust wrapper around tavily_search() that DOES NOT pass unsupported kwargs.
    It normalizes output into a list of {title, snippet, link}.
    """
    try:
        # IMPORTANT: don't pass n= since your tavily_search doesn't accept it.
        raw = tavily_search(question)
    except TypeError:
        # Some implementations require only the query; retry without any other params
        raw = tavily_search(question)
    except Exception as e:
        logger.warning(f"tavily call failed: {e}")
        return []

    items = _normalize_tavily_payload(raw)[:limit]
    normd: List[Dict[str, str]] = []
    for r in items:
        if not isinstance(r, dict):
            continue
        title = (r.get("title") or r.get("name") or r.get("headline") or "").strip()
        snippet = (r.get("snippet") or r.get("description") or r.get("summary") or "").strip()
        link = (r.get("link") or r.get("url") or r.get("source") or "").strip()
        if title or snippet or link:
            normd.append({"title": title, "snippet": snippet, "link": link})
    return normd

def _synthesize_from_web(llm_chat: ChatGoogleGenerativeAI, question: str) -> Optional[str]:
    """Run tavily, then synthesize a grounded answer."""
    results = _tavily_results(question, limit=6)
    if not results:
        return None

    evidence_lines = []
    for r in results:
        t = r.get("title", "")
        s = r.get("snippet", "")
        l = r.get("link", "")
        if t or s:
            evidence_lines.append(f"- {t} — {s} ({l})")
    evidence = "\n".join(evidence_lines) if evidence_lines else "No web results."

    prompt = f"""SYSTEM:
You are a concise market-research assistant. Answer ONLY using the WEB RESULTS below.
Write crisp, factual bullets and avoid speculation. Add a 'Sources' section listing 3-5 items
as 'Title — domain'.

QUESTION: {question}

WEB RESULTS:
{evidence}

FORMAT:
- One-line summary
- 3–8 bullets with specifics grounded in results
- Sources (3–5 bullets)
"""
    try:
        synthesized = (llm_chat.invoke(prompt).content or "").strip()
        return synthesized or None
    except Exception as e:
        logger.warning(f"LLM synthesize error: {e}")
        return None

# ----------------------------------------------------------------------
# Chatbot (DB-first, Serper fallback)
# ----------------------------------------------------------------------

SENTINEL = "__NEEDS_OPEN_QA__"

def _needs_open_qa(text: str) -> bool:
    """
    Decide if we should fall back to open-domain:
    - No text at all
    - Model returned the exact sentinel (or included it)
    - Output looks thin or generic per your heuristic
    """
    if not text:
        return True
    t = (text or "").strip()
    # Exact or substring match for robustness
    if t.upper() == SENTINEL or SENTINEL in t:
        return True
    # Keep your heuristic (assumes you have this helper)
    return _looks_thin_or_generic(t)

def _prompt_context_first(eff_topic: str, context_block: str, user_query: str) -> str:
    # Tell the model to answer only from CONTEXT; if insufficient, output ONLY the sentinel.
    return f"""SYSTEM:
You are a concise market-research assistant.
Use ONLY the CONTEXT below. If the CONTEXT is insufficient to answer the USER QUESTION,
OUTPUT EXACTLY this token and nothing else: {SENTINEL}.

Prefer bullet points and crisp phrasing. Do not invent references.

TOPIC: {eff_topic}

CONTEXT:
{context_block}

USER QUESTION:
{user_query}

RESPONSE FORMAT:
- If sufficient context: brief one-line summary, then 3–8 bullet points with specifics.
- If insufficient context: output ONLY {SENTINEL} (no other text).
"""

def _prompt_open_domain(eff_topic: str,user_query: str) -> str:
    # Free the model to use its general knowledge (no external browsing here)
    return f"""SYSTEM:
You are a concise market-research assistant. Answer using your general knowledge based on the topic (no external browsing).
Be factual, avoid speculation, and prefer crisp bullets.

TOPIC: {eff_topic}

USER QUESTION:
{user_query}

RESPONSE FORMAT:
- One-line summary
- 3–8 bullets with specifics
- (Optional) What to check next
"""

async def _generate_follow_up_suggestions(llm_chat: ChatGoogleGenerativeAI, text: str) -> List[str]:
    """Generate follow-up questions based on a report or chat answer."""
    if not text or len(text.strip()) < 50:
        return []

    prompt = f"""
Based on the provided market research text, generate 2 distinct and actionable follow-up questions in 10 words.
Format the output as a numbered list. Do not include any introductory or concluding sentences.

TEXT:
{text[:4000]}

FOLLOW-UP QUESTIONS:
"""
    try:
        # Using ainvoke for async operation
        response = await llm_chat.ainvoke(prompt)
        content = getattr(response, "content", "") or ""

        # Split by newline and filter out empty lines
        lines = [line.strip() for line in content.split('\n') if line.strip()]

        # Clean up leading numbers/bullets (e.g., "1. ", "- ", "* ")
        suggestions = [re.sub(r'^\s*[\d\.\-\*]+\s*', '', line) for line in lines]

        # Return only non-empty, cleaned suggestions
        return [s for s in suggestions if s]

    except Exception as e:
        logger.warning(f"Follow-up suggestion generation failed: {e}")
        return []

@app.post("/chatbot")
async def chatbot_rag(request: Request, query: str = Form(...), topic: Optional[str] = Form(None)):
    global previous_topic, chat_history_mem

    uid = _resolve_uid(request)

    print("\n======== /chatbot DEBUG ========")
    print(f"Resolved_user_id: {uid}")
    print(f"Query='{query}' Topic='{topic}'")
    print("==============================")

    try:
        await broadcast_progress("Chatbot retrieving context…")

        eff_topic = _effective_topic(topic)
        context_block = _make_context_block(eff_topic)

        llm_chat = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0.3,
        )

        # ---------- Pass 1: Context-first ----------
        await broadcast_progress("Composing from local context…")
        answer_ctx = ""
        try:
            raw = llm_chat.invoke(
                _prompt_context_first(eff_topic, context_block or "", query)
            )
            answer_ctx = (getattr(raw, "content", "") or "").strip()
        except Exception as e:
            logger.warning(f"Context-first LLM error: {e}")

        # Decide if we need open-domain (strict sentinel + heuristic)
        need_open = _needs_open_qa(answer_ctx)

        # ---------- Pass 2: Open-domain (general knowledge) ----------
        answer_open = ""
        if need_open:
            await broadcast_progress("Context insufficient — answering from general knowledge…")
            try:
                raw = llm_chat.invoke(_prompt_open_domain(eff_topic,query))
                answer_open = (getattr(raw, "content", "") or "").strip()
            except Exception as e:
                logger.warning(f"Open-domain LLM error: {e}")

        # Pick best so far
        answer = answer_open if need_open else answer_ctx

        # ---------- Optional Pass 3: Web synth fallback (only if still thin) ----------
        if _looks_thin_or_generic(answer):
            await broadcast_progress("Searching the web…")
            try:
                synthesized = _synthesize_from_web(llm_chat, query)
                if synthesized:
                    answer = synthesized.strip()
            except Exception as e:
                logger.warning(f"Web synth fallback failed: {e}")

        # runtime cache
        try:
            chat_history_mem.append({
                "type": "chat", "topic": eff_topic, "query": query, "response": answer
            })
        except Exception as e:
            logger.debug(f"chat_history_mem append failed: {e}")

    
        # persist (user + assistant only)
        try:
            _exec_sql("INSERT INTO chat_history (user_id, topic, role, message) VALUES (%s,%s,'user',%s)",
                  (uid, eff_topic, query))
            _exec_sql("INSERT INTO chat_history (user_id, topic, role, message) VALUES (%s,%s,'assistant',%s)",
                  (uid, eff_topic, answer))
        except Exception as e:
            logger.warning(f"Persist chat messages failed: {e}")

        # --- NEW: Generate follow-up suggestions ---
        await broadcast_progress("Generating follow-up suggestions…")
        suggestions = await _generate_follow_up_suggestions(llm_chat, answer)

        # --- MODIFIED: Return response with suggestions ---
        return JSONResponse(content={"response": answer, "suggestions": suggestions})

    except Exception as e:
        logger.error(f"/chatbot error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})



# ----------------------------------------------------------------------
# History / read endpoints
# ----------------------------------------------------------------------

@app.get("/api/report/{rid}")
def api_report_read(rid: int, request: Request, user_id: int | None = None):
    try:
        uid = _resolve_uid(request, user_id)
        rows = _exec_sql(
            "SELECT id, topic, research, created_at, archived, share_token "
            "FROM research_topics WHERE id=%s AND user_id=%s",
            (rid, uid), fetch=True
        ) or []
        if not rows:
            return JSONResponse(status_code=404, content={"error": "not found"})
        r = rows[0]
        if int(r.get("archived", 0) or 0) == 1:
            return JSONResponse(status_code=410, content={"error": "archived"})
        return JSONResponse(content={
            "id": r["id"],
            "topic": r["topic"],
            "client_name": r["client_name"],
            "research": r["research"] or "",
            "created_at": str(r["created_at"]),
            "share_token": r.get("share_token"),
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/report-by-topic")
def api_report_by_topic(request: Request, topic: str, user_id: int | None = None):
    """Latest report for a topic and client_name for this user."""
    try:
        uid = _resolve_uid(request, user_id)
        rows = _exec_sql(
            """
            SELECT id, topic,client_name, research, created_at, archived, share_token
            FROM research_topics
            WHERE user_id=%s AND topic=%s AND archived=0
            ORDER BY id DESC LIMIT 1
            """,
            (uid, topic), fetch=True
        ) or []
        if not rows:
            return JSONResponse(status_code=404, content={"error": "not found"})
        r = rows[0]
        return JSONResponse(content={
            "id": r["id"],
            "topic": r["topic"],
            "client_name": r.get("client_name", ""),
            "research": r["research"] or "",
            "created_at": str(r["created_at"]),
            "share_token": r.get("share_token"),
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/report-history")
def api_report_history(request: Request, user_id: int | None = None):
    try:
        uid = _resolve_uid(request, user_id)
        rows = _exec_sql(
            "SELECT id, topic, LEFT(research, 200) AS research_snippet, created_at, archived, share_token "
            "FROM research_topics WHERE user_id=%s "
            "ORDER BY id DESC LIMIT 50",
            (uid,), fetch=True
        ) or []
        data = [{
            "id": r["id"],
            "topic": r["topic"],
            "client_name": r["client_name"],
            "snippet": r["research_snippet"] or "",
            "created_at": str(r["created_at"]),
            "archived": int(r.get("archived", 0) or 0),
            "share_token": r.get("share_token"),
        } for r in rows if int(r.get("archived", 0) or 0) == 0]
        return JSONResponse(content=data)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/chat-history")
def api_chat_history(request: Request, user_id: int | None = None):
    try:
        uid = _resolve_uid(request, user_id)
        if uid is None:
            return JSONResponse(status_code=401, content={"error": "Authentication required"})

        rows = _exec_sql(
            """
            SELECT topic, MAX(created_at) AS last_at, COUNT(*) AS cnt
            FROM (
                SELECT topic, created_at FROM chat_history WHERE archived=0 AND user_id=%s
                UNION ALL
                SELECT topic, created_at FROM research_topics WHERE archived=0 AND user_id=%s
            ) t
            GROUP BY topic
            ORDER BY last_at DESC
            LIMIT 200
            """,
            (uid, uid), fetch=True
        ) or []

        topics = [{
            "topic": r["topic"] or "General",
            "last_at": str(r["last_at"]),
            "count": int(r["cnt"] or 0),
        } for r in rows]
        return JSONResponse(content=topics)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/chat-by-id/{cid}")
def api_chat_by_id(cid: int, request: Request, user_id: int | None = None):
    try:
        uid = _resolve_uid(request, user_id)
        rows = _exec_sql(
            "SELECT id, topic, role, message, created_at, archived, share_token "
            "FROM chat_history WHERE id=%s AND user_id=%s",
            (cid, uid), fetch=True
        ) or []
        if not rows:
            return JSONResponse(status_code=404, content={"error": "not found"})
        r = rows[0]
        if int(r.get("archived", 0) or 0) == 1:
            return JSONResponse(status_code=410, content={"error": "archived"})
        return JSONResponse(content={
            "id": r["id"],
            "topic": r["topic"] or "General",
            "client_name": r["client_name"],
            "role": r["role"],
            "message": r["message"] or "",
            "created_at": str(r["created_at"]),
            "share_token": r.get("share_token"),
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/chat-thread")
def api_chat_thread(request: Request, topic: str, user_id: int | None = None):
    """Full thread (user + assistant only) for a topic, ordered asc, scoped to user."""
    try:
        uid = _resolve_uid(request, user_id)
        rows = _exec_sql(
            "SELECT id, topic,client_name, role, message, created_at "
            "FROM chat_history "
            "WHERE user_id=%s AND topic=%s AND archived=0 AND role!='report' "
            "ORDER BY id ASC LIMIT 500",
            (uid, topic), fetch=True
        ) or []
        data = [{
            "id": r["id"],
            "role": r["role"],
            "message": r["message"] or "",
            "created_at": str(r["created_at"]),
        } for r in rows]
        return JSONResponse(content=data)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ----------------------------------------------------------------------
# Actions
# ----------------------------------------------------------------------

@app.post("/api/history/action")
def api_history_action(payload: dict = Body(...)):
    try:
        kind = payload.get("kind")              # "report" | "chat" | "topic"
        action = payload.get("action")          # "share" | "rename" | "archive" | "delete"
        item_id = payload.get("id")
        value = payload.get("value")            # for topic name / rename

        if kind not in ("report", "chat", "topic"):
            return JSONResponse(status_code=400, content={"error": "invalid kind"})

        # ---------- TOPIC-WIDE ACTIONS (affect both research_topics & chat_history) ----------
        if kind == "topic":
            if not isinstance(value, str) or not value.strip():
                return JSONResponse(status_code=400, content={"error": "topic value required"})
            topic = value.strip()

            if action == "delete":
                _exec_sql("DELETE FROM chat_history WHERE topic=%s", (topic,))
                _exec_sql("DELETE FROM research_topics WHERE topic=%s", (topic,))
                return JSONResponse(content={"ok": True})

            if action == "archive":
                _exec_sql("UPDATE chat_history SET archived=1 WHERE topic=%s", (topic,))
                _exec_sql("UPDATE research_topics SET archived=1 WHERE topic=%s", (topic,))
                return JSONResponse(content={"ok": True})

            if action == "rename":
                new_name = payload.get("new_name") or payload.get("newTopic") or payload.get("value_new")
                if not isinstance(new_name, str) or not new_name.strip():
                    return JSONResponse(status_code=400, content={"error": "new topic name required"})
                new_name = new_name.strip()
                _exec_sql("UPDATE chat_history SET topic=%s WHERE topic=%s", (new_name, topic))
                _exec_sql("UPDATE research_topics SET topic=%s WHERE topic=%s", (new_name, topic))
                return JSONResponse(content={"ok": True})

            return JSONResponse(status_code=400, content={"error": "invalid action for topic"})

        # ---------- PER-ROW ACTIONS (existing) ----------
        if not isinstance(item_id, int):
            try:
                item_id = int(item_id)
            except Exception:
                return JSONResponse(status_code=400, content={"error": "invalid id"})

        if action == "rename":
            if kind == "report":
                _exec_sql("UPDATE research_topics SET topic=%s WHERE id=%s", (value, item_id))
            else:
                _exec_sql("UPDATE chat_history SET topic=%s WHERE id=%s", (value, item_id))
            return JSONResponse(content={"ok": True})

        if action == "archive":
            if kind == "report":
                _exec_sql("UPDATE research_topics SET archived=1 WHERE id=%s", (item_id,))
            else:
                _exec_sql("UPDATE chat_history SET archived=1 WHERE id=%s", (item_id,))
            return JSONResponse(content={"ok": True})

        if action == "delete":
            if kind == "report":
                # Cascade: delete report and all chats for same topic
                row = _exec_sql("SELECT topic FROM research_topics WHERE id=%s", (item_id,), fetch=True) or []
                _exec_sql("DELETE FROM research_topics WHERE id=%s", (item_id,))
                if row:
                    _exec_sql("DELETE FROM chat_history WHERE topic=%s", (row[0]["topic"],))
                return JSONResponse(content={"ok": True})

            else:  # kind == "chat"
                # Cascade: delete whole chat thread for that topic and any reports for that topic
                row = _exec_sql("SELECT topic FROM chat_history WHERE id=%s", (item_id,), fetch=True) or []
                _exec_sql("DELETE FROM chat_history WHERE id=%s", (item_id,))
                if row:
                    topic = row[0]["topic"]
                    _exec_sql("DELETE FROM chat_history WHERE topic=%s", (topic,))
                    _exec_sql("DELETE FROM research_topics WHERE topic=%s", (topic,))
                return JSONResponse(content={"ok": True})

        if action == "share":
            token = secrets.token_urlsafe(16)
            if kind == "report":
                _exec_sql("UPDATE research_topics SET share_token=%s WHERE id=%s", (token, item_id))
            else:
                _exec_sql("UPDATE chat_history SET share_token=%s WHERE id=%s", (token, item_id))
            return JSONResponse(content={"ok": True, "share_url": f"/share/{token}"})

        return JSONResponse(status_code=400, content={"error": "invalid action"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/share/{token}", response_class=HTMLResponse)
def share_view(token: str):
    try:
        r = _exec_sql(
            "SELECT 'report' AS kind, id, topic, research AS content, created_at "
            "FROM research_topics WHERE share_token=%s",
            (token,), fetch=True
        )
        if r:
            row = r[0]
            html = f"""
            <html><head><title>Shared Report</title></head>
            <body style="font-family:Arial;padding:20px;max-width:900px;margin:auto;">
              <h2>{row['topic']}</h2>
              <div style="white-space:pre-wrap;border:1px solid #ddd;padding:12px;border-radius:6px;">{row['content']}</div>
              <p style="color:#666">Shared report • Created at {row['created_at']}</p>
            </body></html>"""
            return HTMLResponse(content=html)

        c = _exec_sql(
            "SELECT 'chat' AS kind, id, topic, role, message AS content, created_at "
            "FROM chat_history WHERE share_token=%s",
            (token,), fetch=True
        )
        if c:
            row = c[0]
            html = f"""
            <html><head><title>Shared Chat</title></head>
            <body style="font-family:Arial;padding:20px;max-width:900px;margin:auto;">
              <h2>Conversation: {row['topic'] or 'General'}</h2>
              <p><b>{row['role']}:</b></p>
              <div style="white-space:pre-wrap;border:1px solid #ddd;padding:12px;border-radius:6px;">{row['content']}</div>
              <p style="color:#666">Shared message • Created at {row['created_at']}</p>
            </body></html>"""
            return HTMLResponse(content=html)

        return HTMLResponse("<h3>Invalid or expired share link.</h3>", status_code=404)
    except Exception as e:
        return HTMLResponse(f"<h3>Error: {e}</h3>", status_code=500)

# ----------------------------------------------------------------------
# Run
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)