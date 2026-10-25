from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from app.models.org import User

# 사번으로 db에서 회원 정보 조회
def get_by_emp_no(session: Session, emp_no: str) -> User | None:
    stmt = select(User).where(User.emp_no == emp_no).options(joinedload(User.dept))
    return session.scalar(stmt)