# 실행 기록 - 질문 한건이 행(레코드) 하나로 남는다. 
from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

# 질문 한건의 실행 기록을 담을 테이블(모델)
class Run(Base, TimestampMixin):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True) 
    status: Mapped[str] = mapped_column(String(24), default="완료")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    mode: Mapped[str] = mapped_column(String(8), default="mock")
    # 근거 목록 통째로 담기 
    sources: Mapped[list | None] = mapped_column(JSON, nullable=True)


# 실행 하나 안의 단계 하나를 담을 테이블(모델)
class RunStep(Base):
    __tablename__ = "run_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), nullable=False)
    # 몇 번째 단계인가. 시간순이 아니라 번호순으로 그리기 위해 따로 지정 
    ord: Mapped[int] = mapped_column(Integer, default=0) 
    name: Mapped[str] = mapped_column(String(64))
    ok: Mapped[bool] = mapped_column(default=True)
    ms: Mapped[int] = mapped_column(Integer, default=0)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    
