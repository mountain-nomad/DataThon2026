from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

Record = dict[str, Any]


class PredictRequest(BaseModel):
    records: list[Record] = Field(..., min_length=1)


class Prediction(BaseModel):
    prediction: Any
    probabilities: dict[str, float] | None = None


class PredictResponse(BaseModel):
    model_version: str
    predictions: list[Prediction]


class PredictionLogRead(BaseModel):
    id: int
    created_at: datetime
    model_version: str
    input: Record
    output: dict[str, Any]
