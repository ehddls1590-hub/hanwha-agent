from __future__ import annotations

# 도구명 
NAME = "search_documents"

# 부작용 등급. (조회 도구라 none, 내부쓰기, 외부 실행 구분용도)
SIDE_EFFECT = "none"

# 모델에게 보낼 근거의 필드 
SOURCE_KEYS = ("doc_id", "title", "version", "locator", "score", "quote", "text")

# 도구 정의 (json schema)
SCHEMA = {
    "name" : NAME, 
    "description": "사내 규정 문서를 검색해 근거 문단을 돌려준다. 현행 버전, 보안 등급 필터가 적용된다.", 
    "input_schema": {
        "type": "object", 
        "properties": {
            "query": {"type": "string", "description": "찾을 내용. 질문을 그대로 넣어도 된다."},
        },
        "required": ["query"],
    },
}

# 검색어 하나로 사내 문서를 검색해 근거 문단을 리턴하는 함수
def run(*, query: str, user: dict) -> dict:
    from app.db.session import session_scope
    from app.rag.retriever import LiveRetriever


    with session_scope() as session:
        found = LiveRetriever().search(question=query, user=user,session=session)
        return {
            "sources": [{k:s.get(k) for k in SOURCE_KEYS }for s in found.sources],
            "steps": found.steps,
            "best_score": found.best_score,
            "passed": found.passed,
            "version_note": found.version_note,
            "threshold": found.threshold,
        }

    

