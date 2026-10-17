"""Background jobs: analyzer in a child process, then evidence frames, legal basis and verdict.

The analyzer runs in a long-lived child process (models load once), one per concurrency slot.
A thread can't be stopped, a process can: on timeout the child is killed and respawned, so a
hung analyzer never blocks the queue and every job ends within JOB_TIMEOUT_SEC.

Processing time varies per video, so the analyzer gets a deadline and reports partial results.
When the deadline passes, the last partial result that has at least one specialist verdict is
returned as `done` (with a limitation noted); only a job with no verdict at all fails.
"""

import asyncio
import logging
import multiprocessing as mp
import time
from collections.abc import Callable
from multiprocessing.connection import Connection

from app import jobs
from app.analyzers import AnalysisContext, load_analyzer, run_analyzer
from app.config import settings
from app.legal import LegalIndex, citation
from app.video import extract_frames, probe_duration

log = logging.getLogger(__name__)

POSTPROCESS_RESERVE_SEC = 15.0  # of the job budget, kept for frame extraction
HARD_KILL_GRACE_SEC = 5.0  # past the analyzer's deadline before its process is killed


def _serve(conn: Connection, spec: str) -> None:
    """Child process: load the analyzer once, then answer one video at a time."""
    try:
        analyzer = load_analyzer(spec)
    except Exception as e:
        load_error = f"Could not load analyzer {spec!r}: {e}"
        logging.basicConfig(level=logging.INFO)
        log.exception(load_error)
    else:
        load_error = None
    while True:
        video_path, deadline = conn.recv()
        if load_error:
            conn.send(("error", load_error))
            continue
        ctx = AnalysisContext(deadline, lambda partial: conn.send(("partial", partial)))
        try:
            conn.send(("ok", run_analyzer(analyzer, video_path, ctx).model_dump()))
        except Exception as e:  # noqa: BLE001  (reported to the job, not raised)
            conn.send(("error", f"Analyzer error: {type(e).__name__}: {e}"))


class AnalysisTimeout(Exception):
    def __init__(self, partial: dict | None) -> None:
        self.partial = partial


class AnalyzerProcess:
    def __init__(self, spec: str) -> None:
        self.spec = spec
        self.proc: mp.Process | None = None
        self.conn: Connection | None = None

    def start(self) -> None:
        if self.proc and self.proc.is_alive():
            return
        parent, child = mp.get_context("spawn").Pipe()
        self.proc = mp.get_context("spawn").Process(
            target=_serve, args=(child, self.spec), daemon=True
        )
        self.proc.start()
        self.conn = parent

    def kill(self) -> None:
        if self.proc:
            self.proc.kill()
            self.proc.join(5)
        self.proc = self.conn = None

    def analyze(self, video_path: str, deadline: float, on_partial: Callable[[dict], None]) -> dict:
        """Blocking; call from a thread. Raises AnalysisTimeout with the last partial result."""
        self.start()
        self.conn.send((video_path, deadline))
        partial = None
        while True:
            left = deadline + HARD_KILL_GRACE_SEC - time.time()
            if left <= 0 or not self.conn.poll(left):
                self.kill()
                raise AnalysisTimeout(partial)
            try:
                kind, payload = self.conn.recv()
            except EOFError:
                self.kill()
                raise RuntimeError("Analyzer process crashed") from None
            if kind == "partial":
                partial = payload
                on_partial(payload)
            elif kind == "error":
                raise RuntimeError(payload)
            else:
                return payload


def _evidence_timestamps(at: float, stamps: list[float] | None, duration: float) -> list[float]:
    n = settings.max_evidence_frames
    stamps = stamps[:n] if stamps else [at + offset for offset in (0.0, -1.0, 1.0)[:n]]
    last = max(duration - 0.05, 0.0)  # a seek to the very end returns no frame
    return sorted({round(min(max(t, 0.0), last), 2) for t in stamps})


def _evidence_frames(video_path: str, at: float, stamps: list[float] | None, duration: float):
    """1–3 frames; falls back to the timecode, the middle and the start so there is always one."""
    frames = extract_frames(video_path, _evidence_timestamps(at, stamps, duration))
    if not frames:
        last = max(duration - 0.05, 0.0)
        frames = extract_frames(video_path, [min(at, last), duration / 2, 0.0])[:1]
    return frames


def _clamp(t: float | None, duration: float) -> float | None:
    if t is None:
        return None
    return round(min(max(t, 0.0), duration) if duration else max(t, 0.0), 2)


def _rule_text(r: dict) -> str:
    """The catalog quote without its "Нарушение:" prefix: "кассир оставляет ..."."""
    return (r.get("quote") or "").strip().removeprefix("Нарушение:").strip()


def _type_name(basis: dict | None, r: dict) -> str:
    """Human-readable violation type for the API ("Название типа нарушения").

    The regulation's own wording comes first: it is what the organizers' violation types are
    written in. The legal mapping's type name is the fallback.
    """
    if text := _rule_text(r).rstrip("."):
        return text[:1].upper() + text[1:]
    if basis and basis.get("name"):
        return basis["name"]
    return r.get("type") or r.get("rule_id") or "Нарушение"


def _description(r: dict, basis: dict | None) -> str:
    """What is visible, why it may be a violation, and the public source."""
    lines = [r.get("evidence") or "Признаки нарушения на видео."]
    if text := _rule_text(r):
        lines.append(f"Почему это может быть нарушением: по регламенту — {text}")
    if basis and (cite := citation(basis)):
        lines.append(cite)
    return "\n".join(lines)


PIPELINE_FIELDS = ("scenario", "rule_id", "status", "quote", "evidence", "start_sec", "end_sec")


def pipeline_item(r: dict, frames: list | None = None, basis: dict | None = None) -> dict:
    return {k: r.get(k) for k in PIPELINE_FIELDS} | {
        "evidence_frames": frames or [],
        "legal_basis": basis,
    }


def build_result(video_path: str, analysis: dict, legal: LegalIndex) -> dict:
    """Analyzer output -> the stored job fields: the pipeline view and the API violations."""
    duration = probe_duration(video_path)
    results, violations = [], []
    for r in analysis["specialist_results"]:
        r["start_sec"] = _clamp(r["start_sec"], duration)
        r["end_sec"] = _clamp(r["end_sec"], duration)
        conf = r.get("confidence")
        if r["status"] == "violation" and conf is not None and conf < settings.min_confidence:
            # Kept visible in the pipeline view, but not reported as a violation.
            r["status"] = "insufficient_evidence"
        frames, basis = [], legal.resolve(r.get("rule_id"), r.get("type"))
        if r["status"] == "violation":
            stamps = r.get("evidence_timestamps")
            at = r["start_sec"] if r["start_sec"] is not None else (stamps or [0.0])[0]
            at = _clamp(at, duration) or 0.0
            frames = _evidence_frames(video_path, at, stamps, duration)
            violations.append(
                {
                    "type": _type_name(basis, r),
                    "timecode_sec": at,
                    "description": _description(r, basis),
                    "evidence_frames": frames,
                    # internal, for the web UIs only
                    "rule_id": r.get("rule_id"),
                    "legal_basis": basis,
                    "confidence": conf,
                }
            )
        results.append(pipeline_item(r, frames, basis))
    violations.sort(key=lambda v: v["timecode_sec"])
    return {
        "verdict": "violation" if violations else "no_violation",
        "violations": violations,
        "scenario": analysis["scenario"],
        "specialist_results": results,
        "duration_sec": duration,
    }


def _stages(partial: dict) -> int:
    return 2 if partial.get("specialist_results") else 1 if partial.get("scenario") else 0


class Worker:
    def __init__(self, legal: LegalIndex) -> None:
        self.legal = legal
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.slots = [
            AnalyzerProcess(settings.analyzer) for _ in range(settings.max_concurrent_jobs)
        ]
        self.tasks: list[asyncio.Task] = []

    def start(self) -> None:
        for slot in self.slots:
            slot.start()  # start loading models now, not on the first upload
            self.tasks.append(asyncio.create_task(self._loop(slot)))

    def stop(self) -> None:
        for task in self.tasks:
            task.cancel()
        for slot in self.slots:
            slot.kill()

    def submit(self, job_id: str) -> None:
        self.queue.put_nowait(job_id)

    async def _loop(self, slot: AnalyzerProcess) -> None:
        while True:
            job_id = await self.queue.get()
            try:
                await self._run(job_id, slot)
            except Exception as e:  # never let one job kill the worker
                log.exception("Job %s failed", job_id)
                jobs.fail(job_id, f"Internal error: {e}")

    async def _run(self, job_id: str, slot: AnalyzerProcess) -> None:
        job = jobs.get(job_id)
        if job is None or job["status"] != "processing":
            return
        # The analyzer's deadline leaves time for the hard kill and for frame extraction.
        analyzer_deadline = job["deadline"] - POSTPROCESS_RESERVE_SEC - HARD_KILL_GRACE_SEC
        if analyzer_deadline - time.time() <= 1:
            jobs.fail(job_id, "Timed out while waiting in the queue")
            return

        def on_partial(partial: dict) -> None:  # shown by /pipeline while the job runs
            jobs.update(
                job_id,
                stages_done=_stages(partial),
                scenario=partial.get("scenario"),
                specialist_results=[pipeline_item(r) for r in partial["specialist_results"]],
            )

        limitations = []
        try:
            analysis = await asyncio.to_thread(
                slot.analyze, job["video_path"], analyzer_deadline, on_partial
            )
        except AnalysisTimeout as e:
            if not (e.partial and e.partial.get("specialist_results")):
                jobs.fail(job_id, f"Analysis timed out after {settings.job_timeout_sec:.0f} s")
                return
            analysis = e.partial
            limitations.append(
                "Анализ остановлен по времени: возвращены результаты завершенных этапов."
            )
        except RuntimeError as e:
            jobs.fail(job_id, str(e))
            return
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(build_result, job["video_path"], analysis, self.legal),
                timeout=max(job["deadline"] - time.time(), 1.0),
            )
        except TimeoutError:
            jobs.fail(job_id, "Timed out while extracting evidence frames")
            return
        jobs.finish(job_id, status="done", stages_done=3, limitations=limitations, **result)
