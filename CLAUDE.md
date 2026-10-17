# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Hackathon (DataThon 2026): detect possible cashier violations in top-down bank CCTV videos. The **platform is deliberately minimal: one FastAPI service in `backend/`** (API + a simple web page + background jobs), plus the Next.js `frontend/` (`/demo-inference` and `/demo-dashboard` both talk to it). `docker-compose.yml` runs only the backend. `ml/` (iris demo) is unused; the real model will be a **separate ML microservice the team builds**, reached through `ANALYZER=http` (the default; `mock` only when set explicitly) and the contract in `README.md` ("Plugging in the ML microservice"). Don't build that service or add a model unless asked. `backend/backend_description.md` describes a bigger contract (router/specialists pipeline, demo dashboard) that is **not** what's implemented; `README.md` documents what is.

Note: `~/Desktop/CLAUDE.md` (an ancestor directory) describes an unrelated thesis project (histogram cardinality estimators) — ignore it for this repo.

## Commands

```bash
cp backend/.env.example backend/.env   # API_KEY is required, the app refuses to start without it
cp frontend/.env.example frontend/.env.local   # ANALYSIS_API_KEY = backend API_KEY
make install                           # uv sync in backend/, npm ci --legacy-peer-deps in frontend/
make backend | make frontend | make dev   # :8000 (simple UI at /, docs at /docs) / Next.js :3000 / both
make up                                # docker compose up --build (single service, data on a named volume)
make lint                              # ruff check + ruff format --check
```

There is no test suite. Python commands run from inside `backend/` (imports are `from app...`).

## Backend architecture (`backend/app/`)

- `api.py`: `/api/v1/analyze` and `/api/v1/jobs/{id}` are the **exact jury contract** (`X-API-Key`, compared with `secrets.compare_digest`). Don't add fields there; `jobs.public_view()` strips internal ones. The key-less routers are:
  - `ui` (`/ui/*`) for the simple page;
  - `frontend` (`/api/jobs/*`) for Next.js: `GET /api/jobs?status=` (history, newest first), `/{id}/pipeline`, `/{id}/video` (`FileResponse`, Range) and `PUT /{id}/results/{index}/review`.
  - Review marks live in the job's `reviews` dict, never in the model output. `index` is the position in `specialist_results`.
- `main.py`: the `local_only` middleware lets **only `/api/v1/*`, `/health`, `/docs`, `/openapi.json` answer remote clients**. Everything else needs the socket peer and every `X-Forwarded-For` / `X-Real-Ip` / `Cf-Connecting-Ip` address to be loopback or private, so publishing through a tunnel exposes the jury API only. Python counts documentation ranges (203.0.113.0/24…) as private, so test with a real public IP such as 8.8.8.8.
- `jobs.py`: job state is one JSON file per job in `DATA_DIR/jobs/`, written atomically (tmp + `os.replace`) under a lock.
  - `finish()` and `update()` only write while the job is `processing`, so a timeout that already failed a job is never overwritten.
  - Readers call `expire_if_overdue()`, so the deadline (`created_at + JOB_TIMEOUT_SEC`, default 270, queue time included) holds even if the worker is stuck.
  - At startup, leftover `processing` jobs become `failed`. `delete_old_uploads()` runs hourly when `UPLOAD_RETENTION_HOURS > 0`.
- `worker.py`: an `asyncio.Queue` with `MAX_CONCURRENT_JOBS` slots. Each slot owns a long-lived **spawned child process** that loads the analyzer once (`_serve`).
  - The child gets `(video_path, deadline)`. It streams `("partial", …)` messages, which are saved through `jobs.update()` with `stages_done` 1/2 so `/pipeline` shows live progress, then `("ok", …)` or `("error", …)`.
  - At `deadline + HARD_KILL_GRACE_SEC` the child is killed (a thread can't be stopped). If the last partial has specialist results, the job ends `done` with them and a `limitations` note; otherwise it fails.
  - `build_result()`:
    1. a violation below `MIN_CONFIDENCE` becomes `insufficient_evidence`;
    2. timecodes are clamped;
    3. 1–3 frames with a fallback so there's always one;
    4. the legal basis;
    5. the jury `type` (the catalog quote minus `Нарушение:`, else the legal type name) and `description` (evidence + "Почему…" + "Основание: …"; the simple page splits on `\nОснование:`);
    6. the verdict.
- `storage.py`: `get_storage()` → `SupabaseStorage` (`STORAGE_BACKEND=supabase`, default) or `LocalStorage`. After local validation `_start_job` uploads the file to a private bucket as `{YYYY}/{MM}/{job_id}{ext}` and the job keeps `storage_path` beside `video_path`; the analyzer always reads the local copy. A storage failure is `502` and creates no job. Signed URLs come only from the local-only `GET /api/jobs/{id}/video-url`; `SUPABASE_KEY` must be the secret/service_role key (the bucket is created at startup).
- `legal.py`: `LegalIndex.resolve(rule_id, type_hint)` returns the legal basis for a result.
  - The chain is crosswalk (`specialist_crosswalk.yaml`: rule_id → `T..` or an inline entry) → `violation_types` → `rules` (`R..`) → `sources` in the team's `fortebank_violation_legal_mapping_updated.yaml`.
  - Unmapped means `None`; never guess. Source URLs drop `utm_*` and prefer `alternate_url`. `binding` is false for non-normative sources.
  - The crosswalk is a **draft for the team to review**; the mapping YAML is theirs, so don't edit it.
- `analyzers/`: models, `AnalysisContext` (`deadline`, `time_left()`, `report(partial)`), `run_analyzer()` (passes `ctx` only if `analyze` takes two parameters) and `load_analyzer("mock" | "http" | "module:Class")`.
  - `analyze()` returns an `AnalysisResult` (router `Scenario` + `SpecialistResult`s, mirroring the specialist prompts' JSON) or a flat `list[Detection]`.
  - `http.py` is the ML microservice client: multipart `file` + `deadline_sec` + `job_id`, and an NDJSON stream of `partial` / `result` / `error` events, or plain JSON.
  - `MockAnalyzer` reports router → specialists step by step, skips a specialist that wouldn't fit the deadline, quotes real catalog lines, is seeded by the file hash and marks its evidence `[MOCK]`.
- `video.py`: OpenCV only (no system ffmpeg needed): `probe_duration` (also the upload validation) and `extract_frames` (JPEG, long side ≤ 640, base64).
- `static/index.html`: vanilla JS, Russian, Forte tokens (see the design notes below). No web fonts, because the service must work offline.
- Sample videos are H.264 `.mov`, 464×848 **portrait**, ~30 fps. Their filenames mix Latin `X-` and Cyrillic `Х-`.

## Frontend (`frontend/`)

- **Frontend.** Next.js 16 with `cacheComponents` enabled and `output: "standalone"`. Product: AI cash-operations video monitoring; the spec is `frontend/frontend_description.md`. Exactly three routes:
  - `/` is the landing page;
  - `/demo-inference` (`frontend_description2.md`) uploads a `.mov` to `POST /api/v1/analyze`. That upload is handled by the **static** route handler `src/app/api/v1/analyze/route.ts`, which adds `X-API-Key` from the server-only `ANALYSIS_API_KEY` (`.env.local`) and streams the body through. It must stay static: plain `rewrites()` run *before* dynamic routes, so a `[...path]` handler would be bypassed. It then polls the UI endpoint `GET /api/jobs/{id}/pipeline` every 2.5 s with a 5-minute timeout (`lib/api.ts: waitForJob`); `toPipelineResult` adapts the response.
    - The AI pipeline is router → specialists → localization, shown as a 4-circle stepper (`StageProgress`) and three stacked result cards (`StageResults`).
    - The 7 router scenarios are canonical ids in `lib/types.ts` (`SCENARIOS`, `SCENARIO_CODES`). Their names and the violation types each specialist checks are in the dictionaries under `scenarios`. Specialist text (`quote`, `evidence`) is shown untranslated, and results from non-routed scenarios are dropped.
    - Stages are revealed one at a time. If the backend sends no `stages_done`, they are revealed only after `done`, with a note saying so; never fake progress.
    - When stage 3 finds a violation, the video grid animates into two columns. The right column plays `start_sec..end_sec` of the same file (`VideoPlayer segment`), falling back to the evidence frame;
  - Each violation shows `components/LegalBasis.tsx` (source → clause → limitations, from `legal_basis` mapped in `lib/api.ts: toLegalBasis`). Its labels live in the dictionaries under `legal`.
  - `/demo-dashboard` shows statistics and episode cards over the history of finished analyses from `GET /api/jobs?status=done`. That history is the videos uploaded on `/demo-inference`; there is no local demo set.
    - There is no camera grid: the camera panel from `frontend_description.md` was removed on request.
    - Every number is derived from that one list.
    - Marking a false positive calls `PUT /api/jobs/{id}/results/{index}/review` optimistically and rolls back on error. It changes only `reviewStatus`, never the model output.
    - Episodes play `start_sec..end_sec` of the job's `preview_url` through `components/media/EpisodeMedia.tsx`, which is shared with the inference page.
    - Without a backend, the page shows an honest error or empty state.

  - **i18n (ru primary, kk, en).** Every route lives under `app/[lang]/`, the root layout included, and is prerendered for all three locales. `src/proxy.ts` serves Russian at unprefixed URLs by rewriting to `/ru/...`; `/ru/...` redirects to the unprefixed URL, and `/kk`, `/en` are prefixed. The proxy matcher skips `/api`, so video uploads are never buffered by it. Dictionaries are `src/i18n/dictionaries/*.ts`: `ru.ts` defines the shape, and the others `satisfies Dictionary`, so a missing key fails `tsc`. **The language switcher translates in place; it doesn't navigate.**
    - `I18nProvider` holds all three dictionaries on the client. `setLocale` swaps the dictionary, then updates `<html lang>`, the tab title and the URL through `history.replaceState`, so an uploaded video, analysis results and review marks survive.
    - Visible text must therefore come from `useI18n()` in client components (the landing is `components/Landing.tsx`; `PageIntro` takes a dictionary key).
    - Server `getDictionary()`, which reads `next/root-params`, is only for `generateMetadata`. Text rendered from it would not switch.
    - Client components call `useI18n()` (`t`, `locale`, `href(path)`, `setLocale`). Build internal links with `href()` / `localePath()`, never raw `"/..."`. Pages pass `path` to `SiteHeader` instead of using `usePathname()`, which would cause a hydration mismatch behind the rewrite. Plurals use `plural()` with Intl plural forms. Model text from the backend is never translated. Dates go through `formatDateTime`, which formats `kk` as `ru`, because Chrome's ICU has no Kazakh date data.
  Shared models are in `lib/types.ts`. Video and frames go through `components/media/`:
    - `VideoPlayer` supports timeline markers and ranges, a `segment` clip mode, `fallbackSrc` and `fallback`;
    - `EpisodeMedia`, `EvidenceFrames` and `MediaPlaceholder`. Video is 16:9 with `object-contain`, never `cover`. The backend contract actually implemented is in `README.md`; `backend/backend_description.md` is the older, larger design.
- **Design system.** Any UI work goes through the `forte-design` skill (`.claude/skills/forte-design/SKILL.md`). Its "Project direction" section is what the user approved:
  - white background, minimal, magenta (`#A31551`) only as an accent;
  - only Forte's four main colours and the two brand gradients;
  - no gradient blocks (one thin `bg-gradient-primary` line at most);
  - light theme only;
  - Open Sans with weights 300/400/600/700/800;
  - only real data, never filler.

  Colours are CSS-variable tokens in `src/app/globals.css`, exposed to Tailwind via `@theme inline`. Don't hard-code hex in components. `BrandMark.tsx` renders the official logo files from `public/brand/Forte_logos/`; never a text logo. The brand book lives in `forte-brandbook.md`, with an identical copy at `.claude/skills/forte-design/references/brandbook.md`; edit both together.
- **Config.** pydantic-settings reading env vars / `.env` (`backend/.env.example`; docker compose uses `backend/.env` as `env_file` and overrides `DATA_DIR=/data`).

## Conventions / gotchas

- `frontend/AGENTS.md`: this Next.js version has breaking changes vs. older knowledge — read the bundled docs in `frontend/node_modules/next/dist/docs/` before writing Next.js code.
- The root `.gitignore` is the GitHub Python template, whose `lib/` rule would ignore `frontend/src/lib/`; an explicit `!frontend/src/lib/` exception keeps it tracked. `data/*` and `ml/artifacts/*` are gitignored (only `.gitkeep` is tracked), so trained models and datasets live locally. `backend/.gitignore` ignores `backend/data/` (uploads, job JSON).
- `frontend/public/.gitkeep` must stay: the frontend Dockerfile copies `public/`.
- Ruff line length is 100 in both Python services.
- `package.json` currently pins `eslint-config-next@^14` next to Next 16, so plain `npm install` fails with ERESOLVE. Use `npm ci --legacy-peer-deps`. The right fix is pinning it to 16.x. `eslint-config-next` must match the installed `next` major (16.x). `npm audit fix --force` downgrades it to 14.x, which breaks `npm run lint` with `ERR_MODULE_NOT_FOUND` while the build still passes.
