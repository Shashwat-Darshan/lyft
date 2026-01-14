import json
import time
import hmac
import hashlib
import logging
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000"
SECRET = "testsecret"

# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="E2E_TEST | %(levelname)s | %(message)s",
)
log = logging.getLogger("E2E_TEST")


def sign(secret: str, body: str) -> str:
    return hmac.new(
        secret.encode(),
        body.encode(),
        hashlib.sha256,
    ).hexdigest()


def assert_or_log(cond, msg):
    if not cond:
        log.error(msg)
        assert cond, msg


def post_webhook(body: dict, valid=True):
    body_json = json.dumps(body, separators=(",", ":"))
    sig = sign(SECRET, body_json) if valid else "123"

    return requests.post(
        f"{BASE_URL}/webhook",
        data=body_json,
        headers={
            "Content-Type": "application/json",
            "X-Signature": sig,
        },
        timeout=5,
    )


def test_full_stack_e2e():
    """
    Matches evaluator script EXACTLY (curl-equivalent).
    Assumes docker-compose stack is already running.
    """

    # -----------------------------
    # 2. Health checks
    # -----------------------------
    log.info("Checking /health/live")
    r = requests.get(f"{BASE_URL}/health/live", timeout=5)
    assert_or_log(r.status_code == 200, "/health/live failed")

    log.info("Checking /health/ready")
    r = requests.get(f"{BASE_URL}/health/ready", timeout=5)
    assert_or_log(r.status_code == 200, "/health/ready failed")

    # -----------------------------
    # 3. Webhook + signature
    # -----------------------------
    base_msg = {
        "message_id": "m1",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello",
    }

    log.info("Invalid signature → expect 401")
    r = post_webhook(base_msg, valid=False)
    assert_or_log(r.status_code == 401, "Invalid signature did not return 401")

    log.info("Valid signature → insert")
    r = post_webhook(base_msg, valid=True)
    assert_or_log(r.status_code == 200, f"Valid webhook failed: {r.text}")

    log.info("Duplicate webhook → no new row")
    r = post_webhook(base_msg, valid=True)
    assert_or_log(r.status_code == 200, "Duplicate webhook failed")

    # -----------------------------
    # 4. Seed more messages
    # -----------------------------
    extra_msgs = [
        {
            "message_id": "m2",
            "from": "+14155550111",
            "to": "+14155550100",
            "ts": "2025-01-15T10:01:00Z",
            "text": "Hello again",
        },
        {
            "message_id": "m3",
            "from": "+14155550222",
            "to": "+14155550100",
            "ts": "2025-01-15T10:02:00Z",
            "text": "Yo",
        },
        {
            "message_id": "m4",
            "from": "+919876543210",
            "to": "+14155550100",
            "ts": "2025-01-15T10:03:00Z",
            "text": "Final",
        },
    ]

    for msg in extra_msgs:
        r = post_webhook(msg, valid=True)
        assert_or_log(r.status_code == 200, f"Seed failed for {msg['message_id']}")

    total_expected = 1 + len(extra_msgs)

    # -----------------------------
    # 5. /messages checks
    # -----------------------------
    log.info("Checking /messages basic list")
    r = requests.get(f"{BASE_URL}/messages", timeout=5)
    assert_or_log(r.status_code == 200, "/messages failed")
    payload = r.json()

    assert_or_log(payload["total"] == total_expected, "Total mismatch")
    assert_or_log(len(payload["data"]) == total_expected, "Data length mismatch")

    # Ordering check
    timestamps = [
        (m["ts"], m["message_id"]) for m in payload["data"]
    ]
    assert_or_log(
        timestamps == sorted(timestamps),
        "Messages not ordered by ts asc, message_id asc",
    )

    # Pagination
    r = requests.get(f"{BASE_URL}/messages?limit=2&offset=0", timeout=5)
    data = r.json()
    assert_or_log(len(data["data"]) == 2, "Pagination limit failed")
    assert_or_log(data["limit"] == 2 and data["offset"] == 0, "Pagination echo failed")

    # Filter by sender
    r = requests.get(
        f"{BASE_URL}/messages?from=+919876543210", timeout=5
    )
    data = r.json()
    assert_or_log(
        all(m["from"] == "+919876543210" for m in data["data"]),
        "from= filter failed",
    )

    # since filter
    r = requests.get(
        f"{BASE_URL}/messages?since=2025-01-15T09:30:00Z", timeout=5
    )
    assert_or_log(r.json()["total"] == total_expected, "since filter failed")

    # q filter
    r = requests.get(f"{BASE_URL}/messages?q=Hello", timeout=5)
    data = r.json()
    assert_or_log(data["total"] >= 2, "q filter failed")

    # -----------------------------
    # 6. /stats
    # -----------------------------
    log.info("Checking /stats")
    r = requests.get(f"{BASE_URL}/stats", timeout=5)
    stats = r.json()

    assert_or_log(stats["total_messages"] == total_expected, "stats total mismatch")
    assert_or_log(stats["senders_count"] == 3, "senders_count mismatch")

    summed = sum(s["count"] for s in stats["messages_per_sender"])
    assert_or_log(summed == total_expected, "messages_per_sender sum mismatch")

    assert_or_log(
        stats["first_message_ts"] == "2025-01-15T10:00:00Z",
        "first_message_ts incorrect",
    )
    assert_or_log(
        stats["last_message_ts"] == "2025-01-15T10:03:00Z",
        "last_message_ts incorrect",
    )

    # -----------------------------
    # 7. /metrics (optional)
    # -----------------------------
    log.info("Checking /metrics")
    r = requests.get(f"{BASE_URL}/metrics", timeout=5)
    assert_or_log(r.status_code == 200, "/metrics failed")

    text = r.text
    assert_or_log(
        "http_requests_total" in text,
        "http_requests_total missing",
    )
    assert_or_log(
        "webhook_requests_total" in text,
        "webhook_requests_total missing",
    )

    log.info("✅ FULL E2E STACK TEST PASSED")
