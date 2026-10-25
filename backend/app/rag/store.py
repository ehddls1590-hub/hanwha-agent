from __future__ import annotations

import re

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.logging import get_logger
from app.models.document import Chunk, DocumentVersion, Document

log = get_logger(__name__)

# ------------- 적재 -----------------------------------
# 문서 버전의 청크를 모두 재저장하는 함수 (재 임베딩시에도 사용)
def save_chunks(session: Session, version: DocumentVersion,
                drafts: list, vectors: list[list[float]]) -> int:

    # 기존에 저장된 chunks 삭세
    for old in list(version.chunks):
        session.delete(old)
    session.flush()

    for i, (d, vec) in enumerate(zip(drafts, vectors, strict=False)):
        session.add(Chunk(version_id=version.id, ord=i, kind=d.kind,
                          locator=d.locator, text=d.text, embedding=vec))
    version.chunk_count = len(drafts)
    session.flush() 
    log.info("청크 적재 : %s %s - %d청크 - %d벡터", version.doc_id, version.version, len(drafts), len(vectors))

    return len(drafts)


# --- 검색------------------------------------------------------------
def _row(chunk: Chunk,  version: DocumentVersion, doc: Document, score:float) -> dict:
    return {
        "chunk_id": chunk.id,
        "doc_id" : doc.id,
        "title": doc.title,
        "dept_id" : doc.dept_id,
        "security_level" : doc.security_level,
        "version": version.version,
        "version_status" : version.status,
        "locator": chunk.locator,
        "kind":chunk.kind,
        "text": chunk.text,
        "score": round(float(score), 4),
    }

# 질문 벡터에 가까운 청크를 가까운 순서대로 리턴해주는 함수
def vector_search(session: Session, query_vec: list[float], *, limit: int = 12) -> list[dict]:
    if not query_vec:
        return[]
    distance = Chunk.embedding.cosine_distance(query_vec).label("distance")
    stmt = (
        select(Chunk, DocumentVersion, Document, distance)
        .join(DocumentVersion, Chunk.version_id == DocumentVersion.id)
        .join(Document, DocumentVersion.doc_id == Document.id)
        .where(Chunk.embedding.is_not(None))
        .order_by("distance")
        .limit(limit)
    )
    return [
        _row(chunk, version, doc, 1.0 - float(dist))
        for chunk, version, doc, dist in session.execute(stmt)
    ]

# ------- 키워드 검색 ----------------------------------------
# 글자로 찾는 함수
def keyword_search(session: Session, query: str, *, limit: int = 12) -> list[dict]:
    stmt = (select(Chunk, DocumentVersion, Document)
            .join(DocumentVersion, Chunk.version_id == DocumentVersion.id)
            .join(Document, DocumentVersion.doc_id == Document.id))
    rows = list(session.execute(stmt))
    if not rows:
        log.warning("키워드 검색: 청크가 한 건도 없습니다 - 적재를 먼저 하세요.")
        return []

    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        log.warning("키워드 검색이 꺼져 있습니다 - rank_bm25 미설치.")
        return []

    scores = BM25Okapi([_tokenize(c.text) for c, _, _ in rows]).get_scores(_tokenize(query))
    top = max(scores) if len(scores) else 0.0
    out = [_row(chunk, version, doc, (s / top) if top else 0.0)
        for (chunk, version, doc), s in zip(rows, scores, strict=False)
    ]
    out.sort(key=lambda r: r["score"], reverse=True)
    return out[:limit]

# 본문과 질의를 같은 규칙으로 낱말로 분활하는 함수
def _tokenize(text: str) -> list[str]:
    return [ t for t in re.findall(r"[가-힣A-Za-z0-9]+", text or "") if len(t) > 1]

# RRF : 점수의 척도가 다른 두 결과를 *순위*로 합친다 
def fuse(vector_rows: list[dict], keyword_rows: list[dict], *, k: int = 60) -> list[dict]:
    ranks: dict[int, dict] = {}
    for source, rows in (("vector",vector_rows),("keyword", keyword_rows)):
        for rank, row in enumerate(rows, 1):
            if row["chunk_id"] not in ranks: 
                first = row["score"] if source == "vector" else 0.0
                ranks[row["chunk_id"]] = {**row, "score": first, "keyword_score": 0.0, "_rrf": 0.0}
            entry = ranks[row["chunk_id"]]
            entry["_rrf"] += 1.0 / (k + rank)
            if source == "keyword":
                entry["keyword_score"] = row["score"]

    merged = list(ranks.values())
    merged.sort(key=lambda r: r["_rrf"], reverse=True)
    for r in merged:
        r.pop("_rrf", None)
    return merged


# 정해진 청크들과 질문 벡터의 유사를 재는 함수 
def vector_scores(session: Session, query_vec: list[float], chunk_ids: list[int]) -> dict[int, float]:
    if not query_vec or not chunk_ids:
        return {}
    distance = Chunk.embedding.cosine_distance(query_vec)
    stmt = (select(Chunk.id, distance)
            .where(Chunk.id.in_(chunk_ids))
            .where(Chunk.embedding.is_not(None)))
    return {cid: round(1.0 - float(dist), 4) for cid, dist in session.execute(stmt)}
