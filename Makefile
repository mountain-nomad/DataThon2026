.PHONY: install train ml backend frontend dev up down lint

install:          ## Install all dependencies
	cd ml && uv sync
	cd backend && uv sync
	cd frontend && npm install

train:            ## Train baseline model (iris demo). Pass ARGS="--data ../data/train.csv --target y"
	cd ml && uv run python -m training.train $(ARGS)

ml:               ## Run ML inference API on :8001
	cd ml && uv run fastapi dev app/main.py --port 8001

backend:          ## Run backend API on :8000
	cd backend && uv run fastapi dev app/main.py --port 8000

frontend:         ## Run Next.js on :3000
	cd frontend && npm run dev

dev:              ## Run all three locally (Ctrl+C stops all)
	$(MAKE) -j3 ml backend frontend

up:               ## Run everything in Docker
	docker compose up --build

down:
	docker compose down

lint:
	cd ml && uv run ruff check . && uv run ruff format --check .
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && npm run lint
