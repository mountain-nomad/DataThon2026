# Backend Specification — AI Cash Operations Monitoring

REST API (FastAPI, `backend/`, port 8000) behind the frontend described in
`frontend/frontend_description.md` and `frontend/frontend_description2.md` (the AI pipeline on
`/demo-inference`). This document is the contract between the three services:

```text
browser ──> frontend :3000 ──(/api/* proxy)──> backend :8000 ──> ml :8001
jury    ──────────────────── X-API-Key ──────> backend :8000
```

**Assumptions.** The jury API is known only from the frontend spec: the two endpoints, the
`job_id`, the status values and the result fields `verdict`, `violations`, `timecode_sec`,
`description` and `evidence_frames`. Everything else about it below is marked
**[assumption]**. Check it against the task statement before implementing.

---

## 1. Principles

- **Everything is local.** Video, inference and transcoding run on local machines. No cloud AI
  APIs and no external video services.
- **No face recognition or identification.** Nothing in the API returns or stores identities.
- **AI output is never overwritten.** Human review (false positives) is stored separately from
  the model output.
- **No authorisation for the UI and no history or export features.** The only secret is the jury's
  `X-API-Key`.
- **Errors have one shape:** FastAPI's `{"detail": "<human-readable message>"}`. The frontend
  shows `detail` as-is.
- **JSON is `snake_case`.** The frontend converts it to its camelCase models in `lib/api.ts`.
- **Times are seconds** (`float`). Every timecode is relative to the **original recording**,
  except `episode_timecode_sec`.
- **No UI language on the backend.** The UI is ru/kk/en. The backend returns ids (scenario
  ids, `status` values, `rule_id`) and the frontend translates them. Free text from the model
  (`quote`, `evidence`, `description`) is returned as generated and shown untranslated. There is
  no `Accept-Language` handling.

---

## 2. Endpoint overview

| Method | Path | Auth | Used by | Purpose |
|---|---|---|---|---|
| `POST` | `/api/v1/analyze` | `X-API-Key` | jury, `/demo-inference` | Upload a `.mov` and start analysis |
| `GET` | `/api/v1/jobs/{job_id}` | `X-API-Key` | jury, `/demo-inference` | Job status and result (jury contract) |
| `GET` | `/api/jobs/{job_id}/pipeline` | — | `/demo-inference` | Stage progress and the router/specialist output |
| `GET` | `/api/jobs/{job_id}/preview.mp4` | — | `/demo-inference` | Browser-playable preview of the upload |
| `GET` | `/api/demo/cameras` | — | `/demo-dashboard` | The 16 demo cameras |
| `GET` | `/api/demo/events` | — | `/demo-dashboard` | Detected episodes (one list, the source for all stats) |
| `PUT` | `/api/events/{event_id}/review` | — | `/demo-dashboard` | Mark or unmark a false positive |
| `GET` | `/api/media/{path}` | — | both demos | Demo previews, clips and frames (static, supports Range) |
| `GET` | `/api/health` | — | ops | Backend + ML status (already exists) |

`/api/v1/*` is the jury contract. **Don't add or rename fields there for the UI.** UI extras
live under `/api/jobs/*`, `/api/demo/*` and `/api/events/*`.

The existing iris endpoints (`/api/model`, `/api/predict`, `/api/predict/csv`,
`/api/predictions`) are no longer used by the frontend. Remove them along with
`PredictionLog` once the video pipeline works.

---

## 3. Jury API (`/api/v1`)

### 3.1 Authentication

- Header: `X-API-Key: <key>`. The key is read from the `API_KEY` env var and compared with
  `secrets.compare_digest`.
- Missing or wrong key: `401 {"detail": "Invalid or missing API key"}`.
- If `API_KEY` is empty, the backend refuses to start. This prevents an open endpoint by
  accident.
- The key never reaches the browser. See §8 for how the frontend's server adds it.

### 3.2 `POST /api/v1/analyze`

Request: `multipart/form-data` with one field, `file`.

Validation, in this order:

| Check | Failure |
|---|---|
| `file` field present | `422` (FastAPI default) |
| Extension is `.mov` (case-insensitive) | `415 {"detail": "Only .mov files are accepted."}` |
| Size > 0 | `400 {"detail": "The file is empty."}` |
| Size ≤ `MAX_UPLOAD_MB`, checked **while streaming**, not after | `413 {"detail": "File exceeds <N> MB."}` |
| `ffprobe` finds at least one video stream | `422 {"detail": "The file contains no readable video stream."}` |

The upload is streamed to `UPLOAD_DIR/{job_id}/original.mov` in chunks (1 MB), never read
into memory as a whole. On any validation failure, the partial file is deleted.

Response `200` **[assumption: status code per task statement]**:

```json
{ "job_id": "3f0c9a1e-6a0b-4a52-9c1d-2f7e1b8d4c10" }
```

- `job_id` is a UUID4 string.
- The response returns as soon as the file is stored and the job is queued. Analysis runs in
  the background (§5).
- The job is created with status `processing`.

### 3.3 `GET /api/v1/jobs/{job_id}`

Responses:

| Case | Code | Body |
|---|---|---|
| Unknown `job_id` | `404` | `{"detail": "Job not found"}` |
| Still running | `200` | `{"job_id": "…", "status": "processing"}` |
| Failed | `200` | `{"job_id": "…", "status": "failed", "error": "<reason>"}` |
| Done | `200` | see below |

Done:

```json
{
  "job_id": "3f0c9a1e-…",
  "status": "done",
  "verdict": "violations_detected",
  "violations": [
    {
      "type": "cash_counted_outside_camera_view",
      "timecode_sec": 754.2,
      "description": "Employee moves the cash bundle below the counter edge while counting.",
      "evidence_frames": [
        { "timestamp_sec": 753.8, "image_base64": "/9j/4AAQSkZJRgABAQ…" }
      ]
    }
  ]
}
```

| Field | Type | Notes |
|---|---|---|
| `verdict` | string | `"violations_detected"` if `violations` is non-empty, otherwise `"no_violations"`. **[assumption: exact values per task statement]**. The frontend derives the verdict from `violations.length`, so it works either way. |
| `violations[].type` | string | Violation class id. **[assumption: the jury contract may not include it; the frontend also reads `violation_type`, and falls back to "Unclassified"]** |
| `violations[].timecode_sec` | float | Seconds from the start of the **original** file. |
| `violations[].description` | string | What is visible on the video, in one or two sentences. Factual, with no conclusion of guilt. |
| `violations[].evidence_frames` | array, 1–3 items | `{timestamp_sec, image_base64}`. The image is JPEG, base64 **without** a `data:` prefix, long side ≤ 640 px (keeps the response small). **[assumption: format per task statement; the frontend also accepts plain base64 strings]** |

Violations are sorted by `timecode_sec`. The response always carries the same model output for
the same job: review marks don't change it.

**Derived from the pipeline (§4.1).** `violations` holds the specialist results with
`status == "violation"`. Each one maps as follows:
- `type` ← `rule_id`;
- `timecode_sec` ← `start_sec`;
- `description` ← `evidence`;
- `evidence_frames` ← `evidence_frames`.

The jury payload carries no `no_violation` or `insufficient_evidence` results.

---

## 4. UI endpoints

### 4.1 `GET /api/jobs/{job_id}/pipeline`

The source for the whole result screen of `/demo-inference`. It's polled every 2.5 s from the
moment of upload, so it answers **while the job is still running** and shows partial results.

```json
{
  "job_id": "3f0c9a1e-…",
  "status": "processing",
  "error": null,
  "stages_done": 2,
  "duration_sec": 63.0,
  "preview_url": null,
  "scenario": { "primary": "CLIENT_CASH_DEPOSIT", "secondary": "COUNTING_FROM_SAFE" },
  "specialist_results": [
    {
      "scenario": "CLIENT_CASH_DEPOSIT",
      "rule_id": "…",
      "status": "violation",
      "quote": "…",
      "evidence": "…",
      "start_sec": 44.2,
      "end_sec": 51.0,
      "evidence_frames": [{ "timestamp_sec": 44.2, "image_base64": "…" }]
    }
  ]
}
```

| Field | Notes |
|---|---|
| `status`, `error` | Same as in `/api/v1/jobs/{id}`. |
| `stages_done` | How many AI stages are finished: `0`, `1` (scenario), `2` (violations) or `3` (localization). `3` when `done`. **`null` if the backend doesn't track stages.** The UI then animates the stages only after `done` and says so: it never fakes progress. |
| `scenario` | Router output, present from `stages_done >= 1`. `primary` is required. `secondary` is the second candidate, or `null`. Values are **canonical ids** of the 7 router classes (table below). The frontend also normalises labels like `"COUNTING / DEPOSIT WITHOUT CLIENT"`, and shows anything outside the 7 as-is with a note. |
| `specialist_results` | Present from `stages_done >= 2`. **Exactly what the specialists returned, nothing invented.** |
| `[].scenario` | The scenario id whose specialist produced the result. It must be `primary` or `secondary`; the UI drops anything else, because a specialist's verdict is only valid for its scenario. |
| `[].status` | `"violation"`, `"no_violation"` or `"insufficient_evidence"`. A specialist that found nothing still returns **one** result with `no_violation` or `insufficient_evidence` (`rule_id` may be `null`), so the UI can show that outcome. |
| `[].rule_id`, `[].quote`, `[].evidence` | As returned by the specialist. `quote` is the rule text the specialist cites, and `evidence` is what it saw on the video **[assumption: check the prompt's output format]**. |
| `[].start_sec`, `[].end_sec` | Localized episode, in seconds of the original. `null` if it wasn't localized. The UI plays this range of the original as the "violation episode" clip, so **no clip files need to be cut** for this page. Without `start_sec` it shows `evidence_frames[0]`. |
| `[].evidence_frames` | 0–3 frames, same format as §3.3. They are the fallback when the episode can't be played. |
| `preview_url`, `duration_sec` | `preview_url` is `null` until the preview is ready (§5). The UI uses it only when the browser can't decode the uploaded `.mov` itself. |

- `404` if the job is unknown. There is no `409`: a running job returns what it has.
- `failed` keeps whatever partial `scenario` and `specialist_results` it had.
- Unauthenticated, like all UI endpoints. The job id is an unguessable UUID, and the data is
  what the jury endpoint would return.

Scenario ids (router classes, `frontend_description2.md` §2):

| Id | Router label |
|---|---|
| `ENTRY` | ENTRY |
| `COUNTING_DEPOSIT_WITHOUT_CLIENT` | COUNTING / DEPOSIT WITHOUT CLIENT |
| `CLIENT_CASH_DEPOSIT` | CLIENT CASH DEPOSIT |
| `COUNTING_FROM_SAFE` | COUNTING FROM SAFE |
| `OPENING_A_CASH_BAG` | OPENING A CASH BAG |
| `RECEIVING_A_BAG_FROM_CLIENT` | RECEIVING A BAG FROM CLIENT |
| `EXIT_CLOSING` | EXIT / CLOSING |

The rule: id = the label in upper case, with every run of non-alphanumerics replaced by `_`.
Scenario names in ru/kk/en, and the list of violation types each specialist checks, live in the
frontend dictionaries (`t.scenarios`). The backend doesn't send them.

### 4.2 `GET /api/jobs/{job_id}/preview.mp4`

Browser-playable H.264/AAC MP4 of the uploaded `.mov`. A browser may not decode the codec
inside a `.mov`. The preview is for display only; inference always uses the original.

- `404` until the preview exists, or if the job is unknown.
- Must support HTTP `Range` requests (`206 Partial Content`), otherwise seeking and
  "Jump to timestamp" break. Starlette's `FileResponse` handles this.
- Recommended encode: `ffmpeg -i original.mov -c:v libx264 -preset veryfast -crf 26
  -vf "scale='min(1280,iw)':-2" -movflags +faststart -c:a aac preview.mp4`. Aspect ratio is kept;
  never crop or pad.

### 4.3 `GET /api/demo/cameras`

```json
[
  { "id": "cam-01", "name": "CAM 01", "video_url": "/api/media/cameras/cam-01.mp4", "status": "demo" },
  { "id": "cam-12", "name": "CAM 12", "video_url": null, "status": "unavailable" }
]
```

- Always 16 items, ordered `cam-01` … `cam-16`, read from `DEMO_DIR/manifest.json` (§6.1).
- `status`: `"demo"` (prerecorded, available) or `"unavailable"` (file missing or marked so).
  `"playing"` is a client-side state; the backend never sends it.
- If a camera's file is listed but missing on disk, return it as `"unavailable"` with
  `video_url: null` rather than failing the whole list.
- `video_url` points to a **light preview** (≤ 640 px wide, ≤ 1 Mbit/s, H.264, no audio), not
  the original. The dashboard plays up to 16 of them.

### 4.4 `GET /api/demo/events`

The one list behind the dashboard's episodes **and** all its statistics. There is deliberately no
stats endpoint: the frontend derives every count from this list, so the numbers can't drift apart.

```json
[
  {
    "id": "ev-01",
    "camera_id": "cam-03",
    "process_name": "Cash counting",
    "type": "cash_counted_outside_camera_view",
    "type_label": "Cash counted outside camera view",
    "description": "…",
    "timecode_sec": 754.2,
    "clip_start_sec": 744.0,
    "clip_url": "/api/media/clips/ev-01.mp4",
    "episode_timecode_sec": 10.2,
    "evidence_frames": [{ "timestamp_sec": 753.8, "image_base64": "…" }],
    "regulatory_source": null,
    "review_status": "pending"
  }
]
```

- Sorted by `camera_id`, then `timecode_sec`.
- `episode_timecode_sec = timecode_sec − clip_start_sec`, clamped to `[0, clip duration]`. It is
  computed by the backend, which knows the clip duration. `null` if `clip_start_sec` is unknown.
- `clip_url` is `null` if the clip file is missing (the UI shows "clip failed to load").
- `evidence_frames` may be empty (the UI shows "no evidence frame").
- `review_status` is joined from the review table (§4.5). The rest is the stored model output.
- Optional query filters (the spec's "nice to have" filters): `camera_id`, `type`,
  `review_status`. With no filters, return everything.

### 4.5 `PUT /api/events/{event_id}/review`

Marks or unmarks a false positive. It is idempotent, and undo is the same call with `pending`.

Request:

```json
{ "review_status": "false_positive" }
```

| Case | Code | Body |
|---|---|---|
| OK | `200` | The full event, as in §4.4, with the new `review_status` |
| Unknown event | `404` | `{"detail": "Event not found"}` |
| Bad value | `422` | FastAPI validation error |

Stored in its own table, `EventReview(event_id PK, review_status, updated_at)`. The event's
model output is never modified. `pending` deletes the row or sets it; either way, the result
is the same.

### 4.6 `GET /api/media/{path}`

A static mount of `DEMO_DIR/media/` (`cameras/*.mp4`, `clips/*.mp4`). It must support `Range`.
Paths are resolved inside `DEMO_DIR/media` only, and anything that escapes it (`..`) returns 404.
Use `fastapi.staticfiles.StaticFiles`, which already does both.

### 4.7 `GET /api/health`

The existing endpoint stays. Extend the `ml` part with whether the video model is loaded, and
add `ffmpeg: "ok" | "missing"` (the result of checking `FFMPEG_PATH` at startup).

---

## 5. Job processing

```text
POST /analyze ─> store file ─> job(status=processing, stages_done=0) ─> queue
queue worker: validate (ffprobe) ─> ML /route ─> save scenario, stages_done=1
                                ─> ML /specialists ─> save specialist_results, stages_done=3
                                ─> build the jury payload (§3.3) ─> status=done
                                └─> build preview.mp4 (in parallel, doesn't block "done")
any error / timeout ─> status=failed, error="<reason>"
```

1. **Persistence.** The `AnalysisJob` table has these columns:
   - `id`, `status`, `stages_done`, `created_at`, `finished_at`, `error`;
   - `scenario` and `specialist_results` (JSON, §4.1);
   - `result` (JSON, the exact jury `done` payload);
   - `duration_sec`.

   Partial results are saved after each stage, so `/pipeline` shows them during processing.
   Results survive a backend restart.
2. **Queue.** An in-process `asyncio.Queue` with `MAX_CONCURRENT_JOBS` workers (default 1;
   inference is CPU- or GPU-bound). The upload request only enqueues the job.
3. **Timeout.** A job still running after `JOB_TIMEOUT_SEC` (default 270 s, under the
   frontend's 5-minute polling limit) is marked `failed` with
   `"Analysis timed out after N s"`, so the client gets a clear answer instead of its own timeout.
4. **Preview** is transcoded in parallel with inference. A preview failure does not fail the
   job: `preview_url` stays `null`.
5. **Restart.** On startup, jobs still marked `processing` are set to `failed` with
   `"Interrupted by a server restart"`.
6. **Retention.** Jobs older than `JOB_RETENTION_HOURS` (default 24) are deleted, along with
   their files, at startup. There is no history feature, so nothing needs to be kept longer.

---

## 6. Data the backend owns

### 6.1 Demo set: `DEMO_DIR` (default `../data/demo`, gitignored)

```text
data/demo/
├── manifest.json
├── events.json          # model output for the demo recordings, precomputed by running the pipeline
└── media/
    ├── cameras/cam-01.mp4 … cam-16.mp4   # light previews
    └── clips/ev-01.mp4 …                 # short episode clips
```

`manifest.json`:

```json
{ "cameras": [ { "id": "cam-01", "name": "CAM 01", "video": "cameras/cam-01.mp4", "status": "demo" } ] }
```

`events.json` uses the §4.4 event shape without `review_status`, `type_label`,
`regulatory_source` or `episode_timecode_sec`, which the backend adds at read time.
Build it by running the real pipeline over the demo recordings and cutting the clips with ffmpeg,
for example from `clip_start_sec` to `clip_start_sec + 20`. Don't hand-write events.

### 6.2 Rules: `RULES_FILE` (default `../data/rules.json`)

```json
{
  "cash_counted_outside_camera_view": {
    "label": "Cash counted outside camera view",
    "process_name": "Cash counting",
    "regulatory_source": null
  }
}
```

- `regulatory_source` is filled in **only** when a person has confirmed the document and section:
  `{"document_title": "…", "section": "…", "url": "…"}`.
- Unknown types get `label = type` and `regulatory_source = null`.

---

## 7. Backend ↔ ML service (internal)

The ML service (`ml/`, :8001) gains a video endpoint. The backend talks to it through
`ml_client` (503 if the service is unreachable, 502 if it returns an error). These become a
`failed` job with a readable `error`.

The pipeline runs as two calls (internal, no auth, not exposed through the frontend), so the
backend can report real stage progress (§4.1 `stages_done`). The video is shared through a
volume, so gigabytes aren't copied over HTTP.

`POST /route` is the router (stage 1):

```json
// request
{ "video_path": "/data/uploads/3f0c9a1e-…/original.mov" }
// response
{
  "model_version": "0.1.0",
  "duration_sec": 63.0,
  "scenario": { "primary": "CLIENT_CASH_DEPOSIT", "secondary": "COUNTING_FROM_SAFE" }
}
```

`POST /specialists` runs the specialists of the routed scenarios: violations (stage 2) and their
localization (stage 3).

```json
// request
{ "video_path": "/data/uploads/3f0c9a1e-…/original.mov", "scenarios": ["CLIENT_CASH_DEPOSIT", "COUNTING_FROM_SAFE"] }
// response: the §4.1 specialist_results items, plus an internal confidence
{
  "specialist_results": [
    {
      "scenario": "CLIENT_CASH_DEPOSIT",
      "rule_id": "…",
      "status": "violation",
      "quote": "…",
      "evidence": "…",
      "start_sec": 44.2,
      "end_sec": 51.0,
      "confidence": 0.81,
      "evidence_frames": [{ "timestamp_sec": 44.2, "image_base64": "…" }]
    }
  ]
}
```

- Only the specialists of the requested scenarios run. Violations from other scenarios are never
  checked or returned.
- If the pipeline can only run as one call, keep a single `/analyze-video` that returns both
  parts. The backend then sets `stages_done = null` during processing; the UI handles that (§4.1).
- `confidence` stays internal. The backend may turn a `violation` below `MIN_CONFIDENCE` into
  `insufficient_evidence`, but never drops it silently. It isn't sent to the jury unless the task
  asks for it.
- `ml_client` needs a separate, long timeout for this call (`ML_VIDEO_TIMEOUT_SEC`, default 260 s).
  The current 30 s timeout is for tabular `/predict`.
- In docker-compose, both `backend` and `ml` mount the same `uploads` volume at `/data/uploads`.
  In `make dev`, they share a host path.

---

## 8. Frontend integration note (X-API-Key)

`/demo-inference` calls `/api/v1/analyze` and `/api/v1/jobs/{id}` from the browser. The current
`next.config.ts` rewrite forwards requests **without** adding headers, so these calls would get
`401`. Add a Next.js Route Handler at `frontend/src/app/api/v1/[...path]/route.ts`. It:

- forwards the request to `BACKEND_URL` and adds `X-API-Key` from a **server-only** env var
  (`ANALYSIS_API_KEY`, never `NEXT_PUBLIC_*`);
- streams the request body through (`duplex: "half"`) and does not buffer the video.

Route handlers take precedence over `rewrites()`, so everything else under `/api/*` keeps using
the plain rewrite. That includes `/api/jobs/{id}/pipeline`, which the UI polls after the upload
instead of `/api/v1/jobs/{id}`.

---

## 9. Configuration (`backend/.env`, pydantic-settings)

| Var | Default | Purpose |
|---|---|---|
| `API_KEY` | — (required) | Jury key for `/api/v1/*` |
| `UPLOAD_DIR` | `./data/uploads` | Uploaded originals and previews |
| `MAX_UPLOAD_MB` | `2048` | Upload limit, enforced while streaming |
| `MAX_CONCURRENT_JOBS` | `1` | Inference workers |
| `JOB_TIMEOUT_SEC` | `270` | Job is marked failed after this |
| `JOB_RETENTION_HOURS` | `24` | Cleanup at startup |
| `ML_SERVICE_URL` | `http://localhost:8001` | Existing |
| `ML_VIDEO_TIMEOUT_SEC` | `260` | Timeout for the ML pipeline calls (`/route`, `/specialists`) |
| `MIN_CONFIDENCE` | `0.5` | A `violation` below it becomes `insufficient_evidence` |
| `FFMPEG_PATH` / `FFPROBE_PATH` | `ffmpeg` / `ffprobe` | Local binaries; add `ffmpeg` to the backend Dockerfile |
| `DEMO_DIR` | `../data/demo` | Demo set (§6.1) |
| `RULES_FILE` | `../data/rules.json` | Type labels and confirmed norms (§6.2) |
| `DATABASE_URL`, `CORS_ORIGINS` | existing | — |

---

## 10. Scope

### MVP

- `/api/v1/analyze` + `/api/v1/jobs/{id}` with key auth, streaming upload, validation, queue,
  timeout and `failed` reasons.
- ML `/route` + `/specialists` (or a single `/analyze-video`) and the `ml_client` calls.
- `/api/jobs/{id}/pipeline` (§4.1). Without it `/demo-inference` shows no results.
- `/api/jobs/{id}/preview.mp4` with Range support.
- `/api/demo/cameras`, `/api/demo/events`, `PUT /api/events/{id}/review`, `/api/media/*`.
- Frontend Route Handler for `X-API-Key` (§8) and switching `lib/demo-data.ts` to
  `/api/demo/*`.

### If time allows

- Real `stages_done` (two ML calls instead of one).
- Filters on `/api/demo/events`.
- `ffmpeg` and video-model status in `/api/health`.

## 11. Open questions (confirm against the task statement)

1. Exact `verdict` values, and whether `type` is part of each violation.
2. `evidence_frames` format: objects or plain base64 strings, JPEG or PNG, any size limits.
3. Expected status code of `POST /analyze` (200 or 202) and whether `status` can take other
   values (for example `queued`).
4. Is there an upload size limit, or a time limit per video, that the jury will test?
5. Specialist output: what `quote` and `evidence` contain, the full list of `rule_id`s per
   scenario, and whether there is one result per rule or one per scenario.
6. Does the router return the label (`"CLIENT CASH DEPOSIT"`) or an id? Does it return a
   confidence for the second candidate?
