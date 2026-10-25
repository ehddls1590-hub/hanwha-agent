from __future__ import annotations

import time # 추가 

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse 
from app.api.v1 import auth, documents, chat, ops
from app.core.config import get_settings # 추가 
from app.core.exceptions import AgentError
from contextlib import asynccontextmanager
from app.core.logging import setup_logging, get_logger # 추가 
from fastapi.exceptions import RequestValidationError
from app.integrations import factory # 추가 

# 추가 
log = get_logger(__name__)

# 추가 : 서버 스타트 시, 로컬 모델 미리 열어두기 
def _warn_up_models() -> None:
    settings = get_settings()
    if not settings.warn_up_models:
        return 
    started = time.perf_counter()
    try:
        if settings.embed_provider == "local":
            factory.get_embedder()
        if settings.reranker == "cross_encoder":
            factory.get_cross_encoder() 
    except AgentError as e:
        log.warning("모델을 미리 열지 못했습니다 - %s (첫 질문에서 다시 엽니다)", e.message)
        return 
    log.info("모델 미리 열기 완료: %.1f초", time.perf_counter() - started)



#  lifespan 함수 정의 : FastAPI 앱이 시작될 때, 종료될 때 실행되는 함수
# lifespan 함수 정의 
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging() 
    _warn_up_models()   # 추가 
    yield 

app = FastAPI(
    title="사내 AI 에이전트", 
    version="0.1.0",
    lifespan=lifespan
)

# 서버 상태 확인용 API
@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

# 라우터 연결 
app.include_router(
    documents.router,  # 수정 
    prefix="/api/v1"
)
# 추가 
app.include_router(
    auth.router,
    prefix="/api/v1"
)
app.include_router(
    chat.router,
    prefix="/api/v1"
)

app.include_router(
    ops.router,
    prefix="/api/v1"
)

## 예외 핸들러
@app.exception_handler(AgentError)
async def agent_error_error(
        request: Request,
        exc: AgentError
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": str(exc),
            "detail": None
            }
    )

# 사번 입력 안하고 로그인시 비번 로그에 노출 -> 예외로 잡기 
@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    # exc.errors() 에는 사용자가 보낸 값이 통째로 들어 있다. 필드 이름만 돌려주고 값은 감춘다.
    fields = ", ".join(
        ".".join(str(p) for p in e["loc"][1:]) or "요청 본문" for e in exc.errors()
    )
    return JSONResponse(
        status_code=422,
        content={"code": "validation_failed", "message": f"입력값을 확인하세요 — {fields}", "detail": None},
    )