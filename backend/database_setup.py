# Market Research\database_setup.py
import os
import logging
from typing import Optional
from fastapi import Request, HTTPException
from mysql.connector import pooling, Error as MySQLError

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# DB CONFIGURATION
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
    """Create or fetch MySQL connection pool."""
    global _db_pool
    if _db_pool is None:
        _db_pool = pooling.MySQLConnectionPool(
            pool_name="mr_web_pool",
            pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
            **_DB_CONFIG
        )
    return _db_pool

def _exec_sql(q: str, params=None, fetch: bool = False):
    """
    Execute an SQL query safely using the connection pool.
    - Use fetch=True if you want results.
    """
    cnx = cur = None
    try:
        cnx = _get_pool().get_connection()
        cur = cnx.cursor(dictionary=True)
        cur.execute(q, params or ())
        if fetch:
            return cur.fetchall()
        cnx.commit()
    except MySQLError as e:
        logger.error(f"MySQL Error: {e}")
        raise RuntimeError(f"MySQL error: {e}")
    finally:
        try:
            if cur:
                cur.close()
            if cnx:
                cnx.close()
        except Exception:
            pass

# ----------------------------------------------------------------------
# AUTHENTICATION: Resolve User ID
# ----------------------------------------------------------------------

def _resolve_uid(request: Request, user_id: Optional[int] = None) -> int:
    """
    Resolve the logged-in user's ID.
    Priority:
      1. Explicit user_id param.
      2. Cookie-based session.
    Raises HTTP 401 if user is not authenticated.
    """

    # 1. If user_id explicitly provided → trust it
    if isinstance(user_id, int):
        return user_id

    # 2. Check cookies for session-based authentication
    try:
        cookie_user_id = request.cookies.get("user_id")
        if cookie_user_id:
            try:
                return int(cookie_user_id)
            except ValueError:
                raise HTTPException(status_code=401, detail="Invalid user_id in cookie")
    except Exception:
        pass

    # 3. If still missing, reject request
    raise HTTPException(status_code=401, detail="Not authenticated (user_id missing)")

# ----------------------------------------------------------------------
# DATABASE INIT (ONE-TIME SCHEMA ENSURE)
# ----------------------------------------------------------------------

def _ensure_tables():
    """
    Ensures that required tables exist.
    Uses your existing schema for:
    - users
    - chat_history
    - research_topics
    """
    logger.info("Checking required tables...")

    # Check users table
    _exec_sql("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            status ENUM('ACTIVE','INACTIVE','SUSPENDED') DEFAULT 'ACTIVE',
            last_login DATETIME DEFAULT NULL,
            register_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            plan_type ENUM('FREE','BASIC','PRO') DEFAULT 'FREE'
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # Check research_topics table
    _exec_sql("""
        CREATE TABLE IF NOT EXISTS research_topics (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT DEFAULT NULL,
            topic VARCHAR(255) NOT NULL,
            research LONGTEXT,
            remark VARCHAR(20) DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            archived TINYINT(1) DEFAULT 0,
            share_token VARCHAR(64) DEFAULT NULL,
            record_type ENUM('report','chat') NOT NULL DEFAULT 'report',
            role ENUM('user','assistant') DEFAULT NULL,
            parent_id INT DEFAULT NULL,
            KEY idx_rt_parent (parent_id),
            KEY idx_rt_topic (topic),
            KEY idx_rt_user_id (user_id),
            CONSTRAINT fk_research_topics_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # Check chat_history table
    _exec_sql("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT DEFAULT NULL,
            topic VARCHAR(255),
            role ENUM('user','assistant','report') NOT NULL,
            message LONGTEXT,
            remark TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            archived TINYINT(1) DEFAULT 0,
            share_token VARCHAR(64) DEFAULT NULL,
            KEY idx_chat_user_id (user_id),
            CONSTRAINT fk_chat_history_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL ON UPDATE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

        # --- sectors master ---
    _exec_sql("""
        CREATE TABLE IF NOT EXISTS sectors (
            sector_id INT AUTO_INCREMENT PRIMARY KEY,
            sector_name VARCHAR(100) NOT NULL UNIQUE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # --- product categories linked to sectors ---
    _exec_sql("""
        CREATE TABLE IF NOT EXISTS product_categories (
            category_id INT AUTO_INCREMENT PRIMARY KEY,
            sector_id INT NOT NULL,
            category_name VARCHAR(150) NOT NULL,
            CONSTRAINT fk_pc_sector
              FOREIGN KEY (sector_id) REFERENCES sectors(sector_id)
              ON DELETE CASCADE ON UPDATE CASCADE,
            CONSTRAINT uq_sector_category UNIQUE (sector_id, category_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
        # Seed sectors (idempotent)
    _exec_sql("""
        INSERT INTO sectors (sector_name) VALUES
        ('Automotive'), ('Healthcare'), ('Technology'), ('Finance'),
        ('Retail'), ('Energy'), ('Telecom'), ('FMCG'), ('Pharma')
        ON DUPLICATE KEY UPDATE sector_name = VALUES(sector_name);
    """)

    # Seed sample categories for each sector (idempotent by UNIQUE(sector_id, category_name))
    _exec_sql("""
        INSERT INTO product_categories (sector_id, category_name)
        SELECT s.sector_id, v.category_name
        FROM (
          SELECT 'Automotive' AS sector_name, 'Passenger Vehicles' AS category_name UNION ALL
          SELECT 'Automotive','Commercial Vehicles' UNION ALL
          SELECT 'Automotive','Auto Components' UNION ALL

          SELECT 'Healthcare','Medical Devices' UNION ALL
          SELECT 'Healthcare','Hospitals & Clinics' UNION ALL
          SELECT 'Healthcare','Pharmaceutical Services' UNION ALL

          SELECT 'Technology','Software' UNION ALL
          SELECT 'Technology','Hardware' UNION ALL
          SELECT 'Technology','AI & Cloud Solutions' UNION ALL

          SELECT 'Finance','Banking' UNION ALL
          SELECT 'Finance','Insurance' UNION ALL
          SELECT 'Finance','Investment Services' UNION ALL

          SELECT 'Retail','E-commerce' UNION ALL
          SELECT 'Retail','Supermarkets' UNION ALL
          SELECT 'Retail','Fashion & Apparel' UNION ALL

          SELECT 'Energy','Renewables' UNION ALL
          SELECT 'Energy','Oil & Gas' UNION ALL
          SELECT 'Energy','Power Generation' UNION ALL

          SELECT 'Telecom','Mobile Services' UNION ALL
          SELECT 'Telecom','Broadband' UNION ALL
          SELECT 'Telecom','Enterprise Solutions' UNION ALL

          SELECT 'FMCG','Food & Beverages' UNION ALL
          SELECT 'FMCG','Personal Care' UNION ALL
          SELECT 'FMCG','Household Products' UNION ALL

          SELECT 'Pharma','Generic Drugs' UNION ALL
          SELECT 'Pharma','Biotech' UNION ALL
          SELECT 'Pharma','Nutraceuticals'
        ) v
        JOIN sectors s ON s.sector_name = v.sector_name
        ON DUPLICATE KEY UPDATE category_name = VALUES(category_name);
    """)


    logger.info("Tables ensured successfully.")
