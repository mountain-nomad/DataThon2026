"""Analyze a video by link: read frames straight from the link, run the pipeline, return the
result in the jury API format (task §10).

The video is never saved: OpenCV's FFmpeg reads the link (e.g. a Supabase Storage signed URL)
over HTTP and fetches only the byte ranges around the requested moments, decoding frames in
memory. The pipeline then sends frames, not the video, to the model.

run_inference(video_url) returns:

    {"job_id": ..., "status": "done", "verdict": "violation" | "no_violation",
     "violations": [{"type", "timecode_sec", "description",
                     "evidence_frames": [{"timestamp_sec", "image_base64"}]}]}

or {"job_id": ..., "status": "failed", "error": ...}.

The PIPELINE section is a PLACEHOLDER until the real pipeline (ml/pipeline.py) is ready: it
reads real frames but does not call the model, and returns one marked placeholder violation.
call_model() and frame_parts() are ready for the real pipeline. Settings (see .env.example):

    INFERENCE_ENDPOINT_URL  base URL ending in /v1, e.g. https://api.runpod.ai/v2/<id>/openai/v1
    INFERENCE_API_KEY       sent as "Authorization: Bearer ..." (empty: no header)
    INFERENCE_MODEL         model name the endpoint expects, e.g. qwen/qwen3.8-27b
    INFERENCE_TIMEOUT_SEC   per request, default 240
    INFERENCE_MAX_TOKENS    answer length limit, default 1024
    INFERENCE_FRAMES        frames sampled per video, default 16
"""

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

import cv2

from ml.prompts import PROMPT

MAX_FRAME_SIDE = 640  # keeps requests to the model and the jury response small


def _setting(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(f"{name} is not set (see inference/.env.example)")
    return value


# --- Frames from the link ----------------------------------------------------------------------


class VideoStream:
    """A video read over HTTP without saving it; use as a context manager."""

    def __init__(self, video_url: str) -> None:
        self.cap = cv2.VideoCapture(video_url, cv2.CAP_FFMPEG)
        if not self.cap.isOpened():
            raise RuntimeError("Could not open the video from the link (expired or not a video?)")
        fps = self.cap.get(cv2.CAP_PROP_FPS) or 0.0
        frames = self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
        self.duration = frames / fps if fps > 0 else 0.0

    def __enter__(self) -> "VideoStream":
        return self

    def __exit__(self, *_) -> None:
        self.cap.release()

    def frames_at(self, timestamps: list[float]) -> list[dict]:
        """JPEG frames at the given seconds as [{timestamp_sec, image_base64}]."""
        last = max(self.duration - 0.05, 0.0)  # a seek to the very end returns no frame
        out = []
        for ts in sorted({round(min(max(t, 0.0), last), 2) for t in timestamps}):
            self.cap.set(cv2.CAP_PROP_POS_MSEC, ts * 1000)
            ok, frame = self.cap.read()
            if not ok:
                continue
            h, w = frame.shape[:2]
            if (scale := MAX_FRAME_SIDE / max(h, w)) < 1:
                frame = cv2.resize(frame, (round(w * scale), round(h * scale)), cv2.INTER_AREA)
            ok, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ok:
                out.append(
                    {"timestamp_sec": ts, "image_base64": base64.b64encode(jpeg.tobytes()).decode()}
                )
        return out

    def sample(self, count: int) -> list[dict]:
        """`count` frames evenly spread over the video (the middle of each equal part)."""
        return self.frames_at([self.duration * (i + 0.5) / count for i in range(count)])


# --- Model endpoint ----------------------------------------------------------------------------


def frame_parts(frames: list[dict], prompt: str) -> list[dict]:
    """Message parts: each frame labeled with its second, then the prompt."""
    parts = []
    for f in frames:
        parts.append({"type": "text", "text": f"Кадр t={f['timestamp_sec']:.1f} с:"})
        parts.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{f['image_base64']}"},
            }
        )
    parts.append({"type": "text", "text": prompt})
    return parts


def call_model(content: list[dict]) -> str:
    """One request to the endpoint: message parts (text, images) in, the model's text out."""
    url = _setting("INFERENCE_ENDPOINT_URL").rstrip("/") + "/chat/completions"
    body = {
        "model": _setting("INFERENCE_MODEL"),
        "messages": [{"role": "user", "content": content}],
        "temperature": 0,  # the same video should get the same answer
        "max_tokens": int(_setting("INFERENCE_MAX_TOKENS", "1024")),
        # Qwen otherwise writes its "Thinking Process" into the answer before the actual reply.
        "chat_template_kwargs": {"enable_thinking": False},
    }
    headers = {"Content-Type": "application/json"}
    if api_key := _setting("INFERENCE_API_KEY", ""):
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers=headers, method="POST"
    )
    timeout = float(_setting("INFERENCE_TIMEOUT_SEC", "240"))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.load(response)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        raise RuntimeError(f"Model endpoint error {e.code}: {detail}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"Model endpoint unreachable at {url}: {e.reason}") from None
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(f"Unexpected endpoint response: {str(data)[:500]}") from None


# --- PIPELINE ----------------------------------------------------------------------------------
# PLACEHOLDER until ml/pipeline.py is ready: real frames, no model call (no endpoint cost), one
# marked fake violation at the middle of the video. Replace run_pipeline() with the real
# pipeline: it samples frames from `video`, sends them with the prompt(s) through
# call_model(frame_parts(...)), parses the answers and returns the violations in this shape.


def run_pipeline(video: VideoStream, prompt: str) -> list[dict]:
    t = round(video.duration / 2, 1)
    return [
        {
            "type": "PLACEHOLDER: тип нарушения",
            "timecode_sec": t,
            "description": (
                "[PLACEHOLDER] Модель еще не подключена: это тестовый результат, кадры не "
                "анализировались. Кадры ниже взяты из видео в указанный момент."
            ),
            "evidence_frames": video.frames_at([t - 1, t, t + 1]),
        }
    ]


# -----------------------------------------------------------------------------------------------


def run_inference(video_url: str, prompt: str | None = None, job_id: str | None = None) -> dict:
    """Analyze the video at `video_url` and return the jury-format result.

    `prompt` defaults to ml.prompts.PROMPT. `job_id` defaults to the file name in the link.
    """
    job_id = job_id or Path(urlsplit(video_url).path).stem or "job"
    if not video_url.startswith(("http://", "https://")):
        return {"job_id": job_id, "status": "failed", "error": "video_url must be an http(s) link"}
    prompt = PROMPT if prompt is None else prompt
    try:
        with VideoStream(video_url) as video:
            violations = run_pipeline(video, prompt)
    except RuntimeError as e:
        return {"job_id": job_id, "status": "failed", "error": str(e)}
    violations.sort(key=lambda v: v["timecode_sec"])
    return {
        "job_id": job_id,
        "status": "done",
        "verdict": "violation" if violations else "no_violation",
        "violations": violations,
    }
