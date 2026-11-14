from pgvector.sqlalchemy import Vector
from sqlalchemy import Computed, ForeignKey, Index
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Document(Base):
    __tablename__ = "documents"
    code: Mapped[str] = mapped_column(unique=True)
    title: Mapped[str]
    origin: Mapped[str]
    content_hash: Mapped[str]
    status: Mapped[str] = mapped_column(default="processing")
    chunk_count: Mapped[int] = mapped_column(default=0)


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        Index("ix_chunks_tsv", "tsv", postgresql_using="gin"),
        Index("ix_chunks_embedding", "embedding", postgresql_using="hnsw",
              postgresql_ops={"embedding": "vector_cosine_ops"}),
    )
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    n: Mapped[int]
    citation_key: Mapped[str] = mapped_column(unique=True)
    section: Mapped[str | None]
    text: Mapped[str]
    tsv: Mapped[str] = mapped_column(TSVECTOR, Computed("to_tsvector('english', text)", persisted=True))
    embedding: Mapped[list[float]] = mapped_column(Vector(384))
