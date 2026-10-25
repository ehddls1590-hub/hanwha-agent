from __future__ import annotations

import time

# 채팅 라우터

from fastapi import APIRouter

from app.schemas.chat import AskOut, ChatRequest
from app.services import chat_service
from app.core.logging import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# 채팅 질문 요청 -> 답변 돌려주기
@router.post("/messages", response_model=AskOut)
def create_message(payload: ChatRequest, tools: bool = False) -> AskOut:
    started = time.perf_counter()
    log.info("채팅 요청 시작: tools=%s, question_chars=%d", tools, len(payload.question))
    try:
        if tools:
            out = chat_service.ask_with_tools(question=payload.question)
        else:
            out = chat_service.ask(question=payload.question)
    except Exception:
        log.exception("채팅 요청 실패: tools=%s, elapsed=%.1fs", tools, time.perf_counter() - started)
        raise
    log.info("채팅 요청 완료: run_id=%s, elapsed=%.1fs", out.run_id, time.perf_counter() - started)
    return out
# * 추가 *
# 실행 기록 한건 조회
@router.get("/runs/{run_id}")
def read_run(run_id: str) -> dict:
    # 서비스에게 run_id주고 DB에서 실행 기록 한개 조회해오도록 시키기
    return chat_service.get_run(run_id=run_id)


