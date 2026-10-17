"""Job state as one JSON file per job: DATA_DIR/jobs/{job_id}.json."""

import json
import os
import threading
import time
import uuid
from pathlib import Path

from app.config import settings
from app.storage import StorageError, get_storage

_lock = threading.Lock()  # the worker thread and request handlers both write


def new_job_id() -> str:
    return uuid.uuid4().hex  # unguessable: the /ui endpoints have no API key


def _path(job_id: str) -> Path:
    return settings.jobs_dir / f"{job_id}.json"


def get(job_id: str) -> dict | None:
    if not job_id.isalnum():
        return None
    try:
        return json.loads(_path(job_id).read_text())
    except FileNotFoundError:
        return None


def _write(job: dict) -> None:
    tmp = _path(job["job_id"]).with_suffix(".tmp")
    tmp.write_text(json.dumps(job, ensure_ascii=False))
    os.replace(tmp, _path(job["job_id"]))  # atomic: readers never see a half-written file


def save(job: dict) -> None:
    with _lock:
        _write(job)


def create(job_id: str, video_path: Path, filename: str, storage_path: str | None = None) -> dict:
    job = {
        "job_id": job_id,
        "status": "processing",
        "created_at": time.time(),
        "deadline": time.time() + settings.job_timeout_sec,
        "filename": filename,
        "video_path": str(video_path),  # local working copy, what the analyzer reads
        "storage_path": storage_path,  # object key in the Supabase bucket, None for local storage
    }
    save(job)
    return job


def finish(job_id: str, **fields) -> None:
    """Set the final state, unless the job already ended (e.g. a timeout marked it failed)."""
    with _lock:
        job = get(job_id)
        if job is None or job["status"] != "processing":
            return
        job.update(fields, finished_at=time.time())
        _write(job)


def update(job_id: str, **fields) -> None:
    """Save progress (partial results) of a job that is still running."""
    with _lock:
        job = get(job_id)
        if job is None or job["status"] != "processing":
            return
        job.update(fields)
        _write(job)


def fail(job_id: str, error: str) -> None:
    finish(job_id, status="failed", error=error)


def set_review(job_id: str, index: int, review_status: str) -> dict | None:
    """Human review of one specialist result. Stored apart from the model output."""
    with _lock:
        job = get(job_id)
        if job is None:
            return None
        reviews = job.setdefault("reviews", {})
        if review_status == "pending":
            reviews.pop(str(index), None)
        else:
            reviews[str(index)] = review_status
        _write(job)
        return job


def list_jobs(status: str | None = None) -> list[dict]:
    """All jobs, newest first."""
    out = []
    for path in settings.jobs_dir.glob("*.json"):
        try:
            job = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue  # being replaced right now, or not a job file
        if status is None or job["status"] == status:
            out.append(job)
    return sorted(out, key=lambda j: j["created_at"], reverse=True)


def delete_old_uploads() -> None:
    """Remove uploaded videos (local and stored copies, not results) older than
    UPLOAD_RETENTION_HOURS."""
    if settings.upload_retention_hours <= 0:
        return
    cutoff = time.time() - settings.upload_retention_hours * 3600
    for job in list_jobs():
        if job["status"] != "processing" and job["created_at"] < cutoff:
            Path(job["video_path"]).unlink(missing_ok=True)
            if job.get("storage_path"):
                try:
                    get_storage().delete(job["storage_path"])
                except StorageError:
                    continue  # retried next hour
                with _lock:
                    if current := get(job["job_id"]):
                        current["storage_path"] = None
                        _write(current)


def expire_if_overdue(job: dict) -> dict:
    """Readers enforce the deadline too, so a stuck worker can't keep a job in 'processing'."""
    if job["status"] == "processing" and time.time() > job["deadline"]:
        fail(job["job_id"], f"Analysis timed out after {settings.job_timeout_sec:.0f} s")
        job = get(job["job_id"]) or job
    return job


def fail_interrupted() -> None:
    """At startup: jobs left 'processing' by a previous run will never finish."""
    for path in settings.jobs_dir.glob("*.json"):
        job = json.loads(path.read_text())
        if job["status"] == "processing":
            fail(job["job_id"], "Interrupted by a server restart")


def public_view(job: dict) -> dict:
    """The exact API contract: no internal fields."""
    out = {"job_id": job["job_id"], "status": job["status"]}
    if job["status"] == "failed":
        out["error"] = job.get("error") or "Analysis failed"
    elif job["status"] == "done":
        out["verdict"] = job["verdict"]
        out["violations"] = [
            {k: v[k] for k in ("type", "timecode_sec", "description", "evidence_frames")}
            for v in job["violations"]
        ]
    return out
