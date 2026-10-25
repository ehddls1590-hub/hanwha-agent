# 특정 기능에 종속되지 않는 공통 응답 스키마 만들기

from pydantic import BaseModel

class HealthOut(BaseModel):
    status: str

class ErrorOut(BaseModel):
    code: int
    message: str
    detail: str | None = None

