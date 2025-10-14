# backend/auth/db.py
import os
from mysql.connector import pooling, Error as MySQLError

_DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "market_research"),
}
_pool = None

def _get_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="auth_pool",
            pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
            **_DB_CONFIG
        )
    return _pool

def exec_sql(q, params=None, fetch=False):
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

def ensure_users_table():
    # Create users table if missing + add columns when upgrading
    exec_sql("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            plan_type ENUM('FREE','BASIC','PRO') DEFAULT 'FREE',
            status ENUM('ACTIVE','INACTIVE','SUSPENDED') DEFAULT 'ACTIVE',
            register_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP NULL,
            last_password_change TIMESTAMP NULL,
            failed_logins INT DEFAULT 0,
            is_verified TINYINT(1) DEFAULT 0
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    # idempotent safe ALTERs
    for alter in [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_type ENUM('FREE','BASIC','PRO') DEFAULT 'FREE'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS status ENUM('ACTIVE','INACTIVE','SUSPENDED') DEFAULT 'ACTIVE'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS register_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP NULL",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_password_change TIMESTAMP NULL",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_logins INT DEFAULT 0",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified TINYINT(1) DEFAULT 0",
    ]:
        try:
            exec_sql(alter)
        except Exception:
            # MySQL <8.0 doesn't support IF NOT EXISTS for all clauses; ignore if already exists
            pass
