from collections.abc import Callable

from langgraph.graph import END, START, StateGraph

from app.agent.patterns import Step
from app.agent.state import WorkflowState

# search -> (pick이 고른 갈래) -> END
def build_graph(search: Step, routes: dict[str, Step], pick: Callable[[dict], str]):
    g = StateGraph(WorkflowState) # 상태 선언
    g.add_node("search", search) # 첫 단계 노드로 등록: 검색 
    for name, step in routes.items(): # 분기별 노트 등록, 각 노드는 END로 가는 선을 이어주기
        g.add_node(name, step)
        g.add_node(name, END )
    g.add_edge(START, "search") # 시작 -> search 실행
    g.add_conditional_edges("search", pick, {name: name for name in routes})
    return g.compile() # 그래프 생성

'''
START -> search -> pick(state) ----- "found"        -> found            -> END

                               ----- "insufficient" -> insufficient     -> END

'''



