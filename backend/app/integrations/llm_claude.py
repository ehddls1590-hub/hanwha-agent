# Claude 어댑터 
from __future__ import annotations
import json
import re
import time
from pathlib import Path
from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger
from app.integrations.ports import LLMResult, ToolCall

# 로거 생성 
log = get_logger(__name__)

# 프롬프트 파일의 서식지 
PROMPTS = Path(__file__).resolve().parent.parent / 'agent' / 'prompts'  # app/agent/prompts 

# 요금 : USD/MTok - 모델 개정시 여기만 수정 
PRICING = {'input': 1.0, 'cache_write': 1.25, 'cache_read': 0.1, 'output': 5.0}
# 환율 
USD_KRW = 1400.0

# 호출 한번의 비용을 원화로 어림 계산해주는 함수 
def estimate_cost_krw(input_tok: int, output_tok: int) -> float:
    usd = input_tok / 1000000 * PRICING['input'] + output_tok / 1000000 * PRICING['output']
    return round(usd * USD_KRW, 1)


# 프롬프트 파일을 하나 읽어서 문자열로 리턴해주는 함수 
def _load_prompt(name: str) -> str:
    path = PROMPTS / name
    return path.read_text(encoding="utf-8") if path.exists() else ""

# 근거 문서 목록을 모델이 읽을 문자열 한 덩어리로 변환해서 리턴하는 함수 
def _context_block(contexts: list[dict]) -> str:
    # contexts : 근거 항목 목록  
    lines = []
    for i, c in enumerate(contexts, 1):
        lines.append(
            f"[근거 {i}] {c.get('title')} {c.get('version')} · {c.get('locator')} "
            f"(유사도 {c.get('score', 0):.2f})\n{c.get('text') or c.get('quote') or ''}"  # 수정 
        )
    return "\n\n".join(lines) if lines else "(근거 문서 없음)"


# Claude Messages API 어댑터 
class ClaudeLLM:
    name = 'claude'

    # SDK와 키를 확인하고 클라이언트를 만들기 
    def __init__(self) -> None:
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise ExternalServiceError("anthropic 패키지가 설치 되어 있지 않습니다.") from exc

        settings = get_settings() 
        key = settings.anthropic_api_key  # SecretStr | None 값이 비어있을 수도 있다. 
        if key is None:
            raise ExternalServiceError("ANTHROPIC_API_KEY 가 비어있습니다.")
        self._client = Anthropic(api_key=key.get_secret_value()) 
        self._model = settings.llm_model

    # 공통으로 사용하는 호출 함수 : Messages API를 한번 호출하고, 본문,토큰,걸린시간을 리턴 
    def _call(self, system: str, user_text: str) -> tuple[str, dict, int]:
        # system : 시스템 프롬프트 한 덩어리 
        # user_text : 사용자 메세지 본문 

        started = time.perf_counter()  # 시간차이 구하는 기능 
        # claude api 호출 
        try:
            response = self._client.messages.create(
                model=self._model, 
                max_tokens=get_settings().max_tokens, 
                system=system,
                messages=[{"role": "user", "content": user_text}],
            )
        except Exception as exc: 
            log.exception("Claude 호출 실패")
            raise ExternalServiceError(f"Claude 호출에 실패했습니다: {exc}") from exc

        # * 응답 받은 내용중 필요한 부분만 추출해서 우리 규격으로 만들기 *
        # 응답 텍스트 꺼내기 
        text = "".join(b.text for b in response.content if getattr(b, "type", "") == "text")
        usg = response.usage  # 사용량 정보 꺼내기 
        # 사용량 정보 정리 
        usage = {
            "input": getattr(usg, "input_tokens", 0) or 0, 
            "cache_read": getattr(usg, "cache_read_input_tokens", 0) or 0, 
            "cache_write": getattr(usg, "cache_creation_input_tokens", 0) or 0, 
            "output": getattr(usg, "output_tokens", 0) or 0,
        }
        # 걸린 시간 계산 
        elapsed = int((time.perf_counter() - started) * 1000) 
        # 결과 리턴 
        return text, usage, elapsed


    # 근거 문서를 싣고 질문에 답하는 함수 : ports.py의 LLMPort 메서드 구현체 
    def answer(self, *, question: str, contexts: list[dict], user: dict) -> LLMResult: 
        # question : 사용자 질문 
        # contexts : 근거 문서 목록. 
        # user : 질문한 사람. 
        system = _load_prompt("answer_system.md") 
        prompt = (
            f"## 사용자\n{user.get('name')} - {user.get('dept')}\n\n"
            f"## 근거 문서\n{_context_block(contexts)}\n\n"
            f"## 질문\n{question}"
        )
        text, usage, ms = self._call(system, prompt) # 위 _call 함수 불러서 호출하고 리턴데이터 받기 
        total_in = usage["input"] + usage["cache_read"] + usage["cache_write"] # 입력토큰 합계 
        return LLMResult(
            text=text, 
            model=self._model,
            input_tok=total_in,
            cache_tok=usage["cache_read"],
            output_tok=usage["output"],
            cost_krw=estimate_cost_krw(total_in, usage["output"]),
            latency_ms=ms
        )

    # 도구 목록을 함께 전달해 Messages API를 한번 호출 
    def _call_tools(self, system: str, messages: list[dict], tools: list[dict]) -> tuple[object, dict, int]:
        started = time.perf_counter() 
        try:
            resp = self._client.messages.create(
                model=self._model, 
                max_tokens=get_settings().max_tokens, 
                system=system, 
                messages=messages, 
                tools=tools, 
            )
        except Exception as e:
            log.exception("Claude 도구 호출 실패")
            raise ExternalServiceError(f"Claude 호출에 실패했습니다: {e}") from e 
        u = resp.usage 
        usage = {
            "input": getattr(u, "input_tokens", 0) or 0, 
            "cache_read": getattr(u, "cache_read_input_tokens", 0) or 0, 
            "cache_write": getattr(u, "cache_creation_input_tokens", 0) or 0, 
            "output": getattr(u, "output_tokens", 0) or 0,
        }
        return resp, usage, int((time.perf_counter() - started) * 1000)
    
   # 도구 목록을 전달하고, 1회 호출한다.
    def answer_with_tools(self, *, messages: list[dict], tools: list[dict], user: dict) -> LLMResult:
        system = _load_prompt("agent_system.md")
        system = f"{system}\n\n## 질문한 사람\n{user.get('name')} - {user.get('dept')}"
        resp, usage, ms = self._call_tools(system, messages, tools)
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        calls = [ToolCall(id=b.id, name=b.name, args=dict(b.input))
            for b in resp.content if getattr(b, "type", "") == "tool_use"]
        total_in = usage["input"] + usage["cache_read"] + usage["cache_write"]
        return LLMResult(
            text=text, model=self._model, input_tok=total_in, 
            cache_tok=usage["cache_read"], output_tok=usage["output"], 
            cost_krw=estimate_cost_krw(total_in, usage["output"]), latency_ms=ms, 
            extras={
                "tool_calls": calls, 
                "stop_reason": resp.stop_reason, 
                "blocks": [b.model_dump(exclude_none=True) for b in resp.content]
            }
        )

# 매개변수 추가
def answer(self, *, question: str, contexts: list[dict], user: dict, system: str | None = None ) -> LLMResult:

    system = system or _load_prompt("answer_system.md")
    prompt = (
        f"## 사용자\n{user.get('name')} - {user.get('dept')}\n\n"
        f"## 근거 문서\n{_context_block(contexts)}\n\n"
        f"## 질문\n{question}"

    )

# 모델이 코드펜스로 감싸서 보낸 경우, 원할한 파싱을 위한 전처리 함수 
def _extract_json(text: str) -> dict:
    # 정규 표현식으로 원하는 부분만 추출 
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    raw = fenced.group(1) if fenced else text

    # 펜스가 없으면 앞뒤에 설명 문장이 붙어 있을 수 있다. 첫 { 와 마지막 } 사이만 남긴다.
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        log.warning("응답 JSON 파싱 실패")
        return {}

    