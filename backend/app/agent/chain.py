# 우리 포트를 Runnable로 만들어주는 로직처리
# servies/chat_service.py -> agent/chain.py -> integrations/ports.LLMPort 주입 
# mock / live 분기 처리 X
# 재시도, 폴백 처리 X

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda

from app.integrations.ports import LLMPort, LLMResult

# 현재 파일 기준으로 app/agent/prompts 폴더경로 잡아놓기
PROMPT_DIR = Path(__file__).parent / "prompts"

# md 파일 찾아 읽어 문자열로 리턴해주는 함수
def load_prompt(name:str):
    # name: 확장자를 뺀 md 파일명 "answer_system"
    path = PROMPT_DIR / f"{name}.md"
    if not path.is_file():
        raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다:{path}")
    return path.read_text(encoding="utf-8").strip() # 파일 읽은 내용 앞뒤 공백 없애고 리턴

# system + human 두 칸짜리 프롬프트 템플릿을 만들어주는 함수
def build_prompt(*, system_prompt: str | None = None) -> ChatPromptTemplate:
    # system_prompt : 시스템 메세지 본문. 외부에서 주지 않으면 answer_system 으로 처리
    system_prompt = system_prompt or load_prompt("answer_system")
    return ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_prompt),
            ("human", "{question}")
        ]
    )

# 메인 함수 : 질문 -> LLMResult 
def build_result_chain(
        llm: LLMPort,
        *,
        system_prompt: str | None = None,
        contexts: list[dict] | None = None,
        user: dict | None = None,
) -> Runnable:
    # llm : LLMPort를 만족하는 어댑터. 추후 LLMPort 규격만 맞으면 다른 API 모델 사용가능
    # contexts : 근거 목록
    # user : 질문한 사람
    prompt = build_prompt(system_prompt=system_prompt)
    port_contexts: list[dict] = [] if contexts is None else contexts
    port_user: dict = {} if user is None else user

    # ChatPromptTemplate -> LLMResult 연결 다리
    def call_port(value) -> LLMResult:
        messages = value.to_messages()
        question = str(messages[-1].content) # human message
        if system_prompt is None:
            return llm.answer(question=question, contexts=port_contexts, user=port_user)
        return llm.answer(question=question, contexts=port_contexts, user=port_user, system=str(messages[0].content)) # system prompt

    llm_step = RunnableLambda(call_port).with_config(run_name="LLMPort")

    return prompt | llm_step # 파이프라인 연결해서 리턴 -> 받은 쪽에서  with_retry()로 재시도 가능

# 질문 -> 답변 문자열
def build_answer_chain(llm: LLMPort, **kwargs) -> Runnable:
    # 결과가 있으면 텍스트만 추출해서 runnable 타입으로 리턴
    return build_result_chain(llm, **kwargs) | RunnableLambda(lambda r: r.text)

# 질문 -> schema 객체 파싱해서 리턴
def build_parsed_chain(llm: LLMPort, *, schema: type, **kwargs) -> Runnable:
    # schema : 결과를 담을 pydantic 모델
    parser = PydanticOutputParser(pydantic_object=schema)
    base = kwargs.pop("system_prompt", None) or load_prompt("answer_system")
    system_prompt = f"{base}\n\n{parser.get_format_instructions()}"
    return build_answer_chain(llm, system_prompt=system_prompt, **kwargs) | parser






