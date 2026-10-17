from datetime import UTC, datetime
from typing import Any

from sqlmodel import JSON, Column, Field, SQLModel


class PredictionLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
    model_version: str
    input: dict[str, Any] = Field(sa_column=Column(JSON))
    output: dict[str, Any] = Field(sa_column=Column(JSON))
