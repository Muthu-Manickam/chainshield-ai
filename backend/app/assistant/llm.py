import hashlib
import json
from collections.abc import Callable

from langchain_core.messages import AIMessage, convert_to_messages
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.assistant.models import LlmCache
from app.core.config import settings


class LLMError(Exception):
    pass


def complete(db: Session, messages: list, schema: type[BaseModel]) -> BaseModel:
    def call(chat: ChatOpenAI) -> tuple[AIMessage, dict]:
        result = chat.with_structured_output(schema, include_raw=True).invoke(messages)
        if result["parsing_error"] or result["parsed"] is None:
            raise LLMError(f"unparseable output: {result['parsing_error']}")
        return result["raw"], result["parsed"].model_dump(mode="json")

    response = _cached_call(db, _request_hash(messages, schema.model_json_schema()), call)
    return schema.model_validate(response)


def complete_with_tools(db: Session, messages: list, tools: list) -> AIMessage:
    def call(chat: ChatOpenAI) -> tuple[AIMessage, dict]:
        message = chat.bind_tools(tools).invoke(messages)
        return message, message.model_dump(mode="json")

    specs = [convert_to_openai_tool(tool) for tool in tools]
    return AIMessage.model_validate(_cached_call(db, _request_hash(messages, specs), call))


def _request_hash(messages: list, schema) -> str:
    dumped = [message.model_dump(mode="json", exclude={"id"}) for message in convert_to_messages(messages)]
    payload = json.dumps([settings.llm_model, dumped, schema], sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def _cached_call(db: Session, key: str, call: Callable[[ChatOpenAI], tuple[AIMessage, dict]]) -> dict:
    cached = db.scalar(select(LlmCache).where(LlmCache.request_hash == key))
    if cached:
        return cached.response
    if settings.llm_mode == "replay":
        raise LLMError("no cached response (LLM_MODE=replay)")
    spent = db.scalar(select(func.coalesce(func.sum(LlmCache.cost_usd), 0.0)))
    if spent >= settings.llm_budget_usd:
        raise LLMError(f"LLM budget of ${settings.llm_budget_usd} reached")

    error = None
    # Primary model, one retry, then the fallback model.
    for model in (settings.llm_model, settings.llm_model, settings.llm_fallback_model):
        try:
            raw, response = call(_chat(model))
        except Exception as exc:  # noqa: BLE001 - any provider or parse failure moves to the next attempt
            error = exc
            continue
        cost = raw.response_metadata.get("token_usage", {}).get("cost") or 0.0
        db.add(LlmCache(request_hash=key, model=model, response=response, cost_usd=cost))
        db.commit()
        return response
    raise LLMError(f"LLM call failed: {error}") from error


def _chat(model: str) -> ChatOpenAI:
    callbacks = []
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        from langfuse.langchain import CallbackHandler

        callbacks.append(CallbackHandler())
    # Reasoning models return empty content below ~500 max_tokens and reject temperature.
    return ChatOpenAI(
        model=model,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        max_tokens=1000,
        use_responses_api=False,
        extra_body={"reasoning": {"effort": "low"}, "usage": {"include": True}},
        callbacks=callbacks,
    )
