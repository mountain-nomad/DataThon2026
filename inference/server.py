"""The ML microservice: the backend's ANALYZER=http contract (README "Plugging in the ML
microservice"), backed by the ml/ pipeline. Runs on the GPU machine.

    GET  /health   {"status": "ok", "model_loaded": ..., "model_version": ..., "busy": ...}
    POST /analyze  multipart: `video_url` (a link, e.g. a Supabase signed URL) or `file`,
                   plus `deadline_sec` and `job_id`; answers an NDJSON stream of
                   partial / result / error events.

Reach it over HTTPS (a tunnel or the GPU host's proxy) with INFERENCE_API_KEY set, or over an
SSH tunnel to 127.0.0.1. Settings are environment variables, see inference/.env.example.
"""

import json
import os
import re
import secrets
import shutil
import time
import uuid
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Annotated
from urllib.parse import urlsplit

import httpx
from fastapi import Depends, FastAPI, Form, Header, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from inference import pipeline

CHUNK = 1 << 20
VIDEO_EXTENSIONS = (".mov", ".mp4", ".mkv", ".avi")  # what ml/scripts/bootstrap_repro.py reads


def _env(name: str, default: str) -> str:
    return os.environ.get(name) or default


API_KEY = _env("INFERENCE_API_KEY", "")
MAX_VIDEO_MB = int(_env("INFERENCE_MAX_VIDEO_MB", "500"))
DEFAULT_DEADLINE_SEC = float(_env("INFERENCE_DEFAULT_DEADLINE_SEC", "1800"))
DOWNLOAD_TIMEOUT_SEC = float(_env("INFERENCE_DOWNLOAD_TIMEOUT_SEC", "120"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inputs left by a crash or by a client that disconnected before its stream started.
    for inbox in pipeline.JOBS_DIR.glob("*/input"):
        _discard(inbox)
    yield


app = FastAPI(title="Cash desk video analysis: ML service", version="0.1.0", lifespan=lifespan)


def require_api_key(authorization: Annotated[str | None, Header()] = None) -> None:
    if API_KEY and not secrets.compare_digest(authorization or "", f"Bearer {API_KEY}"):
        raise HTTPException(401, "Invalid or missing API key")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        # The checkpoint is on disk; each pipeline stage loads it itself.
        "model_loaded": pipeline.checkpoint_ready(),
        "model_version": pipeline.model_version(),
        "busy": pipeline.busy(),
    }


def _extension(name: str) -> str:
    ext = Path(name).suffix.lower()
    return ext if ext in VIDEO_EXTENSIONS else ".mov"


def _download(url: str, dest: Path) -> None:
    limit = MAX_VIDEO_MB * CHUNK
    size = 0
    try:
        with (
            httpx.stream("GET", url, timeout=DOWNLOAD_TIMEOUT_SEC, follow_redirects=True) as resp,
            dest.open("wb") as out,
        ):
            if resp.is_error:
                raise pipeline.PipelineError(f"Video link answered {resp.status_code}")
            for chunk in resp.iter_bytes(CHUNK):
                size += len(chunk)
                if size > limit:
                    raise pipeline.PipelineError(f"Video exceeds {MAX_VIDEO_MB} MB")
                out.write(chunk)
    except httpx.HTTPError as e:
        raise pipeline.PipelineError(f"Video download failed: {type(e).__name__}: {e}") from None
    if size == 0:
        raise pipeline.PipelineError("The video link returned an empty file")


def _discard(inbox: Path) -> None:
    """Delete the input video, and the job folder unless the pipeline kept its run there."""
    shutil.rmtree(inbox, ignore_errors=True)
    with suppress(OSError):
        inbox.parent.rmdir()  # only if empty


def _events(video: Path, video_url: str | None, deadline: float):
    try:
        if video_url:
            _download(video_url, video)
        yield from pipeline.run(video, deadline)
    except pipeline.PipelineError as e:
        yield {"event": "error", "detail": str(e)}
    finally:
        _discard(video.parent)


@app.post("/analyze", dependencies=[Depends(require_api_key)])
async def analyze(
    file: UploadFile | None = None,
    video_url: Annotated[str | None, Form()] = None,
    deadline_sec: Annotated[float | None, Form()] = None,
    job_id: Annotated[str | None, Form()] = None,
) -> StreamingResponse:
    if bool(file) == bool(video_url):
        raise HTTPException(422, "Send exactly one of `file` or `video_url`")
    if video_url and not video_url.startswith(("http://", "https://")):
        raise HTTPException(422, "video_url must be an http(s) link")
    deadline = time.time() + (deadline_sec or DEFAULT_DEADLINE_SEC)
    # The file stem becomes the pipeline's video id: keep it plain ASCII and unique.
    job_id = job_id if job_id and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", job_id) else None
    job_id = f"{job_id or 'job'}-{uuid.uuid4().hex[:8]}"
    name = file.filename if file else urlsplit(video_url).path
    inbox = pipeline.job_dir(job_id) / "input"
    inbox.mkdir(parents=True)
    video = inbox / f"{job_id}{_extension(name or '')}"
    if file:
        # Saved before responding: the upload is closed once the handler returns.
        size = 0
        with video.open("wb") as out:
            while chunk := await file.read(CHUNK):
                size += len(chunk)
                if size > MAX_VIDEO_MB * CHUNK:
                    out.close()
                    _discard(inbox)
                    raise HTTPException(413, f"Video exceeds {MAX_VIDEO_MB} MB")
                out.write(chunk)

    def stream():
        for event in _events(video, video_url, deadline):
            yield json.dumps(event, ensure_ascii=False) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")
