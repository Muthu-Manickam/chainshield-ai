# --- K1 ---
import re

from sqlalchemy import func, select

from app.core.config import settings
from app.knowledge import search
from app.knowledge.ingest import _sections, ingest_file
from app.knowledge.models import Chunk, Document
from app.seed import corpus_sources, seed_documents
from tests.conftest import login_as


def load_questions() -> list[tuple[str, str]]:
    text = (settings.guidance_dir / "questions.md").read_text()
    return re.findall(r"^\| \d+ \| (.+?) \| (.+?) \|$", text, re.MULTILINE)


def retrieval_eval(db) -> dict:
    """Recall@5 and MRR by document code on answerable questions; evidence-gap accuracy on all of them."""
    reciprocal_ranks, gap_correct, best_scores = [], 0, []
    for question, expected in load_questions():
        result = search.search(db, question)
        unanswerable = expected == "UNANSWERABLE"
        gap_correct += result.evidence_gap == unanswerable
        best_scores.append((result.best_score, unanswerable))
        if not unanswerable:
            codes = [chunk.citation_key.split("#")[0] for chunk in result.chunks]
            code = expected.split("#")[0]
            reciprocal_ranks.append(1 / (codes.index(code) + 1) if code in codes else 0)
    return {"recall_at_5": sum(rank > 0 for rank in reciprocal_ranks) / len(reciprocal_ranks),
            "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks),
            "gap_accuracy": gap_correct / len(best_scores), "best_scores": best_scores}


def test_seed_ingests_corpus_idempotently_and_search_meets_eval(db):
    seed_documents(db)
    assert db.scalar(select(func.count()).select_from(Document)) == len(corpus_sources()) == 18
    chunk_ids = db.scalars(select(Chunk.id).order_by(Chunk.id)).all()
    assert db.scalar(select(Chunk.citation_key).where(Chunk.n == 1, Chunk.document_id == 1)).endswith("#1")
    seed_documents(db)
    assert db.scalars(select(Chunk.id).order_by(Chunk.id)).all() == chunk_ids

    metrics = retrieval_eval(db)
    print({key: round(value, 3) for key, value in metrics.items() if key != "best_scores"})
    assert metrics["recall_at_5"] >= 0.85
    assert metrics["mrr"] >= 0.7
    assert metrics["gap_accuracy"] >= 0.85


def test_markdown_split_on_headings():
    sections = _sections(settings.guidance_dir / "sops" / "SOP-03.md")
    assert [heading for heading, _ in sections][:4] == [None, "SOP-03 Port Disruption and Alternate Port", "Purpose",
                                                        "Roles"]


def test_html_keeps_article_headings_only():
    headings = [heading for heading, _ in _sections(settings.data_dir / "corpus/public/PUB-07.html")]
    assert "Documentation" in headings and "Book Navigation" not in headings


def test_reingest_with_new_content_replaces_chunks(db, tmp_path):
    path = tmp_path / "x.md"
    path.write_text("## Alpha\nfirst text")
    ingest_file(db, path, "TST-01", "Test", "team-authored")
    path.write_text("## Beta\nsecond text\n## Gamma\nthird text")
    doc = ingest_file(db, path, "TST-01", "Test", "team-authored")
    assert doc.chunk_count == 2
    assert db.scalars(select(Chunk.section).order_by(Chunk.n)).all() == ["Beta", "Gamma"]


def test_search_route(client, db, tmp_path):
    path = tmp_path / "x.md"
    path.write_text("## Holds\nA supervisor approves holding a shipment worth over $10,000.")
    ingest_file(db, path, "TST-02", "Holds", "team-authored")
    login_as(client, "analyst")
    body = client.get("/api/knowledge/search", params={"q": "who approves holding a shipment?"}).json()
    assert body["chunks"][0]["citation_key"] == "TST-02#1"
    assert client.get("/api/knowledge/stats").json()["documents"] == 1
