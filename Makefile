.PHONY: install backend frontend dev up down lint

install:          ## Install backend and frontend dependencies
	cd backend && uv sync
	# --legacy-peer-deps: package.json pins eslint-config-next 14 next to Next 16 (peer conflict)
	cd frontend && npm ci --legacy-peer-deps

backend:          ## API + simple web UI on :8000
	cd backend && uv run fastapi dev app/main.py --port 8000

frontend:         ## Next.js UI on :3000 (needs frontend/.env.local, see README)
	cd frontend && npm run dev -- --port 3000

dev:              ## Both (Ctrl+C stops both)
	$(MAKE) -j2 backend frontend

up:               ## Backend only, in Docker
	docker compose up --build

down:
	docker compose down

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && npm run lint
