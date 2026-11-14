from datetime import UTC, datetime
from functools import cache
from pathlib import Path

import pandas as pd
from ml.features import clean_text
from ml.text import CLASSES
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import record_audit
from app.core.config import settings
from app.core.models import User
from app.signals import registry
from app.signals.models import Incident
from app.signals.schemas import Classification, IncidentStats

PAGE_SIZE = 50
MIN_TOKENS = 3
UNREVIEWED = ("classified", "needs_review")


def load_pool(db: Session, path: Path) -> int:
    """Insert the queue pool (never the promotion holdout) with status `pool`; tweets already loaded are skipped."""
    tweets = pd.read_parquet(path)
    tweets = tweets[tweets.pool & ~tweets.pool_holdout]
    loaded = set(db.scalars(select(Incident.tweet_id).where(Incident.source == "pool")))
    rows = [Incident(tweet_id=row.tweet_id, text=row.text, event=row.event, source="pool", gold_label=row.category,
                     status="pool") for row in tweets.itertuples() if row.tweet_id not in loaded]
    db.add_all(rows)
    db.commit()
    return len(rows)


def classify(db: Session, texts: list[str]) -> list[Classification]:
    if not texts:
        return []
    version, model = registry.champion(db, "incident")
    threshold = model.metadata["review_threshold"]
    probs = model.predict_proba(texts)
    humanitarian = 1 - probs[:, model.classes.index("not_humanitarian")]
    return [
        Classification(label=model.classes[row.argmax()], confidence=float(row.max()), screening_score=float(score),
                       needs_review=bool(row.max() < threshold or len(clean_text(text).split()) < MIN_TOKENS),
                       model_version_id=version.id)
        for text, row, score in zip(texts, probs, humanitarian)
    ]


def classify_text(db: Session, text: str) -> Classification:
    return classify(db, [text])[0]


def apply(incident: Incident, result: Classification) -> None:
    incident.predicted_label = result.label
    incident.confidence = result.confidence
    incident.screening_score = result.screening_score
    incident.model_version_id = result.model_version_id
    incident.status = "needs_review" if result.needs_review else "classified"


def release(db: Session, count: int) -> list[Incident]:
    rows = list(db.scalars(select(Incident).where(Incident.status == "pool").order_by(Incident.id).limit(count)))
    for incident, result in zip(rows, classify(db, [row.text for row in rows])):
        apply(incident, result)
    db.commit()
    return rows


@cache
def held_out_texts() -> frozenset[str]:
    tweets = pd.read_parquet(settings.data_dir / "processed/tweets.parquet")
    return frozenset(clean_text(text) for text in tweets[tweets.split.isin(["dev", "test"])].text)


def add_manual(db: Session, text: str, user: User) -> Incident:
    if clean_text(text) in held_out_texts():
        raise ValueError("text duplicates an evaluation tweet")
    incident = Incident(text=text, source="manual", status="pool")
    apply(incident, classify_text(db, text))
    db.add(incident)
    record_audit(db, user, "incident.add", "incident", None, {"text": text})
    db.commit()
    return incident


def mark_reviewed(incident: Incident, label: str, user: User, source: str) -> None:
    incident.reviewed_label = label
    incident.reviewed_by = user.id
    incident.reviewed_at = datetime.now(UTC)
    incident.review_source = source
    incident.status = "reviewed"


def review(db: Session, incident_id: int, label: str, user: User) -> Incident | None:
    incident = db.get(Incident, incident_id)
    if incident is None:
        return None
    if label not in CLASSES:
        raise ValueError(f"unknown label: {label}")
    mark_reviewed(incident, label, user, "analyst")
    record_audit(db, user, "incident.review", "incident", incident.id, {"label": label})
    db.commit()
    return incident


def release_gold(db: Session, user: User) -> int:
    """Admin shortcut: every pool tweet not yet reviewed gets its gold label as the reviewed label."""
    rows = list(db.scalars(select(Incident).where(
        Incident.source == "pool", Incident.status != "reviewed", Incident.gold_label.is_not(None))))
    for incident in rows:
        mark_reviewed(incident, incident.gold_label, user, "batch")
    record_audit(db, user, "incident.release_gold", "incident", None, {"count": len(rows)})
    db.commit()
    return len(rows)


def reclassify_unreviewed(db: Session) -> int:
    """Re-score the unreviewed queue with the champion (the new one after a promotion)."""
    rows = list(db.scalars(select(Incident).where(Incident.status.in_(UNREVIEWED))))
    for incident, result in zip(rows, classify(db, [row.text for row in rows])):
        apply(incident, result)
    db.commit()
    return len(rows)


def search_incidents(db: Session, status: str | None, label: str | None, page: int) -> tuple[list[Incident], int]:
    query = select(Incident)
    query = query.where(Incident.status == status) if status else query.where(Incident.status != "pool")
    if label:
        query = query.where(func.coalesce(Incident.reviewed_label, Incident.predicted_label) == label)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.order_by(Incident.id.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))
    return list(rows), total


def get_incident(db: Session, incident_id: int) -> Incident | None:
    return db.get(Incident, incident_id)


def count_by(db: Session, column) -> dict[str, int]:
    rows = db.execute(select(column, func.count()).where(column.is_not(None)).group_by(column))
    return {key: count for key, count in rows}


def incident_stats(db: Session) -> IncidentStats:
    by_status = count_by(db, Incident.status)
    return IncidentStats(
        by_status=by_status,
        by_label=count_by(db, func.coalesce(Incident.reviewed_label, Incident.predicted_label)),
        needs_review=by_status.get("needs_review", 0),
    )
