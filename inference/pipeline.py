"""Run the ml/ pipeline on one video and map its output to the backend's AnalysisResult.

The pipeline is ml/scripts/run_pipeline.py, run unchanged as a subprocess (the scripts are a
hash-pinned reproduction snapshot, see ml/configs/source_sha256.json):

    router -> video timelines -> object reconciliation -> final text audit

It prints "Run: scripts/<stage>.py" before each stage, which is how progress is reported: once
the timeline stage starts, the router's scenario is known and sent as a partial result.

Each stage loads Qwen3.8-27B itself, so one video takes minutes, not seconds. The stages also
rewrite shared manifests in ml/artifacts/, so only one video runs at a time (`_lock`).
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from collections import deque
from collections.abc import Iterator
from pathlib import Path

ML = Path(__file__).resolve().parents[1] / "ml"
sys.path.insert(0, str(ML / "scripts"))
# Pure Python, loads no model.
from scenario_audit import ROUTES, rule_catalog

JOBS_DIR = ML / "artifacts" / "service"
# Frame caches the stages write per video (by sha256): the router's and the timelines'.
FRAME_CACHES = (ML / "artifacts/video_v2", ML / "artifacts/all_videos_full_frame_usage_rule/frames")
TIMELINE_STAGE = "Run: scripts/context_object_timelines.py"
MODEL = json.loads((ML / "configs/model.json").read_text())

# Router class digit -> the scenario id the backend and frontend use ("EXIT / CLOSING" -> EXIT_CLOSING).
SCENARIOS = {
    c["label"]: "_".join("".join(ch if ch.isalnum() else " " for ch in c["name"]).upper().split())
    for c in json.loads((ML / "configs/classes.json").read_text())
}
# Every catalog rule the final audit can cite, by id ("s2:L58"), with its exact quote.
RULES = rule_catalog((ML / "scenario (2).md").read_text(), range(1, 8))

_lock = threading.Lock()


class PipelineError(RuntimeError):
    pass


def checkpoint_ready() -> bool:
    return (ML / MODEL["path"] / "config.json").exists()


def model_version() -> str:
    return f"{MODEL['repo']}@{MODEL['revision'][:7]} ({MODEL['quantization']})"


def busy() -> bool:
    return _lock.locked()


def job_dir(job_id: str) -> Path:
    return JOBS_DIR / job_id


def _scenario(labels: list[str]) -> dict:
    names = [SCENARIOS[label] for label in labels]
    return {"primary": names[0], "secondary": names[1] if len(names) > 1 else None}


def _router_labels(run: Path) -> list[str]:
    for path in (run / "router").glob("*.json"):
        record = json.loads(path.read_text())
        if "predicted_labels" in record:
            if record.get("status") != "done":
                raise PipelineError(f"Router: {record.get('error') or record.get('status')}")
            return record["predicted_labels"]
    raise PipelineError("Router produced no record")


def to_analysis_result(record: dict) -> dict:
    """A final_text_audit record -> AnalysisResult (scenario + one result per finding)."""
    labels = record["categories"]
    parsed, public = record["parsed"], record["result"]
    results = []
    # `public` is the pipeline's jury JSON: the same findings in the same order, with the
    # description cleaned of timestamps and the timecode moved to the nearest real frame.
    for finding, out in zip(parsed["violations"], public["violations"], strict=True):
        rule = RULES.get(finding["rule_id"], {})
        label = next((lb for lb in labels if rule.get("section") in ROUTES[lb]), labels[0])
        warning = finding["type"].startswith("ПРЕДУПРЕЖДЕНИЕ")
        results.append(
            {
                "scenario": SCENARIOS[label],
                "status": "violation",
                "rule_id": finding["rule_id"],
                # The backend words the jury type and the "why" line from a "Нарушение:" quote.
                # A warning cites an ideal step instead, so it keeps the model's own type.
                "quote": None if warning else rule.get("quote"),
                "type": finding["type"],
                "evidence": out["description"],
                "start_sec": out["timecode_sec"],
                "evidence_timestamps": [out["timecode_sec"]],
            }
        )
    if not results:
        summary = " ".join(parsed.get("evidence_check") or [])
        results = [
            {"scenario": SCENARIOS[label], "status": "no_violation", "evidence": summary}
            for label in labels
        ]
    return {"scenario": _scenario(labels), "specialist_results": results}


def _cleanup(job: Path, sha: str) -> None:
    """Videos and their frames must not be kept (contest rules); KEEP_ARTIFACTS=1 keeps the run."""
    if os.environ.get("KEEP_ARTIFACTS", "").lower() in ("1", "true", "yes"):
        shutil.rmtree(job / "input", ignore_errors=True)
        return
    shutil.rmtree(job, ignore_errors=True)
    for cache in FRAME_CACHES:
        shutil.rmtree(cache / sha, ignore_errors=True)


def run(video: Path, deadline: float) -> Iterator[dict]:
    """Analyze `video` (JOBS_DIR/<job>/input/<file>); yields the backend's NDJSON events:
    {"event": "partial", "result": ...} after the router, then {"event": "result", ...}.

    Raises PipelineError. The subprocess is killed at `deadline` (time.time()), so a client
    that gave up never keeps the GPU busy.
    """
    job = video.parent.parent
    with video.open("rb") as f:
        sha = hashlib.file_digest(f, "sha256").hexdigest()
    try:
        if not _lock.acquire(timeout=max(deadline - time.time(), 0)):
            raise PipelineError("Timed out waiting for the previous video to finish")
        try:
            yield from _run_locked(video, job / "run", deadline)
        finally:
            _lock.release()
    finally:
        _cleanup(job, sha)


def _run_locked(video: Path, run_dir: Path, deadline: float) -> Iterator[dict]:
    if not checkpoint_ready():
        raise PipelineError(f"No checkpoint at ml/{MODEL['path']} (see ml/README.md)")
    cmd = [sys.executable, "-u", "scripts/run_pipeline.py", "--video-dir", str(video.parent),
           "--output-dir", str(run_dir.relative_to(ML))]  # fmt: skip
    proc = subprocess.Popen(
        cmd, cwd=ML, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
    )
    killer = threading.Timer(max(deadline - time.time(), 0), proc.kill)
    killer.start()
    tail: deque[str] = deque(maxlen=30)
    try:
        for line in proc.stdout:
            tail.append(line.rstrip())
            if line.startswith(TIMELINE_STAGE):
                partial = {"scenario": _scenario(_router_labels(run_dir)), "specialist_results": []}
                yield {"event": "partial", "result": partial}
        code = proc.wait()
    finally:
        killer.cancel()
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    if code != 0:
        if time.time() >= deadline:
            raise PipelineError("Pipeline stopped at the deadline")
        raise PipelineError(f"Pipeline failed (exit {code}): " + "\n".join(tail)[-1500:])
    record = json.loads((run_dir / "final/records" / f"{video.stem}.json").read_text())
    if record.get("status") != "done":
        raise PipelineError(f"Final audit: {record.get('error') or record.get('status')}")
    yield {"event": "result", "result": to_analysis_result(record)}
