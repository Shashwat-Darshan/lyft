"""Structured JSON logging utilities."""
import json
import time
import uuid
from datetime import datetime
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

# Configure root logger to output JSON
logger = logging.getLogger()
handler = logging.StreamHandler()

# Set log level from environment (will be updated in main.py)
def configure_logging(level: str = "INFO"):
    """Configure logging level."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    handler.setLevel(log_level)

configure_logging()


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs JSON logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "method"):
            log_data["method"] = record.method
        if hasattr(record, "path"):
            log_data["path"] = record.path
        if hasattr(record, "status"):
            log_data["status"] = record.status
        if hasattr(record, "latency_ms"):
            log_data["latency_ms"] = record.latency_ms
        if hasattr(record, "message_id"):
            log_data["message_id"] = record.message_id
        if hasattr(record, "dup"):
            log_data["dup"] = record.dup
        if hasattr(record, "result"):
            log_data["result"] = record.result
        
        return json.dumps(log_data)


handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
logger.propagate = False


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log requests in JSON format."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Store request_id in request state
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Calculate latency
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Track metrics
        try:
            from app.routes.metrics import http_requests_total, request_latency_ms
            http_requests_total.labels(
                path=request.url.path,
                status=response.status_code
            ).inc()
            request_latency_ms.observe(latency_ms)
        except Exception:
            # Metrics might not be initialized yet, ignore
            pass
        
        # Create log record
        log_record = logging.LogRecord(
            name="http",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="",
            args=(),
            exc_info=None,
        )
        log_record.request_id = request_id
        log_record.method = request.method
        log_record.path = request.url.path
        log_record.status = response.status_code
        log_record.latency_ms = latency_ms
        
        logger.handle(log_record)
        
        return response

