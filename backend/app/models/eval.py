# 골든셋 문항을 테스트한 결과를 적어두는 테이블들 
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


# 설정 하나를 한 번 측정한 결과 
class EvalRun(Base, TimestampMixin):
    __tablename__ = "eval_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config: Mapped[str] = mapped_column(String(64), nullable=False)  # '기본검색' 
    ord: Mapped[int] = mapped_column(Integer, default=0)             # 막대 순서 
    accuracy: Mapped[float] = mapped_column(Float, default=0.0)      # 0~100
    item_count: Mapped[int] = mapped_column(Integer, default=30)     # 문항수
    measured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

# 정답률이 낮은 질문 유형 테이블 
class EvalWeakType(Base, TimestampMixin):
    __tablename__ = "eval_weak_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ord: Mapped[int] = mapped_column(Integer, default=0)
    label: Mapped[str] = mapped_column(String(120), nullable=False) 
    count: Mapped[int] = mapped_column(Integer, default=0)
    accuracy: Mapped[str] = mapped_column(String(16), default="-") # 화면에 그대로 출력할 문자열 형태로 저장 
    diagnosis: Mapped[str] = mapped_column(Text, default="")  
