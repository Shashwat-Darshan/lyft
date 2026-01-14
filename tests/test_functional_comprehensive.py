"""Comprehensive functional tests - no Docker/Make required."""
import pytest
import hmac
import hashlib
import json
import os
import tempfile
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.models import init_db, get_db_path
from app.storage import get_messages, get_stats


@pytest.fixture(scope="function")
def test_db(monkeypatch):
    """Create a temporary test database for each test."""
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
    """Set up test environment variables."""
    monkeypatch.setenv("WEBHOOK_SECRET", "testsecret")
    monkeypatch.setenv("DATABASE_URL", settings.database_url)
    monkeypatch.setenv("LOG_LEVEL", "INFO")
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


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_live(self, client):
        """Test liveness probe."""
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    
    def test_health_ready(self, client):
        """Test readiness probe."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}
    
    def test_health_ready_fails_without_secret(self, client, monkeypatch):
        """Test readiness fails when WEBHOOK_SECRET is not set."""
        # Temporarily override the secret for this test
        original_secret = settings.webhook_secret
        settings.webhook_secret = None
        monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
        
        try:
            response = client.get("/health/ready")
            assert response.status_code == 503, f"Expected 503, got {response.status_code}. Response: {response.json()}"
        finally:
            # Restore the secret
            settings.webhook_secret = original_secret
            monkeypatch.setenv("WEBHOOK_SECRET", "testsecret")


class TestWebhookEndpoint:
    """Test webhook endpoint functionality."""
    
    @pytest.fixture
    def valid_message(self):
        """Valid message payload."""
        return {
            "message_id": "m1",
            "from": "+919876543210",
            "to": "+14155550100",
            "ts": "2025-01-15T10:00:00Z",
            "text": "Hello"
        }
    
    def test_webhook_invalid_signature(self, client, valid_message):
        """Test webhook rejects invalid signature."""
        body = json.dumps(valid_message).encode()
        
        response = client.post(
            "/webhook",
            content=body,
            headers={"X-Signature": "123", "Content-Type": "application/json"}
        )
        
        assert response.status_code == 401
        assert response.json() == {"detail": "invalid signature"}
    
    def test_webhook_valid_signature_creates_message(self, client, valid_message):
        """Test webhook accepts valid signature and creates message."""
        body = json.dumps(valid_message).encode()
        signature = compute_signature("testsecret", body)
        
        response = client.post(
            "/webhook",
            content=body,
            headers={"X-Signature": signature, "Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        
        # Verify message was inserted
        messages, total = get_messages()
        assert total == 1
        assert messages[0]["message_id"] == "m1"
    
    def test_webhook_duplicate_idempotent(self, client, valid_message):
        """Test webhook handles duplicate messages idempotently."""
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
        
        # Verify only one message in DB
        messages, total = get_messages()
        assert total == 1
    
    def test_webhook_validation_errors(self, client):
        """Test webhook validation rejects invalid payloads."""
        # Empty message_id
        invalid = {
            "message_id": "",
            "from": "+919876543210",
            "to": "+14155550100",
            "ts": "2025-01-15T10:00:00Z"
        }
        body = json.dumps(invalid).encode()
        signature = compute_signature("testsecret", body)
        
        response = client.post(
            "/webhook",
            content=body,
            headers={"X-Signature": signature, "Content-Type": "application/json"}
        )
        assert response.status_code == 422
        
        # Invalid phone number format
        invalid2 = {
            "message_id": "m2",
            "from": "919876543210",  # Missing +
            "to": "+14155550100",
            "ts": "2025-01-15T10:00:00Z"
        }
        body2 = json.dumps(invalid2).encode()
        signature2 = compute_signature("testsecret", body2)
        
        response2 = client.post(
            "/webhook",
            content=body2,
            headers={"X-Signature": signature2, "Content-Type": "application/json"}
        )
        assert response2.status_code == 422


class TestMessagesEndpoint:
    """Test messages listing endpoint."""
    
    def test_messages_empty(self, client):
        """Test messages endpoint with no messages."""
        response = client.get("/messages")
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["total"] == 0
        assert data["limit"] == 50
        assert data["offset"] == 0
    
    def test_messages_pagination(self, client):
        """Test pagination parameters."""
        # Seed some messages
        messages = [
            {"message_id": f"m{i}", "from": "+919876543210", "to": "+14155550100",
             "ts": f"2025-01-15T{10+i:02d}:00:00Z", "text": f"Message {i}"}
            for i in range(5)
        ]
        
        for msg in messages:
            body = json.dumps(msg).encode()
            signature = compute_signature("testsecret", body)
            client.post(
                "/webhook",
                content=body,
                headers={"X-Signature": signature, "Content-Type": "application/json"}
            )
        
        # Test pagination
        response = client.get("/messages?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert data["limit"] == 2
        assert data["offset"] == 0
        assert data["total"] == 5
    
    def test_messages_filter_from(self, client, test_db):
        """Test filtering by sender."""
        # Ensure we're using the test database
        # Reinitialize to make sure we're using the correct database
        from app.models import init_db
        init_db()
        
        # Seed messages from different senders
        msg1 = {"message_id": "m1", "from": "+919876543210", "to": "+14155550100",
                "ts": "2025-01-15T10:00:00Z", "text": "Hello"}
        msg2 = {"message_id": "m2", "from": "+911234567890", "to": "+14155550100",
                "ts": "2025-01-15T11:00:00Z", "text": "Hi"}
        
        for msg in [msg1, msg2]:
            body = json.dumps(msg).encode()
            signature = compute_signature("testsecret", body)
            response = client.post(
                "/webhook",
                content=body,
                headers={"X-Signature": signature, "Content-Type": "application/json"}
            )
            assert response.status_code == 200, f"Failed to insert message: {response.text}"
        
        # Verify messages were inserted
        all_messages, total_all = get_messages()
        assert total_all == 2, f"Expected 2 messages, got {total_all}. Messages: {all_messages}"
        
        # Filter by sender (URL encode the + sign)
        from urllib.parse import quote
        encoded_from = quote("+919876543210", safe="")
        response = client.get(f"/messages?from={encoded_from}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1, f"Expected 1 message from +919876543210, got {data['total']}. Data: {data}"
        assert len(data["data"]) == 1
        assert data["data"][0]["from"] == "+919876543210"
    
    def test_messages_filter_since(self, client):
        """Test filtering by timestamp."""
        # Seed messages with different timestamps
        messages = [
            {"message_id": "m1", "from": "+919876543210", "to": "+14155550100",
             "ts": "2025-01-15T09:00:00Z", "text": "Early"},
            {"message_id": "m2", "from": "+919876543210", "to": "+14155550100",
             "ts": "2025-01-15T10:00:00Z", "text": "Late"}
        ]
        
        for msg in messages:
            body = json.dumps(msg).encode()
            signature = compute_signature("testsecret", body)
            client.post(
                "/webhook",
                content=body,
                headers={"X-Signature": signature, "Content-Type": "application/json"}
            )
        
        # Filter by since
        response = client.get("/messages?since=2025-01-15T09:30:00Z")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["data"][0]["ts"] == "2025-01-15T10:00:00Z"
    
    def test_messages_search(self, client):
        """Test text search."""
        messages = [
            {"message_id": "m1", "from": "+919876543210", "to": "+14155550100",
             "ts": "2025-01-15T10:00:00Z", "text": "Hello World"},
            {"message_id": "m2", "from": "+919876543210", "to": "+14155550100",
             "ts": "2025-01-15T11:00:00Z", "text": "Goodbye"}
        ]
        
        for msg in messages:
            body = json.dumps(msg).encode()
            signature = compute_signature("testsecret", body)
            client.post(
                "/webhook",
                content=body,
                headers={"X-Signature": signature, "Content-Type": "application/json"}
            )
        
        # Search
        response = client.get("/messages?q=Hello")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "Hello" in data["data"][0]["text"]
    
    def test_messages_ordering(self, client):
        """Test messages are ordered by ts ASC, message_id ASC."""
        messages = [
            {"message_id": "m2", "from": "+919876543210", "to": "+14155550100",
             "ts": "2025-01-15T10:00:00Z", "text": "Second"},
            {"message_id": "m1", "from": "+919876543210", "to": "+14155550100",
             "ts": "2025-01-15T10:00:00Z", "text": "First"},
            {"message_id": "m3", "from": "+919876543210", "to": "+14155550100",
             "ts": "2025-01-15T09:00:00Z", "text": "Earliest"}
        ]
        
        for msg in messages:
            body = json.dumps(msg).encode()
            signature = compute_signature("testsecret", body)
            client.post(
                "/webhook",
                content=body,
                headers={"X-Signature": signature, "Content-Type": "application/json"}
            )
        
        response = client.get("/messages")
        data = response.json()
        
        # Should be ordered: m3 (earliest ts), then m1, m2 (same ts, m1 < m2)
        assert data["data"][0]["message_id"] == "m3"
        assert data["data"][1]["message_id"] == "m1"
        assert data["data"][2]["message_id"] == "m2"


class TestStatsEndpoint:
    """Test stats endpoint."""
    
    def test_stats_empty(self, client):
        """Test stats with no messages."""
        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_messages"] == 0
        assert data["senders_count"] == 0
        assert data["messages_per_sender"] == []
        assert data["first_message_ts"] is None
        assert data["last_message_ts"] is None
    
    def test_stats_with_messages(self, client):
        """Test stats with multiple messages."""
        messages = [
            {"message_id": "m1", "from": "+919876543210", "to": "+14155550100",
             "ts": "2025-01-15T09:00:00Z", "text": "First"},
            {"message_id": "m2", "from": "+919876543210", "to": "+14155550100",
             "ts": "2025-01-15T10:00:00Z", "text": "Second"},
            {"message_id": "m3", "from": "+911234567890", "to": "+14155550100",
             "ts": "2025-01-15T11:00:00Z", "text": "Third"}
        ]
        
        for msg in messages:
            body = json.dumps(msg).encode()
            signature = compute_signature("testsecret", body)
            client.post(
                "/webhook",
                content=body,
                headers={"X-Signature": signature, "Content-Type": "application/json"}
            )
        
        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_messages"] == 3
        assert data["senders_count"] == 2
        assert len(data["messages_per_sender"]) == 2
        assert data["first_message_ts"] == "2025-01-15T09:00:00Z"
        assert data["last_message_ts"] == "2025-01-15T11:00:00Z"
        
        # Verify messages_per_sender sums to total
        total_from_senders = sum(s["count"] for s in data["messages_per_sender"])
        assert total_from_senders == data["total_messages"]


class TestMetricsEndpoint:
    """Test metrics endpoint."""
    
    def test_metrics_endpoint(self, client):
        """Test metrics endpoint returns 200 and contains required metrics."""
        # Make some requests to generate metrics
        client.get("/health/live")
        client.get("/messages")
        
        response = client.get("/metrics")
        assert response.status_code == 200
        
        content = response.text
        assert "http_requests_total" in content
        assert "webhook_requests_total" in content or "request_latency_ms" in content