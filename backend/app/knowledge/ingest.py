from pathlib import Path

from sqlalchemy.orm import Session

from app.knowledge.models import Document


def ingest_file(db: Session, path: Path, code: str, title: str, origin: str) -> Document:
    raise NotImplementedError  # STUB


def embed(texts: list[str]) -> list[list[float]]:
    return []  # STUB
