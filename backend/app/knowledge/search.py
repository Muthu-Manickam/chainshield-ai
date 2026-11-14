from sqlalchemy.orm import Session

from app.knowledge.models import Document
from app.knowledge.schemas import SearchResult


def search(db: Session, query: str, k: int = 5) -> SearchResult:
    return SearchResult(chunks=[], evidence_gap=True, best_score=None)  # STUB


def list_documents(db: Session) -> list[Document]:
    return []  # STUB


def knowledge_stats(db: Session) -> dict:
    return {}  # STUB
