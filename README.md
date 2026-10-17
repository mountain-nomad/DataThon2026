# DataThon 2026

Hackathon skeleton: **Next.js frontend → FastAPI backend → FastAPI ML inference service**.

```
browser ──► frontend :3000 ──(/api/* rewrite)──► backend :8000 ──► ml :8001
            Next.js 16                           FastAPI + SQLite   FastAPI + sklearn
```

| Folder      | What it does |
|-------------|--------------|
| `frontend/` | Next.js (App Router, TS, Tailwind). Dashboard: service status, single JSON prediction, CSV batch upload, prediction history. API client in `src/lib/api.ts`. |
| `backend/`  | Business logic + persistence. Proxies predictions to the ML service and logs them (`PredictionLog` table, SQLModel). Add your domain endpoints in `app/routers/`. |
| `ml/`       | Inference API (`app/`) + training (`training/train.py`). Loads `artifacts/model.joblib` at startup; serves dummy predictions if no model exists. |
| `data/`     | Put competition data here (gitignored). |

## Quick start

Requires `uv`, Node 20+.

```bash
make install
make train        # baseline model on iris so everything works end to end
make dev          # ml :8001, backend :8000, frontend :3000
```

Open http://localhost:3000. API docs: http://localhost:8000/docs and http://localhost:8001/docs.

Docker alternative: `make train && make up`.

## When the task drops

1. Put data in `data/`, then train a baseline:
   `make train ARGS="--data ../data/train.csv --target <col>"` (add `--task regression` if inference guesses wrong).
2. Reload without restarting: `curl -X POST localhost:8001/model/reload`.
3. Replace the model: keep the `ModelService.predict()` contract in `ml/app/model.py` (records in, predictions out), and swap sklearn for whatever you need (torch, lightgbm, an LLM API...).
4. Tighten schemas: `Record = dict[str, Any]` in `ml/app/schemas.py` / `backend/app/schemas.py` → a real Pydantic model.
5. Build the actual UI in `frontend/src/app/` and add endpoints in `backend/app/routers/`.

## Endpoints

**Backend** (`/api` prefix): `GET /health`, `GET /model`, `POST /predict` `{records:[...]}`, `POST /predict/csv` (multipart `file`), `GET /predictions?limit=&offset=`

**ML**: `GET /health`, `GET /model`, `POST /model/reload`, `POST /predict` `{records:[...]}`

## Config

Each service reads `.env` (see `.env.example`): `ML_SERVICE_URL`, `DATABASE_URL` (Postgres works too: add `psycopg[binary]` and use `postgresql+psycopg://...`), `CORS_ORIGINS`, `MODEL_PATH`, and `BACKEND_URL` for the Next.js rewrite (build-time).
