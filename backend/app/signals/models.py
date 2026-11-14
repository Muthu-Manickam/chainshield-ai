from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ModelVersion(Base):
    __tablename__ = "model_versions"
    task: Mapped[str]
    version: Mapped[int]
    family: Mapped[str]
    artifact_path: Mapped[str]
    artifact_hash: Mapped[str]
    snapshot_hash: Mapped[str | None]
    git_commit: Mapped[str | None]
    metrics: Mapped[dict]
    gate: Mapped[dict | None]
    status: Mapped[str] = mapped_column(default="candidate")
    promoted_at: Mapped[datetime | None]


class Order(Base):
    __tablename__ = "orders"
    order_id: Mapped[int] = mapped_column(unique=True)
    order_date: Mapped[datetime]
    market: Mapped[str]
    order_region: Mapped[str]
    shipping_mode: Mapped[str]
    customer_segment: Mapped[str]
    order_total: Mapped[float]
    item_count: Mapped[int]
    features: Mapped[dict]
    block: Mapped[str]
    released: Mapped[bool] = mapped_column(default=False)
    late: Mapped[bool | None]
    risk_score: Mapped[float | None]
    risk_band: Mapped[str | None]
    factors: Mapped[list | None]
    model_version_id: Mapped[int | None] = mapped_column(ForeignKey("model_versions.id"))


class Incident(Base):
    __tablename__ = "incidents"
    tweet_id: Mapped[str | None]
    text: Mapped[str]
    event: Mapped[str | None]
    source: Mapped[str]
    gold_label: Mapped[str | None]
    status: Mapped[str]
    predicted_label: Mapped[str | None]
    confidence: Mapped[float | None]
    screening_score: Mapped[float | None]
    model_version_id: Mapped[int | None] = mapped_column(ForeignKey("model_versions.id"))
    reviewed_label: Mapped[str | None]
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None]
    review_source: Mapped[str | None]
