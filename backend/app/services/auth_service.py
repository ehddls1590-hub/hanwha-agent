from __future__ import annotations

from app.core.exceptions import AuthFailed
from app.core.security import verify_password
from app.db.session import session_scope
from app.models.org import User
from app.repositories import user_repo

# 변환함수 : User 정보를 UserOut이 받을 수 있는 정보로 돌려주는 함수       #v1
def _to_out(user: User) -> dict:
    return {
        "id": user.id,
        "emp_no": user.emp_no,
        "name": user.name,
        "dept": user.dept.name,
        "role": user.role,
        "clearance": user.clearance,
    }

# 인증 로직 처리 : 사번과 비밀번호를 확인하고 사용자 정보를 리턴 (비번 확인 O)             #Servises
def authenticate(emp_no: str, password: str) -> dict:
    with session_scope() as s:
        # DB에서 emo_no로 사원 정보 조회.
        user = user_repo.get_by_emp_no(s, emp_no)
        # 사번이 없거나 비밀번호가 일치하지 않으면 
        if user is None or not verify_password(password, user.password_hash): # 입력비번, DB에 암호화된 비번 비교 
            raise AuthFailed() # 우리가 만든 인증 예외 발생 
        return _to_out(user) # User형태의 사용자 정보를 UserOut 형태로 데이터 변형해서 리턴 

# 사번으로 지금 현재 사용자 정보를 돌려줌 (비번 확인 X)           #repo
def get_me(emp_no: str) -> dict:
    with session_scope() as s:
        # DB에서 emp_no로 사원 정보 조회 
        user = user_repo.get_by_emp_no(s, emp_no)
        if user is None:
            raise AuthFailed()
        return _to_out(user)



