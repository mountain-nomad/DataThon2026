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
- **Frontend.** Next.js 16 with `cacheComponents` enabled and `output: "standalone"`. Product: AI cash-operations video monitoring; the spec is `frontend/frontend_description.md`. Exactly three routes:
  - `/` is the landing page;
  - `/demo-inference` uploads a `.mov` to `POST /api/v1/analyze`, then polls `GET /api/v1/jobs/{id}` every 2.5 s with a 5-minute timeout (`lib/api.ts: waitForJob`). `toViolationEvents` adapts the jury API's snake_case response to the frontend model;
  - `/demo-dashboard` shows a 4×4 camera grid, statistics and episode cards, all from the local demo set in `lib/demo-data.ts`. Statistics are derived from that one event list. Marking a false positive changes only `reviewStatus`, never the model output.

  - **i18n (ru primary, kk, en).** Every route lives under `app/[lang]/`, the root layout included, and is prerendered for all three locales. `src/proxy.ts` serves Russian at unprefixed URLs by rewriting to `/ru/...`; `/ru/...` redirects to the unprefixed URL, and `/kk`, `/en` are prefixed. The proxy matcher skips `/api`, so video uploads are never buffered by it. Dictionaries are `src/i18n/dictionaries/*.ts`: `ru.ts` defines the shape, and the others `satisfies Dictionary`, so a missing key fails `tsc`. Server code calls `getDictionary()`, which reads `next/root-params`. Client components call `useI18n()` (`t`, `locale`, `href(path)`). Build internal links with `href()` / `localePath()`, never raw `"/..."`. Pages pass `path` to `SiteHeader` instead of using `usePathname()`, which would cause a hydration mismatch behind the rewrite. Plurals use `plural()` with Intl plural forms. Demo data in `lib/demo-data.ts` is not translated.
  Shared models are in `lib/types.ts`. Video and frames go through `components/media/` (`VideoPlayer` with timeline markers and `seekTo`, `MediaPlaceholder`, `EvidenceFrames`). Media is not added yet: `videoUrl` and `clipUrl` are undefined and placeholders render. Video is 16:9 with `object-contain`, never `cover`. The backend REST contract for all of this is `backend/backend_description.md` (not implemented yet).
- **Design system.** Any UI work goes through the `forte-design` skill (`.claude/skills/forte-design/SKILL.md`). Its "Project direction" section is what the user approved:
  - white background, minimal, magenta (`#A31551`) only as an accent;
  - only Forte's four main colours and the two brand gradients;
  - no gradient blocks (one thin `bg-gradient-primary` line at most);
  - light theme only;
  - Open Sans with weights 300/400/600/700/800;
  - only real data, never filler.

  Colours are CSS-variable tokens in `src/app/globals.css`, exposed to Tailwind via `@theme inline`. Don't hard-code hex in components. `BrandMark.tsx` renders the official logo files from `public/brand/Forte_logos/`; never a text logo. The brand book lives in `forte-brandbook.md`, with an identical copy at `.claude/skills/forte-design/references/brandbook.md`; edit both together.
- **Config.** Each Python service uses pydantic-settings reading env vars / `.env` (see `.env.example` in each folder). In docker-compose, the backend reaches ML at `http://ml:8001`, SQLite lives on a named volume, and `ml/artifacts` is bind-mounted so you can retrain on the host and hit `/model/reload`.

## Conventions / gotchas

- `frontend/AGENTS.md`: this Next.js version has breaking changes vs. older knowledge — read the bundled docs in `frontend/node_modules/next/dist/docs/` before writing Next.js code.
- The root `.gitignore` is the GitHub Python template, whose `lib/` rule would ignore `frontend/src/lib/`; an explicit `!frontend/src/lib/` exception keeps it tracked. `data/*` and `ml/artifacts/*` are gitignored (only `.gitkeep` is tracked), so trained models and datasets live locally.
- `frontend/public/.gitkeep` must stay: the frontend Dockerfile copies `public/`.
- Ruff line length is 100 in both Python services.
- `eslint-config-next` must match the installed `next` major (16.x). `npm audit fix --force` downgrades it to 14.x, which breaks `npm run lint` with `ERR_MODULE_NOT_FOUND` while the build still passes.
