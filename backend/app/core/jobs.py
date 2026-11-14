from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.models import EvalRun, Job


def start_job(db: Session, background: BackgroundTasks, kind: str, fn: Callable, *args) -> Job:
    """Runs fn(db, *args) after the response with its own session; a dict return value becomes the job result."""
    job = Job(kind=kind)
    db.add(job)
    db.commit()
    background.add_task(run_job, job.id, fn, *args)
    return job


def run_job(job_id: int, fn: Callable, *args) -> None:
    with SessionLocal() as db:
        job = db.get(Job, job_id)
        job.status = "running"
        db.commit()
        try:
            result = fn(db, *args)
            job.result = result if isinstance(result, dict) else None
            job.status = "done"
        except Exception as exc:  # noqa: BLE001  (any failure is stored on the job)
            db.rollback()
            job.status, job.error = "failed", f"{type(exc).__name__}: {exc}"
        job.finished_at = datetime.now(UTC)
        db.commit()


def get_job(db: Session, job_id: int) -> Job | None:
    return db.get(Job, job_id)


def record_eval(db: Session, kind: str, name: str, metrics: dict) -> EvalRun:
    run = EvalRun(kind=kind, name=name, metrics=metrics)
    db.add(run)
    db.commit()
    return run


def list_evals(db: Session, kind: str | None = None) -> list[EvalRun]:
    query = select(EvalRun).order_by(EvalRun.id)
    if kind:
        query = query.where(EvalRun.kind == kind)
    return list(db.scalars(query))
