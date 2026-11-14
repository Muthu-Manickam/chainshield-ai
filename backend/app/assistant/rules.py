from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assistant.models import ActionRule
from app.assistant.schemas import RuleResult, RuleUpdate
from app.core.auth import record_audit
from app.core.models import User
from app.signals.schemas import RiskSummary


def rejection(rule: ActionRule, category: str, summary: RiskSummary, evidence_gap: bool) -> str | None:
    if category not in rule.categories:
        return f"Not applicable to {category} incidents"
    if summary.high < rule.min_high_risk_orders:
        return f"Needs at least {rule.min_high_risk_orders} high-risk orders in scope, found {summary.high}"
    if rule.requires_evidence and evidence_gap:
        return "Needs supporting guidance, none found"
    return None


def check(db: Session, category: str, summary: RiskSummary, evidence_gap: bool) -> list[RuleResult]:
    results = []
    for rule in db.scalars(select(ActionRule).where(ActionRule.is_active).order_by(ActionRule.id)):
        reason = rejection(rule, category, summary, evidence_gap)
        results.append(RuleResult(rule_code=rule.code, name=rule.name, eligible=reason is None,
                                  reason=reason or "All conditions met", approval_role=rule.approval_role,
                                  cost_usd=rule.cost_usd))
    return results


def list_rules(db: Session) -> list[ActionRule]:
    return list(db.scalars(select(ActionRule).order_by(ActionRule.id)))


def update_rule(db: Session, rule_id: int, data: RuleUpdate, user: User) -> ActionRule | None:
    rule = db.get(ActionRule, rule_id)
    if not rule:
        return None
    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(rule, field, value)
    record_audit(db, user, "update_rule", "action_rule", rule.id, changes)
    db.commit()
    return rule
