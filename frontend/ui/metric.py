"""지표 타일 — st.metric 대신 색·간격을 우리가 잡는다."""
from __future__ import annotations

import html

import streamlit as st


def metrics(items: list[dict]) -> None:
    """
    items: [{label, value, delta?, tone?}]
      tone: '' | 'ok' | 'wait' | 'no'
    """
    out = ['<div class="ag-metrics">']
    for it in items:
        tone = it.get("tone") or ""
        cls = f"ag-metric ag-metric--{tone}" if tone else "ag-metric"
        delta = it.get("delta")
        delta_html = (
            f'<div class="ag-metric-delta" style="color:var(--ag-muted)">'
            f"{html.escape(str(delta))}</div>"
            if delta
            else ""
        )
        out.append(
            f'<div class="{cls}">'
            f'<div class="ag-metric-label">{html.escape(str(it["label"]))}</div>'
            f'<div class="ag-metric-value">{html.escape(str(it["value"]))}</div>'
            f"{delta_html}</div>"
        )
    out.append("</div>")
    st.markdown("".join(out), unsafe_allow_html=True)
