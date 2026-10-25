from fastapi import FastAPI, Query
from typing import Annotated
app = FastAPI(
    title="사내 업무 에이전트 연습",
    version="0.1.0",
)

# 사용자 요청을 처리해줄 uri 매핑 함수들
#  GET / health
@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

# ex. 문서 목록을 조회하는 함수
@app.get("/documents")
def list_documents(
    dept: str | None = None,
    limit: int = 20
)-> dict:
    return {"documents": 
        {"dept": dept, "limit": limit}
    }

# 요청 범위 제한
# ex. 문서 목록 조회시 범위 제한 주기
# @app.get("/documents/limited")
# def list_documents_limited(
#     dept: str | None = None,
#     limit: Annotated[int, Query(gt=0, le=100)] = 20
# ) -> dict:
#     return {"documents": 
#         {"dept": dept, "limit": limit}
#     }

#  * 경로 변수를  고정 아래에 배치
# ex. 특정 문서를 조회하는 함수
@app.get("/documents/{doc_id}")
def get_document(doc_id: str) -> dict:
    return {"doc_id": doc_id,
            "title": f"{doc_id}문서 제목"
    }

# ex.  타입 검증 -  레벨 조회
@app.get("/levels/{level}")
def get_level(level: int) -> dict:
    return {"level": level
        
    }


documents = [
    {
        "doc_id": "DOC-HR-014",
        "title": "2026년 휴가 운영 규정",
        "dept": "인사",
        "security_level": "일반",
        "file_format": "docx",
        "status": "active",
    },
    {
        "doc_id": "DOC-HR-021",
        "title": "복리후생 운영 지침",
        "dept": "인사",
        "security_level": "일반",
        "file_format": "pdf",
        "status": "active",
    },
    {
        "doc_id": "DOC-SE-011",
        "title": "정보보안 관리 규정",
        "dept": "보안",
        "security_level": "3급",
        "file_format": "pdf",
        "status": "active",
    },
    {
        "doc_id": "DOC-PU-007",
        "title": "구매 계약 업무 지침",
        "dept": "구매",
        "security_level": "대외비",
        "file_format": "docx",
        "status": "active",
    },
]

# 문서 전체 조회
@app.get("/practice/documents")
def search_documents(
    dept: str | None = None,
    security_level: str | None = None,
    file_format: str | None = None,
    limit: Annotated[int, Query(gt=0, le=100)] = 20
) -> list[dict]:

    #원본 복사
    result = documents.copy()
    # 부서 조건
    if dept is not None:
        result = [doc for doc in result if doc["dept"] == dept]
    # 보안 등급 조건
    if security_level is not None:
        result = [doc for doc in result if doc["security_level"] == security_level]
    # 파일 형식 조건
    if file_format is not None:
        result = [doc for doc in result if doc["file_format"] == file_format]

    return result[:limit]



