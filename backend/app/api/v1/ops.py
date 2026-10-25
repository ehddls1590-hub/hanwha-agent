from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.services import eval_service
router = APIRouter(prefix='/ops', tags=['ops'])

class EvalRunOut(BaseModel):
    config: str
    ord: int
    accuracy: float
    item_count: int
    measured_at: str | None = None

@router.get('/eval-runs', response_model=list[EvalRunOut])
def list_eval_runs(limit: Annotated[int, Query(ge=1, le=100)]=20) -> list[dict]:
    return eval_service.list_eval_runs(limit=limit)

