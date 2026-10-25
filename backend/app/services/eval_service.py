from __future__ import annotations

from sqlalchemy import select

from app.db.session import session_scope
from app.models.eval import EvalRun

# 측정 이력을 막대 그래프 순서대로 리턴해주는 함수 
def list_eval_runs(*, limit: int = 20) -> list[dict]:
    with session_scope() as s:
        rows = s.execute(select(EvalRun).order_by(EvalRun.ord).limit(limit)).scalars().all() 
        return [
            {
                "config": r.config, 
                "ord": r.ord, 
                "accuracy": r.accuracy, 
                "item_count": r.item_count, 
                "measured_at": r.measured_at.isoformat() if r.measured_at else None,
            }
            for r in rows
        ]
    