"""Webhook endpoint for ingesting WhatsApp-like messages."""
import hmac
import hashlib
from fastapi import APIRouter, Request, Response, Header, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from app.config import settings
from app.storage import insert_message
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class WebhookMessage(BaseModel):
    """Pydantic model for webhook message validation."""
    message_id: str = Field(..., min_length=1)
    from_: str = Field(..., alias="from")
    to: str
    ts: str
    text: Optional[str] = Field(None, max_length=4096)
    
    @field_validator("from_", "to")
    @classmethod
    def validate_msisdn(cls, v: str) -> str:
        """Validate E.164-like format: starts with +, then digits only."""
        if not v.startswith("+"):
            raise ValueError("must start with +")
        if not v[1:].isdigit():
            raise ValueError("must contain only digits after +")
        return v
    
    @field_validator("ts")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate ISO-8601 UTC timestamp with Z suffix."""
        if not v.endswith("Z"):
            raise ValueError("must end with Z")
        try:
            from datetime import datetime
            datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("must be valid ISO-8601 UTC timestamp")
        return v


def verify_signature(body: bytes, signature_header: Optional[str]) -> bool:
    """
    Verify HMAC-SHA256 signature.
    
    Args:
        body: Raw request body bytes
        signature_header: X-Signature header value
    
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature_header:
        return False
    
    if not settings.webhook_secret:
        return False
    
    # Compute expected signature
    expected_sig = hmac.new(
        settings.webhook_secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected_sig, signature_header)


@router.post("/webhook")
async def webhook(
    request: Request,
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
):
    """
    Ingest inbound WhatsApp-like messages with HMAC signature validation.
    
    Returns 200 on success (created or duplicate), 401 on invalid signature,
    422 on validation error.
    """
    # Read raw body for signature verification
    body_bytes = await request.body()
    
    # Verify signature
    if not verify_signature(body_bytes, x_signature):
        # Track metrics
        from app.routes.metrics import http_requests_total, webhook_requests_total
        http_requests_total.labels(path="/webhook", status=401).inc()
        webhook_requests_total.labels(result="invalid_signature").inc()
        # Log error
        log_record = logging.LogRecord(
            name="webhook",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Invalid signature",
            args=(),
            exc_info=None,
        )
        log_record.request_id = getattr(request.state, "request_id", "unknown")
        log_record.method = request.method
        log_record.path = request.url.path
        log_record.status = 401
        log_record.result = "invalid_signature"
        logger.handle(log_record)
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid signature"
        )
    
    # Parse and validate JSON
    import json
    try:
        data = json.loads(body_bytes.decode('utf-8'))
        message = WebhookMessage(**data)
    except Exception as e:
        # Log validation error
        log_record = logging.LogRecord(
            name="webhook",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg=f"Validation error: {str(e)}",
            args=(),
            exc_info=None,
        )
        log_record.request_id = getattr(request.state, "request_id", "unknown")
        log_record.method = request.method
        log_record.path = request.url.path
        log_record.status = 422
        log_record.result = "validation_error"
        log_record.message_id = data.get("message_id", "unknown") if isinstance(data, dict) else "unknown"
        logger.handle(log_record)
        
        # Track metrics
        from app.routes.metrics import http_requests_total, webhook_requests_total
        http_requests_total.labels(path="/webhook", status=422).inc()
        webhook_requests_total.labels(result="validation_error").inc()
        
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    
    # Insert message (handles idempotency)
    is_new, result = insert_message(
        message_id=message.message_id,
        from_msisdn=message.from_,
        to_msisdn=message.to,
        ts=message.ts,
        text=message.text,
    )
    
    # Log webhook request
    log_record = logging.LogRecord(
        name="webhook",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Webhook processed",
        args=(),
        exc_info=None,
    )
    log_record.request_id = getattr(request.state, "request_id", "unknown")
    log_record.method = request.method
    log_record.path = request.url.path
    log_record.status = 200
    log_record.result = result
    log_record.message_id = message.message_id
    log_record.dup = not is_new
    logger.handle(log_record)
    
    # Track metrics
    from app.routes.metrics import http_requests_total, webhook_requests_total
    http_requests_total.labels(path="/webhook", status=200).inc()
    webhook_requests_total.labels(result=result).inc()
    
    return {"status": "ok"}

