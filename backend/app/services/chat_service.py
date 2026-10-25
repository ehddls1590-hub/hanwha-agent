from __future__ import annotations

import time 
import json 

import app.integrations.factory as factory 

from pydantic import ValidationError

from app.core.guards import check_question
from app.core.logging import get_logger
from app.core.config import get_settings
from app.core.exceptions import NotFound, ApprovalRequired
from app.db.session import session_scope
from app.models import Run, UsageLog
from app.services.ids import next_run_id
from app.schemas.chat import AnswerOut, AskOut, AnswerSource
from app.agent.chain import build_result_chain 
from app.tools import registry
from app.agent.patterns import route, route_after_search, run_chain, run_parallel



log = get_logger(__name__)

# 첫 호출 1회 + 재시도 2회 = 3회 
MAX_ATTEMPTS = 3

# 폴백 답변 본문
FALLBACK_ANSWER = "요청을 처리했지만 근거를 확인하지 못했습니다. 담당 부서에 문의해 주세요."

# 질문자 (임시)
DEFAULT_USER = {"name": "김민준", "dept": "인프라사업부 2팀"}

# 근거 문서 목록!! 
NO_CONTEXTS: list[dict] = []

# pydantic 의 오류 목록을 모델에게 다시 보낼 한 줄의 문장으로 변경해서 리턴 : 재시도 힌트 
def _hint_from(errors: list[dict]) -> str:
    # errors : ValidationError 가 돌려주는 목록 
    parts = []
    for err in errors:
        where = ".".join(str(x) for x in err.get("loc", ())) or "(최상위)"
        parts.append(f"{where}: {err.get('msg', '')}")
    return "/".join(parts)

# fallback : 재시도 다 사용뒤 사용자에게 보낼 답 리턴해주는 함수 
def _fallback(run_id: str, attemps: int) -> AskOut:
    # 사용자에게 응답해줄 최종 응답 결과 
    return AskOut(
        answer=FALLBACK_ANSWER, 
        sources=[], 
        enough_evidence=False, 
        run_id=run_id,
        attempts=attemps, 
        fallback_used=True
    )

# 호출 한번의 사용량과 원가를 usage_logs에 남기는 함수 
def _record_usage(run_id: str, result) -> None:
    # run_id : 실행 고유번호 
    # result : 어댑터가 돌려준 LLMResult 타입 응답데이터 
    try:
        with session_scope() as session:
            session.add(
                UsageLog(
                    run_id=run_id, 
                    model=result.model, 
                    input_tok=result.input_tok, 
                    cache_tok=result.cache_tok, 
                    output_tok=result.output_tok, 
                    cost_krw=result.cost_krw
                )
            )
    except Exception as e:
        log.warning("사용 기록 실패(무시하고 계속): %s", e)

# 열어둔 실행 기록 행들을 결과로 체워서 닫기 
def _close_run(run_id: str, out: AskOut, started: float) -> None:
    with session_scope() as session: 
        run = session.get(Run, run_id)
        run.answer = out.answer
        run.status = "완료"
        run.latency_ms = int((time.perf_counter() - started) * 1000)
        run.sources = [s.model_dump() for s in out.sources]

# 본체 : 질문 하나에 대답하기 
def ask(*, question: str, run_id: str | None = None, user_id: int = 1) -> AskOut:
    #1. 가드 호출 -> 여기서 던져진 예외는 이 함수를 통과해 전역 핸들러까지 올라간다. 
    q = check_question(question) 

    # 2. 어댑터 한 개. 
    llm = factory.get_llm() 

    from app.integrations.langfuse_client import score, trace
    from app.integrations.llm_claude import _extract_json 

    started = time.perf_counter() # 시작시간 

    # 질문 정보 DB Run에 저장 
    with session_scope() as session:
        if run_id is None:
            run_id = next_run_id(session) # run_id 없으면 생성 
        session.add(
            Run(
                id=run_id, 
                user_id=user_id, 
                question=q, 
                status="진행중",
                mode=get_settings().app_mode
            )
        )

    # NO_CONTEXTS 갈아 끼우기 
    from app.rag.retriever import LiveRetriever
    with session_scope() as session: 
        found = LiveRetriever().search(
            question=q, user={**DEFAULT_USER, "clearance": "일반"}, session=session
        )
    log.info("검색 : 근거 %d건 · 최고 %.2f · 기준 %.2f", len(found.sources), found.best_score, found.threshold)

    if not found.passed:
        log.info("임계값 미달(%.2f < %.2f) - 근거 부족으로 응답합니다. (run_id=%s)", found.best_score, found.threshold, run_id)
        out = _fallback(run_id, attemps=1)
        out.steps = found.steps  # 못 넘은 단계까지 화면에 그대로 보여주기 
        _close_run(run_id, out, started)
        return out 

    # 체인에 연결
    chain = build_result_chain(llm, contexts=found.sources, user=DEFAULT_USER).with_retry(
        stop_after_attempt=2
    )


    # langfuse 감싸서 llm 요청 
    with trace(
        "ask", 
        run_id=run_id,
        user_id=str(user_id),
        metadata={"question_len" : len(q)},
    ):
        out = None
        hint = ""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            # 3. llm 호출 
            #   프롬프트 준비 
            prompt = q if not hint else f"{q}\n\n[직전 응답의 문제] {hint}\n출력 형식을 지켜 다시 답해 주세요."
            #   llm에 질문 던지기 
            result = chain.invoke({"question": prompt})

            # 검증 전에 usage_log 기록 하기 
            _record_usage(run_id, result)

            try:
                data = _extract_json(result.text) # 응답 파싱 
                AnswerOut.model_validate(data)   # 규격에 맞는지 검사하는 부분 
            except ValidationError as e:
                hint = _hint_from(e.errors(include_url=False))
                # log.warning(f"스키마 위반 {attempt}/{MAX_ATTEMPTS}회 : {hint}")
                log.warning("스키마 위반 %d/%d회 : %s", attempt, MAX_ATTEMPTS, hint)
                continue 

            # 통과 시 out 변수에 담기 
            out = AskOut(**data, run_id=run_id, attempts=attempt, fallback_used=False)
            break 
        # end of for 

        if out is None:
            # 3번 다 시도했다. 로그 남기고, 폴백 실행 
            log.warning("스키마 검증에 %d회 모두 실패하여 폴백으로 응답합니다.(run_id=%s)", MAX_ATTEMPTS, run_id)
            out = _fallback(run_id, MAX_ATTEMPTS)
            score(run_id, "schema_ok", 0.0)

        out.steps = found.steps
        _close_run(run_id, out, started)
        return out 

# 실행 기록 한 건 조회 
def get_run(*, run_id: str) -> dict:
    with session_scope() as session:
        run = session.get(Run, run_id) # PK로 레코드 한건 조회 
        if run is None:
            raise NotFound(f"실행 기록을 찾을 수 없습니다: {run_id}")
        return {
            "run_id": run_id, 
            "user_id": run.user_id, 
            "question": run.question,
            "answer": run.answer, 
            "status": run.status,
            "latency_ms":  run.latency_ms, 
            "mode": run.mode,
            "sources": run.sources or [], 
            "created_at": run.created_at.isoformat(),
        }

# ----- 도구 루프 추가 -------------------------------------

# 도구 호출 요청, 응답 왕복의 횟수 상한값
MAX_TOOL_TURNS = 4 

# * 아래 두개 삭제 * 
# 모델에게 전달하는 도구 정의 목록 
# TOOLS = [search_documents.SCHEMA, create_draft.SCHEMA]

# 도구 이름 -> 실제로 실행하라 함수 
# TOOL_RUNNERS = {search_documents.NAME: search_documents.run, 
#                 create_draft.NAME: create_draft.run} 

# 왕복 상한에 도달해 답변을 완성하지 못했을때의 문구 
TOOL_LIMIT_ANSWER = "(도구 호출 상한에 닿아 답을 마치지 못했습니다)"

# 질문 하나에 도구 루프로 답하는 함수 
def ask_with_tools(*, question: str, run_id: str | None = None, user_id: int = 1) -> AskOut:
    q = check_question(question)
    llm = factory.get_llm()
    started = time.perf_counter() 
    with session_scope() as session:
        if run_id is None:
            run_id = next_run_id(session)
        session.add(Run(id=run_id, user_id=user_id, question=q, 
                    status="진행중", mode=get_settings().app_mode))

    user = {**DEFAULT_USER, "clearance": "일반"} # 임시 사용자 정보 

    registry.load_all() 
    tools = registry.all_tools() 
    schemas = [t.schema for t in tools]
    by_name = {t.name: t for t in tools} 

    ours = {"search_documents": {"user": user}, 
            "create_draft": {"user": user, "run_id": run_id}}

    messages: list[dict] = [{"role": "user", "content": q}]
    last_out: dict = {}    # 마지막 도구 실행 결과 
    made: dict | None = None # 초안 결과 따로 받기 
    sent: dict | None = None # 슬랙 전송 결과 별도로 받기 
    text = TOOL_LIMIT_ANSWER  # 상한에 도달하면 이 문구가 남아있도록 초기화 

    for turn in range(1, MAX_TOOL_TURNS + 1):
        result = llm.answer_with_tools(messages=messages, tools=schemas, user=user)
        _record_usage(run_id, result) 

        calls = result.extras.get("tool_calls") or [] 
        if not calls: # 도구 호출하지 않았을 경우 = 마지막 턴 
            text = result.text 
            break 

        # assistant 턴을 대화 기록에 그대로 추가 -> 모델이 직전 응답 기억 
        messages.append({"role": "assistant", "content": result.extras["blocks"]})
        blocks = []
        for c in calls:
            tool = by_name.get(c.name)

            try:
                out = tool.run(**c.args, **ours.get(c.name, {})) if tool else {"error": f"모르는 도구: {c.name}"}
            except ApprovalRequired as e:
                out = {"error": str(e), "approval_required": True}
            
            if tool and c.name == "create_draft":
                made = out 
            elif tool and c.name == "search_documents":
                last_out = out 
            elif tool and c.name == "send_slack" and not out.get("approval_required"):
                sent = out

            blocks.append({"type": "tool_result", "tool_use_id": c.id, 
                           "content": json.dumps(out, ensure_ascii=False, default=str)})
        messages.append({"role": "user", "content": blocks})
    else: 
        log.warning("도구 호출 상항 %d회에 닿았습니다(run_id=%s)", MAX_TOOL_TURNS, run_id) 

    # 출처는 모델에게 다시 묻지 않는다. 
    sources = []
    for s in last_out.get("sources", []):
        try:
            sources.append(AnswerSource(**s))
        except ValidationError:
            log.warning("근거를 스키마로 만들지 못해 건너띕니다: %s", s.get("doc_id"))

    out = AskOut(answer=text, sources=sources, run_id=run_id, attempts=turn,
                 enough_evidence=bool(last_out.get("passed")),
                 steps=last_out.get("steps", []), fallback_used=False, 
                 draft=made if made and "body" in made else None,
                 sent=sent)
    _close_run(run_id, out, started)
    return out 

# --- 워크 플로우 ------------

def _wf_search(state: dict) -> dict:
    out = registry.get("search_documents").run(query=state["question"], user=state["user"])
    return {"sources": out["sources"], "passed": out["passed"]}

def _wf_found(state: dict) -> dict:
    tool = registry.get("get_document_versions")
    ids = sorted({s["doc_id"] for s in state["sources"]})
    return {"versions": run_parallel({d: (tool.run, {"doc_id" : d}) for d in ids})}

def _wf_insufficient(state: dict) -> dict:
    return {"versions" : [], "note": FALLBACK_ANSWER}

def _wf_route(state: dict ) -> dict:
    return route(state, route_after_search, {"found": _wf_found, "insufficient": _wf_insufficient})

def run_workflow(*, question: str) -> dict:
    q = check_question(question)
    registry.load_all()
    state = { "question": q, "user" : {**DEFAULT_USER, "clearance" : "일반"}}
    return run_chain([_wf_search, _wf_route], state)

# ------- 그래프 --------------------------
def run_graph(*, question: str) -> dict:
    from app.agent.graph import build_graph
    q = check_question(question)
    registry.load_all()
    graph = build_graph(_wf_search, {"found": _wf_found,"insufficient": _wf_insufficient}, route_after_search)
    return graph.invoke({"question":q, "user": {**DEFAULT_USER, "clearance": "일반"}})




