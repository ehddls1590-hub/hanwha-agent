from __future__ import annotations

from sqlalchemy import Row, desc, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.document import Document, DocumentVersion


def list_documents(
    session: Session,
    *,
    dept_id: str | None = None,
    security_level: str | None = None,
    status: str | None = None,
    q: str | None = None,
    limit: int = 50,
) -> list[Row]:
    stmt = select(DocumentVersion, Document).join(
        Document, DocumentVersion.doc_id == Document.id
    )
    # 조건값 여부에 따라 쿼리문에 조건 추가
    if dept_id:
        stmt = stmt.where(Document.dept_id == dept_id)
    if security_level:
        stmt = stmt.where(Document.security_level == security_level)
    if status:
        stmt = stmt.where(DocumentVersion.status == status)
    if q:
        stmt = stmt.where(
            or_(Document.title.ilike(f"%{q}%"), Document.id.ilike(f"%{q}%"))
        )

    # 로딩 전력: 즉시 로딩
    stmt = stmt.options(joinedload(Document.dept))
    # 정렬, 개수 제한
    stmt = stmt.order_by(Document.id, desc(DocumentVersion.version)).limit(limit)
    # 최종 결과 리스트로 만들어 리턴
    return list(session.execute(stmt).all())

# 문서 id로 문서 한개 조회
def get_document(session: Session, doc_id: str) -> Document | None:
    return session.get(Document, doc_id)

# 특정 문서에 문서에 버전 한개 추가
def add_version(session: Session, doc: Document, **fields) -> DocumentVersion:
    version = DocumentVersion(doc_id=doc.id, **fields)
    session.add(version)
    session.flush()
    return version
