# 부서와 사용자 모델
from __future__ import annotations
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

# 보안 등급
CLEARANCE: dict[str, int] = {"일반": 1, "3급": 2, "대외비": 3}

# 부서 모델
class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    id: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    # back_poplates로 양쪽 이름을 맞춰두기.    
    users: Mapped[list["User"]] = relationship(back_populates="dept")
    documents: Mapped[list["Document"]] = relationship(back_populates="dept")

# 사용자 모델 
class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    emp_no: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(50))
    dept_id: Mapped[str] = mapped_column(ForeignKey("departments.id"))
    role: Mapped[str] = mapped_column(String(10))       
    clearance: Mapped[str] = mapped_column(String(10))  
    password_hash: Mapped[str] = mapped_column(String(100), default="")
      

    dept: Mapped["Department"] = relationship(back_populates="users")
    documents: Mapped[list["Document"]] = relationship(back_populates="owner")

    # 보안 등급 숫자로 리턴, default 1로 가장 낮은 보안 등급처리
    @property
    def clearance_level(self) -> int:
        return CLEARANCE.get(self.clearance, 1)

    # 승인 권한 있는지 체크: 팀장이나 관리자만 승인 권한 있다고 부여
    @property
    def can_approve(self) -> bool:

        return self.role in {"팀장", "관리자"}
    
