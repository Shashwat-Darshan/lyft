"""Tests for webhook endpoint."""
import pytest
import hmac
import hashlib
import json
from fastapi.testclient import TestClient
from app.main import app

# Create client per test to avoid state issues
@pytest.fixture
def client():
    return TestClient(app)


def compute_signature(secret: str, body: bytes) -> str:
    """Compute HMAC-SHA256 signature."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture
def valid_message():
    """Valid message payload."""
    return {
        "message_id": "m1",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello"
    }


def test_webhook_valid_signature(valid_message, monkeypatch, client):
    """Test webhook with valid signature."""
    # Set webhook secret
    monkeypatch.setenv("WEBHOOK_SECRET", "testsecret")
    from app.config import settings
    settings.webhook_secret = "testsecret"
    
    body = json.dumps(valid_message).encode()
    signature = compute_signature("testsecret", body)
    
    response = client.post(
        "/webhook",
        content=body,
        headers={"X-Signature": signature, "Content-Type": "application/json"}
    )
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webhook_invalid_signature(valid_message, monkeypatch, client):
    """Test webhook with invalid signature."""
    monkeypatch.setenv("WEBHOOK_SECRET", "testsecret")
    from app.config import settings
    settings.webhook_secret = "testsecret"
    
    body = json.dumps(valid_message).encode()
    
    response = client.post(
        "/webhook",
        content=body,
        headers={"X-Signature": "invalid", "Content-Type": "application/json"}
    )
    
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid signature"}


def test_webhook_missing_signature(valid_message, monkeypatch, client):
    """Test webhook with missing signature."""
    monkeypatch.setenv("WEBHOOK_SECRET", "testsecret")
    from app.config import settings
    settings.webhook_secret = "testsecret"
    
    body = json.dumps(valid_message).encode()
    
    response = client.post(
        "/webhook",
        content=body,
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 401


def test_webhook_duplicate_message(valid_message, monkeypatch, client):
    """Test idempotency - duplicate message_id."""
    monkeypatch.setenv("WEBHOOK_SECRET", "testsecret")
    from app.config import settings
    settings.webhook_secret = "testsecret"
    
    body = json.dumps(valid_message).encode()
    signature = compute_signature("testsecret", body)
    
    # First request
    response1 = client.post(
        "/webhook",
        content=body,
        headers={"X-Signature": signature, "Content-Type": "application/json"}
    )
    assert response1.status_code == 200
    
    # Duplicate request
    response2 = client.post(
        "/webhook",
        content=body,
        headers={"X-Signature": signature, "Content-Type": "application/json"}
    )
    assert response2.status_code == 200
    assert response2.json() == {"status": "ok"}


def test_webhook_validation_error(monkeypatch, client):
    """Test webhook with invalid payload."""
    monkeypatch.setenv("WEBHOOK_SECRET", "testsecret")
    from app.config import settings
    settings.webhook_secret = "testsecret"
    
    invalid_message = {
        "message_id": "",  # Empty message_id
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
    }
    
    body = json.dumps(invalid_message).encode()
    signature = compute_signature("testsecret", body)
    
    response = client.post(
        "/webhook",
        content=body,
        headers={"X-Signature": signature, "Content-Type": "application/json"}
    )
    
    assert response.status_code == 422

