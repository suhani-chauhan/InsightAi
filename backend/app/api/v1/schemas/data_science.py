"""Request/response contracts for the Data Science workspace API.

Response bodies are deliberately open (``dict``) — the analytical payloads are
large, deeply nested and computed by :mod:`app.data_science`; re-declaring every
field here would be duplication with no safety gain. Request bodies are strict.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    columns: list[str] = Field(min_length=1)
    rows: list[dict[str, Any]] = Field(min_length=1)
    name: Optional[str] = None
    source: str = "query_result"
    source_detail: dict[str, Any] = Field(default_factory=dict)


class CleaningOperation(BaseModel):
    op: str
    params: dict[str, Any] = Field(default_factory=dict)


class CleaningOperationsRequest(BaseModel):
    operations: list[CleaningOperation] = Field(min_length=1)

    def as_dicts(self) -> list[dict[str, Any]]:
        return [o.model_dump() for o in self.operations]


class EdaRequest(BaseModel):
    target: Optional[str] = None


class DetectTaskRequest(BaseModel):
    target: str


class TrainRequest(BaseModel):
    target: str
    task: Optional[Literal["classification", "regression"]] = None
    models: Optional[list[str]] = None
    test_size: float = Field(default=0.2, ge=0.1, le=0.4)
    primary_metric: Optional[str] = None
    cross_validation: bool = True
    drop_columns: Optional[list[str]] = None


class PredictRequest(BaseModel):
    feature_values: dict[str, Any]


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class SessionCreatedResponse(BaseModel):
    session_id: str
    dataset: dict[str, Any]


__all__ = [
    "CreateSessionRequest",
    "CleaningOperation",
    "CleaningOperationsRequest",
    "EdaRequest",
    "DetectTaskRequest",
    "TrainRequest",
    "PredictRequest",
    "AskRequest",
    "SessionCreatedResponse",
]
