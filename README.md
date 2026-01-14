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

## Scoring Criteria (10 points)

### Core Correctness (4 pts) ✅
- Health endpoints (`/health/live`, `/health/ready`)
- `/webhook` success & idempotency
- Basic `/messages` listing and ordering

### Advanced Endpoints (4 pts) ✅
- HMAC-SHA256 signature behavior (401 on invalid, 200 on valid, duplicates idempotent)
- `/messages` pagination + filtering (limit, offset, from, since, q)
- `/stats` correctness (total_messages, senders_count, messages_per_sender, timestamps)

### Observability & Ops (1 pt) ✅
- `/metrics` with required metrics: `http_requests_total`, `webhook_requests_total`
- JSON logs with `request_id`, `result` fields, one line per request

### Docs & Hygiene (1 pt) ✅
- README with how to run (make up, URLs)
- How to hit endpoints (examples provided)
- Design decisions documented:
  - HMAC verification implementation
  - Pagination contract details
  - /stats and metrics definitions

## Quick Start

> **New to this project?** Start with [SETUP.md](SETUP.md) for detailed setup instructions from scratch.

### Prerequisites

- Python 3.11+ (for local development)
- Docker and Docker Compose (for containerized deployment)
- Make (for convenience commands, optional)

### Using Makefile Commands

The project includes a `Makefile` with convenient commands:

```bash
make up      # Start the service: docker compose up -d --build
make down    # Stop the service: docker compose down -v
make logs    # View logs: docker compose logs -f api
make test    # Run tests: python -m pytest tests/ -v
```

### Running the Service

#### Option 1: Docker Compose (Recommended)

```bash
export WEBHOOK_SECRET="your-secret-key"
export DATABASE_URL="sqlite:////data/app.db"
docker compose up -d --build
curl http://localhost:8000/health/live
```

#### Option 2: Local Development

```bash
python -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate on Windows
pip install -r requirements.txt
export WEBHOOK_SECRET="your-secret-key"
uvicorn app.main:app --reload
```

#### Option 3: Using Makefile

```bash
make up      # Start service
make logs    # View logs
make down    # Stop service
```

## API Endpoints

### POST /webhook
Ingest messages with HMAC-SHA256 signature validation.

**Headers:** `Content-Type: application/json`, `X-Signature: <hex HMAC-SHA256>`

**Body:**
```json
{
  "message_id": "m1",
  "from": "+919876543210",
  "to": "+14155550100",
  "ts": "2025-01-15T10:00:00Z",
  "text": "Hello"
}
```

**Response:** `200 OK` | `401 Unauthorized` | `422 Validation Error`

### GET /messages
List messages with pagination and filters.

**Query Params:** `limit` (1-100, def 50), `offset` (def 0), `from`, `since`, `q`

**Response:**
```json
{
  "data": [{...}],
  "total": 10,
  "limit": 50,
  "offset": 0
}
```

**Examples:**
```bash
curl http://localhost:8000/messages
curl "http://localhost:8000/messages?limit=10&offset=0"
curl "http://localhost:8000/messages?from=+919876543210"
curl "http://localhost:8000/messages?since=2025-01-15T09:00:00Z"
curl "http://localhost:8000/messages?q=Hello"
```

### GET /stats
Message statistics and sender metrics.

**Response:**
```json
{
  "total_messages": 123,
  "senders_count": 10,
  "messages_per_sender": [{"from": "+919876543210", "count": 50}],
  "first_message_ts": "2025-01-10T09:00:00Z",
  "last_message_ts": "2025-01-15T10:00:00Z"
}
```

### GET /health/live
Liveness probe → always 200 when running.

### GET /health/ready
Readiness probe → 200 if DB is ready and WEBHOOK_SECRET is set, else 503.

### GET /metrics
Prometheus metrics endpoint (text format).

## Design Decisions

### HMAC Signature Verification
- Computed: `hex(HMAC_SHA256(key=WEBHOOK_SECRET, message=raw_body))`
- Verified using constant-time comparison to prevent timing attacks
- Invalid signatures → HTTP 401, no database write

### Idempotency
- `message_id` is PRIMARY KEY → duplicates caught at DB level
- Both first and duplicate calls → HTTP 200 `{"status": "ok"}`
- Logs indicate "created" vs "duplicate"

### Pagination & Filtering
- Offset-based: `limit` (1-100, default 50), `offset` (default 0)
- Ordering: `ORDER BY ts ASC, message_id ASC` (deterministic)
- Filters: `from` (exact), `since` (ISO-8601), `q` (substring)
- `total` always reflects matching records (ignoring limit/offset)

### Statistics Endpoint
- `total_messages`: COUNT(*)
- `senders_count`: COUNT(DISTINCT from_msisdn)
- `messages_per_sender`: Top 10 senders by count
- `first_message_ts`, `last_message_ts`: MIN/MAX timestamps

### Prometheus Metrics
```
http_requests_total{path, status}    # All HTTP requests
webhook_requests_total{result}       # created, duplicate, invalid_signature, validation_error
request_latency_ms_bucket            # Histogram: 100ms, 500ms, 1000ms, 2000ms, 5000ms, +Inf
```

### Structured JSON Logging
- One JSON object per line (compatible with `jq`)
- Fields: `ts`, `level`, `request_id`, `method`, `path`, `status`, `latency_ms`
- Webhook logs add: `message_id`, `dup`, `result`

## Environment Variables

| Variable | Required | Default |
|----------|----------|---------|
| `WEBHOOK_SECRET` | ✅ Yes | N/A |
| `DATABASE_URL` | No | `sqlite:////data/app.db` |
| `LOG_LEVEL` | No | `INFO` |


```

## Project Structure

```
app/
  main.py, config.py, models.py, storage.py, logging_utils.py
  routes/ - webhook.py, messages.py, stats.py, health.py, metrics.py

tests/
  test_webhook.py, test_messages.py, test_stats.py

Dockerfile, docker-compose.yml, requirements.txt
```

## Testing

```bash
python -m pytest tests/ -v
```


## Setup Used

VS code(coding) + Cursor(intial start) + chatgpt(planning) + perplexity(planning) + claude(markdown)

## License

MIT

## Author

Shashwat Darshan-25177-DCE

