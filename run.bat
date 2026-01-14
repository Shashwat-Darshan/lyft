@echo off
REM Local development server startup script for Windows

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Set default environment variables if not set
if "%WEBHOOK_SECRET%"=="" set WEBHOOK_SECRET=dev-secret-key
if "%DATABASE_URL%"=="" set DATABASE_URL=sqlite:///./data/app.db
if "%LOG_LEVEL%"=="" set LOG_LEVEL=INFO

REM Create data directory
if not exist "data" mkdir data

REM Run the server
echo Starting server on http://localhost:8000
echo Press Ctrl+C to stop
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

