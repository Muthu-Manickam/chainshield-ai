from langchain_core.messages import AIMessage
from pydantic import BaseModel
from sqlalchemy.orm import Session


class LLMError(Exception):
    pass


def complete(db: Session, messages: list, schema: type[BaseModel]) -> BaseModel:
    raise LLMError("LLM client not implemented")  # STUB


def complete_with_tools(db: Session, messages: list, tools: list) -> AIMessage:
    raise LLMError("LLM client not implemented")  # STUB
