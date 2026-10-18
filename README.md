# DataThon 2026: cash desk video analysis

A local service that takes a top-down CCTV video of a bank cash desk and reports possible
cashier violations:
- type and timecode;
- 1–3 evidence frames;
- what is visible and why it may be a violation;
- the public legal source.

| Part | What it is |
|---|---|
| `backend/` | FastAPI service: the jury API, background jobs and a simple web page |
| `frontend/` | Next.js UI: `/demo-inference` (upload, AI pipeline stages, violation episode) and `/demo-dashboard` (history, statistics, false-positive review) |
| `ml/` | The ML team's Qwen3.8-27B pipeline (router → timelines → final audit), an offline CLI for a CUDA GPU; see `ml/README.md` |
| `inference/` | The ML microservice: runs the `ml/` pipeline on the GPU machine behind [the contract below](#plugging-in-the-ml-microservice) |

The analysis sits behind a swappable interface. By default `ANALYZER=http` sends each video to
the ML microservice; until it runs, uploads are still stored but the job ends `failed` ("ML
service unreachable"), never with invented results. `ANALYZER=mock` (fake results marked
`[MOCK]`) is for UI development only and must be set explicitly.

Fully local: no cloud services, works offline once installed. Dependencies are open source with
licences that allow commercial use (FastAPI/Pydantic/PyYAML/httpx: MIT/BSD, OpenCV: Apache 2.0
with LGPL FFmpeg bundled, Next.js/React: MIT).

## Run locally

### 1. Prerequisites (once)

- **uv**, the Python package manager: `curl -LsSf https://astral.sh/uv/install.sh | sh`. It
  installs the right Python by itself.
- **Node.js 20 or newer**: from [nodejs.org](https://nodejs.org) or `brew install node`.
- **git** and **make**: preinstalled on macOS (`xcode-select --install` if missing).

No ffmpeg, Docker or GPU is needed.

### 2. Get the code

```bash
git clone https://github.com/mountain-nomad/DataThon2026.git
cd DataThon2026
git switch feature/backend-jury-api   # until this branch is merged into main
```

### 3. Create the two config files

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

Put **the same key** in both files:

| File | Line |
|---|---|
| `backend/.env` | `API_KEY=<long random string>` |
| `frontend/.env.local` | `ANALYSIS_API_KEY=<the same string>` |

`python3 -c "import secrets; print(secrets.token_hex(16))"` generates one. Both files are
gitignored: each person creates their own, and keys never go through git.

### 4. Install and run

```bash
make install    # backend deps (uv) + frontend deps (npm)
make dev        # backend :8000 + frontend :3000; Ctrl+C stops both
```

| Address | What's there |
|---|---|
| http://localhost:3000/demo-inference | Upload a `.mov` and watch the stages |
| http://localhost:3000/demo-dashboard | History and statistics of finished analyses |
| http://localhost:8000 | The simple built-in page |
| http://localhost:8000/docs | API docs |

### Things that might trip you up

- **No ML service, no results.** `ANALYZER=http` is the default: without the ML service at
  `ML_SERVICE_URL` (see [below](#plugging-in-the-ml-microservice)) every job ends `failed` with
  "ML service unreachable". The video is still stored. Fake results need `ANALYZER=mock`.
- **Port 3000 already in use:** Next.js silently moves to 3001. Stop the other program, or
  open the address Next.js prints.
- **The first backend start takes about 20 seconds.** Uploads before it's ready fail with
  "connection refused".
- **Don't run plain `npm install`.** It fails with ERESOLVE, because `package.json` pins
  `eslint-config-next@14` next to Next 16. `make install` uses `npm ci --legacy-peer-deps`.
- **Test videos are not in the repo.** Share them separately, and keep them private.

### Windows (no `make`)

Run in two terminals:

```bash
cd backend && uv sync && uv run fastapi dev app/main.py --port 8000
cd frontend && npm ci --legacy-peer-deps && npm run dev -- --port 3000
```

### API only, in Docker

No uv or Node needed: create `backend/.env` as in step 3, then run `docker compose up --build`.
It starts the backend on :8000, without the frontend.

## Jury API

Every `/api/v1` request needs the `X-API-Key` header; otherwise `401`.

```bash
curl -X POST https://<address>/api/v1/analyze -H "X-API-Key: <key>" -F "file=@video_017.mov"
# {"job_id":"3f2a9c1e..."}
curl https://<address>/api/v1/jobs/3f2a9c1e... -H "X-API-Key: <key>"
```

```json
{
  "job_id": "3f2a9c1e...",
  "status": "done",
  "verdict": "violation",
  "violations": [
    {
      "type": "Кассир оставляет сейф открытым после извлечения денег и перехода к подсчету",
      "timecode_sec": 44.2,
      "description": "Что видно...\nПочему это может быть нарушением: по регламенту — ...\nОснование: Правила ... (Постановление Правления НБ РК ... №231), п. 20, абз. 2 (https://old.adilet.zan.kz/rus/docs/V1900019680)",
      "evidence_frames": [{ "timestamp_sec": 44.2, "image_base64": "/9j/4AAQ..." }]
    }
  ]
}
```

- **`status` and `verdict`:** `status` is `processing`, `done` or `failed` (a failed job has
  `error`). `verdict` is `violation` or `no_violation`; with `no_violation`, `violations` is
  empty.
- **`type`:** the regulation's wording of the violation (the specialist catalog quote).
- **`description`:**
  1. what is visible;
  2. why it may be a violation (the regulation rule);
  3. the public legal source with its clause and link.
- **`evidence_frames`:** 1–3 JPEG frames, base64 without a `data:` prefix, long side ≤ 640 px.
  There is always at least one: if the frames at the timecode can't be read, the middle or start
  of the video is used.
- **Upload errors:** `415` wrong extension, `400` empty file, `413` too large, `422` no readable
  video stream, `502` the video couldn't be stored in Supabase (no job is created). An unknown
  job returns `404`.

### Video storage (Supabase)

With `STORAGE_BACKEND=supabase` (the default), the upload flow is:

1. `POST /api/v1/analyze` streams the file to `DATA_DIR/uploads/{job_id}.mov` and validates it.
2. The backend uploads the file unchanged to the private bucket `SUPABASE_BUCKET` as
   `{YYYY}/{MM}/{job_id}.mov`. The bucket is created on the first start.
3. The job stores that stable `storage_path` next to the local `video_path`. The analyzer keeps
   reading the local copy.

The jury response stays `{"job_id": ...}`. Signed URLs come from an internal endpoint, which is
local-only and needs no key:

```bash
curl -s -X POST localhost:8000/api/v1/analyze -H "X-API-Key: $API_KEY" -F "file=@video.mov"
# {"job_id":"b5badd7120e3429b8e3c575b58eafd1a"}
curl -s localhost:8000/api/jobs/b5badd7120e3429b8e3c575b58eafd1a/video-url
# {"job_id":"b5ba…","storage_path":"2026/10/b5ba….mov",
#  "url":"https://<project>.supabase.co/storage/v1/object/sign/videos/2026/10/b5ba….mov?token=…",
#  "expires_in":3600}
```

- **Signed URLs:** every call mints a new one. `/api/jobs/{id}/pipeline` also returns
  `storage_path`.
- **After the local copy is deleted** (`UPLOAD_RETENTION_HOURS`), `/api/jobs/{id}/video`
  redirects (`307`) to a signed URL. Retention deletes the stored object too.
- **`SUPABASE_KEY` must be the secret (`sb_secret_…`) / service_role key.** The publishable or
  anon key fails at startup with a row-level security error. The key stays on the backend and is
  never sent to the frontend.
- **File size:** the Supabase free plan caps a file at 50 MB. That covers the ~29 MB sample
  clips, but not the default `MAX_UPLOAD_MB=500`. Raise the project's limit or lower
  `MAX_UPLOAD_MB` to match.
- **Contest rules:** the ТЗ forbids passing jury test videos to third parties without the
  organiser's permission. Without that permission, run the jury build with
  `STORAGE_BACKEND=local`, which keeps videos only in `DATA_DIR/uploads`.

### Time limit

The jury counts a video as unprocessed after 5 minutes.
- **Every job ends within `JOB_TIMEOUT_SEC`** (default 270 s), counted from the upload, queue
  time included.
- **Processing time varies per video**, so the analyzer gets a deadline. It reports partial
  results as it goes: router, then each specialist.
- **When the deadline passes:**
  - the analyzer process is killed;
  - the job returns `done` with the finished specialists' results;
  - a note goes into `limitations`, which is internal and not sent to the jury.
- **A job fails only when not even one specialist finished.**
- **Queueing:** jobs run `MAX_CONCURRENT_JOBS` at a time (default 1). If the jury sends many
  videos at once, later ones wait, and the wait eats into their budget. Measure the model's time
  per video and raise the concurrency if the GPU allows.

### Handing it to the jury

1. Use a long random `API_KEY` in `backend/.env`. Send it to the jury together with the
   address.
2. Publish only the backend. For example, run `cloudflared tunnel --url http://localhost:8000`
   for an HTTPS address, or put the backend behind a reverse proxy with a domain.
3. **Only `/api/v1/*`, `/health` and `/docs` answer remote clients.** Everything else answers
   only loopback and private-network clients (`LOCAL_ONLY_UI=true`): the web pages, the
   key-less `/ui/*` and `/api/jobs/*` endpoints, the uploaded videos and the history.
   - Tunnels and proxies pass the real client address in `X-Forwarded-For` /
     `Cf-Connecting-Ip`, and those requests count as remote.
   - So the test videos can't be seen or downloaded through the public address.
4. **Test videos must not be used for training, published or passed on.** With
   `STORAGE_BACKEND=local` they are stored only in `backend/data/uploads/`; the default
   `supabase` also copies them to Supabase (see Video storage). `UPLOAD_RETENTION_HOURS` deletes them (results stay) after the
   given time; keep it `0` until the jury has collected the results. Never add them to a dataset.

## Plugging in the ML microservice

Set `ANALYZER=http` and `ML_SERVICE_URL=http://<host>:<port>` in `backend/.env`. `inference/`
is that service ([below](#inference-service-inference)); any other service must implement:

**`GET /health`** → `{"status": "ok", "model_loaded": true, "model_version": "..."}`. It's shown
in the backend's `/health`.

**`POST /analyze`**, a form (`multipart/form-data`, or urlencoded when there's no file), with
`Authorization: Bearer <ML_SERVICE_KEY>` when that is set:

| Field | Meaning |
|---|---|
| `video_url` | A signed Supabase link to the video. Sent when the upload is in Supabase and `ML_SEND_LINK=true` (the default); the service downloads it itself. |
| `file` | The video (`.mov`), sent instead of `video_url` otherwise (`STORAGE_BACKEND=local`, `ML_SEND_LINK=false`). |
| `deadline_sec` | Seconds the analysis may take from now. Do less when it's small: fewer frames, skip the secondary scenario. |
| `job_id` | For logs |

**Response:** either a plain JSON `AnalysisResult`, or better, a stream
(`Content-Type: application/x-ndjson`) with one JSON object per line:

```
{"event": "partial", "result": {"scenario": {...}, "specialist_results": []}}
{"event": "partial", "result": {"scenario": {...}, "specialist_results": [...]}}
{"event": "result",  "result": {"scenario": {...}, "specialist_results": [...]}}
```

`{"event": "error", "detail": "..."}` fails the job with that message.

How the partials are used:
- they drive the frontend's stage progress;
- if the deadline passes, the last partial is returned to the jury instead of a failure.

An `AnalysisResult` is the router scenario plus the specialist outputs, in the same fields as the
specialist prompts' JSON:

```json
{
  "scenario": { "primary": "COUNTING_FROM_SAFE", "secondary": null },
  "specialist_results": [
    {
      "scenario": "COUNTING_FROM_SAFE",
      "status": "violation",
      "rule_id": "s3:L85",
      "quote": "Нарушение: кассир оставляет сейф открытым после извлечения денег и перехода к подсчету.",
      "evidence": "Кассир переходит к счетной машинке, дверца сейфа остается открытой.",
      "start_sec": 44.2,
      "end_sec": 51.0,
      "confidence": 0.81,
      "evidence_timestamps": null
    }
  ]
}
```

**`scenario`:** one of the 7 router classes:
- `ENTRY`
- `COUNTING_DEPOSIT_WITHOUT_CLIENT`
- `CLIENT_CASH_DEPOSIT`
- `COUNTING_FROM_SAFE`
- `OPENING_A_CASH_BAG`
- `RECEIVING_A_BAG_FROM_CLIENT`
- `EXIT_CLOSING`

**`specialist_results`:** one item per finding. A specialist that found nothing returns one item
with `no_violation` or `insufficient_evidence`.
- **`status`:** `violation`, `no_violation` or `insufficient_evidence`.
- **`rule_id` and `quote`:** from the specialist's catalog, copied exactly.
- **`start_sec` / `end_sec`:** seconds of the original video.
- **Optional fields:**
  - `confidence`: a violation below `MIN_CONFIDENCE` is shown as `insufficient_evidence` and not
    sent to the jury;
  - `evidence_timestamps`: where to take the frames; the default is `start_sec` ± 1 s;
  - `type`: a violation type id from the legal mapping, e.g. `T10`.

What the backend does with it:
1. the evidence frames, from the original file;
2. the legal basis;
3. the jury `type` and `description`;
4. the verdict;
5. the timeout and the queue.

The ML service only has to answer this contract. `backend/app/analyzers/http.py` is the client.
Without a separate service, a Python class works too:
- `ANALYZER=module.path:ClassName` with `analyze(video_path, ctx)`;
- `ctx.time_left()` and `ctx.report(partial)` play the same roles as `deadline_sec` and the
  partial events.

## Inference service (`inference/`)

The ML microservice. It runs the `ml/` pipeline **unchanged** (`ml/scripts/run_pipeline.py`:
router → video timelines → object reconciliation → final text audit), so it must run **on the
GPU machine** (the RTX 5090), in the pipeline's own environment. The backend can run anywhere
that reaches it.

```
frontend ──upload──▶ backend ──file──▶ Supabase (private bucket)
                        │  signed link
                        ▼
              inference/ on the GPU machine ── downloads the video by the link
                        │  ml/scripts/run_pipeline.py (Qwen3.8-27B)
                        ▼
backend ◀── NDJSON: router scenario, then the findings ── evidence frames, legal basis, verdict
   │
   ▼
frontend (/demo-inference stages and results)
```

- **Input:** a link (`video_url`) or an uploaded `file`, see the contract above. The video, its
  frames and the run folder are deleted after each job (`KEEP_ARTIFACTS=1` keeps the run's prompts
  and raw answers in `ml/artifacts/service/` for debugging; the video is always deleted).
- **Progress:** a `partial` event with the router's scenario as soon as the timeline stage
  starts, then the `result`. Each finding becomes one `violation` result with the catalog
  `rule_id` (`s2:L58`…, the ids in `backend/specialist_crosswalk.yaml`) and the pipeline's
  description and timecode; no finding gives one `no_violation` per routed scenario.
  A `ПРЕДУПРЕЖДЕНИЕ:` (warning) finding keeps the model's own type, since it cites an ideal step
  rather than a `Нарушение:` line.
- **One video at a time.** The stages share manifests in `ml/artifacts/`; a second request waits
  for the first, up to its deadline. `/health` shows `busy`.
- **Time:** every stage loads the 27B model itself, so one video takes several minutes. That is
  longer than the default `JOB_TIMEOUT_SEC=270` (the jury's 5-minute limit): measure it on the
  5090 and raise `JOB_TIMEOUT_SEC` for demos. At the deadline the service kills the pipeline, so
  the GPU is freed.

### Run it on the GPU machine

```bash
# once: the ml/ environment and checkpoint as in ml/README.md, then
ml/.venv/bin/python -m pip install -r inference/requirements.txt
cp inference/.env.example inference/.env      # set INFERENCE_API_KEY for HTTPS

ml/.venv/bin/python -m inference                    # 127.0.0.1:8001, reach it over SSH
ml/.venv/bin/python -m inference --host 0.0.0.0     # public: refuses to start without a key
```

### Connect the backend

**Over SSH** (the GPU is reachable only by SSH, e.g. a lab machine). Keep a tunnel open on the
machine that runs the backend, through a jump host if needed:

```bash
ssh -N -L 8001:127.0.0.1:8001 user@gpu-host                  # direct
ssh -N -L 8001:127.0.0.1:8001 -J user@jump-host user@gpu-host # via a jump host (e.g. the lab laptop)
```

Then `ML_SERVICE_URL=http://localhost:8001` in `backend/.env`. If the GPU machine has no internet
access, it can't download the Supabase link: set `ML_SEND_LINK=false` and the backend uploads the
file through the tunnel instead.

**Over HTTPS** (the backend is somewhere else, e.g. in the cloud). Publish the service from the
GPU machine, or from a machine that has the SSH tunnel above, e.g. with
`cloudflared tunnel --url http://localhost:8001`. Then set `ML_SERVICE_URL=https://<address>`
and `ML_SERVICE_KEY` (= the service's `INFERENCE_API_KEY`) in `backend/.env`.

Try it without the backend:

```bash
curl -N -X POST http://localhost:8001/analyze -H "Authorization: Bearer $INFERENCE_API_KEY" \
  -F video_url="https://<project>.supabase.co/storage/v1/object/sign/videos/….mov?token=…"
curl -N -X POST http://localhost:8001/analyze -H "Authorization: Bearer $INFERENCE_API_KEY" \
  -F file=@video.mov
```

## Legal sources (task §6)

Each detected violation is linked: **public source → clause → violation type → regulation rule →
video fragment**. On the frontend this is shown under each violation, next to the localized
episode and the evidence frames. In the API it is the last line of `description`.

| File | Contents |
|---|---|
| `backend/fortebank_violation_legal_mapping_updated.yaml` | The team's research: sources, clauses (`R01`–`R21`), violation types (`T01`–`T17`) with limitations |
| `backend/specialist_crosswalk.yaml` | **Draft** link from specialist `rule_id` to violation type. It needs the team's review. Unmapped rules are shown as "not mapped", never guessed. |

The mapping's own caveats are carried through, not hidden:
- every clause is still `human_verified: false` until someone checks it on Әділет;
- the office-safety sample instruction is marked as a supplementary, non-binding source;
- each type's limitations are shown next to the violation.

Sources used:

| Source | Link |
|---|---|
| Правила осуществления кассовых операций и операций по инкассации банкнот, монет и ценностей (Постановление Правления НБ РК от 29.11.2019 №231) | https://old.adilet.zan.kz/rus/docs/V1900019680 |
| Правила организации охраны и устройства помещений банков (Постановление Правления НБ РК от 24.02.2020 №14) | https://old.adilet.zan.kz/rus/docs/V2000020075 |
| Закон РК от 28.08.2009 №191-IV о противодействии легализации (отмыванию) доходов | https://old.adilet.zan.kz/rus/docs/Z090000191_ |
| Закон РК «О банках и банковской деятельности в Республике Казахстан» №258-VIII | https://old.adilet.zan.kz/rus/docs/Z2600000258 |
| Требования к обеспечению информационной безопасности банков (Постановление Правления АРРФР №53) | https://old.adilet.zan.kz/rus/docs/V2600038336 |
| Инструкция по безопасности и охране труда для офис-менеджера (образец, ZakonPravo.kz; supplementary, not a normative act) | https://zakonpravo.kz/instrukciya-po-bezopasnosti-i-ohrane-truda-dlya-ofis-menedzhera |

## Configuration (`backend/.env`)

| Var | Default | Purpose |
|---|---|---|
| `API_KEY` | — (required) | Jury key; the service won't start without it |
| `ANALYZER` | `http` | `http` (the ML microservice), `mock` (fake results, UI dev only) or `module.path:ClassName` |
| `ML_SERVICE_URL` | `http://localhost:8001` | ML microservice, for `ANALYZER=http` |
| `ML_SERVICE_KEY` | — | Bearer token for the ML service (its `INFERENCE_API_KEY`) |
| `ML_SEND_LINK` | `true` | Send the ML service the Supabase signed link; `false` uploads the file |
| `MOCK_DELAY_SEC` | `3` | Fake processing time of the mock |
| `JOB_TIMEOUT_SEC` | `270` | Upload to done/failed, queue included |
| `MAX_CONCURRENT_JOBS` | `1` | Videos analyzed at the same time |
| `MIN_CONFIDENCE` | `0.5` | Below it, a violation becomes `insufficient_evidence` |
| `MAX_UPLOAD_MB` | `500` | Upload limit |
| `DATA_DIR` | `./data` | `uploads/` (videos) and `jobs/` (one JSON per job) |
| `LEGAL_MAPPING_FILE` | `./fortebank_violation_legal_mapping_updated.yaml` | Sources, clauses, violation types |
| `CROSSWALK_FILE` | `./specialist_crosswalk.yaml` | Specialist rule → violation type |
| `LOCAL_ONLY_UI` | `true` | Key-less endpoints and pages answer local clients only |
| `UPLOAD_RETENTION_HOURS` | `0` | Delete uploaded videos after N hours (`0` keeps them) |
| `UI_ENABLED` | `true` | The simple page and `/ui/*` |
| `STORAGE_BACKEND` | `supabase` | `supabase` (also store uploads in a private bucket) or `local` |
| `SUPABASE_URL` | — | `https://<project>.supabase.co`, required for `supabase` |
| `SUPABASE_KEY` | — | Secret / service_role key, backend only, required for `supabase` |
| `SUPABASE_BUCKET` | `videos` | Private bucket, created on start if missing |
| `SIGNED_URL_TTL_SEC` | `3600` | Lifetime of signed video URLs |

Jobs that are still `processing` when the service restarts are marked `failed`.
