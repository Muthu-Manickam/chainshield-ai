import json
import uuid
from collections.abc import Iterator
from typing import Annotated, TypedDict

from fastapi import HTTPException
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assistant import llm, tools, validator
from app.assistant.models import ChatMessage
from app.assistant.schemas import ChatEvent
from app.core.models import User

MAX_TOOL_CALLS = 4
SYSTEM = (
    "You are ChainShield's read-only operations assistant. Answer from tool results only, in a few sentences. "
    f"Use at most {MAX_TOOL_CALLS} tool calls. Cite guidance as [citation_key] using keys from search_guidance. "
    "Only state numbers that appear in tool results. Never propose, recommend or approve actions, and never "
    "claim an incident caused a specific order's delay. If the tools do not answer the question, say you don't know."
)
DONT_KNOW = "I don't know: none of ChainShield's tools returned data for this question."


class State(TypedDict):
    messages: Annotated[list, add_messages]
    calls: list[dict]  # {name, args, result} per executed tool call


def answer(db: Session, user: User, session_id: str | None, message: str) -> Iterator[str]:
    # Ownership is checked before streaming starts so the router can still return 404.
    if session_id and _owner(db, session_id) not in (None, user.id):
        raise HTTPException(404, "Chat session not found")
    return _answer(db, user, session_id or uuid.uuid4().hex, message)


def history(db: Session, session_id: str, user: User | None = None) -> list[ChatMessage]:
    if user and _owner(db, session_id) not in (None, user.id):
        raise HTTPException(404, "Chat session not found")
    return list(db.scalars(select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.id)))


def _owner(db: Session, session_id: str) -> int | None:
    return db.scalar(select(ChatMessage.user_id).where(ChatMessage.session_id == session_id).limit(1))


def _answer(db: Session, user: User, session_id: str, message: str) -> Iterator[str]:
    db.add(ChatMessage(session_id=session_id, user_id=user.id, role="user", content=message))
    db.commit()
    state = {"messages": [SystemMessage(SYSTEM), *_past_turns(db, session_id)], "calls": []}
    seen = 0
    try:
        for mode, chunk in _graph(db).stream(state, stream_mode=["updates", "values"]):
            if mode == "values":
                state = chunk
            elif "tools" in chunk:
                for call in chunk["tools"]["calls"][seen:]:
                    yield _event(type="tool", name=call["name"], content=json.dumps(call["args"]))
                seen = len(chunk["tools"]["calls"])
        text, citations, degraded = _final(db, state)
    except llm.LLMError as exc:
        yield _event(type="error", content=str(exc))
        yield _event(type="done", content=session_id)
        return
    db.add(ChatMessage(session_id=session_id, user_id=user.id, role="assistant", content=text,
                       tool_calls=[{"name": c["name"], "args": c["args"]} for c in state["calls"]],
                       citations=citations))
    db.commit()
    yield _event(type="answer", content=text, citations=citations, degraded=degraded)
    yield _event(type="done", content=session_id)


def _past_turns(db: Session, session_id: str) -> list:
    roles = {"user": HumanMessage, "assistant": AIMessage}
    return [roles[m.role](m.content) for m in history(db, session_id)]


def _graph(db: Session):
    def agent(state: State) -> dict:
        return {"messages": [llm.complete_with_tools(db, state["messages"], tools.TOOLS)]}

    def run_tools(state: State) -> dict:
        by_name = {tool.name: tool for tool in tools.TOOLS}
        messages, calls = [], list(state["calls"])
        for call in state["messages"][-1].tool_calls:
            if len(calls) >= MAX_TOOL_CALLS:
                result = {"error": "tool call limit reached"}
            elif call["name"] not in by_name:
                result = {"error": f"unknown tool {call['name']}"}
            else:
                try:
                    result = by_name[call["name"]].func(db, **call["args"])
                except Exception as exc:  # noqa: BLE001 - a failing tool is an evidence gap, not a crash
                    result = {"error": str(exc)}
                calls.append({"name": call["name"], "args": call["args"], "result": result})
            messages.append(ToolMessage(json.dumps(result, default=str), tool_call_id=call["id"]))
        return {"messages": messages, "calls": calls}

    def route(state: State) -> str:
        wants_tools = state["messages"][-1].tool_calls and len(state["calls"]) < MAX_TOOL_CALLS
        return "tools" if wants_tools else END

    graph = StateGraph(State)
    graph.add_node("agent", agent)
    graph.add_node("tools", run_tools)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route)
    graph.add_edge("tools", "agent")
    return graph.compile()


def _final(db: Session, state: dict) -> tuple[str, list, bool]:
    """Validated answer, one regeneration with the errors, then the raw tool results with degraded=true."""
    results = [c["result"] for c in state["calls"]]
    if not any(r and "error" not in r for r in results):
        return DONT_KNOW, [], False
    chunks = {c["citation_key"]: c for r in results for c in r.get("chunks", []) if "citation_key" in c}
    reply = state["messages"][-1]
    # Unanswered tool calls cannot be sent back to the model.
    messages = state["messages"][:-1] if reply.tool_calls else state["messages"]
    for attempt in range(2):
        errors = _check(reply, set(chunks), results)
        if not errors:
            cited = validator.CITATION.findall(reply.content)
            return reply.content, [chunks[key] for key in dict.fromkeys(cited)], False
        if attempt == 0:
            messages = [*messages, HumanMessage(
                "Your answer failed validation: " + "; ".join(errors) + ". Rewrite it without calling tools.")]
            reply = llm.complete_with_tools(db, messages, tools.TOOLS)
    return _table(state["calls"]), [], True


def _check(reply: AIMessage, citation_keys: set[str], results: list[dict]) -> list[str]:
    if reply.tool_calls or not isinstance(reply.content, str) or not reply.content.strip():
        return ["No final text answer"]
    return validator.validate(reply.content, citation_keys, results)


def _table(calls: list[dict]) -> str:
    sections = []
    for call in calls:
        result = call["result"]
        rows = result.get("items") or result.get("chunks") or [result]
        columns = list(dict.fromkeys(key for row in rows for key in row))
        lines = [f"**{call['name']}**", "", "| " + " | ".join(columns) + " |", "|" + " --- |" * len(columns)]
        lines += ["| " + " | ".join(_cell(row.get(col)) for col in columns) + " |" for row in rows]
        sections.append("\n".join(lines))
    return "I could not produce a verified answer. Raw tool results:\n\n" + "\n\n".join(sections)


def _cell(value) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text.replace("|", "\\|").replace("\n", " ")


def _event(**fields) -> str:
    return f"data: {ChatEvent(**fields).model_dump_json(exclude_none=True)}\n\n"
