from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class User(Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    role: Mapped[str]
    is_active: Mapped[bool] = mapped_column(default=True)


class Job(Base):
    __tablename__ = "jobs"
    kind: Mapped[str]
    status: Mapped[str] = mapped_column(default="queued")
    log: Mapped[str] = mapped_column(default="")
    error: Mapped[str | None]
    result: Mapped[dict | None]
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    finished_at: Mapped[datetime | None]


class AuditLog(Base):
    __tablename__ = "audit_log"
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str]
    entity: Mapped[str]
    entity_id: Mapped[str | None]
    detail: Mapped[dict | None]


class EvalRun(Base):
    __tablename__ = "eval_runs"
    kind: Mapped[str]
    name: Mapped[str]
    metrics: Mapped[dict]
