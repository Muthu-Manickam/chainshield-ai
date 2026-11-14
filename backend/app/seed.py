"""Idempotent demo data: `python -m app.seed`. Each step skips with a log line when its input is missing."""
import json
import logging

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.assistant.investigation import fail_stale_runs
from app.core.auth import create_user
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.jobs import record_eval
from app.core.models import EvalRun, User
from app.core.schemas import UserCreate

log = logging.getLogger("seed")

# --- B0 ---

DEMO_PASSWORD = "chainshield"


def seed_users(db: Session) -> None:
    if db.scalar(select(exists().select_from(User))):
        log.info("users: already seeded")
        return
    for role in ("analyst", "supervisor", "admin"):
        create_user(db, UserCreate(email=f"{role}@chainshield.local", password=DEMO_PASSWORD, role=role), None)
    log.info("users: 3 demo users")


def seed_evals(db: Session) -> None:
    files = sorted((settings.artifacts_dir / "eval").glob("*.json"))
    if not files:
        log.info("evals: no files in %s", settings.artifacts_dir / "eval")
        return
    if db.scalar(select(exists().select_from(EvalRun))):
        log.info("evals: already seeded")
        return
    for path in files:
        for name, metrics in json.loads(path.read_text()).items():
            record_eval(db, path.stem, name, metrics)
    log.info("evals: %d files", len(files))

# --- G2 ---


def seed_action_rules(db: Session) -> None:
    log.info("action rules: not implemented")  # STUB

# --- S1 ---


def seed_orders(db: Session) -> None:
    log.info("orders: not implemented")  # STUB

# --- S2 ---


def seed_incidents(db: Session) -> None:
    log.info("incidents: not implemented")  # STUB

# --- RG1 ---


def seed_models(db: Session) -> None:
    log.info("models: not implemented")  # STUB

# --- K1 ---


def seed_documents(db: Session) -> None:
    log.info("documents: not implemented")  # STUB

# --- main ---


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
    steps = (seed_users, seed_action_rules, seed_orders, seed_incidents, seed_models, seed_documents, seed_evals,
             fail_stale_runs)
    with SessionLocal() as db:
        for step in steps:
            step(db)


if __name__ == "__main__":
    main()
