"""Run the recorded ML pipeline locally in an isolated directory per upload."""
import json
from pathlib import Path
import subprocess
import sys
from app.analyzers import AnalysisResult, AnalysisContext, normalize

ROOT = Path(__file__).resolve().parents[3]
CODES = {"1": "ENTRY", "2": "COUNTING_DEPOSIT_WITHOUT_CLIENT", "3": "CLIENT_CASH_DEPOSIT",
         "4": "COUNTING_FROM_SAFE", "5": "OPENING_A_CASH_BAG",
         "6": "RECEIVING_A_BAG_FROM_CLIENT", "7": "EXIT_CLOSING"}

def scenario_from_labels(labels):
    from app.analyzers import Scenario
    if not labels or any(label not in CODES for label in labels):
        return None
    return Scenario(primary=CODES[labels[0]],
                    secondary=CODES[labels[1]] if len(labels) > 1 else None)

def read_completed_scenario(folder):
    for path in (folder / "artifacts/run/router").glob("*.json"):
        try:
            record = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue  # the router may still be writing this file
        if isinstance(record, dict) and record.get("status") == "done":
            scenario = scenario_from_labels(record.get("predicted_labels"))
            if scenario:
                return scenario
    return None

class LocalAnalyzer:
    def analyze(self, video_path: str, ctx: AnalysisContext) -> AnalysisResult:
        video = Path(video_path).resolve()
        command = [sys.executable, str(ROOT / "deploy/run_job.py"), str(video), str(ctx.deadline)]
        # The supervisor outlives a worker timeout long enough to stop all GPU subprocesses.
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        reported = False
        while True:
            try:
                stdout, stderr = proc.communicate(timeout=0.5)
                break
            except subprocess.TimeoutExpired:
                if not reported:
                    scenario = read_completed_scenario(ROOT / "local/jobs" / video.stem)
                    if scenario:
                        ctx.report(AnalysisResult(scenario=scenario))
                        reported = True
        if proc.returncode:
            raise RuntimeError(stderr[-2000:] or stdout[-2000:] or "Local pipeline failed")
        data = json.loads(stdout)
        if data.get("status") != "done":
            raise RuntimeError(data.get("error", "Local pipeline failed"))
        return result_to_analysis(data)


def result_to_analysis(data):
    from app.analyzers import SpecialistResult
    from app.finding_catalog import require_type
    findings = data.get("_findings", [])
    violations = data["violations"]
    if len(findings) != len(violations):
        raise ValueError("Missing internal finding metadata")
    limitations = data.get("_limitations", [])
    if not isinstance(limitations, list) or any(not isinstance(x, str) for x in limitations):
        raise ValueError("Invalid model limitations")
    results = []
    for public, internal in zip(violations, findings):
        rule_id = internal["rule_id"]
        if public["type"] != internal["type"]:
            raise ValueError("Public and internal finding types disagree")
        entry = require_type(rule_id, public["type"])
        if not isinstance(public.get("description"), str) or not public["description"].strip():
            raise ValueError("Missing finding description")
        results.append(SpecialistResult(
            status="violation", rule_id=rule_id, quote=entry["quote"],
            evidence=public["description"], type=public["type"],
            start_sec=public["timecode_sec"], evidence_timestamps=[public["timecode_sec"]],
            limitations=limitations,
        ))
    if not results:
        results = [SpecialistResult(status="no_violation", limitations=limitations)]
    return AnalysisResult(scenario=scenario_from_labels(data.get("_categories")), specialist_results=results)
