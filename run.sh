#!/bin/bash
# Local development server startup script

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Set default environment variables if not set
export WEBHOOK_SECRET=${WEBHOOK_SECRET:-"dev-secret-key"}
export DATABASE_URL=${DATABASE_URL:-"sqlite:///./data/app.db"}
export LOG_LEVEL=${LOG_LEVEL:-"INFO"}

# Create data directory
mkdir -p data

# Run the server
echo "Starting server on http://localhost:8000"
echo "Press Ctrl+C to stop"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

