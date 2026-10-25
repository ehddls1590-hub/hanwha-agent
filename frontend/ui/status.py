"""처리 단계 목록 — 검색 과정 · 업로드 파이프라인."""
from __future__ import annotations

import html

import streamlit as st

_MARK = {"ok": "✓", "no": "✕", "wait": "◐", "todo": "·"}


def steps_html(items: list[dict]) -> str:
    """items: [{name, state: 'ok'|'no'|'wait'|'todo', time?}]"""
    out = ['<div class="ag-steps">']
    for it in items:
        state = it.get("state", "todo")
        time = it.get("time") or ("—" if state in ("no", "todo") else "")
        out.append(
            f'<div class="ag-step ag-step--{state}">'
            f'<div class="ag-step-mark">{_MARK.get(state, "·")}</div>'
            f'<div class="ag-step-name">{html.escape(str(it["name"]))}</div>'
            f'<div class="ag-step-time">{html.escape(str(time))}</div>'
            f"</div>"
        )
    out.append("</div>")
    return "".join(out)


def steps(items: list[dict]) -> None:
    st.markdown(steps_html(items), unsafe_allow_html=True)


def progress(pct: int) -> None:
    pct = max(0, min(100, int(pct)))
    st.markdown(
        f'<div class="ag-progress"><div class="ag-progress-fill" style="width:{pct}%"></div></div>'
        f'<div class="ag-src-meta" style="text-align:right">{pct}%</div>',
        unsafe_allow_html=True,
    )
