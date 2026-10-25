# 의존성 정의하는 파일
import uuid
import logging
from typing import Annotated
from fastapi import Depends, Request
from collections.abc import Iterator
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.db.session import get_sessionmaker

SettingsDep = Annotated[
    Settings, 
    Depends(get_settings)
]

# 로그 편의 함수: 요청 하나를 로그에서 따라갈 수 있게 하는 식별자 생성
def get_request_id(request: Request) -> str:
    return request.headers.get("X-Request-ID") or uuid.uuid4().hex[:8]

RequestIdDep = Annotated[str, Depends(get_request_id)]

# 요청 ID가 붙은 로거.
def get_request_logger(request_id: RequestIdDep) -> logging.Logger:
    return get_logger(f"api.req.{request_id}")

LoggerDep = Annotated[logging.Logger, Depends(get_request_logger)]

# 요청 하나가 사용할 데이터베이스 세션
def get_db() -> Iterator[Session]:
    db = get_sessionmaker()()
    try: 
        yield db
    finally:
        db.close()  

SessionDep = Annotated[Session, Depends(get_db)]


