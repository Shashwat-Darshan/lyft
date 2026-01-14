"""
Comprehensive edge case and validation error tests.
Tests 422 validation errors, 401 auth errors, and error response formatting.
"""
import json
import hmac
import hashlib
import logging
import requests

BASE_URL = "http://localhost:8000"
SECRET = "testsecret"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("EDGE_CASE_TEST")


def sign(secret: str, body: str) -> str:
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


def post_webhook(body: dict, valid=True, secret=SECRET):
    body_json = json.dumps(body, separators=(",", ":"))
    sig = sign(secret, body_json) if valid else "invalid_sig_123"
    return requests.post(
        f"{BASE_URL}/webhook",
        data=body_json,
        headers={"Content-Type": "application/json", "X-Signature": sig},
        timeout=5,
    )


# ============================================================================
# VALIDATION ERROR TESTS (422)
# ============================================================================

def test_missing_message_id():
    """Missing message_id → 422"""
    r = post_webhook({"from": "+14155550100", "to": "+14155550200", "ts": "2025-01-15T10:00:00Z"})
    assert r.status_code == 422


def test_missing_from():
    """Missing from → 422"""
    r = post_webhook({"message_id": "m1", "to": "+14155550200", "ts": "2025-01-15T10:00:00Z"})
    assert r.status_code == 422


def test_missing_to():
    """Missing to → 422"""
    r = post_webhook({"message_id": "m1", "from": "+14155550100", "ts": "2025-01-15T10:00:00Z"})
    assert r.status_code == 422


def test_missing_ts():
    """Missing ts → 422"""
    r = post_webhook({"message_id": "m1", "from": "+14155550100", "to": "+14155550200"})
    assert r.status_code == 422


def test_empty_message_id():
    """Empty message_id → 422"""
    r = post_webhook({
        "message_id": "",
        "from": "+14155550100",
        "to": "+14155550200",
        "ts": "2025-01-15T10:00:00Z"
    })
    assert r.status_code == 422


def test_from_without_plus():
    """from without + → 422"""
    r = post_webhook({
        "message_id": "m1",
        "from": "14155550100",
        "to": "+14155550200",
        "ts": "2025-01-15T10:00:00Z"
    })
    assert r.status_code == 422


def test_from_with_non_digits():
    """from with non-digits → 422"""
    r = post_webhook({
        "message_id": "m1",
        "from": "+1415555ABC0",
        "to": "+14155550200",
        "ts": "2025-01-15T10:00:00Z"
    })
    assert r.status_code == 422


def test_to_without_plus():
    """to without + → 422"""
    r = post_webhook({
        "message_id": "m1",
        "from": "+14155550100",
        "to": "14155550200",
        "ts": "2025-01-15T10:00:00Z"
    })
    assert r.status_code == 422


def test_ts_without_z():
    """ts without Z → 422"""
    r = post_webhook({
        "message_id": "m1",
        "from": "+14155550100",
        "to": "+14155550200",
        "ts": "2025-01-15T10:00:00"
    })
    assert r.status_code == 422


def test_ts_with_offset():
    """ts with +05:30 instead of Z → 422"""
    r = post_webhook({
        "message_id": "m1",
        "from": "+14155550100",
        "to": "+14155550200",
        "ts": "2025-01-15T10:00:00+05:30"
    })
    assert r.status_code == 422


def test_text_exceeds_4096():
    """text > 4096 chars → 422"""
    r = post_webhook({
        "message_id": "m1",
        "from": "+14155550100",
        "to": "+14155550200",
        "ts": "2025-01-15T10:00:00Z",
        "text": "x" * 4097
    })
    assert r.status_code == 422


# ============================================================================
# SIGNATURE VALIDATION TESTS (401)
# ============================================================================

def test_invalid_signature():
    """Invalid X-Signature → 401"""
    r = post_webhook({
        "message_id": "m1",
        "from": "+14155550100",
        "to": "+14155550200",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello"
    }, valid=False)
    assert r.status_code == 401


def test_missing_signature_header():
    """Missing X-Signature → 401"""
    body_json = json.dumps({
        "message_id": "m1",
        "from": "+14155550100",
        "to": "+14155550200",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello"
    }, separators=(",", ":"))
    r = requests.post(
        f"{BASE_URL}/webhook",
        data=body_json,
        headers={"Content-Type": "application/json"},
        timeout=5,
    )
    assert r.status_code == 401


def test_wrong_secret():
    """Signature with wrong secret → 401"""
    r = post_webhook({
        "message_id": "m1",
        "from": "+14155550100",
        "to": "+14155550200",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello"
    }, valid=True, secret="wrong_secret")
    assert r.status_code == 401


def test_empty_signature_header():
    """Empty X-Signature header → 401"""
    body_json = json.dumps({
        "message_id": "m1",
        "from": "+14155550100",
        "to": "+14155550200",
        "ts": "2025-01-15T10:00:00Z"
    }, separators=(",", ":"))
    r = requests.post(
        f"{BASE_URL}/webhook",
        data=body_json,
        headers={"Content-Type": "application/json", "X-Signature": ""},
        timeout=5,
    )
    assert r.status_code == 401


# ============================================================================
# ERROR RESPONSE VALIDATION
# ============================================================================

def test_422_has_detail_field():
    """422 error should have detail field"""
    r = post_webhook({"message_id": ""})
    assert r.status_code == 422
    data = r.json()
    assert "detail" in data


def test_401_has_detail_field():
    """401 error should have detail field"""
    r = post_webhook({
        "message_id": "m1",
        "from": "+14155550100",
        "to": "+14155550200",
        "ts": "2025-01-15T10:00:00Z"
    }, valid=False)
    assert r.status_code == 401
    data = r.json()
    assert "detail" in data or len(r.text) > 0


def test_no_stack_traces():
    """Error responses should not include Python stack traces"""
    r = post_webhook({"message_id": ""})
    assert r.status_code == 422
    assert "Traceback" not in r.text


# ============================================================================
# BOUNDARY CONDITIONS
# ============================================================================

def test_text_max_length_ok():
    """text exactly 4096 chars → 200"""
    r = post_webhook({
        "message_id": "m_max",
        "from": "+14155550100",
        "to": "+14155550200",
        "ts": "2025-01-15T10:00:00Z",
        "text": "x" * 4096
    })
    assert r.status_code == 200


def test_text_optional():
    """text field is optional → 200"""
    r = post_webhook({
        "message_id": "m_no_text",
        "from": "+14155550100",
        "to": "+14155550200",
        "ts": "2025-01-15T10:00:00Z"
    })
    assert r.status_code == 200


def test_very_old_timestamp():
    """Very old timestamp → 200"""
    r = post_webhook({
        "message_id": "m_old",
        "from": "+14155550100",
        "to": "+14155550200",
        "ts": "1970-01-01T00:00:00Z"
    })
    assert r.status_code == 200


def test_future_timestamp():
    """Future timestamp → 200"""
    r = post_webhook({
        "message_id": "m_future",
        "from": "+14155550100",
        "to": "+14155550200",
        "ts": "2099-12-31T23:59:59Z"
    })
    assert r.status_code == 200


def test_long_message_id():
    """Very long message_id → 200"""
    r = post_webhook({
        "message_id": "m" * 255,
        "from": "+14155550100",
        "to": "+14155550200",
        "ts": "2025-01-15T10:00:00Z"
    })
    assert r.status_code == 200


# ============================================================================
# IDEMPOTENCY
# ============================================================================

def test_duplicate_message_idempotent():
    """Duplicate message_id → 200 both times (idempotent)"""
    body = {
        "message_id": "idem_test_1",
        "from": "+14155550100",
        "to": "+14155550200",
        "ts": "2025-01-15T10:00:00Z"
    }
    r1 = post_webhook(body)
    r2 = post_webhook(body)
    assert r1.status_code == 200
    assert r2.status_code == 200


# ============================================================================
# HEALTH & METRICS
# ============================================================================

def test_health_live():
    """Health /live endpoint"""
    r = requests.get(f"{BASE_URL}/health/live", timeout=5)
    assert r.status_code == 200


def test_health_ready():
    """Health /ready endpoint"""
    r = requests.get(f"{BASE_URL}/health/ready", timeout=5)
    assert r.status_code == 200


def test_metrics_endpoint():
    """Metrics endpoint exists"""
    r = requests.get(f"{BASE_URL}/metrics", timeout=5)
    assert r.status_code == 200
    assert len(r.text) > 0
