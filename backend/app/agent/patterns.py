# 에이전트 패턴 세 가지 - 순서(체이닝), 갈래(라우팅), 동시(병렬) 

from __future__ import annotations

from collections.abc import Callable

# ------ 체이닝 ----------------------------------------
# 단계 = state를 받아 변경된 키만 돌려주는 함수.
Step = Callable[[dict], dict]

# 단계를 목록 순서대로 부르고, 단계마다 변경된 키를 state에 합치는 함수 
def run_chain(steps: list[Step], state: dict) -> dict: 
    trace = state.setdefault("trace", [])
    for step in steps:
        changed = step(state)              # 단계에서 변경된 키만 리턴 
        trace.append(step.__name__)        # 어디까지 왔는지 
        state.update(changed)              # 없던 키는 더하고, 있는 키는 덮어쓰기 
        if "error" in changed:             # 에러 발생 -> 다음 스텝은 부르지 않는다. 
            break
    return state 


# --------- 라우팅 -------------------------------------
#  검색 후, 라우팅 : 근거가 기준을 넘었는지. 
def route_after_search(state: dict) -> str: 
    return "found" if state.get("passed") else "insufficient" 

#  라우팅 함수 
def route(state: dict, pick: Callable[[dict], str], routes: dict[str, Step]) -> dict: 
    name = pick(state)
    if name not in routes: 
        raise KeyError(f"작업 갈래 표에 없는 이름: {name!r} - 존재하는 이름: {sorted(routes)}")
    return {"route": name, **routes[name](state)}


# -------- 병렬 처리 -------------------------------------
from concurrent.futures import ThreadPoolExecutor

def run_parallel(calls: dict[str, tuple[Callable[..., dict], dict]], max_workers: int = 4) -> dict[str, dict]:
    with ThreadPoolExecutor(max_workers=max_workers) as ex: 
        futures = {name: ex.submit(fn, **kwargs) for name, (fn, kwargs) in calls.items()}
    out: dict[str, dict] = {} 
    for name, f in futures.items(): 
        try:
            out[name] = f.result() 
        except Exception as e: 
            out[name] = {"error": f"{type(e).__name__}: {e}"}
    return out


