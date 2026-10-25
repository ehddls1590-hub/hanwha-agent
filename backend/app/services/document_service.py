"""
서비스: 사용자 요청에 대한 로직처리하는 곳.
DB정보가 필요하면 
트랜잭션을 여닫는 자리가 여기다.
"""
from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4
from app.core.exceptions import NotFound, ValidationFailed
from app.db.session import session_scope                          # 세션 DB 접속하기위한 통로
from app.models.document import Document, DocumentVersion  # 데이터 넣는 가방들/ import에서  chunk뺌 store에서 import하기 때문
from app.repositories import document_repo                        #리포지토리 DB 접속시 필요


# 사용자에게 전달할 데이터를 예쁘게 만들어주는 함수
def _to_out(version: DocumentVersion, document: Document) -> dict:
    # 여러 객체에 나눠져있는 데이터를 
    return {
        "doc_id": document.id,
        "title": document.title,
        "dept": document.dept.name,
        "version": version.version,
        "security_level": document.security_level,
        "file_format": version.file_format,
        "status": version.status,
        "effective_from": version.effective_from,
        "expires_at": version.expires_at,
        "index_status": version.index_status,
        "index_progress": version.index_progress,
    }

# 문서 목록 조회
def list_documents(
    *,
    dept_id: str | None = None,
    security_level: str | None = None,
    status: str | None = None,
    q: str | None = None,
    limit: int = 50,
) -> list[dict]:

   # 세션 만들어 repository 호출해 결과 받기 
    with session_scope() as s:
        # repository(document_repo)의 문서목록 함수 호출
        rows = document_repo.list_documents(
            s,
            dept_id=dept_id,
            security_level=security_level,
            status=status,
            q=q,
            limit=limit,
        )

        # 위 _to_out에 rows에 있는 문서 version과 문서자체를 전달해서 예쁘게 만들어 리스트로 전달
        return [_to_out(version, document) for version, document in rows]

# 문서 1개 조회 : 문서 id 값 외부에서 전달해주면 해당 문서 1개 조회해서 리턴해준다.
def get_document(*, doc_id: str) -> dict:
    # 세션 생성해 문서 1개 조회
    with session_scope() as s:
        document = document_repo.get_document(s, doc_id)
        if document is None:
            raise NotFound(f"문서를 찾을 수 없습니다: {doc_id}")
        current = document.current
        if current is None:
            raise NotFound(f"현행 버전이 없습니다: {doc_id}")
        return _to_out(current, document)

# 문서 등록(저장) 처리
def create_document(
    *,
    doc_id: str,
    title: str,
    dept_id: str,
    security_level: str,
    version: str,
    effective_from: date,
    file_path: str,
    file_format: str,
    owner_id: int | None = None,
) -> dict:

    with session_scope() as s:
        # 문서 조회
        document = document_repo.get_document(s, doc_id)
        created = document is None
        if document is None:
            document = Document(
                id=doc_id,
                title=title,
                dept_id=dept_id,
                security_level=security_level,
                owner_id=owner_id,
            )
            s.add(document)
            s.flush()
        # 문서 버전이 이미 존재할때
        elif any(v.version == version for v in document.versions):
            raise ValidationFailed(
                f"{doc_id} 의 {version} 은(는) 이미 등록되어 있습니다. "
                "판 번호를 올려 다시 올려 주세요."
            )

        # 새 버전 저장 전에, 기존 버전들의 현행을 만료로 내리는 처리 (현행은 하나만)
        for past in document.versions:
            if past.status == "현행":
               past.status = "만료"
               past.expires_at = effective_from - timedelta(days=1)
               past.index_status = "보관" # 검색 대상에서 제외하겠다


        # 실제 문저 버전 저장
        document_repo.add_version(
            s,
            document,
            version=version,
            status="현행",
            effective_from=effective_from,
            expires_at=None,
            file_path=file_path,
            file_format=file_format,
            index_status="대기",     
        )

        # 저장 후 화면에 전달할 데이터 리턴
        return {
            "doc_id": document.id,
            "title": document.title,
            "version": version,
            "file_format": file_format,
            "file_path": file_path,
            "created": created,
        }

# 문서 한건의 버전을 전부 리턴, 최신 버전이 앞에 오도록 리턴
def list_versions(*, doc_id: str) -> list[dict]:
    with session_scope() as s:
        document = document_repo.get_document(s, doc_id)
        if document is None:
            raise NotFound(f"문서를 찾을 수 없습니다: {doc_id}")
        return[
            {
                "version": v.version,
                "status" : v.status,
                "effective_from" : v.effective_from,
                "chunk_count" : v.chunk_count,
                "embed_model" : v.embed_model,
                "index_status" : v.index_status,
                "indexed_at" : v.indexed_at,
                "searchable" : v.is_searchable,
                "period" : v.period

            }
            for v in sorted(document.versions, key=lambda v: v.version, reverse=True)
        ]

# 업로드 요청한 파일 하나를 파싱 -> 청킹 -> 저장까지 이어주는 함수
def ingest_document(*, doc_id: str, version: str, path: str) -> dict:
    from app.rag import chunker, parser, embedder, store

    with session_scope() as s:
        document = document_repo.get_document(s, doc_id) 
        dv = next((v for v in document.versions if v.version == version), None) if document else None 
        if dv is None:
            raise NotFound(f"문서 버전을 찾을 수 없습니다 :{doc_id} {version}")
        
        parsed = parser.parse(path) 
        if parsed is None:
            raise ValidationFailed(f"파일을 읽지 못했습니다: {path}")

        drafts = chunker.chunk(parsed)

        vectors = embedder.embed_documents([d.text for d in drafts])
        store.save_chunks(s, dv, drafts, vectors)

        # # 기존 버전에 청크들 있는지 확인 -> 있으면 삭제   [store.save_chunks(s, dv, drafts, vectors)로 인해 삭제함]
        # for old in list(dv.chunks):
        #     s.delete(old)   
        # s.flush()   # 삭제 쿼리 DB에 날리기 
        # for i, d in enumerate(drafts):
        #     s.add(Chunk(version_id=dv.id, ord=i, kind=d.kind, locator=d.locator, text=d.text)) 
        # dv.chunk_count = len(drafts) 이것도 같이 삭제 

        dv.index_status = "완료"
        dv.index_progress = 100
        dv.embed_model = embedder.model_label()
        dv.indexed_at = date.today() 
        return {"chunks": len(drafts),   "tables":parsed.table_count, 
                "vectors": len(vectors), "summary": chunker.summarize(drafts)}

    
  # 작업 상태를 담아두는 곳 
_JOBS: dict[str, str] = {}
_STEP_NAMES = ["파일 검증", "문서 파싱", "표 -> 마크다운 변환", "청킹", "임베딩", "검색 반영 및 현행 버전 지정"]

# 작업 하나를 만들어 번호를 리턴해주는 함수 
def start_ingest_job(*, doc_id: str, version: str, path: str) -> str: 
    job_id = uuid4().hex[:8] 
    _JOBS[job_id] = {
        "job_id": job_id, "doc_id": doc_id, "version": version, "path": path, 
        "status": "대기", "progress": 0, 
        "steps": [{"name": n, "state": "todo"} for n in _STEP_NAMES],
        "chunk_count": 0, "message": "",
    }
    return job_id 

# 작업을 실제로 돌리기 함수 : BackgroundTasks 가 응답 보낸 후 호출하는 함수
def run_ingest_job(job_id: str) -> None:
    job = _JOBS.get(job_id)
    if job is None:
        return
    try:
        job["status"] = "진행 중"
        steps = job["steps"]
        result = ingest_document(
            doc_id=job["doc_id"],
            version=job["version"],
            path=job["path"],
        )
        for step in steps:
            step["state"] = "ok"
        steps[1]["time"] = f"표 {result['tables']}개 인식"
        steps[2]["time"] = f"표 {result['tables']}개"
        steps[3]["time"] = f"{result['chunks']}청크"
        steps[4]["time"] = f"{result['vectors']}벡터"
        steps[5]['time'] = "현행 지정 완료"
        job["progress"] = int(6 / len(steps) * 100)
        job["chunk_count"] = result["chunks"]
        job["message"] = result["summary"]
        job["status"] = "완료"
    except Exception as e:
        job["status"] = "실패"
        job["message"] = str(e)

# 이미 등록된 문서 버전 한개를 다시 적재하는 작업 
def start_reindex_job(*, doc_id: str, version: str) -> str:
    with session_scope() as s:
        document = document_repo.get_document(s, doc_id)
        dv = next((v for v in document.versions if v.version == version), None) if document else None
        if dv is None:
            raise NotFound(f"해당 문서 버전을 찾을 수 없습니다: {doc_id} {version}")
        path = dv.file_path or ""
        dv.index_status = "재임베딩"
        dv.index_progress = 0 
    return start_ingest_job(doc_id=doc_id, version=version, path=path) 

# 작업 하나의 진행 상태를 리턴해주는 함수
def get_job(job_id: str) -> dict:
    job = _JOBS.get(job_id)
    if job is None:
        raise NotFound(f"작업을 찾을 수 없습니다: {job_id}")
    return job
