"""Start the ML service from the repo root, on the GPU machine:

    ml/.venv/bin/python -m inference                     # 127.0.0.1:8001 (reach it via SSH)
    ml/.venv/bin/python -m inference --host 0.0.0.0      # behind HTTPS; set INFERENCE_API_KEY

Reads inference/.env if present (variables already set in the shell win).
"""

import argparse
import os
from pathlib import Path

import uvicorn

env_file = Path(__file__).with_name(".env")
if env_file.exists():
    for line in env_file.read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep and not key.strip().startswith("#"):
            os.environ.setdefault(key.strip(), value.strip())

parser = argparse.ArgumentParser(
    prog="python -m inference",
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
parser.add_argument("--host", default="127.0.0.1")
parser.add_argument("--port", type=int, default=8001)
args = parser.parse_args()

if args.host not in ("127.0.0.1", "localhost") and not os.environ.get("INFERENCE_API_KEY"):
    raise SystemExit("Set INFERENCE_API_KEY before listening on a public address")

# One worker: the pipeline runs one video at a time on the GPU.
uvicorn.run("inference.server:app", host=args.host, port=args.port, workers=1)
