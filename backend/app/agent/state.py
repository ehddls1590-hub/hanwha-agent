# 그래프 상태 

import operator
from typing import Annotated, TypedDict

# 질문 하나가 그래프를 한 바퀴 도는 동안의 상태
class WorkflowState(TypedDict, total=False):
    question: str                    # 질문(입력)
    user: str                        # 사용자(입력)
    sources: list[dict]              # search가 사용
    passed: bool                     # 갈래를 고르는 값
    versions: dict                   # found, insufficient가 사용
    note: str                        # insufficient가 사용
    trace: Annotated[list[str], operator.add]




