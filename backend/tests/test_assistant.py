# --- L1 ---
import pytest
from langchain_core.messages import AIMessage
from pydantic import BaseModel

from app.assistant import llm
from app.assistant.models import LlmCache


class Verdict(BaseModel):
    label: str


class FakeChat:
    """Stands in for ChatOpenAI: fails `failures` times, then answers with a cost of $0.01."""

    def __init__(self, models: list, failures: int):
        self.models, self.failures = models, failures

    def __call__(self, model: str):
        self.models.append(model)
        return self

    def with_structured_output(self, schema, include_raw):
        return self

    def invoke(self, messages):
        if len(self.models) <= self.failures:
            raise RuntimeError("provider down")
        raw = AIMessage(content="", response_metadata={"token_usage": {"cost": 0.01}})
        return {"raw": raw, "parsed": Verdict(label="ok"), "parsing_error": None}


def test_l1_replay_serves_cache_only(db):
    with pytest.raises(llm.LLMError):
        llm.complete(db, [("user", "hi")], Verdict)
    db.add(LlmCache(request_hash=llm._request_hash([("user", "hi")], Verdict.model_json_schema()), model="m",
                    response={"label": "cached"}))
    db.commit()
    assert llm.complete(db, [("user", "hi")], Verdict) == Verdict(label="cached")


def test_l1_live_retries_then_caches_cost(db, monkeypatch):
    models = []
    monkeypatch.setattr(llm.settings, "llm_mode", "live")
    monkeypatch.setattr(llm, "_chat", FakeChat(models, failures=1))
    assert llm.complete(db, [("user", "hi")], Verdict) == Verdict(label="ok")
    assert llm.complete(db, [("user", "hi")], Verdict) == Verdict(label="ok")
    assert models == [llm.settings.llm_model] * 2
    assert db.query(LlmCache).one().cost_usd == 0.01


def test_l1_falls_back_then_raises(db, monkeypatch):
    models = []
    monkeypatch.setattr(llm.settings, "llm_mode", "live")
    monkeypatch.setattr(llm, "_chat", FakeChat(models, failures=2))
    llm.complete(db, [("user", "hi")], Verdict)
    assert db.query(LlmCache).one().model == llm.settings.llm_fallback_model
    monkeypatch.setattr(llm, "_chat", FakeChat([], failures=3))
    with pytest.raises(llm.LLMError, match="provider down"):
        llm.complete(db, [("user", "other")], Verdict)


def test_l1_stops_at_budget(db, monkeypatch):
    monkeypatch.setattr(llm.settings, "llm_mode", "live")
    monkeypatch.setattr(llm, "_chat", FakeChat([], failures=0))
    db.add(LlmCache(request_hash="spent", model="m", response={}, cost_usd=llm.settings.llm_budget_usd))
    db.commit()
    with pytest.raises(llm.LLMError, match="budget"):
        llm.complete(db, [("user", "hi")], Verdict)

# --- G2 ---
from app.assistant import rules, validator
from app.assistant.models import ActionRule as ActionRuleRow
from app.core.models import AuditLog
from app.seed import ACTION_RULES, seed_action_rules
from app.signals.schemas import RiskSummary as G2Summary
from tests.conftest import login_as


def _g2_summary(high: int) -> G2Summary:
    return G2Summary(total=10, high=high, medium=0, low=10 - high, mean_score=0.5, by_shipping_mode=[])


def _g2_results(db, category="infrastructure", high=10, gap=False) -> dict:
    seed_action_rules(db)
    return {r.rule_code: r for r in rules.check(db, category, _g2_summary(high), gap)}


def test_g2_seed_is_idempotent(db):
    seed_action_rules(db)
    seed_action_rules(db)
    assert db.query(ActionRuleRow).count() == len(ACTION_RULES) == 8
    assert db.query(ActionRuleRow).filter_by(code="HOLD_SHIPMENT").one().approval_role == "supervisor"


def test_g2_all_rules_pass_with_full_evidence(db):
    results = _g2_results(db)
    assert len(results) == 8 and all(r.eligible for r in results.values())


def test_g2_category_rule(db):
    results = _g2_results(db, category="rescue_donation")
    assert results["NOTIFY_CUSTOMER"].eligible
    assert not results["REROUTE"].eligible and "rescue_donation" in results["REROUTE"].reason
    assert not any(r.eligible for r in _g2_results(db, category="not_humanitarian").values())


def test_g2_high_risk_rule(db):
    results = _g2_results(db, high=3)
    assert results["ESCALATE_CARRIER"].eligible
    assert not results["ALTERNATE_PORT"].eligible and "found 3" in results["ALTERNATE_PORT"].reason


def test_g2_evidence_rule(db):
    results = _g2_results(db, gap=True)
    assert results["MONITOR"].eligible and results["NOTIFY_CUSTOMER"].eligible
    assert not results["HOLD_SHIPMENT"].eligible and "guidance" in results["HOLD_SHIPMENT"].reason


def test_g2_inactive_rule_is_skipped_and_update_is_audited(client, db):
    seed_action_rules(db)
    rule = db.query(ActionRuleRow).filter_by(code="MONITOR").one()
    login_as(client, "analyst")
    assert client.put(f"/api/rules/{rule.id}", json={"is_active": False}).status_code == 403
    login_as(client, "admin")
    response = client.put(f"/api/rules/{rule.id}", json={"is_active": False})
    assert response.status_code == 200 and response.json()["is_active"] is False
    assert client.put("/api/rules/999", json={"is_active": False}).status_code == 404
    assert len(client.get("/api/rules").json()) == 8
    db.expire_all()
    assert "MONITOR" not in _g2_results(db)
    assert db.query(AuditLog).filter_by(action="update_rule").one().detail == {"is_active": False}


G2_TOOLS = [{"high": 12, "mean_score": 0.734, "order_id": 4521}, {"chunks": [{"text": "Holds over $10,000 need"}]}]


@pytest.mark.parametrize("text", [
    "12 high-risk orders, mean risk 0.73 (73%) [SOP-02#1]. Holds over $10,000 need approval [SOP-02#1].",
    "Order 4521 is high risk and the flood is affecting the region.",
])
def test_g2_validator_passes(text):
    assert validator.validate(text, {"SOP-02#1"}, G2_TOOLS, {"HOLD_SHIPMENT"}, ["HOLD_SHIPMENT"]) == []


@pytest.mark.parametrize("text, error", [
    ("See [SOP-09#3].", "Unknown citation SOP-09#3"),
    ("There are 15 high-risk orders.", "Number 15"),
    ("Mean risk is 0.74.", "Number 0.74"),
    ("The flood caused the delay of order 4521.", "delayed a specific order"),
    ("Order #4521 was late because of the bridge collapse.", "delayed a specific order"),
])
def test_g2_validator_fails(text, error):
    errors = validator.validate(text, {"SOP-02#1"}, G2_TOOLS)
    assert len(errors) == 1 and error in errors[0]


def test_g2_validator_rejects_ineligible_action():
    assert validator.validate("", set(), [], {"MONITOR"}, ["MONITOR"]) == []
    assert validator.validate("", set(), [], {"MONITOR"}, ["REROUTE"]) == ["Action REROUTE is not eligible"]

# --- T1 ---
import json
from datetime import datetime
from types import SimpleNamespace

from app.assistant import tools
from app.signals.schemas import Classification, RiskSummary


def _order(**extra):
    return SimpleNamespace(id=1, order_id=77, order_date=datetime(2026, 1, 1), market="LATAM", order_region="x",
                           shipping_mode="Second Class", customer_segment="c", order_total=9.5, block="s1",
                           risk_score=0.8, risk_band="high", features={}, factors=None, late=None,
                           model_version_id=None, **extra)


def test_t1_order_tools_return_json_safe_dicts(db, monkeypatch):
    seen = {}

    def fake_search(db, filters, page, page_size):
        seen["filters"] = filters
        return [_order()], 1

    monkeypatch.setattr(tools.orders, "get_order", lambda db, order_id: _order() if order_id == 1 else None)
    monkeypatch.setattr(tools.orders, "search_orders", fake_search)
    monkeypatch.setattr(tools.orders, "risk_summary", lambda db, f: RiskSummary(
        total=1, high=1, medium=0, low=0, mean_score=0.8, by_shipping_mode=[]))
    assert tools.get_order(db, 1)["order_id"] == 77
    assert tools.get_order(db, 2) == {"error": "order not found"}
    found = tools.search_orders(db, market="LATAM", band="high")
    assert found["total"] == 1 and seen["filters"].band == "high"
    assert tools.risk_summary(db)["high"] == 1
    json.dumps([tools.get_order(db, 1), found])


def test_t1_other_tools_delegate(db, monkeypatch):
    monkeypatch.setattr(tools.incidents, "classify_text", lambda db, text: Classification(
        label="infrastructure", confidence=0.9, screening_score=0.9, needs_review=False, model_version_id=1))
    monkeypatch.setattr(tools.incidents, "search_incidents", lambda db, status, label, page: ([], 0))
    monkeypatch.setattr(tools.knowledge, "search", lambda db, q: SimpleNamespace(
        model_dump=lambda mode: {"chunks": [], "evidence_gap": True, "best_score": 0.1}))
    monkeypatch.setattr(tools.investigation, "get_investigation", lambda db, i: None)
    monkeypatch.setattr(tools.registry, "model_info", lambda db, task: {"task": task})
    assert tools.classify_text(db, "bridge down")["label"] == "infrastructure"
    assert tools.search_incidents(db, status="reviewed") == {"total": 0, "items": []}
    assert tools.search_guidance(db, "port closure")["evidence_gap"] is True
    assert tools.get_investigation(db, 5) == {"error": "investigation not found"}
    assert tools.model_info(db, "risk") == {"task": "risk"}


def test_t1_tools_are_bindable_and_read_only():
    names = {t.name for t in tools.TOOLS}
    assert names == {"get_order", "search_orders", "risk_summary", "search_incidents", "classify_text",
                     "search_guidance", "get_investigation", "model_info"}
    assert tools.TOOLS[0].args_schema.model_json_schema()["required"] == ["order_id"]

# --- G1 ---

# --- G3 ---

# --- X1 ---
