from datetime import datetime
from typing import Any, Literal

from app.core.schemas import Schema
from app.signals.schemas import Incident


class ActionRule(Schema):
    id: int
    code: str
    name: str
    description: str
    cost_usd: float
    approval_role: str
    categories: list[str]
    min_high_risk_orders: int
    requires_evidence: bool
    is_active: bool


class RuleUpdate(Schema):
    name: str | None = None
    description: str | None = None
    cost_usd: float | None = None
    approval_role: str | None = None
    categories: list[str] | None = None
    min_high_risk_orders: int | None = None
    requires_evidence: bool | None = None
    is_active: bool | None = None


class RuleResult(Schema):
    rule_code: str
    name: str
    eligible: bool
    reason: str
    approval_role: str
    cost_usd: float


class InvestigationIn(Schema):
    incident_id: int
    scope: dict[str, Any]


class Investigation(Schema):
    id: int
    incident_id: int
    scope: dict[str, Any]
    status: str
    degraded: bool
    created_at: datetime


class Step(Schema):
    id: int
    node: str
    status: str
    output: dict[str, Any] | None
    error: str | None
    duration_ms: int


class Action(Schema):
    id: int
    investigation_id: int
    rule_code: str
    name: str
    eligible: bool
    reason: str
    rank: int | None
    rationale: str | None
    decision: str
    decided_by: int | None
    decided_at: datetime | None
    created_at: datetime


class DecisionIn(Schema):
    decision: Literal["approved", "rejected"]


class InvestigationDetail(Investigation):
    incident: Incident
    state: dict[str, Any]
    steps: list[Step]
    actions: list[Action]
    report: str | None


class ChatIn(Schema):
    session_id: str | None = None
    message: str


class ChatMessage(Schema):
    id: int
    session_id: str
    user_id: int
    role: str
    content: str
    tool_calls: list[Any] | None
    citations: list[Any] | None
    created_at: datetime


class ChatEvent(Schema):
    type: Literal["tool", "answer", "error", "done"]
    name: str | None = None
    content: str | None = None
    citations: list[Any] | None = None
    degraded: bool | None = None
