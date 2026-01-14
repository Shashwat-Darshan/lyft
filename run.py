#!/usr/bin/env python3
"""Local development server runner."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_config=None,  # Use our custom JSON logging
    )

