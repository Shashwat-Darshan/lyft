"""Database models and schema initialization."""
import sqlite3
from typing import Optional
from contextlib import contextmanager
from app.config import settings


def get_db_path() -> str:
    """Extract database path from DATABASE_URL."""
    # sqlite:////data/app.db -> /data/app.db
    if settings.database_url.startswith("sqlite:///"):
        return settings.database_url.replace("sqlite:///", "", 1)
    return settings.database_url.replace("sqlite://", "", 1)


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize database schema."""
    db_path = get_db_path()
    
    # Ensure directory exists
    import os
    db_dir = os.path.dirname(db_path)
    if db_dir:  # Only create directory if path has a directory component
        os.makedirs(db_dir, exist_ok=True)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                from_msisdn TEXT NOT NULL,
                to_msisdn TEXT NOT NULL,
                ts TEXT NOT NULL,
                text TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()


def check_db_ready() -> bool:
    """Check if database is accessible and schema exists."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
            return cursor.fetchone() is not None
    except Exception:
        return False

