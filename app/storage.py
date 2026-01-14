"""Database storage operations."""
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from app.models import get_db_connection


def insert_message(
    message_id: str,
    from_msisdn: str,
    to_msisdn: str,
    ts: str,
    text: Optional[str],
) -> Tuple[bool, str]:
    """
    Insert a message into the database.
    
    Returns:
        (is_new, result) where is_new is True if inserted, False if duplicate,
        and result is "created" or "duplicate"
    """
    created_at = datetime.utcnow().isoformat() + "Z"
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO messages (message_id, from_msisdn, to_msisdn, ts, text, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (message_id, from_msisdn, to_msisdn, ts, text, created_at))
            conn.commit()
            return (True, "created")
    except sqlite3.IntegrityError:
        # Duplicate message_id
        return (False, "duplicate")
    except Exception as e:
        raise


def get_messages(
    limit: int = 50,
    offset: int = 0,
    from_msisdn: Optional[str] = None,
    since: Optional[str] = None,
    q: Optional[str] = None,
) -> Tuple[List[Dict], int]:
    """
    Retrieve messages with pagination and filters.
    
    Returns:
        (messages_list, total_count)
    """
    
    # Build WHERE clause
    conditions = []
    params = []
    
    if from_msisdn:
        conditions.append("from_msisdn = ?")
        params.append(from_msisdn)
    
    if since:
        conditions.append("ts >= ?")
        params.append(since)
    
    if q:
        conditions.append("text LIKE ?")
        params.append(f"%{q}%")
    
    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    
    # Get total count
    with get_db_connection() as conn:
        cursor = conn.cursor()
        count_query = f"SELECT COUNT(*) as total FROM messages{where_clause}"
        cursor.execute(count_query, params)
        total = cursor.fetchone()["total"]
        
        # Get paginated results
        query = f"""
            SELECT message_id, from_msisdn as "from", to_msisdn as "to", ts, text
            FROM messages
            {where_clause}
            ORDER BY ts ASC, message_id ASC
            LIMIT ? OFFSET ?
        """
        cursor.execute(query, params + [limit, offset])
        rows = cursor.fetchall()
        
        messages = [
            {
                "message_id": row["message_id"],
                "from": row["from"],
                "to": row["to"],
                "ts": row["ts"],
                "text": row["text"],
            }
            for row in rows
        ]
        
        return (messages, total)


def get_stats() -> Dict:
    """Get message statistics."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Total messages
        cursor.execute("SELECT COUNT(*) as total FROM messages")
        total_messages = cursor.fetchone()["total"]
        
        # Unique senders count
        cursor.execute("SELECT COUNT(DISTINCT from_msisdn) as count FROM messages")
        senders_count = cursor.fetchone()["count"]
        
        # Messages per sender (top 10)
        cursor.execute("""
            SELECT from_msisdn as "from", COUNT(*) as count
            FROM messages
            GROUP BY from_msisdn
            ORDER BY count DESC
            LIMIT 10
        """)
        messages_per_sender = [
            {"from": row["from"], "count": row["count"]}
            for row in cursor.fetchall()
        ]
        
        # First and last message timestamps
        cursor.execute("SELECT MIN(ts) as first, MAX(ts) as last FROM messages")
        row = cursor.fetchone()
        first_message_ts = row["first"]
        last_message_ts = row["last"]
        
        return {
            "total_messages": total_messages,
            "senders_count": senders_count,
            "messages_per_sender": messages_per_sender,
            "first_message_ts": first_message_ts,
            "last_message_ts": last_message_ts,
        }

