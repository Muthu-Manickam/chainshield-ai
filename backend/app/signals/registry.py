import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi import BackgroundTasks
from ml.predictor import Predictor
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.models import Job, User
from app.signals.models import ModelVersion

# task -> (version id, loaded model); reloaded when the task's champion changes
_cache: dict[str, tuple[int, Predictor]] = {}


def hash_dir(path: Path) -> str:
    digest = hashlib.sha256()
    for file in sorted(p for p in path.rglob("*") if p.is_file()):
        digest.update(file.relative_to(path).as_posix().encode())
        digest.update(file.read_bytes())
    return digest.hexdigest()


def register_version(db: Session, task: str, artifact_dir: Path) -> ModelVersion:
    meta = json.loads((artifact_dir / "metadata.json").read_text())
    latest = db.scalar(select(func.max(ModelVersion.version)).where(ModelVersion.task == task))
    has_champion = db.scalar(select(ModelVersion.id).where(ModelVersion.task == task,
                                                           ModelVersion.status == "champion"))
    version = ModelVersion(
        task=task, version=(latest or 0) + 1, family=meta["family"], artifact_path=str(artifact_dir),
        artifact_hash=hash_dir(artifact_dir), snapshot_hash=meta.get("snapshot_hash"),
        git_commit=meta.get("git_commit"), metrics=json.loads((artifact_dir / "metrics.json").read_text()),
        status="candidate" if has_champion else "champion",
        promoted_at=None if has_champion else datetime.now(UTC),
    )
    db.add(version)
    db.commit()
    return version


def load_model(path: str) -> Predictor:
    try:
        return Predictor.load(path)
    except ValueError:
        # Predictor only knows the risk families so far; text models load through ml.text
        from ml.text import load_model as load_text_model

        return load_text_model(path)


def champion(db: Session, task: str) -> tuple[ModelVersion, Predictor] | None:
    version = db.scalar(select(ModelVersion).where(ModelVersion.task == task, ModelVersion.status == "champion"))
    if version is None:
        return None
    cached = _cache.get(task)
    if cached is None or cached[0] != version.id:
        cached = _cache[task] = (version.id, load_model(version.artifact_path))
    return version, cached[1]


def list_versions(db: Session, task: str | None) -> list[ModelVersion]:
    query = select(ModelVersion).order_by(ModelVersion.task, ModelVersion.version.desc())
    if task:
        query = query.where(ModelVersion.task == task)
    return list(db.scalars(query))


def model_info(db: Session, task: str) -> dict:
    versions = list_versions(db, task)
    current = next((v for v in versions if v.status == "champion"), None)
    if current is None:
        return {"task": task, "champion": None, "versions": len(versions)}
    return {
        "task": task, "versions": len(versions),
        "champion": {"id": current.id, "version": current.version, "family": current.family,
                     "promoted_at": current.promoted_at.isoformat(), "metrics": current.metrics},
    }


def release_batch(db: Session, block: str, user: User) -> int:
    return 0  # STUB


def start_retrain(db: Session, background: BackgroundTasks, task: str, family: str, user: User) -> Job:
    raise NotImplementedError  # STUB


def promote(db: Session, version_id: int, user: User, background: BackgroundTasks) -> ModelVersion | None:
    return None  # STUB
