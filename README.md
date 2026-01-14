# WhatsApp-like Message Service

A production-style FastAPI service for ingesting and querying WhatsApp-like messages with HMAC signature validation, idempotency, and comprehensive observability.

## Features

- **Webhook Endpoint**: Ingest messages with HMAC-SHA256 signature validation
- **Idempotent Processing**: Duplicate messages are handled gracefully
- **Message Querying**: Paginated and filterable message listing
- **Analytics**: Statistics endpoint with sender metrics
- **Health Probes**: Liveness and readiness checks
- **Prometheus Metrics**: Exposed via `/metrics` endpoint
- **Structured Logging**: JSON-formatted logs with request tracking
- **12-Factor App**: Configuration via environment variables

## Quick Start

> **New to this project?** Start with [SETUP.md](SETUP.md) for detailed setup instructions from scratch.

### Prerequisites

- Python 3.11+ (for local development)
- Docker and Docker Compose (for containerized deployment, optional)

### Running the Service

#### Option 1: Using Docker Compose (Recommended for Production)

1. Set environment variables:
```bash
export WEBHOOK_SECRET="your-secret-key"
export DATABASE_URL="sqlite:////data/app.db"
```

2. Start the service:
```bash
docker compose up -d --build
```

3. Check health:
```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

4. View logs:
```bash
docker compose logs -f api
```

5. Stop the service:
```bash
docker compose down -v
```

#### Option 2: Running Locally (Development)

1. Create a virtual environment (recommended):
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On Linux/Mac
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set environment variables:
```bash
# On Windows (PowerShell)
$env:WEBHOOK_SECRET="your-secret-key"
$env:DATABASE_URL="sqlite:///./data/app.db"
$env:LOG_LEVEL="INFO"

# On Windows (CMD)
set WEBHOOK_SECRET=your-secret-key
set DATABASE_URL=sqlite:///./data/app.db
set LOG_LEVEL=INFO

# On Linux/Mac
export WEBHOOK_SECRET="your-secret-key"
export DATABASE_URL="sqlite:///./data/app.db"
export LOG_LEVEL="INFO"
```

4. Create data directory (if using local SQLite):
```bash
mkdir -p data
```

5. Start the server:
```bash
# Using uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Or using Python module
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Or run the main module directly
python -m app.main
```

6. The server will be available at `http://localhost:8000`

#### Option 3: Using Python Script

Use the provided `run.py` script:
```bash
python run.py
```

## API Endpoints

### POST /webhook

Ingest inbound WhatsApp-like messages with HMAC signature validation.

**Request Headers:**
- `Content-Type: application/json`
- `X-Signature: <hex HMAC-SHA256 of request body>`

**Request Body:**
```json
{
  "message_id": "m1",
  "from": "+919876543210",
  "to": "+14155550100",
  "ts": "2025-01-15T10:00:00Z",
  "text": "Hello"
}
```

**Response:**
- `200 OK`: Message processed (created or duplicate)
- `401 Unauthorized`: Invalid signature
- `422 Unprocessable Entity`: Validation error

**Example:**
```bash
# Compute signature (using Python)
python3 -c "import hmac, hashlib; print(hmac.new(b'testsecret', b'{\"message_id\":\"m1\",\"from\":\"+919876543210\",\"to\":\"+14155550100\",\"ts\":\"2025-01-15T10:00:00Z\",\"text\":\"Hello\"}', hashlib.sha256).hexdigest())"

# Send request
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: <computed-signature>" \
  -d '{"message_id":"m1","from":"+919876543210","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Hello"}'
```

### GET /messages

List stored messages with pagination and filters.

**Query Parameters:**
- `limit` (optional, int): Number of results (1-100, default: 50)
- `offset` (optional, int): Pagination offset (default: 0)
- `from` (optional, string): Filter by sender MSISDN (exact match)
- `since` (optional, string): Filter by timestamp (ISO-8601 UTC, returns messages with ts >= since)
- `q` (optional, string): Free-text search in message text (case-insensitive)

**Response:**
```json
{
  "data": [
    {
      "message_id": "m1",
      "from": "+919876543210",
      "to": "+14155550100",
      "ts": "2025-01-15T10:00:00Z",
      "text": "Hello"
    }
  ],
  "total": 10,
  "limit": 50,
  "offset": 0
}
```

**Example:**
```bash
# List all messages
curl http://localhost:8000/messages

# Paginated
curl "http://localhost:8000/messages?limit=10&offset=0"

# Filter by sender
curl "http://localhost:8000/messages?from=+919876543210"

# Filter by timestamp
curl "http://localhost:8000/messages?since=2025-01-15T09:00:00Z"

# Text search
curl "http://localhost:8000/messages?q=Hello"
```

### GET /stats

Get message statistics and analytics.

**Response:**
```json
{
  "total_messages": 123,
  "senders_count": 10,
  "messages_per_sender": [
    {"from": "+919876543210", "count": 50},
    {"from": "+911234567890", "count": 30}
  ],
  "first_message_ts": "2025-01-10T09:00:00Z",
  "last_message_ts": "2025-01-15T10:00:00Z"
}
```

**Example:**
```bash
curl http://localhost:8000/stats
```

### GET /health/live

Liveness probe - always returns 200 once the app is running.

### GET /health/ready

Readiness probe - returns 200 only if:
- Database is reachable and schema is applied
- `WEBHOOK_SECRET` is set

### GET /metrics

Prometheus-style metrics endpoint.

**Metrics:**
- `http_requests_total{path, status}`: Total HTTP requests by path and status
- `webhook_requests_total{result}`: Webhook processing outcomes (created, duplicate, invalid_signature, validation_error)
- `request_latency_ms`: Request latency histogram in milliseconds

**Example:**
```bash
curl http://localhost:8000/metrics
```

## Design Decisions

### HMAC Signature Verification

The service uses HMAC-SHA256 for webhook signature verification:

1. The raw request body is read as bytes
2. HMAC-SHA256 is computed using `WEBHOOK_SECRET` as the key
3. The computed signature is compared with the `X-Signature` header using constant-time comparison (`hmac.compare_digest`) to prevent timing attacks
4. If the signature is invalid, the request is rejected with 401 and no database insertion occurs

**Implementation:** See `app/routes/webhook.py::verify_signature()`

### Idempotency

Idempotency is enforced at the database level:

1. The `messages` table has `message_id` as PRIMARY KEY
2. When inserting a duplicate `message_id`, SQLite raises an `IntegrityError`
3. This is caught and handled gracefully, returning the same 200 response
4. The result field in logs indicates "created" vs "duplicate"

**Implementation:** See `app/storage.py::insert_message()`

### Pagination Contract

The `/messages` endpoint uses offset-based pagination:

- `limit`: Number of results per page (1-100, default 50)
- `offset`: Number of records to skip (default 0)
- `total`: Total number of records matching the filters (ignoring limit/offset)
- Results are ordered deterministically: `ORDER BY ts ASC, message_id ASC`

This ensures consistent ordering even when multiple messages have the same timestamp.

**Implementation:** See `app/routes/messages.py` and `app/storage.py::get_messages()`

### Statistics Endpoint

The `/stats` endpoint provides:

- **total_messages**: Simple COUNT(*) query
- **senders_count**: COUNT(DISTINCT from_msisdn)
- **messages_per_sender**: Top 10 senders by message count (GROUP BY with ORDER BY count DESC LIMIT 10)
- **first_message_ts / last_message_ts**: MIN(ts) and MAX(ts) queries

The implementation uses efficient SQL queries that perform well for thousands of rows.

**Implementation:** See `app/storage.py::get_stats()`

### Metrics

Prometheus metrics are exposed via `/metrics`:

- **http_requests_total**: Counter with `path` and `status` labels, incremented for all HTTP requests
- **webhook_requests_total**: Counter with `result` label, incremented for webhook processing outcomes
- **request_latency_ms**: Histogram with buckets [100, 500, 1000, 2000, 5000, +Inf] milliseconds

Metrics are tracked via middleware and route handlers. The metrics endpoint uses the `prometheus-client` library to generate the standard Prometheus exposition format.

**Implementation:** See `app/routes/metrics.py` and middleware integration in `app/main.py`

### Structured Logging

All logs are emitted as JSON, one line per log entry:

**Required fields:**
- `ts`: Server timestamp (ISO-8601 UTC)
- `level`: Log level (INFO, ERROR, etc.)
- `request_id`: Unique identifier per request (UUID)
- `method`: HTTP method
- `path`: Request path
- `status`: HTTP status code
- `latency_ms`: Request latency in milliseconds

**Webhook-specific fields:**
- `message_id`: Message ID from the request
- `dup`: Boolean indicating if message was duplicate
- `result`: Processing result ("created", "duplicate", "invalid_signature", "validation_error")

Logs are formatted using a custom `JSONFormatter` and can be easily parsed with `jq` or ingested by log aggregation systems.

**Implementation:** See `app/logging_utils.py`

## Environment Variables

- `DATABASE_URL`: SQLite database path (default: `sqlite:////data/app.db`)
- `LOG_LEVEL`: Logging level (default: `INFO`)
- `WEBHOOK_SECRET`: Secret key for HMAC signature verification (required)

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY,
    from_msisdn TEXT NOT NULL,
    to_msisdn TEXT NOT NULL,
    ts TEXT NOT NULL,
    text TEXT,
    created_at TEXT NOT NULL
);
```

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app entry
│   ├── config.py                # Environment variables
│   ├── logging_utils.py         # JSON logging middleware
│   ├── models.py                # DB schema / connection
│   ├── storage.py               # DB queries
│   └── routes/                  # Endpoint modules
│       ├── __init__.py
│       ├── webhook.py
│       ├── messages.py
│       ├── stats.py
│       ├── health.py
│       └── metrics.py
├── tests/
│   ├── test_webhook.py
│   ├── test_messages.py
│   └── test_stats.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Testing

Test files are provided in the `tests/` directory. Run tests with:

```bash
python -m pytest tests/ -v
```

## License

MIT

