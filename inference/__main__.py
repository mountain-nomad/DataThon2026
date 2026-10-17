"""Try it from the repo root:

    python -m inference "https://.../video.mov"
"""

import argparse
import json

from inference import run_inference

parser = argparse.ArgumentParser(prog="python -m inference", description=__doc__)
parser.add_argument("video_url", help="http(s) link to the video, e.g. a Supabase signed URL")
parser.add_argument("--prompt", help="defaults to ml/prompts.py PROMPT")
parser.add_argument("--job-id", help="defaults to the file name in the link")
parser.add_argument("--short", action="store_true", help="shorten image_base64 when printing")
args = parser.parse_args()

result = run_inference(args.video_url, args.prompt, args.job_id)
if args.short:
    for v in result.get("violations", []):
        for f in v["evidence_frames"]:
            f["image_base64"] = f["image_base64"][:16] + "..."
print(json.dumps(result, ensure_ascii=False, indent=2))
