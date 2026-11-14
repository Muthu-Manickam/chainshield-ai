from datetime import datetime

from app.core.schemas import Schema


class Document(Schema):
    id: int
    code: str
    title: str
    origin: str
    content_hash: str
    status: str
    chunk_count: int
    created_at: datetime


class Chunk(Schema):
    citation_key: str
    document_title: str
    section: str | None
    text: str
    score: float


class SearchResult(Schema):
    chunks: list[Chunk]
    evidence_gap: bool
    best_score: float | None
