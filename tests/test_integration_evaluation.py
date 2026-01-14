"""Integration test matching the evaluation script."""
import pytest
import hmac
import hashlib
import json
import os
import tempfile
from urllib.parse import quote
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.models import init_db
from app.storage import get_messages, get_stats


@pytest.fixture(scope="function")
def test_db(monkeypatch):
    """Create a temporary test database."""
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    db_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    settings.database_url = db_url
    
    init_db()
    
    yield db_path
    
    try:
        os.unlink(db_path)
    except Exception:
        pass


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch, test_db):
    """Set up test environment matching evaluation script."""
    monkeypatch.setenv("WEBHOOK_SECRET", "testsecret")
    monkeypatch.setenv("DATABASE_URL", "sqlite:////data/app.db")
    settings.webhook_secret = "testsecret"
    yield
    settings.webhook_secret = None


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def compute_signature(secret: str, body: bytes) -> str:
    """Compute HMAC-SHA256 signature."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_evaluation_script_flow(client):
    """
    Complete integration test matching the evaluation script flow.
    This simulates the entire evaluation process.
    """
    
    # Step 1: Health checks
    response = client.get("/health/live")
    assert response.status_code == 200
    
    response = client.get("/health/ready")
    assert response.status_code == 200
    
    # Step 2: Webhook + Signature tests
    body_str = '{"message_id":"m1","from":"+919876543210","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Hello"}'
    body_bytes = body_str.encode()
    
    # Invalid signature → expect 401
    response = client.post(
        "/webhook",
        content=body_bytes,
        headers={"X-Signature": "123", "Content-Type": "application/json"}
    )
    assert response.status_code == 401
    
    # Valid signature → 200, row inserted
    valid_sig = compute_signature("testsecret", body_bytes)
    response = client.post(
        "/webhook",
        content=body_bytes,
        headers={"X-Signature": valid_sig, "Content-Type": "application/json"}
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    
    # Verify message was inserted
    messages, total = get_messages()
    assert total == 1
    
    # Duplicate with same body + sig → 200, but no new row
    response = client.post(
        "/webhook",
        content=body_bytes,
        headers={"X-Signature": valid_sig, "Content-Type": "application/json"}
    )
    assert response.status_code == 200
    
    # Verify still only one message
    messages, total = get_messages()
    assert total == 1
    
    # Step 3: Seed more messages for /messages and /stats
    additional_messages = [
        {"message_id": "m2", "from": "+919876543210", "to": "+14155550100",
         "ts": "2025-01-15T09:00:00Z", "text": "Earlier message"},
        {"message_id": "m3", "from": "+911234567890", "to": "+14155550100",
         "ts": "2025-01-15T11:00:00Z", "text": "Later message"},
        {"message_id": "m4", "from": "+919876543210", "to": "+14155550100",
         "ts": "2025-01-15T10:30:00Z", "text": "Hello again"}
    ]
    
    for msg in additional_messages:
        body = json.dumps(msg).encode()
        signature = compute_signature("testsecret", body)
        response = client.post(
            "/webhook",
            content=body,
            headers={"X-Signature": signature, "Content-Type": "application/json"}
        )
        assert response.status_code == 200
    
    # Step 4: Check /messages pagination & filters
    # Basic list
    response = client.get("/messages")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "total" in data
    assert data["total"] == 4  # m1, m2, m3, m4
    
    # limit+offset
    response = client.get("/messages?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2
    assert data["limit"] == 2
    assert data["offset"] == 0
    assert data["total"] == 4
    
    # filter by from= (URL encode the + sign)
    encoded_from = quote("+919876543210", safe="")
    response = client.get(f"/messages?from={encoded_from}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3  # m1, m2, m4
    
    # filter by since=
    response = client.get("/messages?since=2025-01-15T09:30:00Z")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3  # m1, m3, m4 (after 09:30)
    
    # filter by q=
    response = client.get("/messages?q=Hello")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2  # m1 and m4 contain "Hello"
    
    # Verify ordering: ts ASC, message_id ASC
    response = client.get("/messages")
    data = response.json()
    messages = data["data"]
    # Should be: m2 (09:00), m1 (10:00), m4 (10:30), m3 (11:00)
    assert messages[0]["message_id"] == "m2"
    assert messages[1]["message_id"] == "m1"
    assert messages[2]["message_id"] == "m4"
    assert messages[3]["message_id"] == "m3"
    
    # Step 5: Check /stats
    response = client.get("/stats")
    assert response.status_code == 200
    stats = response.json()
    
    assert stats["total_messages"] == 4
    assert stats["senders_count"] == 2
    assert len(stats["messages_per_sender"]) == 2
    
    # Verify messages_per_sender entries sum up to total_messages
    total_from_senders = sum(s["count"] for s in stats["messages_per_sender"])
    assert total_from_senders == stats["total_messages"]
    
    # Verify first_message_ts and last_message_ts
    assert stats["first_message_ts"] == "2025-01-15T09:00:00Z"
    assert stats["last_message_ts"] == "2025-01-15T11:00:00Z"
    
    # Step 6: Check /metrics
    response = client.get("/metrics")
    assert response.status_code == 200
    content = response.text
    
    # Check for required metrics
    assert "http_requests_total" in content
    assert "webhook_requests_total" in content or "request_latency_ms" in content

