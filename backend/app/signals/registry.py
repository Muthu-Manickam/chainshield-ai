import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
from fastapi import BackgroundTasks
from ml.predictor import TEXT_FAMILIES, Predictor
from ml.risk import LEAKAGE_ALARM
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.auth import record_audit
from app.core.config import settings
from app.core.jobs import start_job
from app.core.models import Job, User
from app.signals import incidents, orders
from app.signals.models import Incident, ModelVersion, Order

GATE_MARGIN = 0.005  # candidate's primary metric may be at most this much below the champion's
BRIER_MARGIN = 0.002  # Brier may be this much worse; smaller gaps are noise on ~3k promotion orders

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
        artifact_hash=hash_dir(artifact_dir), metrics=json.loads((artifact_dir / "metrics.json").read_text()),
        status="candidate" if has_champion else "champion",
        promoted_at=None if has_champion else datetime.now(UTC),
    )
    db.add(version)
    db.commit()
    return version


def champion(db: Session, task: str) -> tuple[ModelVersion, Predictor] | None:
    version = current_champion(db, task)
    if version is None:
        return None
    cached = _cache.get(task)
    if cached is None or cached[0] != version.id:
        cached = _cache[task] = (version.id, Predictor.load(version.artifact_path))
    return version, cached[1]


def list_versions(db: Session, task: str | None) -> list[ModelVersion]:
    query = select(ModelVersion).order_by(ModelVersion.task, ModelVersion.version.desc())
    if task:
        query = query.where(ModelVersion.task == task)
    return list(db.scalars(query))


def model_info(db: Session, task: str) -> dict:
    versions = list_versions(db, task)
    current = next((v for v in versions if v.status == "champion"), None)
    champion = current and {"id": current.id, "version": current.version, "family": current.family,
                            "promoted_at": current.promoted_at.isoformat(), "metrics": current.metrics}
    return {"task": task, "versions": len(versions), "champion": champion}


def current_champion(db: Session, task: str) -> ModelVersion | None:
    return db.scalar(select(ModelVersion).where(ModelVersion.task == task, ModelVersion.status == "champion"))


def release_batch(db: Session, block: str, user: User) -> int:
    count = db.execute(update(Order).where(Order.block == block, ~Order.released).values(released=True)).rowcount
    record_audit(db, user, "model.release_batch", "orders", None, {"block": block, "count": count})
    db.commit()
    return count


def start_retrain(db: Session, background: BackgroundTasks, task: str, family: str, user: User) -> Job:
    if task == "incident" and family not in TEXT_FAMILIES:
        raise ValueError(f"incident models are one of {', '.join(TEXT_FAMILIES)}")
    record_audit(db, user, "model.retrain", "model_version", None, {"task": task, "family": family})
    return start_job(db, background, f"retrain_{task}", retrain, task, family)


def retrain(db: Session, task: str, family: str) -> dict:
    """Snapshot the new labels, train with the ml CLI, register the candidate and gate it against the champion."""
    version = (db.scalar(select(func.max(ModelVersion.version)).where(ModelVersion.task == task)) or 0) + 1
    with TemporaryDirectory() as tmp:
        if task == "risk":
            rows = db.execute(select(Order.block, Order.order_id).where(Order.released).order_by(Order.order_id)).all()
            blocks = sorted({block for block, _ in rows})
            snapshot = json.dumps([blocks, [order_id for _, order_id in rows]])
            args = ["--extra", ",".join(blocks)]
            out = settings.artifacts_dir / "risk" / f"v{version}"
        else:
            labels = pd.DataFrame(db.execute(
                select(Incident.tweet_id, Incident.reviewed_label)
                .where(Incident.status == "reviewed", Incident.tweet_id.is_not(None)).order_by(Incident.tweet_id)
            ).all(), columns=["tweet_id", "category"])
            path = Path(tmp) / "reviewed.parquet"
            labels.to_parquet(path)
            snapshot = labels.to_json()
            args = ["--family", family, "--extra-labels", str(path)]
            out = settings.artifacts_dir / "text" / f"v{version}-{family}"
        env = os.environ | {"CHAINSHIELD_DATA_DIR": str(settings.data_dir),
                            "CHAINSHIELD_ARTIFACTS_DIR": str(settings.artifacts_dir)}
        command = [sys.executable, "-m", "ml", "train", "risk" if task == "risk" else "text", "--version",
                   str(version), *args]
        run = subprocess.run(command, check=False, capture_output=True, text=True, env=env)
    if run.returncode != 0:
        raise RuntimeError(f"training failed ({run.returncode}): {run.stderr[-2000:]}")
    candidate = register_version(db, task, out)
    candidate.snapshot_hash = hashlib.sha256(snapshot.encode()).hexdigest()
    store_gate(db, candidate)
    return {"version_id": candidate.id, "version": candidate.version, "gate": candidate.gate,
            "log": run.stdout[-2000:]}


def promotion_metrics(version: ModelVersion) -> dict:
    """Metrics on the promotion set: s3 for risk, the pool holdout for incident models."""
    if version.task == "risk":
        model = version.family.removeprefix("risk_")
        s3 = version.metrics["s3"][model]
        return {"pr_auc": s3["pr_auc"], "brier": s3["brier"], "val_roc_auc": version.metrics["val"][model]["roc_auc"]}
    holdout = version.metrics["pool_holdout"]
    return {"macro_f1": holdout["macro_f1"], "infrastructure_recall": holdout["per_class_recall"]["infrastructure"]}


def store_gate(db: Session, candidate: ModelVersion) -> None:
    """Gate (CLAUDE.md section 8): primary metric within GATE_MARGIN, Brier within BRIER_MARGIN, infrastructure recall not lower."""
    champ = current_champion(db, candidate.task)
    if champ is None or champ.id == candidate.id:
        return
    new, old = promotion_metrics(candidate), promotion_metrics(champ)
    if candidate.task == "risk":
        checks = {"pr_auc": new["pr_auc"] >= old["pr_auc"] - GATE_MARGIN, "brier": new["brier"] <= old["brier"] + BRIER_MARGIN,
                  "no_leakage_alarm": new["val_roc_auc"] <= LEAKAGE_ALARM}
    else:
        checks = {"macro_f1": new["macro_f1"] >= old["macro_f1"] - GATE_MARGIN,
                  "infrastructure_recall": new["infrastructure_recall"] >= old["infrastructure_recall"]}
    candidate.gate = {"passed": all(checks.values()), "checks": checks, "candidate": new, "champion": old,
                      "champion_id": champ.id}
    db.commit()


def promote(db: Session, version_id: int, user: User, background: BackgroundTasks) -> ModelVersion | None:
    """Make a version the champion (rollback = promote an older one) and rescore with it in a job."""
    version = db.get(ModelVersion, version_id)
    if version is None:
        return None
    if version.status == "champion":
        raise ValueError("version is already the champion")
    previous = current_champion(db, version.task)
    if previous:
        previous.status = "retired"
    version.status, version.promoted_at = "champion", datetime.now(UTC)
    record_audit(db, user, "model.promote", "model_version", version.id, {
        "task": version.task, "version": version.version, "previous": previous.version if previous else None,
        "gate_passed": version.gate["passed"] if version.gate else None,
    })
    db.commit()
    rescore = orders.score_orders if version.task == "risk" else incidents.reclassify_unreviewed
    start_job(db, background, f"rescore_{version.task}", rescore)
    return version
