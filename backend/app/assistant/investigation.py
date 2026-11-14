"""Investigation graph: intake → intelligence → knowledge → planning → validator, then approval and a cited report."""
import asyncio
import logging
import time
from collections.abc import AsyncIterator, Callable
from datetime import UTC, datetime
from typing import TypedDict

from fastapi import BackgroundTasks, HTTPException
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.assistant import llm, rules, validator
from app.assistant import schemas as out
from app.assistant.models import Investigation, InvestigationAction, InvestigationStep
from app.core.auth import record_audit
from app.core.db import SessionLocal
from app.core.jobs import start_job
from app.core.models import User
from app.knowledge import search
from app.signals import incidents, orders
from app.signals.schemas import OrderFilter, RiskSummary

log = logging.getLogger("investigation")

MAX_ATTEMPTS = 2
POLL_SECONDS = 0.5
ROLE_RANK = {"analyst": 0, "supervisor": 1, "admin": 2}
NO_GUIDANCE = "No guidance found for this incident."
EMPTY_RISK = RiskSummary(total=0, high=0, medium=0, low=0, mean_score=None, by_shipping_mode=[])
DISCLAIMER = (
    "AI-assisted draft. Findings and rationales were written by a language model and checked by code for citations, "
    "numbers and eligible actions. Team-authored SOPs are illustrative. The scope was selected by the analyst: the "
    "incident is not linked to orders by data, so no order delay is attributed to it. Every action was decided by a "
    "person."
)


class State(TypedDict, total=False):
    investigation_id: int
    incident_id: int
    scope: dict
    incident: dict
    stop: str | None  # "not_humanitarian" or "needs_review" ends the run at intake
    risk: dict | None
    gaps: dict[str, str]
    findings: str
    guidance: dict
    guidance_summary: str
    citations: list[str]  # keys cited in guidance_summary; the UI shows them as badges
    rules: list[dict]
    plan: list[dict]
    errors: list[str]
    attempts: int
    degraded: bool


class Findings(BaseModel):
    summary: str


class GuidanceSummary(BaseModel):
    summary: str


class RankedAction(BaseModel):
    rule_code: str
    rationale: str


class Plan(BaseModel):
    actions: list[RankedAction]


def intake(db: Session, state: State) -> dict:
    incident = incidents.get_incident(db, state["incident_id"])
    category = incident.reviewed_label or incident.predicted_label
    facts = {"id": incident.id, "text": incident.text, "category": category, "status": incident.status,
             "confidence": incident.confidence}
    if incident.status in ("pool", "needs_review") or not category:
        return {"incident": facts, "stop": "needs_review"}
    if category == "not_humanitarian":
        return {"incident": facts, "stop": "not_humanitarian"}
    try:
        risk = orders.risk_summary(db, OrderFilter.model_validate(state["scope"])).model_dump(mode="json")
        gaps = {}
    except Exception as exc:  # noqa: BLE001  (a tool error is a gap, not a failed run)
        db.rollback()
        risk, gaps = None, {"orders": f"Order risk data unavailable ({type(exc).__name__})."}
    return {"incident": facts, "stop": None, "risk": risk, "gaps": gaps}


def intelligence(db: Session, state: State) -> dict:
    prompt = (f"Incident ({state['incident']['category']}): {state['incident']['text']}\n"
              f"Order risk in the analyst-selected scope: {state['risk'] or 'unavailable'}")
    try:
        answer = ask(db, state, Findings, "Summarise what this incident means for the orders in scope in two or "
                     "three sentences. Use only numbers given here. The scope is not linked to the incident by data: "
                     "never say the incident caused a delay of a specific order.", prompt)
        return {"findings": answer.summary}
    except llm.LLMError:
        return {"findings": findings_template(state), "degraded": True}


def knowledge(db: Session, state: State) -> dict:
    # Phrased as a question: the evidence-gap threshold was tuned on questions, and a bare tweet scores lower.
    query = f"What should we do about a {state['incident']['category'].replace('_', ' ')} incident: " \
            f"{state['incident']['text']}"
    try:
        result = search.search(db, query)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        gaps = {**state["gaps"], "guidance": f"Guidance search failed ({type(exc).__name__})."}
        return {"guidance": {"query": query, "chunks": [], "evidence_gap": True}, "guidance_summary": NO_GUIDANCE,
                "gaps": gaps}
    guidance = {"query": query, "chunks": [chunk.model_dump(mode="json") for chunk in result.chunks],
                "evidence_gap": result.evidence_gap, "best_score": result.best_score}
    found = {"guidance": guidance}
    if result.evidence_gap or not result.chunks:
        return {**found, "guidance_summary": NO_GUIDANCE}
    excerpts = "\n\n".join(f"[{c['citation_key']}] {c['document_title']}: {c['text']}" for c in guidance["chunks"])
    try:
        answer = ask(db, state, GuidanceSummary, "Summarise what the guidance says to do for this "
                     "incident in up to four sentences. Cite every claim with its key in brackets, like [SOP-01#2]. "
                     "Use only the excerpts given.", f"Incident: {state['incident']['text']}\n\n{excerpts}")
        return {**found, "guidance_summary": answer.summary}
    except llm.LLMError:
        return {**found, "guidance_summary": guidance_template(guidance), "degraded": True}


def planning(db: Session, state: State) -> dict:
    summary = RiskSummary.model_validate(state["risk"]) if state["risk"] else EMPTY_RISK
    results = [r.model_dump(mode="json") for r in rules.check(db, state["incident"]["category"], summary,
                                                               state["guidance"]["evidence_gap"])]
    eligible = [r for r in results if r["eligible"]]
    if not eligible:
        return {"rules": results, "plan": []}
    options = "\n".join(f"- {r['rule_code']}: {r['name']} (cost ${r['cost_usd']:,.0f})" for r in eligible)
    try:
        answer = ask(db, state, Plan, "Rank the eligible actions, most useful first, with a one-sentence rationale "
                     "each. Use only the listed codes and only numbers given here.",
                     f"Findings: {state['findings']}\nGuidance: {state['guidance_summary']}\nEligible:\n{options}")
        return {"rules": results, "plan": [a.model_dump() for a in answer.actions]}
    except llm.LLMError:
        return {"rules": results, "plan": plan_template(results), "degraded": True}


def check_output(db: Session, state: State) -> dict:
    """Code check of everything the LLM wrote; after the last attempt the templates replace it."""
    text = "\n".join([state["findings"], state["guidance_summary"], *(a["rationale"] for a in state["plan"])])
    errors = validator.validate(text, citation_keys(state), tool_outputs(state), eligible_codes(state),
                                [a["rule_code"] for a in state["plan"]])
    attempts = state["attempts"] + 1
    if errors and attempts >= MAX_ATTEMPTS:
        return {"errors": errors, "attempts": attempts, "degraded": True, "findings": findings_template(state),
                "guidance_summary": guidance_template(state["guidance"]), "plan": plan_template(state["rules"])}
    return {"errors": errors, "attempts": attempts}


def ask(db: Session, state: State, schema: type[BaseModel], instructions: str, content: str) -> BaseModel:
    messages = [("system", instructions), ("human", content)]
    if state["errors"]:
        messages.append(("human", "Your previous answer was rejected: " + "; ".join(state["errors"])))
    return llm.complete(db, messages, schema)


def findings_template(state: State) -> str:
    category = state["incident"]["category"]
    risk = state["risk"]
    if not risk:
        return f"Incident classified as {category}. Order risk data for the selected scope is unavailable."
    return (f"Incident classified as {category}. The analyst-selected scope holds {risk['total']} orders: "
            f"{risk['high']} high, {risk['medium']} medium and {risk['low']} low risk.")


def guidance_template(guidance: dict) -> str:
    if guidance["evidence_gap"] or not guidance["chunks"]:
        return NO_GUIDANCE
    return "Relevant guidance: " + "; ".join(f"{c['document_title']} [{c['citation_key']}]" for c in guidance["chunks"])


def plan_template(results: list[dict]) -> list[dict]:
    return [{"rule_code": r["rule_code"], "rationale": r["reason"]} for r in results if r["eligible"]]


def citation_keys(state: State) -> set[str]:
    return {chunk["citation_key"] for chunk in state["guidance"]["chunks"]}


def eligible_codes(state: State) -> set[str]:
    return {r["rule_code"] for r in state["rules"] if r["eligible"]}


def tool_outputs(state: State) -> list[dict]:
    return [state["incident"], state["scope"], state.get("risk") or {}, state["guidance"], {"rules": state["rules"]}]


def recorded(name: str, node: Callable[[Session, State], dict]) -> Callable:
    """Runs a node with the run's session and writes its investigation_steps row."""
    def call(state: State, config: RunnableConfig) -> dict:
        db = config["configurable"]["db"]
        started = time.perf_counter()
        try:
            result = node(db, state)
        except Exception as exc:
            db.rollback()
            save_step(db, state["investigation_id"], name, started, None, f"{type(exc).__name__}: {exc}")
            raise
        save_step(db, state["investigation_id"], name, started, result, None)
        return result

    return call


def save_step(db: Session, investigation_id: int, node: str, started: float, output: dict | None, error: str | None):
    db.add(InvestigationStep(investigation_id=investigation_id, node=node, status="error" if error else "ok",
                             output=output, error=error, duration_ms=round((time.perf_counter() - started) * 1000)))
    db.commit()


def build_graph():
    graph = StateGraph(State)
    nodes = {"intake": intake, "intelligence": intelligence, "knowledge": knowledge, "planning": planning,
             "validator": check_output}
    for name, node in nodes.items():
        graph.add_node(name, recorded(name, node))
    graph.add_edge(START, "intake")
    graph.add_conditional_edges("intake", lambda state: END if state["stop"] else "intelligence")
    graph.add_edge("intelligence", "knowledge")
    graph.add_edge("knowledge", "planning")
    graph.add_edge("planning", "validator")
    graph.add_conditional_edges("validator", lambda state: "intelligence" if state["errors"] and
                                state["attempts"] < MAX_ATTEMPTS else END)
    return graph.compile()


GRAPH = build_graph()


def start(db: Session, background: BackgroundTasks, incident_id: int, scope: dict, user: User) -> Investigation:
    if not incidents.get_incident(db, incident_id):
        raise HTTPException(404, "Incident not found")
    investigation = Investigation(incident_id=incident_id, scope=scope, created_by=user.id, state={})
    db.add(investigation)
    db.flush()
    record_audit(db, user, "start", "investigation", investigation.id, {"incident_id": incident_id, "scope": scope})
    db.commit()
    background.add_task(run, investigation.id)
    return investigation


def run(investigation_id: int) -> None:
    with SessionLocal() as db:
        investigation = db.get(Investigation, investigation_id)
        initial = {"investigation_id": investigation.id, "incident_id": investigation.incident_id,
                   "scope": investigation.scope, "gaps": {}, "errors": [], "attempts": 0, "degraded": False}
        try:
            state = GRAPH.invoke(initial, {"configurable": {"db": db}})
        except Exception as exc:  # the failing step row already holds the error
            log.exception("investigation %s failed", investigation_id)
            db.rollback()
            investigation.status, investigation.state = "failed", {**initial, "error": str(exc)}
            db.commit()
            return
        if state["stop"]:
            investigation.status = "closed"
        else:
            state["citations"] = list(dict.fromkeys(validator.CITATION.findall(state["guidance_summary"])))
            save_actions(db, investigation_id, state)
            # Nothing to approve: go straight to the report.
            investigation.status = "awaiting_approval" if eligible_codes(state) else "reporting"
        investigation.state, investigation.degraded = state, state["degraded"]
        db.commit()
        if investigation.status == "reporting":
            write_report(db, investigation_id)


def save_actions(db: Session, investigation_id: int, state: State) -> None:
    ranked = {a["rule_code"]: (rank, a["rationale"]) for rank, a in enumerate(state["plan"], start=1)}
    for result in state["rules"]:
        rank, rationale = ranked.get(result["rule_code"], (None, None))
        db.add(InvestigationAction(investigation_id=investigation_id, rule_code=result["rule_code"],
                                   name=result["name"], eligible=result["eligible"], reason=result["reason"],
                                   rank=rank, rationale=rationale))


def decide(db: Session, investigation_id: int, action_id: int, decision: str, user: User,
           background: BackgroundTasks) -> InvestigationAction | None:
    action = db.get(InvestigationAction, action_id)
    if not action or action.investigation_id != investigation_id:
        return None
    investigation = db.get(Investigation, investigation_id)
    if investigation.status != "awaiting_approval" or not action.eligible or action.decision != "pending":
        raise HTTPException(409, "This action is not awaiting a decision")
    role = next(r["approval_role"] for r in investigation.state["rules"] if r["rule_code"] == action.rule_code)
    if ROLE_RANK[user.role] < ROLE_RANK[role]:
        raise HTTPException(403, f"This action needs {role} approval")
    action.decision, action.decided_by, action.decided_at = decision, user.id, datetime.now(UTC)
    record_audit(db, user, decision, "investigation_action", action.id,
                 {"investigation_id": investigation_id, "rule_code": action.rule_code})
    if not pending_actions(db, investigation_id):
        investigation.status = "reporting"
    db.commit()
    if investigation.status == "reporting":
        start_job(db, background, "report", write_report, investigation_id)
    return action


def pending_actions(db: Session, investigation_id: int) -> int:
    return db.scalar(select(func.count()).select_from(InvestigationAction).where(
        InvestigationAction.investigation_id == investigation_id, InvestigationAction.eligible,
        InvestigationAction.decision == "pending"))


def write_report(db: Session, investigation_id: int) -> dict:
    """Fixed-section Markdown report, checked by the validator again; runs as a job after the last decision."""
    investigation = db.get(Investigation, investigation_id)
    state = investigation.state
    actions = list(db.scalars(select(InvestigationAction).where(InvestigationAction.investigation_id ==
                                                                investigation_id).order_by(InvestigationAction.id)))
    report = render_report(investigation, actions)
    errors = validator.validate(report, citation_keys(state), tool_outputs(state), eligible_codes(state),
                                [a.rule_code for a in actions if a.decision == "approved"])
    if errors:
        report += "\n\n> Automatic checks flagged: " + "; ".join(errors)
        investigation.degraded = True
    investigation.report, investigation.status = report, "completed"
    db.commit()
    return {"investigation_id": investigation_id, "errors": errors}


def render_report(investigation: Investigation, actions: list[InvestigationAction]) -> str:
    state = investigation.state
    incident, scope = state["incident"], state["scope"]
    chosen = sorted((a for a in actions if a.eligible), key=lambda a: (a.rank is None, a.rank or 0))
    lines = [
        f"# Investigation report #{investigation.id}", "",
        "## Incident", f"> {incident['text']}", "", f"Category: {incident['category']}.", "",
        "## Scope", "Analyst-selected, not linked by data: "
        + (", ".join(f"{key} = {value}" for key, value in scope.items() if value) or "all orders") + ".", "",
        "## Findings", state["findings"], "",
        "## Guidance", state["guidance_summary"], "",
        *(f"- [{c['citation_key']}] {c['document_title']}" for c in state["guidance"]["chunks"]), "",
        "## Decisions",
        *(f"- **{a.name}**: {a.decision}. {a.rationale or a.reason}" for a in chosen),
        "", "## Actions rejected by rules",
        *([f"- {a.name}: {a.reason}" for a in actions if not a.eligible] or ["- None"]),
        "", "## Gaps", *([f"- {gap}" for gap in state["gaps"].values()] or ["- None"]),
        "", "---", f"*{DISCLAIMER}*",
    ]
    return "\n".join(lines)


async def stream_steps(investigation_id: int) -> AsyncIterator[str]:
    """Sends each new step row as it is written, then `done` once the run has left `running`."""
    last_id = 0
    while True:
        with SessionLocal() as db:
            investigation = db.get(Investigation, investigation_id)
            steps = list(db.scalars(select(InvestigationStep).where(
                InvestigationStep.investigation_id == investigation_id, InvestigationStep.id > last_id)
                .order_by(InvestigationStep.id)))
        for step in steps:
            last_id = step.id
            yield f"data: {out.Step.model_validate(step).model_dump_json()}\n\n"
        if not investigation or investigation.status != "running":
            break
        await asyncio.sleep(POLL_SECONDS)
    yield 'data: {"type": "done"}\n\n'


def get_investigation(db: Session, investigation_id: int) -> dict | None:
    investigation = db.get(Investigation, investigation_id)
    if not investigation:
        return None
    steps = db.scalars(select(InvestigationStep).where(InvestigationStep.investigation_id == investigation_id)
                       .order_by(InvestigationStep.id))
    actions = db.scalars(select(InvestigationAction).where(InvestigationAction.investigation_id == investigation_id)
                         .order_by(InvestigationAction.rank.is_(None), InvestigationAction.rank,
                                   InvestigationAction.id))
    detail = {**out.Investigation.model_validate(investigation).model_dump(), "state": investigation.state,
              "incident": incidents.get_incident(db, investigation.incident_id), "steps": list(steps),
              "actions": list(actions), "report": investigation.report}
    return out.InvestigationDetail.model_validate(detail, from_attributes=True).model_dump(mode="json")


def list_investigations(db: Session) -> list[Investigation]:
    return list(db.scalars(select(Investigation).order_by(Investigation.id.desc())))


def investigation_stats(db: Session) -> dict:
    by_status = db.execute(select(Investigation.status, func.count()).group_by(Investigation.status))
    return {"by_status": dict(by_status.all())}


def fail_stale_runs(db: Session) -> int:
    """At startup no run can still be alive: background tasks die with the process."""
    result = db.execute(update(Investigation).where(Investigation.status.in_(("running", "reporting")))
                        .values(status="failed"))
    db.commit()
    log.info("investigations: %d stale runs marked failed", result.rowcount)
    return result.rowcount
