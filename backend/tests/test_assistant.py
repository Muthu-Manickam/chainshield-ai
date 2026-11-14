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
import asyncio

from app.assistant import investigation
from app.assistant.models import Investigation as G1Investigation
from app.assistant.schemas import RuleResult as G1Rule
from app.knowledge.schemas import Chunk as G1Chunk
from app.knowledge.schemas import SearchResult as G1Search
from app.signals.models import Incident as G1Incident

G1_RULES = [
    G1Rule(rule_code="REROUTE", name="Reroute", eligible=True, reason="All conditions met",
           approval_role="supervisor", cost_usd=500),
    G1Rule(rule_code="HOLD", name="Hold shipment", eligible=True, reason="All conditions met",
           approval_role="admin", cost_usd=10000),
    G1Rule(rule_code="PORT", name="Alternate port", eligible=False, reason="Needs at least 20 high-risk orders",
           approval_role="supervisor", cost_usd=2000),
]
G1_GOOD = {
    investigation.Findings: investigation.Findings(summary="12 of the 40 orders in scope are high risk."),
    investigation.GuidanceSummary: investigation.GuidanceSummary(summary="Reroute away from closed roads [SOP-01#2]."),
    investigation.Plan: investigation.Plan(actions=[investigation.RankedAction(rule_code="REROUTE",
                                                                               rationale="12 orders are high risk.")]),
}


def _g1_setup(db, monkeypatch, label="infrastructure", status="classified", answers=G1_GOOD) -> int:
    """One incident and fake services; `answers` maps an LLM schema to its reply (an exception is raised)."""
    incident = G1Incident(text="Bridge collapsed on the main highway", source="pool", status=status,
                          predicted_label=label, confidence=0.9)
    db.add(incident)
    db.commit()
    monkeypatch.setattr(investigation.incidents, "get_incident", lambda db, incident_id: db.get(G1Incident,
                                                                                                incident_id))
    monkeypatch.setattr(investigation.orders, "risk_summary", lambda db, filters: G2Summary(
        total=40, high=12, medium=18, low=10, mean_score=0.55, by_shipping_mode=[]))
    monkeypatch.setattr(investigation.search, "search", lambda db, query, k=5: G1Search(chunks=[G1Chunk(
        citation_key="SOP-01#2", document_title="Road closure SOP", section="Steps", text="Reroute.", score=0.8)],
        evidence_gap=False, best_score=0.8))
    monkeypatch.setattr(investigation.rules, "check", lambda db, category, summary, gap: G1_RULES)

    def complete(db, messages, schema):
        if isinstance(answers, Exception):
            raise answers
        return answers[schema]

    monkeypatch.setattr(investigation.llm, "complete", complete)
    return incident.id


def _g1_start(client, incident_id) -> dict:
    response = client.post("/api/investigations", json={"incident_id": incident_id,
                                                        "scope": {"market": "LATAM", "shipping_mode": None}})
    assert response.status_code == 200, response.text
    return client.get(f"/api/investigations/{response.json()['id']}").json()


def test_g1_run_ends_awaiting_approval_with_steps_actions_and_stream(client, db, monkeypatch):
    login_as(client, "analyst")
    detail = _g1_start(client, _g1_setup(db, monkeypatch))
    assert detail["status"] == "awaiting_approval" and detail["degraded"] is False
    assert [s["node"] for s in detail["steps"]] == ["intake", "intelligence", "knowledge", "planning", "validator"]
    assert detail["state"]["findings"] == "12 of the 40 orders in scope are high risk."
    actions = {a["rule_code"]: a for a in detail["actions"]}
    assert actions["REROUTE"]["rank"] == 1 and actions["HOLD"]["rank"] is None
    assert actions["PORT"]["eligible"] is False and actions["PORT"]["reason"].startswith("Needs")

    async def collect():
        return [event async for event in investigation.stream_steps(detail["id"])]

    events = asyncio.run(collect())
    assert len(events) == 6 and events[-1] == 'data: {"type": "done"}\n\n'


def test_g1_validator_failure_retries_once_then_uses_templates(client, db, monkeypatch):
    bad = {**G1_GOOD, investigation.Findings: investigation.Findings(summary="99 orders will be late.")}
    login_as(client, "analyst")
    detail = _g1_start(client, _g1_setup(db, monkeypatch, answers=bad))
    assert detail["status"] == "awaiting_approval" and detail["degraded"] is True
    assert [s["node"] for s in detail["steps"]].count("validator") == 2
    assert detail["state"]["findings"].startswith("Incident classified as infrastructure")


def test_g1_llm_error_degrades_to_templates(client, db, monkeypatch):
    login_as(client, "analyst")
    detail = _g1_start(client, _g1_setup(db, monkeypatch, answers=llm.LLMError("no cache")))
    assert detail["status"] == "awaiting_approval" and detail["degraded"] is True
    assert detail["state"]["guidance_summary"] == "Relevant guidance: Road closure SOP [SOP-01#2]"
    assert len(detail["steps"]) == 5


@pytest.mark.parametrize(("label", "status"), [("not_humanitarian", "classified"), ("infrastructure",
                                                                                     "needs_review")])
def test_g1_intake_closes_not_humanitarian_and_unreviewed(client, db, monkeypatch, label, status):
    login_as(client, "analyst")
    detail = _g1_start(client, _g1_setup(db, monkeypatch, label=label, status=status))
    assert detail["status"] == "closed" and [s["node"] for s in detail["steps"]] == ["intake"]
    assert detail["actions"] == []


def test_g1_tool_error_is_a_gap(client, db, monkeypatch):
    incident_id = _g1_setup(db, monkeypatch)

    def broken(db, query, k=5):
        raise RuntimeError("search down")

    monkeypatch.setattr(investigation.search, "search", broken)
    login_as(client, "analyst")
    detail = _g1_start(client, incident_id)
    assert detail["status"] == "awaiting_approval"
    assert detail["state"]["gaps"] == {"guidance": "Guidance search failed (RuntimeError)."}
    assert detail["state"]["guidance_summary"] == investigation.NO_GUIDANCE


def test_g1_decisions_check_roles_then_write_a_validated_report(client, db, monkeypatch):
    login_as(client, "analyst")
    detail = _g1_start(client, _g1_setup(db, monkeypatch))
    actions = {a["rule_code"]: a["id"] for a in detail["actions"]}
    url = f"/api/investigations/{detail['id']}/actions/{{}}/decision"
    assert client.post(url.format(actions["REROUTE"]), json={"decision": "approved"}).status_code == 403
    login_as(client, "supervisor")
    assert client.post(url.format(actions["REROUTE"]), json={"decision": "approved"}).status_code == 200
    assert client.post(url.format(actions["REROUTE"]), json={"decision": "rejected"}).status_code == 409
    assert client.post(url.format(actions["PORT"]), json={"decision": "approved"}).status_code == 409
    assert client.post(url.format(actions["HOLD"]), json={"decision": "approved"}).status_code == 403
    login_as(client, "admin")
    assert client.post(url.format(actions["HOLD"]), json={"decision": "rejected"}).status_code == 200
    detail = client.get(f"/api/investigations/{detail['id']}").json()
    assert detail["status"] == "completed" and detail["degraded"] is False
    report = detail["report"]
    assert "[SOP-01#2]" in report and "**Reroute**: approved" in report and "**Hold shipment**: rejected" in report
    assert "Alternate port: Needs at least 20" in report and investigation.DISCLAIMER in report
    assert "Automatic checks flagged" not in report
    assert {row.action for row in db.query(AuditLog) if row.entity != "user"} == {"start", "approved", "rejected"}
    assert client.get("/api/investigations/stats").json()["by_status"] == {"completed": 1}


def test_g1_fail_stale_runs(client, db, monkeypatch):
    incident_id = _g1_setup(db, monkeypatch)
    db.add_all([G1Investigation(incident_id=incident_id, scope={}, status=status)
                for status in ("running", "reporting", "awaiting_approval")])
    db.commit()
    assert investigation.fail_stale_runs(db) == 2
    assert sorted(i.status for i in db.query(G1Investigation)) == ["awaiting_approval", "failed", "failed"]

# --- G3 ---
from langchain_core.tools import StructuredTool

from app.assistant import chat
from app.assistant.models import ChatMessage as ChatRow


class G3Args(BaseModel):
    market: str | None = None


G3_TOOL = StructuredTool(name="risk_summary", description="risk", args_schema=G3Args,
                         func=lambda db, market=None: {"total": 40, "high": 12})


def _g3_call(n: int = 0) -> AIMessage:
    return AIMessage("", tool_calls=[{"name": "risk_summary", "args": {"market": "LATAM"}, "id": f"c{n}"}])


def _g3_chat(client, monkeypatch, replies, session_id=None) -> list[dict]:
    """Posts a message with the LLM replaying `replies` (the last one repeats); returns the SSE events."""
    replies = list(replies)
    monkeypatch.setattr(chat.tools, "TOOLS", [G3_TOOL])
    monkeypatch.setattr(chat.llm, "complete_with_tools",
                        lambda db, messages, tools: (replies.pop(0) if len(replies) > 1 else replies[0])
                        .model_copy(update={"id": None}))
    response = client.post("/api/chat", json={"session_id": session_id, "message": "How many high-risk orders?"})
    assert response.status_code == 200, response.text
    return [json.loads(line[6:]) for line in response.text.split("\n\n") if line]


def test_g3_answers_after_tool_events_and_stores_both_messages(client, db, monkeypatch):
    login_as(client, "analyst")
    events = _g3_chat(client, monkeypatch, [_g3_call(), AIMessage("There are 12 high-risk orders out of 40.")])
    assert [e["type"] for e in events] == ["tool", "answer", "done"]
    assert events[0] == {"type": "tool", "name": "risk_summary", "content": '{"market": "LATAM"}'}
    assert events[1]["content"] == "There are 12 high-risk orders out of 40." and events[1]["degraded"] is False
    history = client.get(f"/api/chat/{events[-1]['content']}").json()
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert history[1]["tool_calls"] == [{"name": "risk_summary", "args": {"market": "LATAM"}}]


def test_g3_regenerates_once_then_returns_raw_table(client, monkeypatch):
    login_as(client, "analyst")
    events = _g3_chat(client, monkeypatch, [_g3_call(), AIMessage("There are 15 orders."), AIMessage("12 of 40.")])
    assert events[1] == {"type": "answer", "content": "12 of 40.", "citations": [], "degraded": False}
    events = _g3_chat(client, monkeypatch, [_g3_call(), AIMessage("There are 15 orders."), AIMessage("Still 15.")])
    assert events[1]["degraded"] is True and "| 40 | 12 |" in events[1]["content"]


def test_g3_caps_tool_calls_and_says_dont_know_without_data(client, db, monkeypatch):
    login_as(client, "analyst")
    events = _g3_chat(client, monkeypatch, [_g3_call()])
    assert [e["type"] for e in events].count("tool") == chat.MAX_TOOL_CALLS
    assert events[-2]["degraded"] is True
    events = _g3_chat(client, monkeypatch, [AIMessage("Probably 30.")])
    assert events[0]["content"] == chat.DONT_KNOW


def test_g3_llm_error_and_foreign_session(client, db, monkeypatch):
    login_as(client, "analyst")

    def fail(db, messages, tools):
        raise llm.LLMError("no cached response")

    monkeypatch.setattr(chat.llm, "complete_with_tools", fail)
    response = client.post("/api/chat", json={"message": "hi"})
    assert '"type":"error"' in response.text and response.text.endswith('"}\n\n')
    session_id = db.query(ChatRow).one().session_id
    login_as(client, "supervisor")
    assert client.post("/api/chat", json={"session_id": session_id, "message": "hi"}).status_code == 404

# --- X1 ---
from datetime import UTC

from app.signals.models import Order as X1Order


def _x1_world(db, monkeypatch) -> int:
    """Real rules, incident and orders; only guidance search and the LLM are scripted."""
    seed_action_rules(db)
    incident = G1Incident(text="Port closed after the storm", source="pool", status="classified",
                          predicted_label="infrastructure", confidence=0.9)
    db.add(incident)
    db.add_all(X1Order(order_id=n, order_date=datetime(2017, 1, 1, tzinfo=UTC), market="LATAM",
                       order_region="South America", shipping_mode="Standard Class", customer_segment="Consumer",
                       order_total=100.0, item_count=1, features={}, block="s1", risk_score=0.9, risk_band="high")
               for n in range(1, 7))
    db.commit()
    monkeypatch.setattr(investigation.search, "search", lambda db, query, k=5: G1Search(chunks=[G1Chunk(
        citation_key="SOP-03#1", document_title="Port closure SOP", section="Steps", text="Divert.", score=0.8)],
        evidence_gap=False, best_score=0.8))

    def complete(db, messages, schema):
        if schema is investigation.Plan:
            codes = [line[2:].split(":")[0] for line in messages[1][1].splitlines() if line.startswith("- ")]
            return investigation.Plan(actions=[investigation.RankedAction(rule_code=c, rationale="Fits the scope.")
                                               for c in codes])
        summary = "6 of 6 orders in scope are high risk." if schema is investigation.Findings else \
            "Check the port status and divert if needed [SOP-03#1]."
        return schema(summary=summary)

    monkeypatch.setattr(investigation.llm, "complete", complete)
    return incident.id


def test_x1_combined_journey_start_approve_reject_report(client, db, monkeypatch):
    incident_id = _x1_world(db, monkeypatch)
    login_as(client, "analyst")
    started = client.post("/api/investigations", json={
        "incident_id": incident_id, "scope": {"market": "LATAM", "shipping_mode": "Standard Class"}}).json()
    detail = client.get(f"/api/investigations/{started['id']}").json()
    assert detail["status"] == "awaiting_approval" and detail["degraded"] is False
    assert detail["state"]["citations"] == ["SOP-03#1"] and "6 of 6" in detail["state"]["findings"]
    eligible = [a for a in detail["actions"] if a["eligible"]]
    assert {a["rule_code"] for a in eligible} == {r[0] for r in ACTION_RULES}

    login_as(client, "supervisor")
    url = f"/api/investigations/{detail['id']}/actions/{{}}/decision"
    for n, action in enumerate(eligible):
        decision = "approved" if n == 0 else "rejected"
        assert client.post(url.format(action["id"]), json={"decision": decision}).status_code == 200
    detail = client.get(f"/api/investigations/{detail['id']}").json()
    assert detail["status"] == "completed" and detail["degraded"] is False
    assert "[SOP-03#1]" in detail["report"] and investigation.DISCLAIMER in detail["report"]
    assert "Automatic checks flagged" not in detail["report"]
    assert client.get("/api/investigations/stats").json()["by_status"] == {"completed": 1}
