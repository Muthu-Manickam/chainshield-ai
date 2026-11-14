from pathlib import Path

from fastapi import BackgroundTasks
from ml.predictor import Predictor
from sqlalchemy.orm import Session

from app.core.models import Job, User
from app.signals.models import ModelVersion


def register_version(db: Session, task: str, artifact_dir: Path) -> ModelVersion:
    raise NotImplementedError  # STUB


def champion(db: Session, task: str) -> tuple[ModelVersion, Predictor] | None:
    return None  # STUB


def list_versions(db: Session, task: str | None) -> list[ModelVersion]:
    return []  # STUB


def model_info(db: Session, task: str) -> dict:
    return {}  # STUB


def release_batch(db: Session, block: str, user: User) -> int:
    return 0  # STUB


def start_retrain(db: Session, background: BackgroundTasks, task: str, family: str, user: User) -> Job:
    raise NotImplementedError  # STUB


def promote(db: Session, version_id: int, user: User, background: BackgroundTasks) -> ModelVersion | None:
    return None  # STUB
