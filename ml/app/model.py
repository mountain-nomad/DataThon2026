"""Model loading and inference.

The artifact is a dict saved with joblib by `training/train.py`:
    {"model": sklearn estimator/pipeline, "version": str, "task": str,
     "target": str, "features": [...], "metrics": {...}, "example": {...}}

Swap this for torch / lightgbm / transformers etc. — just keep `predict()`'s contract.
"""

import logging
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from app.schemas import ModelInfo, Prediction, Record

log = logging.getLogger(__name__)


class ModelService:
    def __init__(self, path: Path):
        self.path = path
        self.artifact: dict[str, Any] | None = None

    def load(self) -> None:
        if not self.path.exists():
            log.warning(
                "No model at %s — serving dummy predictions. Run training/train.py.", self.path
            )
            self.artifact = None
            return
        self.artifact = joblib.load(self.path)
        log.info("Loaded model %s from %s", self.artifact.get("version"), self.path)

    @property
    def loaded(self) -> bool:
        return self.artifact is not None

    @property
    def version(self) -> str:
        return self.artifact.get("version", "unknown") if self.artifact else "dummy"

    def info(self) -> ModelInfo:
        if not self.artifact:
            return ModelInfo(loaded=False, version=self.version)
        a = self.artifact
        return ModelInfo(
            loaded=True,
            version=self.version,
            task=a.get("task"),
            target=a.get("target"),
            features=a.get("features", []),
            metrics=a.get("metrics", {}),
            example=a.get("example"),
        )

    def predict(self, records: list[Record]) -> list[Prediction]:
        if not self.artifact:
            return [Prediction(prediction=0) for _ in records]

        model = self.artifact["model"]
        features = self.artifact.get("features")
        df = pd.DataFrame.from_records(records)
        if features:
            df = df.reindex(columns=features)  # missing columns -> NaN, extra columns dropped

        preds = model.predict(df)
        probas = None
        if self.artifact.get("task") == "classification" and hasattr(model, "predict_proba"):
            classes = [str(c) for c in model.classes_]
            probas = [dict(zip(classes, map(float, row))) for row in model.predict_proba(df)]

        return [
            Prediction(prediction=_to_py(p), probabilities=probas[i] if probas else None)
            for i, p in enumerate(preds)
        ]


def _to_py(value: Any) -> Any:
    return value.item() if hasattr(value, "item") else value
