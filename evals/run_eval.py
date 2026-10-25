# 골든셋 30문항으로 검색 정확도를 측정하는 채점기 

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"backend"))

import yaml

from app.core.config import get_settings
from app.db.session import session_scope 
from app.integrations.factory import get_embedder
from app.models import EvalRun
from app.rag import policy, store
from app.rag.retriever import LiveRetriever  
from app.rag.reranker import judge_gate

settings = get_settings() 
GOLDEN = Path(__file__).parent / "golden_set.yaml"
REPORTS = Path(__file__).parent / "reports"
DEFAULT_TOP_N = 3      # 상위 몇 건 안에 들어오면 맞는 것으로 볼 것인가 

# 설정 목록.
CONFIGS = [
    {"name": "기본 검색"},
    {"name": "+ Multi-Query", "multi_query": True},
    {"name": "+ 하이브리드", "multi_query": True, "hybrid": True},
    {"name": "+ 리랭킹", "multi_query": True, "hybrid": True, "rerank": True, "reranker": "simple"},
    {"name": "+ 크로스 인코더", "multi_query": True, "hybrid": True, "rerank": True, "reranker": "cross_encoder"},
]

# 관리자 시각으로 테스트 
EVAL_USER = {"id": "2011-0003", "name":"한서영", "clearance": "대외비", "dept_id": "HR"}


# 질문 하나로 후보를 뽑고 정책으로 거른 뒤, 상위 N건만 남기는 함수 
def retrieve(session, question: str, top_n: int, cfg: dict | None = None) -> list[dict]:
    if (cfg or {}).get("multi_query"): 
        result = LiveRetriever().search(question=question, user=EVAL_USER, session=session, hybrid=bool(cfg.get("hybrid")),
                                        rerank_on=bool(cfg.get("rerank")), reranker=cfg.get("reranker"))
        return result.sources[:top_n] 

    embedder = get_embedder()
    rows = store.vector_search(session, embedder.embed_query(question), limit=settings.retrieval_top_k)
    kept, _ = policy.filter_candidates(rows, user=EVAL_USER, question=question)
    return kept[:top_n] 

# 문항 한개를 채점하는 함수 
def judge(item: dict, hits: list[dict]) -> tuple[bool, str]:

    best, threshold, _ = judge_gate(hits)
    if item.get("unanswerable"):
        ok = best < threshold
        return ok, "근거 부족 정상" if ok else f"임계값 초과({best:.2f}) - 지어낼 위험"
    if best < threshold:
        return False, f"임계값 미달({best:.2f})"

    for h in hits:
        if h.get("doc_id") != item.get("expect_doc"):
            continue
        if item.get("expect_version") and h.get("version") != item["expect_version"]: 
            continue
        if item.get("expect_kind") and h.get("kind") != item["expect_kind"]:
            continue
        keywords = item.get("expect_keywords") or []
        if keywords and not all(k in h.get("text", "") for k in keywords):
            continue
        return True, f"{h['doc_id']} {h['version']} · {h['locator']}"

    return False, "정답 문서가 상위에 없음"


# 설정 하나로 골든셋 문항을 전부 테스트하고, 결과를 하나로 모아주는 함수 
def run_config(cfg: dict, items: list[dict], top_n: int) -> dict:
    results = []
    with session_scope() as session:
        for item in items:
            hits = retrieve(session, item["question"], top_n, cfg)
            ok, why = judge(item, hits)
            results.append({"id": item["id"], "type": item.get("type",""), 
                            "question": item["question"], "ok": ok, "why": why})

    correct = sum(1 for r in results if r["ok"])
    accuracy = round(correct / len(results) * 100, 1) if results else 0.0

    by_type: dict[str, dict] = {}
    for r in results: 
        bucket = by_type.setdefault(r["type"], {"n": 0, "ok": 0})
        bucket["n"] += 1
        bucket["ok"] += 1 if r["ok"] else 0 

    return {"config": cfg["name"], "accuracy": accuracy, "correct": correct, 
            "total": len(results), "by_type": by_type, "results": results}


# 리포트 파일 남기고 총점만 eval_runs DB 테이블에 저장 
def save(report: dict) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORTS / f"eval_{stamp}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    with session_scope() as session:
        session.query(EvalRun).delete()
        for i, run in enumerate(report["runs"]):
            session.add(EvalRun(config=run["config"], ord=i, accuracy=run["accuracy"], 
                                item_count=run["total"], measured_at=datetime.now()))
    return path 

def main() -> int:
    parser = argparse.ArgumentParser(description="골든셋 정확도 측정")
    parser.add_argument("--config", help="한 가지 설정만 측정")
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    parser.add_argument("--no-save", action="store_true", help="DB,파일에 남기지 않음")
    args = parser.parse_args()  

    items = yaml.safe_load(GOLDEN.read_text(encoding="utf-8"))["items"]
    configs = [c for c in CONFIGS if not args.config or c["name"] == args.config]
    if not configs:
        print(f" 알 수없는 설정 : {args.config}")
        return 1 

    print(f"\n 문항 {len(items)}개. 임계값 벡터 {settings.retrieval_threshold}. "
          f"크로스 인코더 {settings.rerank_threshold}. 상위 {args.top_n}건\n")
    runs = []
    for cfg in configs:
        run = run_config(cfg, items, args.top_n)
        runs.append(run)
        print(f" {run['config']:16} {run['accuracy']:5.1f}% ({run['correct']}/{run['total']})")
        for type_name, bucket in sorted(run["by_type"].items()):
            rate = bucket["ok"] / bucket["n"] * 100
            print(f"   {type_name:22} {rate:5.1f}% ({bucket['ok']}/{bucket['n']})")
        print() 

    report = {"measured_at" : datetime.now().isoformat(timespec="seconds"), 
              "threshold": settings.retrieval_threshold, "rerank_threshold": settings.rerank_threshold,
                "top_n": args.top_n, "runs": runs}

    if not args.no_save:
        print(f"  리포트: {save(report)}\n")
    return 0 

if __name__ == "__main__":
    raise SystemExit(main())






