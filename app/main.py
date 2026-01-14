"""FastAPI application entry point."""
from fastapi import FastAPI
from app.config import settings
from app.models import init_db
from app.logging_utils import LoggingMiddleware
from app.routes import health, webhook, messages, stats, metrics
import logging

# Initialize logger
logger = logging.getLogger(__name__)

# Configure logging level
from app.logging_utils import configure_logging
configure_logging(settings.log_level)

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(
    title="WhatsApp-like Message Service",
    description="Production-style FastAPI service for ingesting and querying messages",
    version="1.0.0",
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Include routers
app.include_router(health.router)
app.include_router(webhook.router)
app.include_router(messages.router)
app.include_router(stats.router)
app.include_router(metrics.router)


@app.on_event("startup")
async def startup_event():
    """Validate configuration on startup."""
    if not settings.validate_webhook_secret():
        logger.error("WEBHOOK_SECRET is not set or empty. Service will not be ready.")
    logger.info("Application started")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        log_config=None,  # We use our own JSON logging
    )

