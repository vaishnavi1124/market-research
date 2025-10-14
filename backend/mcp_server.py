# mcp_server.py
import os
import sys
import json
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import requests
from pinecone import Pinecone
import uuid
import google.generativeai as genai
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import plotly.express as px
from utils.Report_Save_to_pdf import save_to_pdf as pro_save_to_pdf

# ---------------- NEW: DB imports ----------------
# Uses mysql-connector-python (pip install mysql-connector-python)
import mysql.connector
from mysql.connector import pooling, Error as MySQLError

# ---------------- MODIFIED EMAIL TOOL IMPORTS START ----------------
# Imports for sending email with attachments
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
# ---------------- MODIFIED EMAIL TOOL IMPORTS END ----------------


load_dotenv()
mcp = FastMCP("Market-Research-Server")

# ---------------- GENAI / PINECONE ----------------
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index_name = "sentiment-index"

try:
    pc.create_index(
        name=index_name,
        dimension=768,
        metric="cosine",
        spec=pc.ServerlessSpec(cloud="aws", region="us-east-1"),
    )
except Exception:
    # Index may already exist
    pass

index = pc.Index(index_name)

# ---------------- Tavily API Setup ----------------
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TAVILY_URL = "https://api.tavily.com/search"

# ---------------- MCP Tool: Tavily Search ----------------
@mcp.tool()
def tavily_search(query: str, result_limit: int = 10) -> str:
    """Perform web search via Tavily API and return structured results"""
    try:
        payload = {"query": query, "num_results": result_limit}
        headers = {
            "Authorization": f"Bearer {TAVILY_API_KEY}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            TAVILY_URL, headers=headers, json=payload, timeout=15
        )
        response.raise_for_status()
        data = response.json()

        output = []
        if "results" in data:
            output.append("🔍 Tavily Search Results:")
            for idx, result in enumerate(data["results"][:result_limit], 1):
                output.append(
                    f"{idx}. {result.get('title', 'No title')}\n"
                    f"   📌 {result.get('url', 'No URL')}\n"
                    f"   📝 {result.get('content', 'No description')}\n"
                )

        if data.get("answer"):
            output.append("\n💡 Tavily Suggested Answer:")
            output.append(data["answer"])

        return "\n".join(output) if output else "No results found"

    except Exception as e:
        return f"❌ Tavily API Error: {str(e)}"

# ---------------- MCP Tool: Tavily Schema ----------------
@mcp.tool()
def get_tavily_schema() -> str:
    """Returns the structure of Tavily API response for reference"""
    return json.dumps(
        {
            "query": "string",
            "answer": "string | null",
            "results": [
                {"title": "string", "url": "string", "content": "string"}
            ],
        },
        indent=2,
    )

# ---------------- MCP Tool: Save to Professional PDF ----------------
@mcp.tool()
def save_to_pdf(content: str, filename: str) -> str:
    """Wrapper to call the professional save_to_pdf from Report_Save_to_pdf."""
    return pro_save_to_pdf(content, filename)

# ---------------- MCP Tool: RAG query ----------------
@mcp.tool()
def rag_mcp_tool(query: str, top_k: int = 3) -> str:
    """Retrieve relevant research from the vector database using semantic search"""
    try:
        embedding = genai.embed_content(
            model="models/embedding-001",
            content=query,
            task_type="retrieval_query",
        )["embedding"]

        results = index.query(vector=embedding, top_k=top_k, include_metadata=True)

        if not results.matches:
            return "No relevant research found in the database."

        output = []
        for match in results.matches:
            meta = match.get("metadata", {})
            topic = meta.get("topic", "Unknown Topic")
            text = meta.get("text", "No content available")
            score = match["score"] if isinstance(match, dict) else match.score
            output.append(
                f"Topic: {topic}\nScore: {float(score):.4f}\nContent:\n{text}\n---"
            )

        return "\n".join(output) if output else "No relevant research found in the database."
    except Exception as e:
        return f"❌ RAG Error: {str(e)}. Please check the Pinecone index or query parameters."

# ---------------- Internal: RAG Upsert ----------------
def rag_upsert(content: str, topic: str) -> str:
    try:
        embedding = genai.embed_content(
            model="models/embedding-001",
            content=content,
            task_type="retrieval_document",
        )["embedding"]

        vid = str(uuid.uuid4())
        index.upsert(
            vectors=[
                {
                    "id": vid,
                    "values": embedding,
                    "metadata": {"topic": topic, "text": content},
                }
            ]
        )
        return f"✅ Upserted {vid}"
    except Exception as e:
        return f"❌ Upsert Error: {str(e)}"

# =======================  DATABASE BOOTSTRAP  =======================
DB_NAME = os.getenv("DB_NAME", "market_research")

# server-level config (no database yet; we need to create it if missing)
_DB_SERVER_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
}

def _ensure_database_and_tables():
    """Idempotently create database and required tables if they don't exist."""
    # 1) Ensure database exists
    try:
        server_cnx = mysql.connector.connect(**_DB_SERVER_CONFIG)
        server_cnx.autocommit = True
        cur = server_cnx.cursor()
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;"
        )
        cur.close()
        server_cnx.close()
    except MySQLError as e:
        raise RuntimeError(f"Failed to ensure database: {e}")

    # 2) Ensure tables inside DB
    try:
        db_cnx = mysql.connector.connect(database=DB_NAME, **_DB_SERVER_CONFIG)
        db_cnx.autocommit = True
        cur = db_cnx.cursor()

        # users
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS `users` (
              `user_id` INT NOT NULL AUTO_INCREMENT,
              `email` VARCHAR(255) NOT NULL,
              `password_hash` VARCHAR(255) NOT NULL,
              `full_name` VARCHAR(255) DEFAULT NULL,
              `status` ENUM('ACTIVE','INACTIVE','SUSPENDED') DEFAULT 'ACTIVE',
              `last_login` DATETIME DEFAULT NULL,
              `register_date` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              `plan_type` ENUM('FREE','BASIC','PRO') DEFAULT 'FREE',
              PRIMARY KEY (`user_id`),
              UNIQUE KEY `email` (`email`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """
        )

        # research_topics
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS `research_topics` (
              `id` INT NOT NULL AUTO_INCREMENT,
              `user_id` INT DEFAULT NULL,
              `topic` VARCHAR(255) NOT NULL,
              `client_name` VARCHAR(255) DEFAULT NULL,
              `research` LONGTEXT,
              `remark` VARCHAR(20) DEFAULT NULL,
              `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
              `archived` TINYINT(1) NOT NULL DEFAULT '0',
              `share_token` VARCHAR(64) DEFAULT NULL,
              `record_type` ENUM('report','chat') NOT NULL DEFAULT 'report',
              `role` ENUM('user','assistant') DEFAULT NULL,
              `parent_id` INT DEFAULT NULL,
              PRIMARY KEY (`id`),
              KEY `idx_rt_parent` (`parent_id`),
              KEY `idx_rt_topic` (`topic`),
              KEY `idx_rt_user_id` (`user_id`),
              CONSTRAINT `fk_research_topics_user`
                FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
                ON DELETE SET NULL ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """
        )

        # chat_history
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS `chat_history` (
              `id` INT NOT NULL AUTO_INCREMENT,
              `user_id` INT DEFAULT NULL,
              `topic` VARCHAR(255) DEFAULT NULL,
               `client_name` VARCHAR(255) DEFAULT NULL,
              `role` ENUM('user','assistant','report') NOT NULL,
              `message` LONGTEXT,
              `remark` TEXT,
              `created_at` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
              `archived` TINYINT(1) DEFAULT '0',
              `share_token` VARCHAR(64) DEFAULT NULL,
              PRIMARY KEY (`id`),
              KEY `idx_chat_user_id` (`user_id`),
              CONSTRAINT `fk_chat_history_user`
                FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
                ON DELETE SET NULL ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
            """
        )

        cur.close()
        db_cnx.close()
    except MySQLError as e:
        raise RuntimeError(f"Failed to ensure tables: {e}")

# ensure DB + tables *before* pool creation
_ensure_database_and_tables()

# =======================  CONNECTION POOL + HELPERS  =======================
_DB_CONFIG = {
    **_DB_SERVER_CONFIG,
    "database": DB_NAME,
}

_connection_pool = None

def _get_pool():
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = pooling.MySQLConnectionPool(
            pool_name="mr_pool",
            pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
            **_DB_CONFIG,
        )
    return _connection_pool

def _exec_sql(query, params=None, fetch=False):
    """Helper to execute SQL safely with pooled connections."""
    cnx = None
    cursor = None
    try:
        pool = _get_pool()
        cnx = pool.get_connection()
        cursor = cnx.cursor(dictionary=True)
        cursor.execute(query, params or ())
        if fetch:
            rows = cursor.fetchall()
            return rows
        cnx.commit()
        return None
    except MySQLError as e:
        raise RuntimeError(f"MySQL error: {e}")
    finally:
        try:
            if cursor:
                cursor.close()
            if cnx:
                cnx.close()
        except Exception:
            pass

# =======================  DB MCP TOOLS  =======================
@mcp.tool()
def db_insert_writer_report(user_id: int, topic: str, research: str, client_name: str, pdf_extract: str) -> str:
    """
    Insert a writer agent report into market_research.research_topics,
    including client_name and the extracted PDF text.
    Returns the inserted row id.
    """
    try:
        _exec_sql(
            "INSERT INTO research_topics (user_id, topic, research, client_name, pdf_extract) VALUES (%s, %s, %s, %s, %s)",
            (user_id, topic, research, client_name, pdf_extract),
        )
        row = _exec_sql(
            "SELECT id FROM research_topics WHERE user_id=%s AND topic=%s ORDER BY id DESC LIMIT 1",
            (user_id, topic),
            fetch=True,
        )
        new_id = row[0]["id"] if row else None
        return f"✅ Inserted report with id={new_id}"
    except Exception as e:
        return f"❌ DB Insert Error: {str(e)}"


@mcp.tool()
def db_update_writer_report(id: int, topic: str = None,client_name: str=None, research: str = None) -> str:
    """
    Update an existing report row by id. Provide either/both topic and research.
    """
    try:
        if topic is None and research is None:
            return "⚠️ Nothing to update. Provide topic and/or research."
        sets = []
        params = []
        if topic is not None:
            sets.append("topic=%s")
            params.append(topic)
        if client_name is not None:
            sets.append("client_name=%s")
            params.append(client_name)
        if research is not None:
            sets.append("research=%s")
            params.append(research)
        params.append(id)
        q = f"UPDATE research_topics SET {', '.join(sets)} WHERE id=%s"
        _exec_sql(q, tuple(params))
        return f"✅ Updated report id={id}"
    except Exception as e:
        return f"❌ DB Update Error: {str(e)}"

@mcp.tool()
def db_delete_writer_report(id: int) -> str:
    """
    Delete a report row by id.
    """
    try:
        _exec_sql("DELETE FROM research_topics WHERE id=%s", (id,))
        return f"✅ Deleted report id={id}"
    except Exception as e:
        return f"❌ DB Delete Error: {str(e)}"

@mcp.tool()
def db_get_reports(limit: int = 10, topic_like: str = None) -> str:
    """
    Optional listing helper (read). Not required, but handy for verification.
    """
    try:
        if topic_like:
            rows = _exec_sql(
                "SELECT id, topic, LEFT(research, 200) AS research_snippet, created_at "
                "FROM research_topics WHERE topic LIKE %s ORDER BY id DESC LIMIT %s",
                (f"%{topic_like}%", limit),
                fetch=True,
            )
        else:
            rows = _exec_sql(
                "SELECT id, topic, LEFT(research, 200) AS research_snippet, created_at "
                "FROM research_topics ORDER BY id DESC LIMIT %s",
                (limit,),
                fetch=True,
            )
        return json.dumps(rows or [], default=str, indent=2)
    except Exception as e:
        return f"❌ DB Get Error: {str(e)}"
    


# ---------------- UPDATED EMAIL TOOL START ----------------
@mcp.tool()
def send_email_to_user(user_id: int, subject: str, body: str, pdf_path: str = None) -> str:
    """
    Sends an email to a registered user based on their user_id.
    Optionally attaches a PDF file if pdf_path is provided.
    """
    try:
        # 1. Fetch the user's email from the database
        user_rows = _exec_sql(
            "SELECT email FROM users WHERE user_id = %s AND status = 'ACTIVE'",
            (user_id,),
            fetch=True
        )
        if not user_rows or not user_rows[0].get('email'):
            return f"❌ DB Error: Could not find an active user or email for user_id={user_id}"
        
        recipient_email = user_rows[0]['email']

        # 2. Get SMTP configuration from environment variables
        smtp_server = os.getenv("SMTP_SERVER")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_username = os.getenv("SMTP_USERNAME")
        smtp_password = os.getenv("SMTP_PASSWORD")

        if not all([smtp_server, smtp_port, smtp_username, smtp_password]):
            return "❌ Configuration Error: SMTP server settings are missing in your .env file."

        # 3. Construct the email message
        msg = MIMEMultipart()
        msg['From'] = smtp_username
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # 4. Attach the PDF if the path is provided and the file exists
        if pdf_path and os.path.exists(pdf_path):
            try:
                with open(pdf_path, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                
                encoders.encode_base64(part)
                filename = os.path.basename(pdf_path)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {filename}",
                )
                msg.attach(part)
            except Exception as e:
                # Log a warning but don't fail the entire process
                print(f"Warning: Could not attach PDF '{pdf_path}'. Error: {e}")


        # 5. Send the email using a secure connection
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)

        return f"✅ Email sent successfully to user {user_id} ({recipient_email})."
    
    except Exception as e:
        return f"❌ Email Sending Error: {str(e)}"
# ---------------- UPDATED EMAIL TOOL END ----------------

# -------------------------------  Run MCP server if invoked directly  -------------------------------
if __name__ == "__main__":
    print("✅ Market Research Server (Serper/Tavily + Pinecone) started...", flush=True)
    mcp.run("stdio")