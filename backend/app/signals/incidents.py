from pathlib import Path

from sqlalchemy.orm import Session

from app.core.models import User
from app.signals.models import Incident
from app.signals.schemas import Classification, IncidentStats


def load_pool(db: Session, csv_path: Path) -> int:
    return 0  # STUB


def release(db: Session, count: int) -> list[Incident]:
    return []  # STUB


def add_manual(db: Session, text: str, user: User) -> Incident:
    raise NotImplementedError  # STUB


def classify_text(db: Session, text: str) -> Classification:
    raise NotImplementedError  # STUB


def review(db: Session, incident_id: int, label: str, user: User) -> Incident | None:
    return None  # STUB


def release_gold(db: Session, user: User) -> int:
    return 0  # STUB


def reclassify_unreviewed(db: Session, version_id: int) -> int:
    return 0  # STUB


def search_incidents(db: Session, status: str | None, label: str | None, page: int) -> tuple[list[Incident], int]:
    return [], 0  # STUB


def get_incident(db: Session, incident_id: int) -> Incident | None:
    return None  # STUB


def incident_stats(db: Session) -> IncidentStats:
    return IncidentStats(by_status={}, by_label={}, needs_review=0, reviews_since_champion=0)  # STUB
