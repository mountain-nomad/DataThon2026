from typing import Any

from pydantic import BaseModel, Field

# A record is one row of features: {"feature_name": value, ...}.
# Kept generic on purpose — tighten it once the task's schema is known.
Record = dict[str, Any]


class PredictRequest(BaseModel):
    records: list[Record] = Field(..., min_length=1)


class Prediction(BaseModel):
    prediction: Any
    probabilities: dict[str, float] | None = None


class PredictResponse(BaseModel):
    model_version: str
    predictions: list[Prediction]


class ModelInfo(BaseModel):
    loaded: bool
    version: str
    task: str | None = None
    target: str | None = None
    features: list[str] = []
    metrics: dict[str, float] = {}
    example: Record | None = None
