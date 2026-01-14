"""Statistics endpoint for message analytics."""
from fastapi import APIRouter
from app.storage import get_stats

router = APIRouter()


@router.get("/stats")
async def stats():
    """
    Provide simple message-level analytics.
    
    Returns:
    - total_messages: Total number of messages
    - senders_count: Number of unique senders
    - messages_per_sender: Top 10 senders by message count
    - first_message_ts: Timestamp of first message (null if none)
    - last_message_ts: Timestamp of last message (null if none)
    """
    return get_stats()

