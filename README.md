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
| `ml/` | The old iris demo skeleton. The real model will be a separate ML microservice, see [the contract below](#plugging-in-the-ml-microservice) |

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

Set `ANALYZER=http` and `ML_SERVICE_URL=http://<host>:<port>` in `backend/.env`. The ML service
must implement:

**`GET /health`** → `{"status": "ok", "model_loaded": true, "model_version": "..."}`. It's shown
in the backend's `/health`.

**`POST /analyze`**, `multipart/form-data`:

| Field | Meaning |
|---|---|
| `file` | The video (`.mov`) |
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

## Inference (`inference/`)

`run_inference(video_url, prompt=None, job_id=None)` takes a video **link** (e.g. a Supabase
Storage signed URL) and returns the result **in the jury API format**:

```json
{"job_id": "48d247dd…", "status": "done", "verdict": "violation",
 "violations": [{"type": "…", "timecode_sec": 35.8, "description": "…",
                 "evidence_frames": [{"timestamp_sec": 35.8, "image_base64": "/9j/4AAQ…"}]}]}
```

- **The video is never saved.** OpenCV's FFmpeg reads the link over HTTP and requests only the
  byte ranges around each moment it needs. The link must support HTTP `Range`, which Supabase
  does. Frames are decoded in memory and sent to the model as images, each labeled with its
  second, so the model can answer with timecodes. Measured on a 142 s, 28.7 MB video: 8 frames
  take 0.3 s and ~33% of the file crosses the network; 16 frames, ~66%.
- **Failures:** an expired link, or a link that isn't a video, returns
  `{"job_id": …, "status": "failed", "error": "…"}`.
- **`job_id`:** defaults to the file name in the link.

**The pipeline is a PLACEHOLDER for now.** It reads real frames but doesn't call the model (no
endpoint cost), and returns one violation marked `PLACEHOLDER` at the middle of the video, with
3 real evidence frames. When `ml/pipeline.py` is ready, its code replaces `run_pipeline()` in
the `PIPELINE` section of `inference/inference.py`. The building blocks:
- `video.sample(n)` and `video.frames_at([seconds])`: frames from the link;
- `frame_parts(frames, prompt)`: message parts for the model (labeled frames + prompt);
- `call_model(parts)`: one OpenAI-compatible `/chat/completions` request; returns the text.

The real pipeline returns the violations in the same shape.

Endpoint settings (see `inference/.env.example`):

| Setting | Meaning |
|---|---|
| `INFERENCE_ENDPOINT_URL` | Endpoint address, e.g. `https://api.runpod.ai/v2/<id>/openai/v1` |
| `INFERENCE_API_KEY` | Endpoint key. Never commit it. |
| `INFERENCE_MODEL` | `qwen/qwen3.8-27b` |
| `INFERENCE_TIMEOUT_SEC` | Request timeout |
| `INFERENCE_MAX_TOKENS` | Answer length limit |
| `INFERENCE_FRAMES` | Frames per video, for the real pipeline |

Needs OpenCV (`inference/requirements.txt`); the backend's environment already has it. Try it
from the repo root:

```bash
backend/.venv/bin/python -m inference "https://<project>.supabase.co/storage/v1/object/sign/videos/….mov?token=…" --short
```

From Python: `from inference import run_inference, VideoStream, frame_parts, call_model`.

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
