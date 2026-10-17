"""Analyzer that calls the ML microservice (ml/, contract in ml/README.md). ANALYZER=http.

POST {ML_SERVICE_URL}/analyze with the video and the remaining time budget; the service streams
NDJSON partial results and a final result. Partials are forwarded through ctx.report(), so the
frontend shows real stage progress and a timeout still returns the finished stages.
"""

import json
from pathlib import Path

import httpx

from app.analyzers import AnalysisContext, AnalysisResult, normalize
from app.config import settings

# The worker kills this process at the deadline, so the HTTP read timeout only has to be longer.
READ_TIMEOUT_MARGIN_SEC = 30.0


class HttpAnalyzer:
    def __init__(self) -> None:
        self.url = settings.ml_service_url.rstrip("/")
        self.client = httpx.Client()

    def analyze(self, video_path: str, ctx: AnalysisContext) -> AnalysisResult:
        budget = max(ctx.time_left(), 1.0)
        timeout = httpx.Timeout(budget + READ_TIMEOUT_MARGIN_SEC, connect=10.0)
        path = Path(video_path)
        try:
            with (
                path.open("rb") as f,
                self.client.stream(
                    "POST",
                    f"{self.url}/analyze",
                    files={"file": (path.name, f, "video/quicktime")},
                    data={"deadline_sec": f"{budget:.1f}", "job_id": path.stem},
                    timeout=timeout,
                ) as resp,
            ):
                if resp.is_error:
                    resp.read()
                    raise RuntimeError(f"ML service error {resp.status_code}: {resp.text[:300]}")
                if "ndjson" not in resp.headers.get("content-type", ""):
                    resp.read()
                    return normalize(resp.json())  # a plain JSON AnalysisResult works too
                for line in resp.iter_lines():
                    if not line.strip():
                        continue
                    msg = json.loads(line)
                    if msg.get("event") == "partial":
                        ctx.report(msg["result"])
                    elif msg.get("event") == "result":
                        return normalize(msg["result"])
                    elif msg.get("event") == "error":
                        raise RuntimeError(f"ML service: {msg.get('detail')}")
        except httpx.ConnectError:
            raise RuntimeError(f"ML service unreachable at {self.url}") from None
        except httpx.HTTPError as e:
            raise RuntimeError(f"ML service request failed: {type(e).__name__}: {e}") from None
        raise RuntimeError("ML service closed the stream without a result")
