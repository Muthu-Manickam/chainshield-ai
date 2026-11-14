from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

Role = Literal["analyst", "supervisor", "admin"]


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page[T](Schema):
    items: list[T]
    total: int


class LoginIn(Schema):
    email: str
    password: str


class User(Schema):
    id: int
    email: str
    role: str
    is_active: bool


class UserCreate(Schema):
    email: str
    password: str
    role: Role


class UserUpdate(Schema):
    role: Role | None = None
    is_active: bool | None = None
    password: str | None = None


class Job(Schema):
    id: int
    kind: str
    status: str
    log: str
    error: str | None
    result: dict[str, Any] | None


class AuditEntry(Schema):
    id: int
    user_id: int | None
    user_email: str | None = None
    action: str
    entity: str
    entity_id: str | None
    detail: dict[str, Any] | None
    created_at: datetime


class EvalRun(Schema):
    id: int
    kind: str
    name: str
    metrics: dict[str, Any]
    created_at: datetime
