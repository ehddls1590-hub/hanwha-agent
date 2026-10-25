# 외부 연동 Protocol :  규격
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

# LLM 호출 한번의 결과
@dataclass
class LLMResult:
    text: str
    model: str
    input_tok: int = 0
    cache_tok: int = 0
    output_tok: int = 0
    cost_krw: float = 0.0
    latency_ms: int = 0
    extras: dict = field(default_factory=dict) # 화면애 필요한 여분 데이터를 실어 보내기

# 도구 호출 한건에 대한 정보를 담는 클래스
@dataclass
class ToolCall:
    id: str        # 호출 번호
    name: str      # 호출하라고 요청한 도구 이름
    args: dict     # 도구에 넘길 인자.


# LLM 어댑터가 지켜야할 규칙 (인터페이스, 코드 규격)
@runtime_checkable
class LLMPort(Protocol):
    # 단순 답변
    def answer(self,*, question: str, contexts: list[dict], user: dict, system: str | None = None) -> LLMResult: ...
    # 도구 목록 전달해 모델 1회 호출
    def answer_with_tools(self, *, messages: list[dict], tools: list[dict], user: dict) -> LLMResult: ...
        
#------------------ 문서 파싱 결과 -------------------------------------------------------
# 파싱 결과의 최소 단위. 문서를 잘라놓은 덩어리 하나 : PDF, DOCX, HWPX
@dataclass

class ParsedBlock:
    kind: str                # 덩어리 종류: 조항, 표
    locator: str             # 원본 어디서 나온 덩어리 인지 : p.6, 표2
    text: str                # 덩어리 글자들

# 문서 한건을 파싱한 결과 전체
@dataclass
class ParsedDoc:
    blocks: list[ParsedBlock] = field(default_factory=list) # 본문에 놓은 순서 그대로 덩어리 목록 저장
    page_count: int = 0                                     # 페이지 수, 페이지 개념이 없는 docx형식은 1로 둔다.
    table_count: int = 0                                    # 표를 몇개 알아봤는지.

# 파서 어댑터가 지켜야할 규칙 : 로컬 파서 또는 파싱 API를 사용해도 아래 모양만 맞춰주면, 같은 코드로 사용가능하게 해줌
@runtime_checkable
class ParserPort(Protocol):
    def parse(self, path: str) -> ParsedDoc: ...

# 검색 결과 담는 객체
@dataclass
class RetrievalResult:
    sources: list[dict] = field(default_factory=list) # 근거 후보 목록
    steps: list[dict] = field(default_factory=list)   # 화면의 검색 과정 보여줄때 사용
    best_score: float = 0.0                           # 후보 중 가장 높은 유사도
    passed: bool = False                              # 최고 점수가 임계점을 넘었는가?
    version_note: str | None = None                   # 만료된 문서버전을 걸렸을때 사용자에게 알려줄 노트
    threshold: float = 0.55                           # 임계값

#-------------  임베딩 ------------------------------
# 임베딩 어댑터가 지켜야 할 규칙
@runtime_checkable
class EmbedderPort(Protocol):
    dim: int
    def embed_document(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...

# -------------- 크로스 인코더 -----------------------
# 크로스 인코더 어댑터가 지켜야할 규약
@runtime_checkable
class RerankerPort(Protocol):
    name: str
    def score_pairs(self, query: str, texts: list[str]) -> list[float]: ...

# ---------- 슬랙 -----------------------------------
# 보내는 쪽 규약 
@dataclass
class SlackResult:
    ok: bool 
    channel: str = ""
    ts: str = ""                # 메세지 식별자 
    error: str | None = None
    simulated: bool = False     # 보내지 않았으면 True

# 보내는 업댑터 규약 
@runtime_checkable
class SlackPort(Protocol):
    def post(self, *, channel: str, text: str) -> SlackResult: ...
