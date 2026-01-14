"""Pytest configuration and fixtures."""
import pytest
import os
import tempfile
from app.config import settings
from app.models import init_db, get_db_path


@pytest.fixture(scope="function")
def test_db(monkeypatch):
    """Create a temporary test database for each test."""
    # Create a temporary database file
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Set the database URL to the temp file
    db_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    settings.database_url = db_url
    
    # Initialize the database
    init_db()
    
    yield db_path
    
    # Cleanup: remove the temporary database file
    try:
        os.unlink(db_path)
    except Exception:
        pass


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch, test_db):
    """Set up test environment variables."""
    monkeypatch.setenv("WEBHOOK_SECRET", "testsecret")
    monkeypatch.setenv("DATABASE_URL", settings.database_url)
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    settings.webhook_secret = "testsecret"
    yield
    # Cleanup
    settings.webhook_secret = None

