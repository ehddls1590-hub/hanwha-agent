# 모델로 메세지를 보내기 전에 검증 하는 기능
from __future__ import annotations

from app.core.config import get_settings
from app.core.exceptions import GuardTripped, RateLimited

# 질문의 최소 길이 지정
MIN_QUESTION_LEN = 2

# 사용할 수 있는 LLM 모델 (추후 .env에 모델을 바꾸면 여기도 변경)
ALLOWED_MODELS = {"claude-haiku-4-5"}

# 사용자 질문 검사 함수
def check_question(text:str) -> str:
    #  text : 사용자가 보낸 질문 원문
    settings = get_settings()
    q = (text or "").strip().rstrip("?")
    if len(q) < MIN_QUESTION_LEN:
        raise GuardTripped("질문이 비어있거나 너무 짧습니다.")
    if len(q) > settings.max_input_chars:
        raise GuardTripped(
            f"질문이 너무 깁니다 ({len(q)}자)."
            f"{settings.max_input_chars}자 이내로 줄여주세요."
        )
    return q

#llm 모델 체크 함수
def check_model(model: str)-> str:
    # model: 부르려는 모델 이름
    if model not in ALLOWED_MODELS:
        raise GuardTripped(f"허용되지 않은 모델입니다: {model}")
    return model


# 오늘 사용한 호출 수가 상한을 넘었는지 체크 함수
def check_daily_limit(used_today: int) -> None:
    # used_today: 오른 이미 사용한 호출 수
    settings = get_settings()
    if used_today >= settings.daily_call_limit:
        raise RateLimited(
            f"오늘 호출 한도({settings.daily_call_limit}회)를 모두 사용했습니다."
        )


    