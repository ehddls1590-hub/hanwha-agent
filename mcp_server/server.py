from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent 

sys.path.insert(0, str(ROOT / "backend"))

from app.core.logging import setup_logging 

# 우리 로그와 우리가 부른 라이브러리의 로그를 표준 오류로 내보기 
setup_logging(stream=sys.stderr)

# 진짜 출구를 변수에 담아두기 
_PROTOCOL_OUT = sys.stdout

# 사용자가 실수로 print를 해도 표준 오류로 나가도록 처리 
sys.stdout = sys.stderr 

# 지정된 MCP 프로토콜 버전 중 선택 
PROTOCOL_VERSION = "2024-11-05"

SERVER_INFO = {"name": "hanwha-agent", "version": "1.0.0"}

CAPABILITIES: dict = {} 

# 메세지 한 줄을 stdout에 작성하는 함수 
def respond(msg_id, result=None, error=None) -> None:
    payload = {"jsonrpc": "2.0", "id": msg_id}
    if error is not None: 
        payload["error"] = error
    else:
        payload["result"] = result 

    _PROTOCOL_OUT.write(json.dumps(payload, ensure_ascii=False) + '\n')
    _PROTOCOL_OUT.flush() 


# handshake 기능 
def on_initialize(msg_id, params: dict) -> None: 
    respond(msg_id, {"protocolVersion": PROTOCOL_VERSION, 
                     "capabilities": CAPABILITIES, "serverInfo": SERVER_INFO})

# ping 
def on_ping(msg_id, params: dict) -> None: 
    respond(msg_id, {})


# 메서드 이름: 처리 함수 형태로 도구 저장 
METHODS = {"initialize": on_initialize, "ping": on_ping}


# 요청 한 건을 처리 함수에 넘겨주는 함수 
def handle(message: dict) -> None: 
    msg_id = message.get("id")
    if msg_id is None:
        return 
    fn = METHODS.get(message.get("method"))
    if fn is None: 
        respond(msg_id, error={"code": -32601,
                               "message": f"지원하지 않는 메서드: {message.get('method')}"})
        return 
    fn(msg_id, message.get("params") or {})

# -------- 도구 적용 -----------------------------------
from app.tools import registry

USER_TOOLS = ("search_documents",)

CLEARANCE = { "type": "string", "enum": ["일반","3급","대외비"], "description": "조회자의 보안등급. 기본값 일반"}

# 외부에 내놓을 도구 (side_effect 가 none인 도구들만)
def _exposed() -> dict:
    registry.load_all()
    return {t.name: t for t in registry.all_tools() if t.side_effect is registry.SideEffect.NONE}

# 등록기 -> MCP 모양으로 옯기기
def on_tools_list(msg_id, params: dict) -> None:
    tools = []
    for t in _exposed().values():
        props = dict(t.schema["input_schema"]["properties"])
        if t.name in USER_TOOLS:
            props["clearance"] = CLEARANCE
        schema = {**t.schema["input_schema"], "properties": props}
        tools.append({"name":t.name, "description": t.description, "inputSchema": schema})
    respond(msg_id, {"tools": tools})

CAPABILITIES["tools"] = {}
METHODS["tools/list"] = on_tools_list

# ---- 도구 호출 -----------------------------------
# 도구 하나 부르는 함수 + 예외 처리
def on_tools_call(msg_id, params: dict) -> None:
    name = params.get("name")
    args = dict(params.get("arguments") or {})
    tool = _exposed().get(name)
    if tool is None:
        respond(msg_id, error={"code": -32601, "message": f"알 수 없는 도구 : {name}"})
        return
    clearance = args.pop("clearance", " 일반")
    ours = ({"user": {"id": "mcp","name": "MCP", "clearance": clearance, "dept_id": ""}} if name in USER_TOOLS else {})

    try:
        out = tool.run(**args, **ours)

    except Exception as e:
        respond(msg_id, {"content": [{"type": "text", "text": f"도구 실행 중 오류: {e}"}],
                         "isError": True})
        return

    text = json.dumps(out, ensure_ascii=False, default=str)
    respond(msg_id, {"content": [{"type": "text", "text": text}], "isError": "error" in out})

METHODS["tools/call"] = on_tools_call


def main() -> int:
    print("[hanwha-agent MCP] 메서드 " + " ·· ".join(METHODS), file=sys.stderr)
    for line in sys.stdin: 
        line = line.strip() 
        if not line: 
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        handle(message)

    return 0 

if __name__ == "__main__":
    raise SystemExit(main())
