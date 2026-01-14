"""Tests for messages endpoint."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)


def test_messages_list_empty(client):
    """Test listing messages when empty."""
    response = client.get("/messages")
    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []
    assert data["total"] == 0
    assert data["limit"] == 50
    assert data["offset"] == 0


def test_messages_pagination(monkeypatch, client):
    """Test pagination parameters."""
    monkeypatch.setenv("WEBHOOK_SECRET", "testsecret")
    from app.config import settings
    settings.webhook_secret = "testsecret"
    
    response = client.get("/messages?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 10
    assert data["offset"] == 0


def test_messages_filter_from(client):
    """Test filtering by sender."""
    from urllib.parse import quote
    encoded_from = quote("+919876543210", safe="")
    response = client.get(f"/messages?from={encoded_from}")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "total" in data


def test_messages_filter_since(client):
    """Test filtering by timestamp."""
    response = client.get("/messages?since=2025-01-15T09:00:00Z")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "total" in data


def test_messages_search(client):
    """Test text search."""
    response = client.get("/messages?q=Hello")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "total" in data

