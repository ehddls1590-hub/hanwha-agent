from  __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# 로그인 요청 모델
class LoginIn(BaseModel):
    emp_no: str = Field(examples=["2016-0231"]) #사번
    password: str = Field(min_length=1) # 비밀번호

# 로그인 성공시 응답해줄 사원 정보 모델
class UserOut(BaseModel):
    id: int
    emp_no: str = Field(examples=["2016-0231"])
    name: str
    dept: str = Field(examples=["인사총무"])
    role: Literal["일반", "팀장", "관리자"]
    clearance: Literal["일반", "3급", "대외비"] 