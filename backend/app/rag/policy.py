# 검색 정책
# - 기본 검색은 현재 유효한 최신본만 대상으로 한다.

from __future__ import annotations
from dataclasses import dataclass

from app.models.org import CLEARANCE

CURRENT = "현행"

@dataclass
class  SearchPolicy:
    current_only: bool = True           # 현행 버전만 검색 대상에 넣는다
    allow_past_on_request: bool = True  # 사용자가 명시라면 이전 버전도 검색한다
    respect_clearance: bool = True      # 보안 등급으로 문서를 거른다
    threshold: float = 0.60             # 이 점수에 못 미치면 '근거 부족'이다

# 아무 조건이 없으면 사용하는 기본 정책
DEFAULT = SearchPolicy()

# 질문이 이전 버전을 가르키는지 확인
def wants_past_version(question: str) -> bool:
    q = (question or "").replace(" ", "")
    hints = ("예전", "이전버전", "과거버전", "개정전","구버전", "예전규정")
    return any(hint in q  for hint in hints) or "v1." in q

# 특정 버전을 검색 대상에 포함시켜도 되는지 판단 
def version_allowed(version_status: str,*, policy: SearchPolicy, question: str) -> bool:
    if not policy.current_only:
        return True
    if version_status == CURRENT:
        return True
    return policy.allow_past_on_request and wants_past_version(question)

# 보안 등급 확인하기
def clearance_allowed(user_clearance: str, doc_level: str, *, policy: SearchPolicy) -> bool:
    if not policy.respect_clearance:
        return True
    return CLEARANCE.get(user_clearance, 1) >= CLEARANCE.get(doc_level, 1)

# 검색 결과를 정책으로 거르기, 통과한 것과 왜 걸렀는지 사유를 함께 돌려주기 
def filter_candidates(rows: list[dict], *, user: dict, 
                      question: str, policy: SearchPolicy = DEFAULT) -> tuple[list[dict], list[str]]:
    kept: list[dict] = []
    reason: list[str] = []

    for row in rows:
        if not version_allowed(row.get("version_status", CURRENT), policy=policy, question=question):
            reason.append(f"{row['title']} {row['version']} - 만료 버전")
            continue
        if not clearance_allowed(user.get("clearance", "일반"), row.get("security_level", "일반"), policy=policy):
            reason.append(f"{row['title']} - 보안등급({row.get('security_level')}) 차단")
            continue
        kept.append(row)

    return kept, reason 


