import asyncio
from collections.abc import AsyncIterator

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.assistant.models import Investigation, InvestigationAction
from app.assistant.schemas import Step
from app.core.models import User


def start(db: Session, background: BackgroundTasks, incident_id: int, scope: dict, user: User) -> Investigation:
    raise NotImplementedError  # STUB


def run(investigation_id: int) -> None:
    pass  # STUB


def decide(db: Session, investigation_id: int, action_id: int, decision: str, user: User,
           background: BackgroundTasks) -> InvestigationAction | None:
    return None  # STUB


def write_report(investigation_id: int) -> None:
    pass  # STUB


async def stream_steps(investigation_id: int) -> AsyncIterator[str]:
    # STUB: three fixture steps for the CP1 probe
    for n, node in enumerate(["intake", "intelligence", "knowledge"], start=1):
        await asyncio.sleep(0.5)
        step = Step(id=n, node=node, status="ok", output={}, error=None, duration_ms=500)
        yield f"data: {step.model_dump_json()}\n\n"
    yield 'data: {"type": "done"}\n\n'


def get_investigation(db: Session, investigation_id: int) -> dict | None:
    return None  # STUB


def list_investigations(db: Session) -> list[Investigation]:
    return []  # STUB


def investigation_stats(db: Session) -> dict:
    return {}  # STUB


def fail_stale_runs(db: Session) -> int:
    return 0  # STUB
