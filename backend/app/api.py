import logging
import secrets
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app import jobs
from app.config import settings
from app.storage import StorageError, get_storage, object_key
from app.video import probe_duration

CHUNK = 1 << 20

log = logging.getLogger(__name__)


def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    if not x_api_key or not secrets.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(401, "Invalid or missing API key")


async def _start_job(request: Request, file: UploadFile) -> dict:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in settings.allowed_extensions:
        allowed = ", ".join(settings.allowed_extensions)
        raise HTTPException(415, f"Unsupported file type. Allowed: {allowed}")
    job_id = jobs.new_job_id()
    path = settings.uploads_dir / f"{job_id}{ext}"
    limit = settings.max_upload_mb * CHUNK
    size = 0
    try:
        with path.open("wb") as out:
            while chunk := await file.read(CHUNK):
                size += len(chunk)
                if size > limit:
                    raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB.")
                out.write(chunk)
        if size == 0:
            raise HTTPException(400, "The file is empty.")
        try:
            await run_in_threadpool(probe_duration, str(path))
        except ValueError as e:
            raise HTTPException(422, str(e)) from e
        storage = get_storage()
        key = object_key(job_id, ext)
        try:
            storage_path = await run_in_threadpool(storage.save, path, key)
        except StorageError as e:
            log.error("Storing upload %s failed: %s", job_id, e)
            raise HTTPException(502, "Video storage failed, try again.") from e
        try:
            jobs.create(job_id, path, file.filename or "", storage_path)
        except BaseException:
            if storage_path:
                with suppress(StorageError):
                    await run_in_threadpool(storage.delete, storage_path)
            raise
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    request.app.state.worker.submit(job_id)
    return {"job_id": job_id}


def _get_job(job_id: str) -> dict:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return jobs.expire_if_overdue(job)


# --- Public API (the exact contract) ---------------------------------------------------------

api = APIRouter(prefix="/api/v1", dependencies=[Depends(require_api_key)], tags=["api"])


@api.post("/analyze")
async def analyze(request: Request, file: UploadFile) -> dict:
    return await _start_job(request, file)


@api.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    return jobs.public_view(_get_job(job_id))


# --- Web UI (same-origin page, no key; job ids are unguessable) ------------------------------

ui = APIRouter(prefix="/ui", tags=["ui"], include_in_schema=False)

# The public fields plus the legal basis, which the page shows on its own.
UI_FIELDS = ("type", "timecode_sec", "description", "evidence_frames", "rule_id", "legal_basis")


@ui.post("/analyze")
async def ui_analyze(request: Request, file: UploadFile) -> dict:
    return await _start_job(request, file)


@ui.get("/jobs/{job_id}")
def ui_get_job(job_id: str) -> dict:
    job = _get_job(job_id)
    out = jobs.public_view(job)
    if job["status"] == "done":
        out["violations"] = [{k: v.get(k) for k in UI_FIELDS} for v in job["violations"]]
    out["filename"] = job.get("filename")
    return out


def _signed_url(job: dict) -> str:
    """A fresh signed URL for the stored object; the stable reference is `storage_path`."""
    try:
        url = get_storage().signed_url(job["storage_path"]) if job.get("storage_path") else None
    except StorageError as e:
        log.warning("No signed URL for job %s: %s", job["job_id"], e)
        url = None
    if url is None:
        raise HTTPException(404, "Video not found")
    return url


def _video(job_id: str) -> Response:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "Video not found")
    if Path(job["video_path"]).exists():
        # FileResponse supports Range requests, which the player needs for seeking. H.264 .mov
        # plays in browsers when served as video/mp4.
        return FileResponse(job["video_path"], media_type="video/mp4")
    # The local copy is gone (retention): send the player to the stored object.
    return RedirectResponse(_signed_url(job), status_code=307)


@ui.get("/jobs/{job_id}/video")
def ui_video(job_id: str) -> Response:
    return _video(job_id)


# --- Next.js frontend (frontend/): /demo-inference and /demo-dashboard, no key ---------------

frontend = APIRouter(prefix="/api/jobs", tags=["frontend"], include_in_schema=False)


def _pipeline_view(job: dict) -> dict:
    reviews = job.get("reviews") or {}
    results = [
        r
        | {"review_status": reviews.get(str(i), "pending") if r["status"] == "violation" else None}
        for i, r in enumerate(job.get("specialist_results") or [])
    ]
    has_video = Path(job["video_path"]).exists() or bool(job.get("storage_path"))
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "error": job.get("error"),
        # 1 = scenario, 2 = specialist verdicts, 3 = done; reported by the analyzer as it goes.
        "stages_done": job.get("stages_done", 0),
        "file_name": job.get("filename"),
        "created_at": datetime.fromtimestamp(job["created_at"], UTC).isoformat(),
        "duration_sec": job.get("duration_sec"),
        "preview_url": f"/api/jobs/{job['job_id']}/video" if has_video else None,
        "storage_path": job.get("storage_path"),
        "scenario": job.get("scenario"),
        "specialist_results": results,
        "limitations": job.get("limitations") or [],
    }


@frontend.get("")
def list_jobs(status: Literal["processing", "done", "failed"] | None = None) -> dict:
    """Analysis history, newest first (the source of /demo-dashboard)."""
    return {"items": [_pipeline_view(j) for j in jobs.list_jobs(status)]}


@frontend.get("/{job_id}/pipeline")
def get_pipeline(job_id: str) -> dict:
    return _pipeline_view(_get_job(job_id))


@frontend.get("/{job_id}/video")
def get_video(job_id: str) -> Response:
    return _video(job_id)


@frontend.get("/{job_id}/video-url")
def get_video_url(job_id: str) -> dict:
    """The stored object and a short-lived signed URL to fetch it (404 with local storage)."""
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return {
        "job_id": job_id,
        "storage_path": job.get("storage_path"),
        "url": _signed_url(job),
        "expires_in": settings.signed_url_ttl_sec,
    }


class Review(BaseModel):
    review_status: Literal["pending", "false_positive"]


@frontend.put("/{job_id}/results/{index}/review")
def review(job_id: str, index: int, body: Review) -> dict:
    """Mark or unmark a violation as a false positive. The model output is never changed."""
    job = jobs.get(job_id)
    results = (job or {}).get("specialist_results") or []
    if job is None or job["status"] != "done":
        raise HTTPException(404, "Job not found")
    if not 0 <= index < len(results) or results[index]["status"] != "violation":
        raise HTTPException(404, "Violation not found")
    job = jobs.set_review(job_id, index, body.review_status)
    return _pipeline_view(job)["specialist_results"][index]
