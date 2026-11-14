from typing import Literal

from langchain_core.tools import StructuredTool
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.assistant import investigation
from app.knowledge import search as knowledge
from app.signals import incidents, orders, registry
from app.signals.schemas import Incident, OrderDetail, OrderFilter, OrderRow

PAGE_SIZE = 10


def _dump(model: BaseModel) -> dict:
    return model.model_dump(mode="json")


def get_order(db: Session, order_id: int) -> dict:
    order = orders.get_order(db, order_id)
    return _dump(OrderDetail.model_validate(order)) if order else {"error": "order not found"}


def search_orders(db: Session, market: str | None = None, shipping_mode: str | None = None,
                  band: str | None = None) -> dict:
    rows, total = orders.search_orders(db, OrderFilter(market=market, shipping_mode=shipping_mode, band=band),
                                       1, PAGE_SIZE)
    return {"total": total, "items": [_dump(OrderRow.model_validate(row)) for row in rows]}


def risk_summary(db: Session, market: str | None = None, shipping_mode: str | None = None) -> dict:
    return _dump(orders.risk_summary(db, OrderFilter(market=market, shipping_mode=shipping_mode)))


def search_incidents(db: Session, status: str | None = None, label: str | None = None) -> dict:
    rows, total = incidents.search_incidents(db, status, label, 1)
    return {"total": total, "items": [_dump(Incident.model_validate(row)) for row in rows[:PAGE_SIZE]]}


def classify_text(db: Session, text: str) -> dict:
    return _dump(incidents.classify_text(db, text))


def search_guidance(db: Session, query: str) -> dict:
    return _dump(knowledge.search(db, query))


def get_investigation(db: Session, investigation_id: int) -> dict:
    return investigation.get_investigation(db, investigation_id) or {"error": "investigation not found"}


class OrderArgs(BaseModel):
    order_id: int


class OrderSearchArgs(BaseModel):
    market: str | None = None
    shipping_mode: str | None = None
    band: Literal["low", "medium", "high"] | None = None


class RiskArgs(BaseModel):
    market: str | None = None
    shipping_mode: str | None = None


class IncidentSearchArgs(BaseModel):
    status: Literal["pool", "classified", "needs_review", "reviewed"] | None = None
    label: str | None = None


class TextArgs(BaseModel):
    text: str


class QueryArgs(BaseModel):
    query: str


class InvestigationArgs(BaseModel):
    investigation_id: int


class TaskArgs(BaseModel):
    task: Literal["risk", "incident"]


def _tool(func, args: type[BaseModel]) -> StructuredTool:
    # `func` takes `db` first; the chat graph supplies it when calling `tool.func(db, **args)`.
    return StructuredTool(name=func.__name__, description=func.__name__.replace("_", " "),
                          args_schema=args, func=func)


TOOLS = [
    _tool(get_order, OrderArgs),
    _tool(search_orders, OrderSearchArgs),
    _tool(risk_summary, RiskArgs),
    _tool(search_incidents, IncidentSearchArgs),
    _tool(classify_text, TextArgs),
    _tool(search_guidance, QueryArgs),
    _tool(get_investigation, InvestigationArgs),
    _tool(registry.model_info, TaskArgs),
]
