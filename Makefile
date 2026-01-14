.PHONY: up down logs test dev install

up:
	docker compose up -d --build

down:
	docker compose down -v

logs:
	docker compose logs -f api

test:
	@echo "Running tests..."
	python -m pytest tests/ -v

# Local development targets
dev:
	@echo "Starting local development server..."
	@echo "Make sure to set WEBHOOK_SECRET environment variable"
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt

