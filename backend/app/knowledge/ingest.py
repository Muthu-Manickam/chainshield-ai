import hashlib
import re
from functools import cache
from html.parser import HTMLParser
from pathlib import Path
from typing import ClassVar

from pypdf import PdfReader
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.knowledge.models import Chunk, Document

MODEL_NAME = "BAAI/bge-small-en-v1.5"
CHUNK_WORDS = 260  # ~350 bge tokens
OVERLAP_WORDS = 40  # ~50 tokens


@cache
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME, device="cpu")


def embed(texts: list[str]) -> list[list[float]]:
    return _model().encode(texts, normalize_embeddings=True, batch_size=32).tolist()


class _ArticleText(HTMLParser):
    """Collects the text of <article>, turning h1-h4 into Markdown headings so the Markdown splitter applies."""

    BLOCKS = frozenset({"p", "li", "tr", "br", "div", "table", "ul", "ol"})
    HEADINGS: ClassVar[dict[str, str]] = {"h1": "#", "h2": "##", "h3": "###", "h4": "####"}
    SKIP = frozenset({"script", "style", "nav"})

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.in_article = 0
        self.skipping = 0

    def handle_starttag(self, tag, attrs):
        if tag == "article":
            self.in_article += 1
        elif tag in self.SKIP:
            self.skipping += 1
        elif tag in self.HEADINGS:
            self.parts.append(f"\n{self.HEADINGS[tag]} ")
        elif tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "article":
            self.in_article -= 1
        elif tag in self.SKIP:
            self.skipping -= 1
        elif tag in self.HEADINGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.in_article and not self.skipping:
            self.parts.append(data)


def _sections(path: Path) -> list[tuple[str | None, str]]:
    """(section heading, text) pairs. PDF sections are pages, Markdown and HTML sections are headings."""
    if path.suffix.lower() == ".pdf":
        return [(f"page {i}", page.extract_text() or "") for i, page in enumerate(PdfReader(path).pages, 1)]
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() in {".html", ".htm"}:
        parser = _ArticleText()
        parser.feed(text)
        text = "".join(parser.parts)
    sections, heading, lines = [], None, []
    for line in text.splitlines():
        match = re.match(r"#{1,4}\s+(.*\S)", line.strip())
        if match:
            sections.append((heading, "\n".join(lines)))
            heading, lines = match.group(1), []
        else:
            lines.append(line)
    sections.append((heading, "\n".join(lines)))
    return sections


def _chunks(path: Path) -> list[tuple[str | None, str]]:
    out = []
    for section, text in _sections(path):
        words = text.replace("\x00", " ").split()  # some PDFs extract NUL bytes, which Postgres text rejects
        for start in range(0, len(words), CHUNK_WORDS - OVERLAP_WORDS):
            out.append((section, " ".join(words[start:start + CHUNK_WORDS])))
            if start + CHUNK_WORDS >= len(words):
                break
    return out


def ingest_file(db: Session, path: Path, code: str, title: str, origin: str) -> Document:
    path = Path(path)
    content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    doc = db.scalar(select(Document).where(Document.code == code))
    if doc and doc.content_hash == content_hash and doc.status == "ready":
        return doc
    if doc:
        db.execute(delete(Chunk).where(Chunk.document_id == doc.id))
        doc.title, doc.origin, doc.content_hash, doc.status = title, origin, content_hash, "processing"
    else:
        doc = Document(code=code, title=title, origin=origin, content_hash=content_hash)
        db.add(doc)
    db.flush()
    chunks = _chunks(path)
    # The heading goes into the embedded text so short sections stay findable by topic.
    vectors = embed([f"{title}. {section or ''}\n{text}" for section, text in chunks])
    db.add_all(
        Chunk(document_id=doc.id, n=n, citation_key=f"{code}#{n}", section=section, text=text, embedding=vector)
        for n, ((section, text), vector) in enumerate(zip(chunks, vectors, strict=True), 1)
    )
    doc.status, doc.chunk_count = "ready", len(chunks)
    db.commit()
    return doc
