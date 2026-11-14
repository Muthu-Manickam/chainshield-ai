from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.assistant.models import ChatMessage
from app.core.models import User


def answer(db: Session, user: User, session_id: str | None, message: str) -> Iterator[str]:
    yield 'data: {"type": "done"}\n\n'  # STUB


def history(db: Session, session_id: str) -> list[ChatMessage]:
    return []  # STUB
