from sqlalchemy.orm import Session

from app.assistant.models import ActionRule
from app.assistant.schemas import RuleResult, RuleUpdate
from app.core.models import User
from app.signals.schemas import RiskSummary


def check(db: Session, category: str, summary: RiskSummary, evidence_gap: bool) -> list[RuleResult]:
    return []  # STUB


def list_rules(db: Session) -> list[ActionRule]:
    return []  # STUB


def update_rule(db: Session, rule_id: int, data: RuleUpdate, user: User) -> ActionRule | None:
    return None  # STUB
