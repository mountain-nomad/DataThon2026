"""Video probing and evidence-frame extraction (OpenCV, which bundles its own FFmpeg)."""

import base64

import cv2

MAX_FRAME_SIDE = 640  # keeps the JSON response small


def probe_duration(path: str) -> float:
    """Duration in seconds. Raises ValueError if there is no readable video stream."""
    cap = cv2.VideoCapture(path)
    try:
        ok, _ = cap.read()
        if not cap.isOpened() or not ok:
            raise ValueError("The file contains no readable video stream.")
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
        return frames / fps if fps > 0 else 0.0
    finally:
        cap.release()


def extract_frames(path: str, timestamps: list[float]) -> list[dict]:
    """JPEG frames at the given seconds as [{timestamp_sec, image_base64}]; unreadable ones skipped."""
    cap = cv2.VideoCapture(path)
    out = []
    try:
        for ts in timestamps:
            cap.set(cv2.CAP_PROP_POS_MSEC, ts * 1000)
            ok, frame = cap.read()
            if not ok:
                continue
            h, w = frame.shape[:2]
            scale = MAX_FRAME_SIDE / max(h, w)
            if scale < 1:
                frame = cv2.resize(frame, (round(w * scale), round(h * scale)), cv2.INTER_AREA)
            ok, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ok:
                out.append(
                    {
                        "timestamp_sec": round(ts, 2),
                        "image_base64": base64.b64encode(jpeg.tobytes()).decode(),
                    }
                )
    finally:
        cap.release()
    return out
