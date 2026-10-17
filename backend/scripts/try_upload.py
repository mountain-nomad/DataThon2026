"""Upload a video to a running backend and check that it landed in Supabase Storage.

Run from backend/:
    uv run python scripts/try_upload.py "data/uploads/Х-37.mov"
    uv run python scripts/try_upload.py video.mov --url http://localhost:8010
"""

import argparse
import os
import sys
import time
from pathlib import Path

import httpx

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def api_key() -> str:
    if key := os.environ.get("API_KEY"):
        return key
    for line in ENV_FILE.read_text().splitlines():
        if line.startswith("API_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    sys.exit(f"API_KEY not found in the environment or {ENV_FILE}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("--url", default="http://localhost:8000", help="backend address")
    args = parser.parse_args()
    if not args.file.is_file():
        sys.exit(f"No such file: {args.file}")

    with httpx.Client(base_url=args.url, timeout=300) as client:
        print(f"1. POST /api/v1/analyze  {args.file.name} ({args.file.stat().st_size:,} bytes)")
        started = time.monotonic()
        with args.file.open("rb") as f:
            r = client.post(
                "/api/v1/analyze",
                headers={"X-API-Key": api_key()},
                files={"file": (args.file.name, f, "video/quicktime")},
            )
        print(f"   {r.status_code} in {time.monotonic() - started:.1f} s: {r.text}")
        r.raise_for_status()
        job_id = r.json()["job_id"]

        print("2. GET /api/jobs/{id}/video-url")
        r = client.get(f"/api/jobs/{job_id}/video-url")
        print(f"   {r.status_code}")
        r.raise_for_status()
        info = r.json()
        print(f"   storage_path: {info['storage_path']}")
        print(f"   expires_in:   {info['expires_in']} s")
        print(f"   url:          {info['url']}")

    print("3. Fetch the signed URL")
    with httpx.Client(timeout=60) as storage:
        r = storage.head(info["url"])
        size = int(r.headers.get("content-length", -1))
        same = "matches" if size == args.file.stat().st_size else "DOES NOT match"
        print(f"   HEAD {r.status_code}, {r.headers.get('content-type')}, {size:,} bytes ({same})")
        r = storage.get(info["url"], headers={"Range": "bytes=0-1023"})
        print(f"   Range request: {r.status_code} (206 = seeking works in the player)")
        unsigned = info["url"].split("?")[0].replace("/object/sign/", "/object/public/")
        r = storage.get(unsigned)
        print(f"   Without a token: {r.status_code} (should be 400/404: the bucket is private)")

    print(f"4. Job {job_id}: poll GET /api/v1/jobs/{{id}} for the analysis result")


if __name__ == "__main__":
    main()
