# 도구(tool) 등록소 
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from app.core.exceptions import ApprovalRequired

class SideEffect(str, Enum):
    NONE = "none"               # 조회 
    INTERNAL = "internal"       # 내부 쓰기 (우리 DB만 변경)
    EXTERNAL = "external"       # 외부 실행 -> 되돌릴 수 없다. 승인 필요 


# 도구 한개 
@dataclass
class Tool:
    name: str
    description: str
    side_effect: SideEffect
    fn: Callable
    schema: dict 
    reversible: bool = True 

    def run(self, **kwargs) -> dict:
        if self.side_effect is SideEffect.EXTERNAL:
            raise ApprovalRequired(f"'{self.name}'은 승인 없이 실행할 수 없습니다.", 
                                   detail="approval_service.approve()를 통해서만 실행됩니다.")
        return self.fn(**kwargs)

# 도구 저장소 
_REGISTRY: dict[str, Tool] = {}

# 도구를 목록에 올리는 함수 
def register(tool: Tool) -> Tool:
    tool.side_effect = SideEffect(tool.side_effect)
    _REGISTRY[tool.name] = tool 
    return tool 

# 도구 꺼내는 함수 
def get(name: str) -> Tool:
    if name not in _REGISTRY:
        raise KeyError(f"등록되지 않은 도구: {name}")
    return _REGISTRY[name]

# 등록된 도구 전부 조회 함수 
def all_tools() -> list[Tool]:
    return list(_REGISTRY.values())

# 도구 모듈을 import 해서 등록시키는 함수 
def load_all() -> None:
    from app.tools import create_draft, search_documents

    for m in (search_documents, create_draft):
        register(Tool(name=m.NAME, description=m.SCHEMA["description"],
                      side_effect=m.SIDE_EFFECT, fn=m.run, schema=m.SCHEMA))
        
    from app.tools import send_slack
    from app.tools import get_document_versions