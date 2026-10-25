from __future__ import annotations

import os
from typing import Any

import httpx2

BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")

TIMEOUT = 10.0
CHAT_TIMEOUT = 120.0

class ApiError(RuntimeError):
    pass

# 모든 호출이 지나가는 내부 공용 함수
def _request(
    method: str,  # GET,POST 전송방식 
    path: str,    # BASE_URL 뒤에 붙는 경로 ex. /api/v1/documents
    *,
    params: dict | None = None,  # 쿼리스트링 ?aaa=10
    json: dict | None = None,    # 요청 본문으로 보낼 dict 타입 데이터 
    data: dict | None = None,    # 멀티파트 텍스트 필드                        # 추가 
    files: dict | None = None,   # 멀티파트 파일데이터 필드                    # 추가 
    emp_no: str | None = None,   # 사원번호. X-Emp-No 헤더값 
    timeout: float = TIMEOUT,
) -> Any:

    clean_params = None
    if params is not None: # 파라미터가 있다면
        # None 
        clean_params = {k: v for k, v in params.items() if v not in (None, "", "전체")}

    headers = {"X-Emp-No": emp_no} if emp_no else None
    url = f"{BASE_URL}{path}"

    try:
        response = httpx2.request(
            method, url, params=clean_params, json=json, data=data, files=files, headers=headers,
            timeout=httpx2.Timeout(timeout, connect=TIMEOUT),
        )
    except httpx2.ConnectError as exc:
        raise ApiError(
            f"백엔드에 연결하지 못했습니다. 터미널에서 서버가 떠 있는지 확인하세요 ({BASE_URL})."
        ) from exc
    except httpx2.TimeoutException as exc:
        raise ApiError(
            f"서버 통신 중 대기 시간을 초과했습니다 (대기 한도: {timeout:g}초). "
            "백엔드 터미널에서 처리 상태와 오류 로그를 확인해 주세요."
        ) from exc

    if response.status_code >= 400:
        try:
            message = response.json().get("message") or response.text
        except ValueError:
            message = response.text
        raise ApiError(message)

    return response.json()


def login(emp_no: str, password: str) -> dict:
    return _request(
        "POST",
        "/api/v1/auth/login",
        json={"emp_no": emp_no, "password": password},
    )


def me(emp_no: str) -> dict:
    return _request("GET", "/api/v1/auth/me", emp_no=emp_no)

# 문서 데이터 목록 요청
def list_documents(
    *,
    dept_id: str | None = None,
    security_level: str | None = None,
    status: str | None = None,
    q: str | None = None,
    limit: int = 20,
    emp_no: str | None = None,
) -> list[dict]:
    params = {
        "dept_id": dept_id,
        "security_level": security_level,
        "status": status,
        "q": q,
        "limit": limit
    }
    return _request("GET","/api/v1/documents", params=params, emp_no=emp_no) # 벡엔드에 요청

# 문서 한건 요청
def get_document(doc_id: str, *, emp_no: str | None = None) -> dict:
    return _request("GET", f"/api/v1/documents/{doc_id}", emp_no=emp_no)

# 나중에 문서상태 화면에 뿌려줄 데이터 요청
def stats(*, emp_no: str | None = None) -> dict:
    rows = list_documents(limit=100, emp_no=emp_no)
    return {
        "total": len(rows),
        "current": sum(1 for row in rows if row["status"] == "현행"),
        "expired": sum(1 for row in rows if row["status"] == "만료"),
        "reindexing": sum(1 for row in rows if row["index_status"] == "재임베딩")
    }

# 질문 하나 백엔드에 보내면 답변을 받아오는 함수 
def ask(question: str, *, tools: bool = False) -> dict:
    # question: 사용자가 입력창에 입력한 질문 
    return _request("POST", "/api/v1/chat/messages", json={"question": question},
                    params={"tools": True} if tools else None, timeout=CHAT_TIMEOUT)

# 파일 하나를 백엔드에 전달 -> 업로드 처리 요청 -> 작업 번호 리턴  
def upload_document(*, doc_id: str, title: str, dept_id: str, security_level: str, 
                    version: str, effective_from: str, filename: str, content: bytes, 
                    emp_no: str | None = None) -> dict:
    return _request("POST", "/api/v1/documents", 
                    data={
                        "doc_id": doc_id, "title": title, "dept_id": dept_id, 
                        "security_level": security_level, "version": version, 
                        "effective_from": effective_from,
                    }, 
                    files={"file": (filename, content)}, 
                    emp_no=emp_no
                )

# 업로드 작업의 진행 상태 하나 요청 
def get_job(job_id: str, *, emp_no:str | None = None) -> dict:
    return _request("GET", f"/api/v1/documents/jobs/{job_id}", emp_no=emp_no)


# 문서 한 건의 버전들을 모두 요청
def list_versions(doc_id: str, *, emp_no: str | None = None) -> list[dict]:
    return _request("GET", f"/api/v1/documents/{doc_id}/versions", emp_no=emp_no)

# 재임베딩 요청 (파일을 다시 올리지는 않는다.)
def reindex(doc_id: str, version: str, *, emp_no: str | None=None) -> dict:
    return _request("POST", f"/api/v1/documents/{doc_id}/versions/{version}/reindex" , emp_no=emp_no)

