"""The analysis interface. The real analyzer is developed separately and plugged in via ANALYZER.

    class MyAnalyzer:
        def analyze(self, video_path: str, ctx: AnalysisContext) -> AnalysisResult: ...

    ANALYZER=my_package.my_module:MyAnalyzer

`ctx` is optional (a one-argument analyze() works too). It carries the deadline: processing time
varies per video, so the analyzer should check ctx.time_left() and do less when it runs short
(fewer frames, skip the secondary scenario). ctx.report(partial) sends what is finished so far:
it drives the frontend's stage progress, and if the deadline passes, the last partial result is
returned instead of a failure.

Two output forms are accepted (pydantic models or plain dicts with the same keys):
- AnalysisResult: the router scenario plus one result per specialist, including no_violation /
  insufficient_evidence outcomes. This is what the frontend's pipeline view shows.
- list[Detection]: violations only, no scenario. The pipeline view then shows just the violations.

The class is instantiated once per worker process (load models in __init__) and must take no
constructor arguments.
"""

import importlib
import inspect
import time
from collections.abc import Callable
from typing import Protocol

from pydantic import BaseModel, TypeAdapter


class Detection(BaseModel):
    type: str
    timecode_sec: float
    description: str
    confidence: float | None = None
    # Where to take evidence frames from; defaults to around timecode_sec.
    evidence_timestamps: list[float] | None = None
    rule_id: str | None = None  # key in rules.yaml


class Scenario(BaseModel):
    # One of the 7 router classes, e.g. "CLIENT_CASH_DEPOSIT" (labels are normalized by the UI).
    primary: str
    secondary: str | None = None


class SpecialistResult(BaseModel):
    limitations: list[str] = []  # actual model limitations, preserved separately from facts
    scenario: str | None = None  # the scenario whose specialist produced it
    status: str  # "violation" | "no_violation" | "insufficient_evidence"
    rule_id: str | None = None
    quote: str | None = None  # the rule text the specialist cites
    evidence: str | None = None  # what is visible; becomes the violation description
    start_sec: float | None = None
    end_sec: float | None = None
    type: str | None = None  # violation class for the API; defaults to rule_id
    confidence: float | None = None
    evidence_timestamps: list[float] | None = None


class AnalysisResult(BaseModel):
    scenario: Scenario | None = None
    specialist_results: list[SpecialistResult] = []


class AnalysisContext:
    def __init__(self, deadline: float, report: Callable[[dict], None]) -> None:
        self.deadline = deadline  # time.time() by which analyze() should return
        self._report = report

    def time_left(self) -> float:
        return self.deadline - time.time()

    def report(self, partial: "AnalysisResult | dict") -> None:
        """Send the result so far (scenario and the specialist results finished so far)."""
        self._report(normalize(partial).model_dump())


class Analyzer(Protocol):
    def analyze(
        self, video_path: str, ctx: AnalysisContext
    ) -> AnalysisResult | list[Detection]: ...


def run_analyzer(analyzer, video_path: str, ctx: AnalysisContext) -> AnalysisResult:
    """Call analyze() with or without ctx, depending on its signature."""
    if len(inspect.signature(analyzer.analyze).parameters) >= 2:
        return normalize(analyzer.analyze(video_path, ctx))
    return normalize(analyzer.analyze(video_path))


_detections = TypeAdapter(list[Detection])


def normalize(output) -> AnalysisResult:
    """Either output form -> AnalysisResult. Raises pydantic.ValidationError on bad output."""
    if isinstance(output, (AnalysisResult, dict)):
        return AnalysisResult.model_validate(output)
    results = [
        SpecialistResult(
            status="violation",
            rule_id=d.rule_id,
            evidence=d.description,
            start_sec=d.timecode_sec,
            type=d.type,
            confidence=d.confidence,
            evidence_timestamps=d.evidence_timestamps,
        )
        for d in _detections.validate_python(output)
    ]
    return AnalysisResult(specialist_results=results)


def load_analyzer(spec: str) -> Analyzer:
    spec = {
        "mock": "app.analyzers.mock:MockAnalyzer",
        "http": "app.analyzers.http:HttpAnalyzer",
    }.get(spec, spec)
    module_name, sep, class_name = spec.partition(":")
    if not sep or not class_name:
        raise ValueError(
            f"ANALYZER must be 'mock', 'http' or 'module.path:ClassName', got {spec!r}"
        )
    cls = getattr(importlib.import_module(module_name), class_name)
    return cls()
