"""Messages listing endpoint with pagination and filters."""
from fastapi import APIRouter, Query
from typing import Optional
from app.storage import get_messages

router = APIRouter()


@router.get("/messages")
async def list_messages(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    from_: Optional[str] = Query(None, alias="from"),
    since: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
):
    """
    List stored messages with pagination and filters.
    
    Query parameters:
    - limit: Number of results (1-100, default 50)
    - offset: Pagination offset (default 0)
    - from: Filter by sender MSISDN (exact match)
    - since: Filter by timestamp (ISO-8601 UTC, returns messages with ts >= since)
    - q: Free-text search in message text (case-insensitive substring)
    
    Results are ordered by ts ASC, message_id ASC.
    """
    messages, total = get_messages(
        limit=limit,
        offset=offset,
        from_msisdn=from_,
        since=since,
        q=q,
    )
    
    return {
        "data": messages,
        "total": total,
        "limit": limit,
        "offset": offset,
    }

