from datetime import datetime
from typing import Any, Literal

from app.core.schemas import Schema

Band = Literal["low", "medium", "high"]


class OrderFilter(Schema):
    market: str | None = None
    shipping_mode: str | None = None
    band: Band | None = None
    include_trained: bool = False
    q: str | None = None


class OrderRow(Schema):
    id: int
    order_id: int
    order_date: datetime
    market: str
    order_region: str
    shipping_mode: str
    customer_segment: str
    order_total: float
    block: str
    risk_score: float | None
    risk_band: str | None


class Factor(Schema):
    feature: str
    value: Any
    impact: float


class OrderDetail(OrderRow):
    features: dict[str, Any]
    factors: list[Factor] | None
    late: bool | None
    model_version_id: int | None


class RiskSummary(Schema):
    total: int
    high: int
    medium: int
    low: int
    mean_score: float | None
    by_shipping_mode: list[dict[str, Any]]


class OrderStats(Schema):
    by_band: dict[str, int]
    by_shipping_mode: list[dict[str, Any]]


class Incident(Schema):
    id: int
    tweet_id: str | None
    text: str
    event: str | None
    source: str
    status: str
    predicted_label: str | None
    confidence: float | None
    screening_score: float | None
    model_version_id: int | None
    reviewed_label: str | None
    reviewed_by: int | None
    reviewed_at: datetime | None
    review_source: str | None
    created_at: datetime


class IncidentIn(Schema):
    text: str


class ReleaseIn(Schema):
    count: int


class ReviewIn(Schema):
    label: str


class Classification(Schema):
    label: str
    confidence: float
    screening_score: float
    needs_review: bool
    model_version_id: int | None


class IncidentStats(Schema):
    by_status: dict[str, int]
    by_label: dict[str, int]
    needs_review: int


class ModelVersion(Schema):
    id: int
    task: str
    version: int
    family: str
    artifact_path: str
    artifact_hash: str
    snapshot_hash: str | None
    git_commit: str | None
    metrics: dict[str, Any]
    gate: dict[str, Any] | None
    status: str
    promoted_at: datetime | None
    created_at: datetime


class ReleaseBatchIn(Schema):
    block: Literal["s1", "s2"]


class RetrainIn(Schema):
    task: Literal["risk", "incident"]
    family: Literal["lr", "xgb", "tfidf", "bilstm", "distilbert"]
