from __future__ import annotations

from html import escape
import streamlit as st

from core import api_client, router, session
from ui.badge import badge_html
from ui.card import card, page_header
from ui.chart import timeline
from ui.status import progress

DEFAULT_DOC = "DOC-HR-014"

def render() -> None:
    doc_id = st.session_state.get("selected_doc", DEFAULT_DOC)

    if st.button("← 문서 관리", key="back_docs"):
        router.go("documents")     

    try:
        doc = api_client.get_document(doc_id, emp_no=session.emp_no())
        versions = api_client.list_versions(doc_id, emp_no=session.emp_no())
    except api_client.ApiError as exc:
        st.error(str(exc))
        return

    page_header(
        doc["title"],
        crumb=f"문서 관리 › {doc['doc_id']}",
        subtitle=f"{doc['dept']} · 보안등급 {doc['security_level']} · {doc['file_format'].upper()}",
        badges=[(f"현행 {doc['version']}", "ok")],
    )

    left, right = st.columns([2.1, 1])
    with left:
        _version_timeline(versions) # 버전 이력
    with right:
        _policy_card() # 검색 정책
        _actions(doc["doc_id"], doc["version"]) # 작업 버튼 (처리 과정 시작)

# 버전 하나를 타임라인 항목 하나로 만들어주는 함수
def _version_block(v: dict) -> str: 
    label = "현행 · 검색 대상" if v["searchable"] else f"{v['status']} · 검색 제외"
    tone = "ok" if v["searchable"] else "neutral"
    detail = " · ".join(x for x in [
        v["period"],
        v["embed_model"] or "임베딩 모델 미기록",
        f"임베딩 완료 {v['indexed_at']}" if v["indexed_at"] else "임베딩 이력 없음",
    ] if x)
    return (
        '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">'
        f'<span style="font-weight:700;font-size:var(--ag-fs-lg)">{escape(v["version"])}</span>'
        f'{badge_html(label, tone)}'
        f'<span style="color:var(--ag-muted);font-size:var(--ag-fs-xs)">'
        f'청크 {v["chunk_count"]} · 검색 반영 {escape(v["index_status"])}</span></div>'
        f'<div class="ag-src-meta">{escape(detail)}</div>'
    )

def _version_timeline(versions: list[dict]) -> None:
    st.subheader("버전 이력")
    if not versions:
        st.info("등록된 문서 버전이 없습니다. ")
        return
    timeline([_version_block(v) for v in versions])
    st.caption("변경 이력(누가 언제 올렸는가)은 추후 감사 로그에서 전달받을 예정")

# 검색 정책 카드 그리기 
def _policy_card() -> None: 
    st.subheader("검색 정책")
    rows = [
        ("현행 버전만 기본 검색", badge_html("ON", "ok")),
        ("사용자 요청 시 과거 판 조회", badge_html("ON", "ok")),
        ("보안등급 필터", badge_html("ON", "ok")),
        ("판정 합격선", badge_html("크로스 인코더 0.2 * 벡터 0.60", "neutral")),
    ]
    body = "".join(
        '<div style="display:flex;justify-content:space-between;align-items:center;'
        'padding:9px 0;border-bottom:1px solid var(--ag-line)">'
        f'<span style="font-size:var(--ag-fs-sm)">{escape(label)}</span>{chip}</div>'
        for label, chip in rows
    )
    card(body)
    st.caption("값은 backend/app/rag/policy.py 의 SearchPolicy 와 .env의 합격선을 정합니다.")

  # 작업 버튼 그리기. 
def _actions(doc_id: str, version: str) -> None: 
    st.subheader("작업")
    if st.button("새 버전 업로드", type="primary", use_container_width=True):
        router.go("document_upload")
    if st.button("재임베딩", use_container_width=True):
        try:
            job = api_client.reindex(doc_id, version, emp_no=session.emp_no())
        except api_client.ApiError as e:
            st.error(str(e))
            return 
        st.session_state["reindex_job"] = job["job_id"]
        st.rerun() 

    _watch_job() 

# 접수한 재임베딩 작업의 진행 상태를 그리는 함수 
def _watch_job() -> None: 
    job_id = st.session_state.get("reindex_job")
    if not job_id:
        return 
    try:
        job = api_client.get_job(job_id, emp_no=session.emp_no())
    except api_client.ApiError as e:
        st.warning(f"작업 상태를 못 읽었습니다: {e}")
        return

    st.caption(f"재임베딩 {job['status']} · 청크 {job['chunk_count']}")
    progress(job['progress'])
    if job["status"] in ("완료", "실패"):
        st.session_state.pop("reindex_job", None)
        if job["message"]:
            st.caption(job["message"])
    elif st.button("다시 보기", key="poll_index"):
        st.rerun() 
