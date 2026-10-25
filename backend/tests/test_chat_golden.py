from __future__ import annotations

import json
from pathlib import Path

import pytest

import app.integrations.factory as factory
from app.core.exceptions import GuardTripped
from app.core.guards import check_model
from app.integrations.ports import LLMResult, RetrievalResult
from app.services import chat_service

GOLDEN_PATH = Path(__file__).resolve().parent / "golden" / "chat_golden.json"
GOLDEN = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def stub_retriever(monkeypatch):
    import app.rag.retreiver_module

    class _StubRetriever:
        name = "stub"
        def search(self, *, question, user, session, **_):
            return RetrievalResult(
                sources=[{"doc_id": "DOC-HR-014", "title": "국내출장 여비 규정",
                          "version": "v2.0", "locator":"제12조(숙박비) * p.6",
                          "score": 0.90, "quote": "(대역)"}],
                steps=[{"name": "대역 검색", "state":"ok"}],
                best_score=0.90, passed=True, threshold=0.55
            )
    monkeypatch.setattr(retirever_module, "LiveRetriever" , _StubRetriever)

# 가짜 LLM
class StubLLM:

    name = "stub"

    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.calls = 0

    def answer(self, *, question: str, contexts: list[dict], user: dict) -> LLMResult:
        text = self.replies[min(self.calls, len(self.replies) - 1)]
        self.calls += 1

        return LLMResult(
            text=text,
            model="claude-haiku-4-5",
            input_tok=1200,
            output_tok=300,
            cost_krw=2.3,
            latency_ms=900,
        )

# 판정 함수
def check(case: dict, out) -> list[str]:
    expect = case["expect"]
    problems: list[str] = []


    for needle in expect.get("contains", []):
        if needle not in out.answer:
            problems.append(f"answer 에 '{needle}' 이 없습니다")


    for needle in expect.get("not_contains", []):
        if needle in out.answer:
            problems.append(f"answer 에 '{needle}' 이 들어 있습니다")

    if "min_sources" in expect and len(out.sources) < expect["min_sources"]:
        problems.append(
            f"근거가 {expect['min_sources']}건 이상이어야 합니다 (현재 {len(out.sources)}건)"
        )
    if "max_sources" in expect and len(out.sources) > expect["max_sources"]:
        problems.append(
            f"sources 가 {expect['max_sources']}건이어야 합니다 (현재 {len(out.sources)}건)"
        )
    for key in ("attempts", "fallback_used", "enough_evidence"):
        if key in expect and getattr(out, key) != expect[key]:
            problems.append(f"{key} 가 {expect[key]} 여야 합니다")

    if "doc_ids" in expect:
        for source in out.sources:
            if source.doc_id not in expect["doc_ids"]:
                problems.append(f"허용되지 않은 doc_id: {source.doc_id}")

    return problems


# 문항 문자열 생성 함수
def _question_of(case: dict) -> str:
    return case["question"] * case.get("repeat", 1)

# 골든셋 한 문항 돌리기 (메인)
@pytest.mark.parametrize("case", GOLDEN, ids=[c["id"] for c in GOLDEN])
def test_golden(case: dict, monkeypatch) -> None:
    
    expect = case["expect"]

   
    if "raises" in expect:
        with pytest.raises(GuardTripped) as caught:
            if case.get("guard") == "check_model":
                check_model(case["question"])
            else:
                chat_service.ask(question=_question_of(case))
        for needle in expect.get("contains", []):
            assert needle in str(caught.value)
        return

    stub = StubLLM(case["stub"])
    monkeypatch.setattr(factory, "get_llm", lambda: stub)

    out = chat_service.ask(question=_question_of(case))

    assert stub.calls > 0, "가짜 어댑터가 한 번도 불리지 않았습니다"
    assert check(case, out) == []
