from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

class Draft(Base, TimestampMixin):
    __tablename__="drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), nullable=False, index=True)
    doc_type: Mapped[str] = mapped_column(String(32))
    fields: Mapped[dict] = mapped_column(JSON)
    body: Mapped[str] = mapped_column(Text)
