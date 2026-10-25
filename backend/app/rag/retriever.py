# 검색 파이프라인 - 질문 하나를 근거가 될 만한 조각으로 변경하는 파일 

from __future__ import annotations

import time 

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.integrations.factory import get_embedder
from app.integrations.ports import RetrievalResult
from app.rag import store, policy
from app.rag.reranker import judge_gate, rerank

log = get_logger(__name__)

# 사람이 사용하는 낱말 -> 규정이 사용하는 낱말 
SYNONYMS = {
    "출장비": "여비 일비 숙박비 식비", 
    "여비": "출장비 일비 숙박비",
    "숙박": "숙박비 호텔 1박", 
    "교통": "교통비 KTX 항공",
    "기준": "규정 상한 지급 기준표",
    "신청서": "신청 양식 서식",
    "법인카드" : "카드 결제 사용",
    "재택": "재택근무 원격"
}

# 질문을 여러 각도로 고쳐 작성 -> 목록으로 리턴 
def expand_queries(question: str, n: int = 3) -> list[str]:
    q = (question or "").strip()  
    out = [q]   # 1. 원문 (오리지널 사용자 질문)
    extra = " ".join(v for k, v in SYNONYMS.items() if k in q)
    if extra:
        out.append(f"{q} {extra}")  # 2. 가상 사전에 걸리는 낱말이 있으면 동의어를 뒤에 덧붙인 질문 추가 

    # 3. 한 글자짜리 조사,군더더기 문자를 걷어내고, 남은 핵심어만으로 된 질문 
    core = " ".join(t for t in q.split() if len(t) > 1)[:120]
    if core and core != q:
        out.append(core)

    return out[:n]

# 긴 본문을 화면에 얹을 수 있는 만큼 줄여주는 함수
def _shorten(text: str, limit:int = 220) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[:limit - 1] + "..."

#  검색 결과 한건으 외부로 내보내는 모양으로 변경
def source_dict(row: dict) -> dict:
    return {**row, "score": round(float(row.get("score", 0.0)), 2),
            "quote": _shorten(row.get("text", ""))}

# 실제 DB를 확인하는 검색기 
class LiveRetriever: 
    name = "live"

    # 질문 하나를 검색 파이프라인에 통과시켜 근거 후보를 리턴해주는 메인 기능 
    def search(self, *, question: str, user: dict, session: Session, hybrid: bool = True,
               rerank_on: bool = True, reranker: str | None = None ) -> RetrievalResult:
        settings = get_settings()
        steps: list[dict] = []
        t0 = time.perf_counter()

        #1. 질의 재작성 
        queries = expand_queries(question, settings.multi_query_n)
        steps.append({"name": f"질의 재작성 · Multi-Query {len(queries)}건 생성",
                      "state": "ok", "time": f"{time.perf_counter() - t0:.1f}s"})
        #2. 갈래마다 벡터 검색 -> chunk_id로 중복 제거 
        embedder = get_embedder() 
        t1 = time.perf_counter()        # 키워드 단계 시작 시간 
        seen: dict[int, dict] = {} 
        question_vec: list[float] = []  # 원래 질문의 벡터를 담을 칸 
        for one in queries:
            vec = embedder.embed_query(one) 
            question_vec = question_vec or vec
            for row in store.vector_search(session, vec, limit=settings.retrieval_top_k):
                seen.setdefault(row["chunk_id"], row)      
        vector_rows = sorted(seen.values(), key=lambda r: r["score"], reverse=True)
        #3. 키워드 검색 -> 원문 하나로 한 번만 돌리기  
        keyword_rows = store.keyword_search(
            session, question, limit=settings.retrieval_top_k) if hybrid else [] 

        candidates = store.fuse(vector_rows, keyword_rows) if hybrid else vector_rows

        sims = store.vector_scores(session, question_vec, [c["chunk_id"] for c in candidates])
        for c in candidates:
            c["score"] = sims.get(c["chunk_id"], 0.0)
        steps.append({
            "name": f"벡터 + 키워드 하이브리드 검색 · 벡터 {len(vector_rows)}건 · "
            f"키워드 {len(keyword_rows)}건 -> 후보 {len(candidates)}", 
            "state": "ok" if keyword_rows else "no", 
            "time": f"{time.perf_counter() - t1:.1f}s"
        })  

        #4. 정책 필터
        t2 = time.perf_counter()
        kept, blocked = policy.filter_candidates(candidates, user=user, question=question)
        if blocked:
            log.info("정책으로 제외: %s", "/".join(blocked[:5]))

        #5 리랭킹
        top = (rerank(question, kept, top_n=settings.rerank_top_n, by=reranker)
               if rerank_on else kept[:settings.rerank_top_n])
        how = {"simple": "(간이)", "cross_encoder":"(크로스 인코더)"}.get(
            top[0].get("rerank_by","") if top else "","")
        steps.append({
            "name": f"후보 {len(kept)}건 -> 리렝킹{how} 상위 {len(top)}건",
            "state":"ok" if top else "no",
            "time": f"{time.perf_counter()- t2:.1f}s"
        })

        #6 임계값 검증
        sources = [source_dict(r) for r in top]
        best, threshold, passed = judge_gate(sources)
        steps.append({
            "name": f"유사도 임계값 검증 * 기준 {threshold:.2f} / 최고 {best:.2f}",
            "state": "ok" if passed else "no"
        })

        # 마무리 : 만료된 버전을 걸러서 답이 줄었다면, 그 사실을 사용자에게 알릴 메세지 한줄 만들기 
        expired = [b.split(" - ")[0] for b in blocked if "만료" in b]
        note = (f"{expired[0]}은(는) 만료된 버전이라 검색에서 제외 했습니다. "
                "과거 문서 버전을 보시려면, 질문에 '개정 전' 처럼 적어 주세요.") if expired else None

        return RetrievalResult(sources=sources, steps=steps, best_score=best,
                               passed=passed, version_note=note, threshold=threshold)