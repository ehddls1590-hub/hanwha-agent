from fastapi import APIRouter, Query, File, Form, UploadFile, BackgroundTasks 
from typing import Annotated

import shutil
from datetime import date
from pathlib import Path

from app.schemas.document import DocumentOut, DocumentCreateOut, JobOut, VersionOut 
from app.api.v1.deps import LoggerDep
from app.core.exceptions import ValidationFailed
from app.services import document_service

# 문서 API를 모아두는 라우터 
router = APIRouter(
    prefix="/documents", 
    tags=["documents"]
)

# 파일 업로드될 경로 지정 
UPLOAD_DIR = Path("uploads")

ALLOWED_EXTS = {".docx", ".pdf"}


# 문서 목록 요청 
@router.get("", response_model=list[DocumentOut])   # ...8000/api/v1/documents
def list_documents(
    dept_id: str | None = None, 
    security_level: str | None = None,
    status: str | None = None, 
    q: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20 
) -> list[dict]:

    # 서비스 함수와 연결 (service -> repository -> DB 데이터 조회) 
    return document_service.list_documents(
        dept_id=dept_id,
        security_level=security_level,
        status=status,
        q=q,
        limit=limit
    )

# 문서 등록 
@router.post("", response_model=DocumentCreateOut, status_code=201)
def upload_document(
    doc_id: Annotated[str, Form()],
    title: Annotated[str, Form()],
    dept_id: Annotated[str, Form()],
    security_level: Annotated[str, Form()],
    version: Annotated[str, Form()],
    effective_from: Annotated[date, Form()],
    file: Annotated[UploadFile, File()],
    background: BackgroundTasks, 
    logger: LoggerDep,
) -> dict:
    
    safe_name = Path(file.filename or "").name
    ext = Path(safe_name).suffix.lower()

    # 우리가 지정한 docx/pdf 아니면 파일 업로드 처리 X 
    if ext not in ALLOWED_EXTS:      
        raise ValidationFailed(
            f"{ext or '확장자 없는'} 파일은 등록할 수 없습니다. "
            "DOCX 또는 PDF 로 변환해 다시 올려 주세요."
        )

    # 업로드할 폴더 없으면 만들어라 
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    # 경로/파일명.확장자 : 저장할 파일명은 우리가 짓는다. 
    dest = UPLOAD_DIR / f"{doc_id}_{version}{ext}"

    # 실제 파일을 조금씩 나눠서 업로드한다. 
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out) # 실제 파일을 dest (저장위치+파일명) 으로 복사하는코드 

    logger.info("문서 파일 저장: %s (%s)", dest, security_level)

    # DB에 파일정보 저장하고, 돌려받은 정보(응답데이터) 화면에 돌려주기 
    result = document_service.create_document(
        doc_id=doc_id,
        title=title,
        dept_id=dept_id,
        security_level=security_level,
        version=version,
        effective_from=effective_from,
        file_path=dest.as_posix(),
        file_format=ext.lstrip("."),
    )
    # 수정+추가 
    job_id = document_service.start_ingest_job(doc_id=doc_id, version=version, path=dest.as_posix())
    background.add_task(document_service.run_ingest_job, job_id)

    return {**result, "job_id": job_id}


# 추가 : 업로드 작업 하나의 진행 상태 정보 요청 처리해주는 매핑 
@router.get("/jobs/{job_id}", response_model=JobOut)
def read_job(job_id: str) -> dict:
    return document_service.get_job(job_id) 


# 문서 1개 조회  : ...8000/api/v1/documents/문서id값
@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: str) -> dict:
    return document_service.get_document(doc_id=doc_id)

# 문서 1개의 해당하는 버전들 요청
@router.get("/{doc_id}/versions", response_model=list[VersionOut])
def list_versions(doc_id: str) -> list[dict]:
    return document_service.list_versions(doc_id=doc_id)

@router.post("/{doc_id}/versions/{version}/reindex", response_model=JobOut, status_code=202)
def reindex_version(doc_id: str, version: str, background: BackgroundTasks) -> dict:
    job_id = document_service.start_reindex_job(doc_id=doc_id, version=version)
    background.add_task(document_service.run_ingest_job, job_id)
    return document_service.get_job(job_id)








