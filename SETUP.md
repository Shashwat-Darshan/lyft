# Setup Guide - From Scratch

This guide will help you set up and run the WhatsApp-like Message Service locally.

## Prerequisites Check

First, verify you have Python installed:

```bash
python --version
# OR
python3 --version
```

You need **Python 3.11 or higher**. If you don't have Python, download it from [python.org](https://www.python.org/downloads/).

## Step-by-Step Setup

### Step 1: Navigate to Project Directory

Open your terminal/command prompt and navigate to the project folder:

```bash
cd C:\Users\shash\OneDrive\Desktop\Projects\backendProject\cursor\lyft
```

### Step 2: Create Virtual Environment

A virtual environment isolates your project dependencies:

**Windows:**
```cmd
python -m venv venv
```

**Linux/Mac:**
```bash
python3 -m venv venv
```

### Step 3: Activate Virtual Environment

**Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
venv\Scripts\activate.bat
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

You should see `(venv)` at the beginning of your command prompt when activated.

### Step 4: Install Dependencies

With the virtual environment activated, install all required packages:

```bash
pip install -r requirements.txt
```

This will install:
- FastAPI
- Uvicorn (ASGI server)
- Pydantic (validation)
- Prometheus client
- And other dependencies

### Step 5: Create Data Directory

Create a directory for the SQLite database:

**Windows:**
```cmd
mkdir data
```

**Linux/Mac:**
```bash
mkdir -p data
```

### Step 6: Set Environment Variables

You need to set the `WEBHOOK_SECRET` environment variable. Choose one method:

#### Option A: Set for Current Session (Temporary)

**Windows (PowerShell):**
```powershell
$env:WEBHOOK_SECRET="my-secret-key-123"
$env:DATABASE_URL="sqlite:///./data/app.db"
$env:LOG_LEVEL="INFO"
```

**Windows (CMD):**
```cmd
set WEBHOOK_SECRET=my-secret-key-123
set DATABASE_URL=sqlite:///./data/app.db
set LOG_LEVEL=INFO
```

**Linux/Mac:**
```bash
export WEBHOOK_SECRET="my-secret-key-123"
export DATABASE_URL="sqlite:///./data/app.db"
export LOG_LEVEL="INFO"
```

#### Option B: Create .env File (Recommended)

Create a file named `.env` in the project root:

```bash
# .env file
WEBHOOK_SECRET=my-secret-key-123
DATABASE_URL=sqlite:///./data/app.db
LOG_LEVEL=INFO
```

The app will automatically read from this file.

### Step 7: Start the Server

Now you can start the server using any of these methods:

#### Method 1: Using the Python Script (Easiest)
```bash
python run.py
```

#### Method 2: Using uvicorn directly
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Method 3: Using Python module
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Method 4: Using Make (if you have Make installed)
```bash
make dev
```

You should see output like:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Step 8: Verify It's Working

Open a new terminal window and test the health endpoint:

```bash
curl http://localhost:8000/health/live
```

Or open in your browser: http://localhost:8000/health/live

You should see:
```json
{"status":"ok"}
```

## Quick Reference Commands

### Starting the Server
```bash
# Activate venv first
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

# Set environment variables
export WEBHOOK_SECRET="my-secret-key"  # Linux/Mac
# OR
$env:WEBHOOK_SECRET="my-secret-key"    # Windows PowerShell

# Start server
python run.py
```

### Stopping the Server
Press `Ctrl+C` in the terminal where the server is running.

### Deactivating Virtual Environment
```bash
deactivate
```

## Troubleshooting

### "python: command not found"
- Use `python3` instead of `python` on Linux/Mac
- Make sure Python is installed and in your PATH

### "pip: command not found"
- Try `python -m pip` or `python3 -m pip`
- Make sure pip is installed with Python

### "ModuleNotFoundError"
- Make sure virtual environment is activated
- Run `pip install -r requirements.txt` again

### "WEBHOOK_SECRET not set" error
- Make sure you've set the environment variable
- Check that it's set in the same terminal session where you're running the server

### Port 8000 already in use
- Change the port: `uvicorn app.main:app --host 0.0.0.0 --port 8001`
- Or stop the process using port 8000

## Next Steps

Once the server is running:

1. **Test health endpoints:**
   ```bash
   curl http://localhost:8000/health/live
   curl http://localhost:8000/health/ready
   ```

2. **View API documentation:**
   Open http://localhost:8000/docs in your browser

3. **Test the webhook endpoint:**
   See the README.md for examples of how to send webhook requests

## Need Help?

- Check the main README.md for API documentation
- Review the logs in the terminal where the server is running
- All logs are in JSON format for easy parsing

