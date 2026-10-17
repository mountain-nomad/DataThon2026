# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Hackathon (DataThon 2026) skeleton built before the task was announced: three services that are meant to be adapted once the problem/dataset is known. The ML problem is still a placeholder (iris demo), and the input schemas are intentionally generic (`Record = dict[str, Any]`).

Note: `~/Desktop/CLAUDE.md` (an ancestor directory) describes an unrelated thesis project (histogram cardinality estimators) — ignore it for this repo.

## Commands

Python services use `uv` (each has its own `pyproject.toml` / `uv.lock` / `.venv`); the frontend uses `npm`. There is no test suite yet.

```bash
make install                 # uv sync in ml/ and backend/, npm install in frontend/
make train                   # train iris demo model -> ml/artifacts/model.joblib
make train ARGS="--data ../data/train.csv --target <col> [--task regression]"   # paths relative to ml/
make dev                     # ml :8001, backend :8000, frontend :3000 in parallel
make ml | make backend | make frontend   # run one service (fastapi dev / next dev, auto-reload)
make up                      # docker compose up --build
make lint                    # ruff check + ruff format --check (both Python services), eslint (frontend)

curl -X POST localhost:8001/model/reload   # pick up a retrained artifact without restarting
cd frontend && npx tsc --noEmit && npm run build   # typecheck / production build
```

Python commands must run from inside `ml/` or `backend/` (imports are `from app...`; training runs as `python -m training.train` so it can import `app.config`).

## Architecture

```
browser -> frontend :3000 --(next.config.ts rewrite /api/*)--> backend :8000 --(httpx)--> ml :8001
```

- **Request path.** The browser only ever calls same-origin `/api/*` (`frontend/src/lib/api.ts`). Next.js rewrites it to `BACKEND_URL` — this is resolved at **build time**, which is why the frontend Dockerfile takes it as a build arg. Backend routes are all mounted under `/api` so the rewrite is 1:1. The backend calls the ML service through the singleton `ml_client` (`backend/app/ml_client.py`), which maps connection errors to 503 and ML errors to 502; `/api/health` swallows these to report `ml: down`.
- **Prediction contract** (same shape in `ml/app/schemas.py`, `backend/app/schemas.py`, and the TS types in `frontend/src/lib/api.ts` — keep all three in sync): request `{records: [ {feature: value, ...} ]}`, response `{model_version, predictions: [{prediction, probabilities?}]}`.
- **Model artifact contract.** `ml/training/train.py` saves a joblib **dict** (not a bare estimator): `model` (sklearn Pipeline), `version`, `task`, `target`, `features`, `metrics`, `example`. `ml/app/model.py: ModelService` depends on these keys: it reindexes incoming records to `features` (missing -> NaN, extras dropped), only emits `probabilities` when `task == "classification"`, and `/model` exposes `metrics`/`example` — the frontend uses `example` to prefill the JSON form. If no artifact exists the service serves dummy predictions (`version="dummy"`) instead of failing. When swapping in another framework, keep `ModelService.predict(records) -> list[Prediction]`.
- **Training baseline.** `train.py` auto-splits numeric vs. other columns into a ColumnTransformer + HistGradientBoosting, infers task (object/category dtype or ≤20 unique values -> classification), reports holdout metrics, then refits on all data before saving.
- **Backend persistence.** SQLModel; `init_db()` runs `create_all` at startup (no migrations). Every prediction is logged to `PredictionLog` (input/output as JSON columns), capped at `MAX_LOGGED_ROWS` per request. CSV uploads are parsed with pandas and NaN is converted to `null` before forwarding (NaN isn't valid JSON).
- **Frontend.** Styled to the ForteBank brand — use the `forte-design` skill (`.claude/skills/forte-design/`) for any UI work. Colours/fonts are CSS-variable tokens in `src/app/globals.css` exposed to Tailwind via `@theme inline` (`bg-primary`, `text-muted`, `bg-hero`…); don't hard-code hex in components. `BrandMark.tsx` is a text placeholder until the official logo SVG is added. Next.js 16 with `cacheComponents` enabled and `output: "standalone"`. The dashboard is entirely client components (`"use client"`, data fetched in `useEffect`); `Dashboard` passes a `refreshKey` that is bumped after each prediction so `HistoryTable` refetches.
- **Config.** Each Python service uses pydantic-settings reading env vars / `.env` (see `.env.example` in each folder). In docker-compose, the backend reaches ML at `http://ml:8001`, SQLite lives on a named volume, and `ml/artifacts` is bind-mounted so you can retrain on the host and hit `/model/reload`.

## Conventions / gotchas

- `frontend/AGENTS.md`: this Next.js version has breaking changes vs. older knowledge — read the bundled docs in `frontend/node_modules/next/dist/docs/` before writing Next.js code.
- The root `.gitignore` is the GitHub Python template, whose `lib/` rule would ignore `frontend/src/lib/`; an explicit `!frontend/src/lib/` exception keeps it tracked. `data/*` and `ml/artifacts/*` are gitignored (only `.gitkeep` is tracked), so trained models and datasets live locally.
- `frontend/public/.gitkeep` must stay: the frontend Dockerfile copies `public/`.
- Ruff line length is 100 in both Python services.
