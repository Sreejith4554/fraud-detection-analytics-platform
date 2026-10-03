"""ULB-compatible contract; dataset columns verified in phase 2."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Nonnegative = Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]


class TransactionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1"]
    source: Literal["SYNTHETIC", "DATASET_REPLAY"]
    amount: Nonnegative
    time: Nonnegative
    v: Annotated[list[Number], Field(min_length=28, max_length=28)]


class ScoreResponse(BaseModel):
    model_score: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
    risk_category: Literal["HIGH", "LOW"]
    decision: Literal["FLAG_FOR_REVIEW", "NO_REVIEW_TRIGGERED"]
    threshold: Annotated[float, Field(ge=0, le=1)]
    model_version: str
    source: Literal["SYNTHETIC", "DATASET_REPLAY"]
    persisted: Literal[False]
    score_interpretation: str
    disclaimer: str


class PredictionResponse(ScoreResponse):
    persisted: Literal[True]
    prediction_id: str
    transaction_id: str
    alert_id: str | None
    created_at: str
