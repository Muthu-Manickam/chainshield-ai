from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.knowledge.ingest import embed
from app.knowledge.models import Chunk, Document
from app.knowledge.schemas import SearchResult

# bge-small expects this instruction on queries (not on passages).
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
# Best cosine below this means the corpus has nothing on the question; tuned on corpus/questions.md.
EVIDENCE_GAP_THRESHOLD = 0.67
RRF_K = 60

# Dense top 20 + keyword top 20 (any query term, so natural questions still match), fused by reciprocal rank.
HYBRID_SQL = text("""
WITH q AS (
    SELECT CAST(:embedding AS vector) AS e,
           CAST(replace(CAST(plainto_tsquery('english', :query) AS text), '&', '|') AS tsquery) AS t
), dense AS (
    SELECT id, row_number() OVER (ORDER BY distance) AS r
    FROM (SELECT c.id, c.embedding <=> q.e AS distance FROM chunks c, q ORDER BY distance LIMIT 20) d
), keyword AS (
    SELECT id, row_number() OVER (ORDER BY rank DESC) AS r
    FROM (SELECT c.id, ts_rank_cd(c.tsv, q.t) AS rank FROM chunks c, q WHERE c.tsv @@ q.t
          ORDER BY rank DESC LIMIT 20) k
), fused AS (
    SELECT id, sum(1.0 / (:rrf_k + r)) AS score FROM (SELECT * FROM dense UNION ALL SELECT * FROM keyword) u
    GROUP BY id
)
SELECT c.citation_key, d.title AS document_title, c.section, c.text, f.score,
       (SELECT 1 - min(c2.embedding <=> q.e) FROM chunks c2 JOIN dense USING (id)) AS best_score
FROM fused f JOIN chunks c USING (id) JOIN documents d ON d.id = c.document_id, q
ORDER BY f.score DESC
LIMIT :k
""")


def search(db: Session, query: str, k: int = 5) -> SearchResult:
    [embedding] = embed([QUERY_PREFIX + query])
    rows = db.execute(HYBRID_SQL, {"embedding": str(embedding), "query": query, "rrf_k": RRF_K, "k": k}).mappings().all()
    best = rows[0]["best_score"] if rows else None
    chunks = [{key: row[key] for key in ("citation_key", "document_title", "section", "text", "score")} for row in rows]
    return SearchResult(chunks=chunks, evidence_gap=best is None or best < EVIDENCE_GAP_THRESHOLD, best_score=best)


def list_documents(db: Session) -> list[Document]:
    return list(db.scalars(select(Document).order_by(Document.code)))


def knowledge_stats(db: Session) -> dict:
    by_origin = dict(db.execute(select(Document.origin, func.count()).group_by(Document.origin)).all())
    return {"documents": sum(by_origin.values()), "chunks": db.scalar(select(func.count()).select_from(Chunk)),
            "by_origin": by_origin}
