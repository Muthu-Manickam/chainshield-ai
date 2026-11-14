from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ActionRule(Base):
    __tablename__ = "action_rules"
    code: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    description: Mapped[str]
    cost_usd: Mapped[float]
    approval_role: Mapped[str]
    categories: Mapped[list]
    min_high_risk_orders: Mapped[int] = mapped_column(default=0)
    requires_evidence: Mapped[bool] = mapped_column(default=False)
    is_active: Mapped[bool] = mapped_column(default=True)


class Investigation(Base):
    __tablename__ = "investigations"
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"))
    scope: Mapped[dict]
    status: Mapped[str] = mapped_column(default="running")
    degraded: Mapped[bool] = mapped_column(default=False)
    state: Mapped[dict] = mapped_column(default=dict)
    report: Mapped[str | None]
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


class InvestigationStep(Base):
    __tablename__ = "investigation_steps"
    investigation_id: Mapped[int] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"))
    node: Mapped[str]
    status: Mapped[str]
    output: Mapped[dict | None]
    error: Mapped[str | None]
    duration_ms: Mapped[int]


class InvestigationAction(Base):
    __tablename__ = "investigation_actions"
    investigation_id: Mapped[int] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"))
    rule_code: Mapped[str]
    name: Mapped[str]
    eligible: Mapped[bool]
    reason: Mapped[str]
    rank: Mapped[int | None]
    rationale: Mapped[str | None]
    decision: Mapped[str] = mapped_column(default="pending")
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None]


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    session_id: Mapped[str] = mapped_column(index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str]
    content: Mapped[str]
    tool_calls: Mapped[list | None]
    citations: Mapped[list | None]


class LlmCache(Base):
    __tablename__ = "llm_cache"
    request_hash: Mapped[str] = mapped_column(unique=True)
    model: Mapped[str]
    response: Mapped[dict]
    cost_usd: Mapped[float] = mapped_column(default=0.0)
