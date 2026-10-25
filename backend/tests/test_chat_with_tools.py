from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

import app.integrations.factory as factory
from app.integrations.ports import LLMResult
from app.services import chat_service


def test_ask_with_tools_creates_run_and_returns_final_answer(monkeypatch) -> None:
    added_runs = []
    closed_runs = []

    class SessionStub:
        def add(self, instance) -> None:
            added_runs.append(instance)

    @contextmanager
    def fake_session_scope():
        yield SessionStub()

    class StubLLM:
        def answer_with_tools(self, *, messages, tools, user) -> LLMResult:
            return LLMResult(text="확인했습니다.", model="stub")

    monkeypatch.setattr(chat_service, "session_scope", fake_session_scope)
    monkeypatch.setattr(chat_service, "next_run_id", lambda _session: "run-tool-1")
    monkeypatch.setattr(chat_service, "get_settings", lambda: SimpleNamespace(app_mode="mock"))
    monkeypatch.setattr(chat_service, "_record_usage", lambda _run_id, _result: None)
    monkeypatch.setattr(
        chat_service,
        "_close_run",
        lambda run_id, out, started: closed_runs.append((run_id, out)),
    )
    monkeypatch.setattr(factory, "get_llm", lambda: StubLLM())

    out = chat_service.ask_with_tools(question="출장비 규정을 알려줘")

    assert len(added_runs) == 1
    assert added_runs[0].id == "run-tool-1"
    assert added_runs[0].user_id == 1
    assert added_runs[0].question == "출장비 규정을 알려줘"
    assert out.answer == "확인했습니다."
    assert out.run_id == "run-tool-1"
    assert closed_runs == [("run-tool-1", out)]
