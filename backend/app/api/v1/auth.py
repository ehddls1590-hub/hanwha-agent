# auth.py
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header

from app.core.exceptions import AuthFailed
from app.schemas.auth import LoginIn, UserOut
from app.services import auth_service

# 인증 관련 요청
router = APIRouter(prefix="/auth", tags=["auth"])

# 로그인 요청
@router.post("/login", response_model=UserOut) # 응답 데이터 타입 USerOut
def login(body: LoginIn) -> dict: # 사용자가 요청한 데이터는 LoginIn 타입으로 취합
    # 서비스야 로직처리해줘: 사용자가 보내준 emp_no, password 줄게, DB가서 일치하는지 확인해봐. 
    # 그리고 회원정보 돌려줘.
    return auth_service.authenticate(body.emp_no, body.password)

# 사용자 정보 요청 : x_emp_no는 JWT 토큰으로 변경 예정
@router.get("/me", response_model=UserOut)
def me(x_emp_no: Annotated[str | None, Header()] = None) -> dict: #x_emp_no 인증키(사번으로 임시사용) : 헤더 정보로 넘어옴
    # 사번이 존재하지 않으면 예외 발생
    if x_emp_no is None:
        raise AuthFailed("로그인이 필요합니다.")
    # 사번이 있으면 회원정보 조회해 리턴
    return auth_service.get_me(x_emp_no) # 회원 정보 리턴





