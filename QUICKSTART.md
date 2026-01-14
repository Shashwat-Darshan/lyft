# Quick Start - 5 Minutes

Get the server running in 5 minutes!

## Windows

1. **Open PowerShell in the project folder**

2. **Create and activate virtual environment:**
   ```powershell
   python -m venv venv
   venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Set environment variable:**
   ```powershell
   $env:WEBHOOK_SECRET="dev-secret-123"
   $env:DATABASE_URL="sqlite:///./data/app.db"
   ```

5. **Create data folder:**
   ```powershell
   mkdir data
   ```

6. **Start server:**
   ```powershell
   python run.py
   ```

7. **Test it:**
   Open browser: http://localhost:8000/health/live

Done! 🎉

## Linux/Mac

1. **Open terminal in the project folder**

2. **Create and activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables:**
   ```bash
   export WEBHOOK_SECRET="dev-secret-123"
   export DATABASE_URL="sqlite:///./data/app.db"
   ```

5. **Create data folder:**
   ```bash
   mkdir -p data
   ```

6. **Start server:**
   ```bash
   python run.py
   ```

7. **Test it:**
   ```bash
   curl http://localhost:8000/health/live
   ```

Done! 🎉

## What's Next?

- View API docs: http://localhost:8000/docs
- Read full setup: [SETUP.md](SETUP.md)
- Read API docs: [README.md](README.md)

