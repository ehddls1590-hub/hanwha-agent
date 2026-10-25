# 실행 번호 run_id 만들어주는 모듈

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Run

RUN_START = 8821

# 다음 run_id 번호 만들어 주는 함수 : RUN-8821 형태로 리턴
def next_run_id(session: Session) -> str:
    # DB에서 조회
    used = session.scalars(select(Run.id)).all()

    numbers = [RUN_START - 1] #  아무 행도 없을때 max()가 죽지 않도록 하는 바닥값
    for run_id in used:
        tail = run_id.removeprefix("RUN-")
        if tail.isdigit():
            numbers.append(int(tail))

    return f"RUN-{max(numbers) +1:04d}"