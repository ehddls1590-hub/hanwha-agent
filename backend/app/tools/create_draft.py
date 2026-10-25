from __future__ import annotations

NAME = "create_draft"

SIDE_EFFECT = "internal"

DOC_TYPES = ("국내출장 신청서", )

# 도구 정의 (json schema)
SCHEMA = {
    "name" : NAME, 
    "description": "업무 문서 초안을 만들어 저장한다. 출장 신청서처럼 양식이 정해진 문서를 쓸 때 부른다.", 
    "input_schema": {
        "type": "object", 
        "properties": {
            "doc_type": {"type": "string", "enum": list(DOC_TYPES), "description": "만들 문서의 양식 이름."},
            "fields": {"type": "object", "description": "양식의 칸과 값. 예: {\"출장지\": \"부산\"}"},
        },
        "required": ["doc_type", "fields"],
    },
}

def run(*, run_id: str, doc_type: str, fields: dict, user: dict) -> dict:
    if doc_type not in DOC_TYPES:
        return {"error": f"모르는 양식입니다: {doc_type}. 가능한 값: {list(DOC_TYPES)}"}

    rows = {k: str(v) for k, v in fields.items()}
    rows["성명 / 소속"] = f"{user.get('name', '')} / {user.get('dept', '')}"

    body = "\n".join([f"[{doc_type}]", *(f"{k}: {v}" for k, v in rows.items())])

    from app.db.session import session_scope
    from app.models.draft import Draft

    with session_scope() as session:
        session.add(Draft(run_id=run_id, doc_type=doc_type, fields=rows, body=body))
    
    return {"doc_type": doc_type, "fields": rows, "body": body}

