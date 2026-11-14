"""Idempotent demo data: `python -m app.seed`. Each step skips with a log line when its input is missing."""
import json
import logging

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.assistant.investigation import fail_stale_runs
from app.assistant.models import ActionRule
from app.core.auth import create_user
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.jobs import record_eval
from app.core.models import EvalRun, User
from app.core.schemas import UserCreate
from app.knowledge.ingest import ingest_file
from app.signals import incidents, orders, registry
from app.signals.models import Incident, ModelVersion, Order

log = logging.getLogger("seed")

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


HUMANITARIAN = ["infrastructure", "affected_people", "rescue_donation", "other_relevant"]
# Illustrative actions; costs and approvers follow the SOP-08 approval matrix (Manager limits map to admin).
ACTION_RULES = [
    ("MONITOR", "Monitor affected orders", "Watch in-scope orders and re-check risk every shift.",
     0, "analyst", HUMANITARIAN, 0, False),
    ("NOTIFY_CUSTOMER", "Notify customers", "Proactive delay notice with fee waiver up to $100 (SOP-05).",
     100, "analyst", HUMANITARIAN, 1, False),
    ("CONFIRM_ROUTE", "Confirm route with carrier", "Get written route status from the carrier (SOP-01).",
     0, "analyst", ["infrastructure"], 1, True),
    ("ESCALATE_CARRIER", "Escalate to carrier", "L3 carrier escalation placed by the Supervisor (SOP-04).",
     0, "supervisor", ["infrastructure", "affected_people"], 3, True),
    ("EXPEDITE", "Expedite high-risk orders", "Air freight or dedicated truck for high-risk orders (SOP-06).",
     6300, "supervisor", ["infrastructure", "affected_people"], 1, True),
    ("REROUTE", "Re-route around damage", "Detour at about $450 per truck per 100 km (SOP-01, SOP-06).",
     4500, "supervisor", ["infrastructure"], 1, True),
    ("HOLD_SHIPMENT", "Hold shipments over $10,000", "Holds over $10,000 need Supervisor approval (SOP-02).",
     700, "supervisor", ["infrastructure", "affected_people"], 1, True),
    ("ALTERNATE_PORT", "Divert to alternate port", "Diversion at about $1,200 per container (SOP-03).",
     12000, "supervisor", ["infrastructure"], 5, True),
]


def seed_action_rules(db: Session) -> None:
    if db.scalar(select(exists().select_from(ActionRule))):
        log.info("action rules: already seeded")
        return
    fields = ("code", "name", "description", "cost_usd", "approval_role", "categories", "min_high_risk_orders",
              "requires_evidence")
    db.add_all(ActionRule(**dict(zip(fields, row, strict=True))) for row in ACTION_RULES)
    db.commit()
    log.info("action rules: %d rules", len(ACTION_RULES))


def seed_orders(db: Session) -> None:
    path = settings.data_dir / "processed" / "orders.parquet"
    if not path.exists():
        log.info("orders: %s missing", path)
    elif db.scalar(select(exists().select_from(Order))):
        log.info("orders: already seeded")
    else:
        log.info("orders: %d loaded", orders.load_orders(db, path))


def seed_incidents(db: Session) -> None:
    path = settings.data_dir / "processed" / "tweets.parquet"
    if not path.exists():
        log.info("incidents: %s missing", path)
        return
    log.info("incidents: %d pool tweets loaded", incidents.load_pool(db, path))
    if db.scalar(select(exists().where(Incident.status != "pool"))):
        log.info("incidents: already released")
    elif registry.champion(db, "incident") is None:
        log.info("incidents: no incident champion yet, release skipped")
    else:
        log.info("incidents: %d released", len(incidents.release(db, 40)))


# the first model of each task becomes champion; later ones stay candidates with a gate (DistilBERT for the demo)
SEED_MODELS = (("risk", "risk/v1"), ("incident", "text/v1-tfidf"), ("incident", "text/v1-distilbert"))


def seed_models(db: Session) -> None:
    for task, subdir in SEED_MODELS:
        path = settings.artifacts_dir / subdir
        if not (path / "metadata.json").exists():
            log.info("models: no artifact in %s", path)
        elif db.scalar(select(exists().where(ModelVersion.artifact_path == str(path)))):
            log.info("models: %s already registered", subdir)
        else:
            version = registry.register_version(db, task, path)
            registry.store_gate(db, version)
            log.info("models: registered %s as %s v%d (%s)", subdir, task, version.version, version.status)
    if db.scalar(select(exists().where(Order.risk_score.is_(None)))):
        log.info("models: scored %d orders", orders.score_orders(db))


def corpus_sources() -> list[dict]:
    """Rows of the corpus/sources.md table with the file path resolved against GUIDANCE_DIR or DATA_DIR."""
    rows = []
    for line in (settings.guidance_dir / "sources.md").read_text().splitlines():
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 7 or cells[0][:4] not in ("PUB-", "SOP-"):
            continue
        path = cells[5]
        path = (settings.data_dir / path.removeprefix("data/") if path.startswith("data/")
                else settings.guidance_dir / path.removeprefix("corpus/"))
        rows.append({"code": cells[0], "title": cells[1], "origin": cells[6], "path": path})
    return rows


def seed_documents(db: Session) -> None:
    if not (settings.guidance_dir / "sources.md").exists():
        log.info("documents: no %s", settings.guidance_dir / "sources.md")
        return
    for source in corpus_sources():
        if not source["path"].exists():
            log.info("documents: %s missing, skipped", source["path"])
            continue
        doc = ingest_file(db, source["path"], source["code"], source["title"], source["origin"])
        log.info("documents: %s %d chunks", doc.code, doc.chunk_count)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
    steps = (seed_users, seed_action_rules, seed_orders, seed_models, seed_incidents, seed_documents, seed_evals,
             fail_stale_runs)
    with SessionLocal() as db:
        for step in steps:
            step(db)


if __name__ == "__main__":
    main()
