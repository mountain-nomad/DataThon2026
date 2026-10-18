"""Supervise a CLI job, preserving its files and killing its process group on timeout."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent

def main():
    video = Path(sys.argv[1]).resolve()
    deadline = float(sys.argv[2])
    parent = os.getppid()
    folder = ROOT / "local/jobs" / video.stem
    folder.mkdir(parents=True, exist_ok=False)
    for name in ("scripts", "configs", "prompts"):
        shutil.copytree(ROOT / "ml" / name, folder / name)
    shutil.copy2(ROOT / "ml/scenario (2).md", folder / "scenario (2).md")
    (folder / "models").mkdir()
    (folder / "models/qwen38_27b").symlink_to(WORKSPACE / "models/qwen38_27b", target_is_directory=True)
    (folder / "inputs").mkdir()
    (folder / "inputs" / video.name).symlink_to(video)
    env = os.environ.copy()
    env.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    command = [str(WORKSPACE / ".venv/bin/python"), "scripts/run_pipeline.py",
               "--video-dir", str(folder / "inputs"), "--output-dir", "artifacts/run"]
    with (folder / "pipeline.log").open("w") as log:
        proc = subprocess.Popen(command, cwd=folder, env=env, stdout=log,
                                stderr=subprocess.STDOUT, start_new_session=True)
        try:
            while proc.poll() is None:
                if time.time() >= deadline or os.getppid() != parent:
                    raise TimeoutError("Local pipeline deadline reached or worker stopped; see " + str(folder))
                time.sleep(0.5)
            if proc.returncode:
                raise RuntimeError("Local pipeline failed; see " + str(folder / "pipeline.log"))
        finally:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
    output = folder / "artifacts/run/final/results" / (video.stem + ".json")
    data = json.loads(output.read_text())
    record = folder / "artifacts/run/final/records" / (video.stem + ".json")
    if record.exists():
        audit = json.loads(record.read_text())
        data["_categories"] = audit.get("categories", [])
        data["_findings"] = audit.get("parsed", {}).get("violations", [])
        data["_limitations"] = audit.get("parsed", {}).get("limitations", [])
    print(json.dumps(data))

if __name__ == "__main__":
    main()
