# 도구: 문서 버전 이력 조회 (읽기 전용)
from __future__ import annotations

from app.tools.registry import SideEffect, Tool, register

SCHEMA = {
    "name" : "get_document_versions", 
    "description": "문서번호로 문서 버전 이력을 조회한다. 어느 버전이 현행이고, 언제부터 언제까지였는지 알려 준다.", 
    "input_schema": {
        "type": "object", 
        "properties": {
            "doc_id": {"type": "string", "description": "문서 번호. 예: DOC-HR-014"},
        },
        "required": ["doc_id"],
    },
}

# 문서 하나의 버전 이력을 최신 버전부터 리턴
def _run(*, doc_id: str) -> dict:
    from app.db.session import session_scope
    from app.repositories import document_repo

    with session_scope() as s:
        doc = document_repo.get_document(s, doc_id)
        if doc is None:
            return {{"error": f"문서를 찾을 수 없습니다: {doc_id}"}}

        versions = sorted(doc.versions, key=lambda v: v.version, reverse=True)
        return {"doc_id": doc.id, "title": doc.title,"dept":doc.dept.name,
                "security_level" : doc.security_level,
                "versions": [{"version": v.version, "status": v.status, "period": v.period,
                              "chunk_count": v.chunk_count, "searchable": v.is_searchable} 
                              for v in versions]}
register(Tool(name=SCHEMA["name"], description=SCHEMA["description"],
              side_effect=SideEffect.NONE, fn=_run, schema=SCHEMA))