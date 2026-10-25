# 채팅 요청과 응답 스키마
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

DOC_IDS = Literal["DOC-HR-014", "DOC-HR-002","DOC-HR-021", "DOC-FI-009",
                   "DOC-PU-007", "DOC-SE-003", "DOC-SE-011","DOC-PM-005"]

# 사용자가 보내오는 질문 하나 담아주는 객체
class ChatRequest(BaseModel):
    question: str = Field(
        min_length=2,
        max_length=2000,
        description="사용자 질문. 두 글자 이상 2000자 이하"
    )

# 답변이 인용한 근거 한개 담아줄 객체(모델)
class AnswerSource(BaseModel):
    doc_id: DOC_IDS = Field(description="인용한 문서 번호. 등록된 여덟 건 중 하나")  # 임시
    title: str = Field(description="문서 제목")
    version: str = Field(description="문서 버전. 예: v2.0")
    locator: str = Field(description="문서 안 위치. 예: 제12조 - p.6")
    score: float = Field(default=0.0, description="유사도 점수. 0 ~ 1. 높을수록 가깝다")

# 모델이 돌려줘야하는 답변의 모양
class AnswerOut(BaseModel):
    answer: str = Field(description="한국어 답변 본문")
    sources: list[AnswerSource] = Field(description="답변이 인용한 근거 목록")
    enough_evidence: bool = Field(description="근거가 충분했는가. 부족하면 False")


# 도구가 만든 문서 초안 한 건
class DraftOut(BaseModel):
    doc_type: str = Field(description="문서 양식 이름. 예: 국내 출장 신청서")
    fields: dict[str,str] = Field(description="양식의 칸과 값. 값은 모두 문자열")
    body: str = Field(description="문서 초안 전문")

# 재시도/폴백 정보 추가 : 라우터가 사용자에게 돌려주는 최종 응답 객체
class AskOut(AnswerOut):
    run_id: str = Field(description="이 질문 한 건의 실행 번호,예: RUN-1234")
    steps: list[dict] = Field(default_factory=list, description="검색 과정 단계 목록")
    attempts: int = Field(default=1, description="스키마 검증에 성공하기까지 부른 횟수")
    fallback_used: bool = Field(
        default=False,
        description="세 번 모두 실패에 폴백 답변으로 대처한 여부"
    )
    draft: DraftOut | None = Field(default=None, description="도구가 만든 문서 초안. 없으면 null")

# 외부 전송하는 도구가 실제로 돌려준 결과물 
class SentOut(BaseModel):
    ok: bool = Field(description="Slack이 전송되었는지")
    channel: str = Field(default="", description="보낸 채널. ID로 올 수 있다")
    ts: str = Field(default="", description="메세지 식별자")
    error: str | None = Field(default=None, description="실패 이유")
    simulated: bool = Field(default=False, description="전송하지 않았으면 True") 


# 재시도/폴백 관련 정보 추가 : 라우터가 사용자에게 돌려주는 최종 응답 객체 
class AskOut(AnswerOut):
    run_id: str = Field(description="이 질문 한 건의 실행 번호.예: RUN-1234")
    steps: list[dict] = Field(default_factory=list, description="검색 과정 단계 목록")
    attempts: int = Field(default=1, description="스키마 검증에 성공하기까지 부른 횟수")
    fallback_used: bool = Field(
        default=False, 
        description="세 번 모두 실패해 폴백 답변으로 대처한 여부"
    )
    draft: DraftOut | None = Field(default=None, description="도구가 만든 문서 초안. 없으면 null")
    sent: SentOut | None = Field(default=None, description="전송하는 도구의 실제 경롸. 막혔으면 null")
