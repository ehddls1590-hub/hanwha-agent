from __future__ import annotations

from app.tools.registry import SideEffect, Tool, register

SCHEMA = {
    "name" : "send_slack", 
    "description": "Slack 채널에 메세지를 보낸다. 외부로 나가므로 팀장 승인이 필요하다.", 
    "input_schema": {
        "type": "object", 
        "properties": {
            "text": {"type": "string", "description": "보낼 문구. 초안을 요약한 한두 문장."},
        },
        "required": ["text"],
    },
}

# approval_service 전용 함수 - 직접 호출 X 
def _execute(*, text: str, channel: str = "") -> dict:
    from app.integrations.factory import get_slack 

    result = get_slack().post(channel=channel, text=text)
    return {"ok": result.ok, "channel": result.channel, "ts": result.ts, 
            "error": result.error, "simulated": result.simulated}

# 도구 등록 
register(Tool(name=SCHEMA["name"], description=SCHEMA["description"],
              side_effect=SideEffect.EXTERNAL, fn=_execute, schema=SCHEMA, 
              reversible=False))

