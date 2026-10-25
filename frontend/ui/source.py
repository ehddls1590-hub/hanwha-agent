"""근거 문서 블록 — 인용문 왼쪽에 2px 세로선."""
from __future__ import annotations

import html

import streamlit as st

from ui.badge import badge_html


def source_html(
    *,
    title: str,
    version: str,
    locator: str,
    score: float,
    quote: str | None = None,
    extra_badge: tuple[str, str] | None = None,
    weak: bool = False,
) -> str:
    """
    weak=True 면 임계값 미달 — 빨간 유사도 배지 + 흐린 인용.
    extra_badge 예: ("시행 2025-07-01", "neutral")
    """
    score_tone = "no" if weak else "accent"
    chips = [badge_html(version, "accent"), badge_html(f"{score:.2f}", score_tone)]
    if extra_badge:
        chips.append(badge_html(*extra_badge))
    head = (
        f'<div class="ag-src-meta">{html.escape(locator)}</div>'
        f'<div style="font-weight:600;font-size:var(--ag-fs-sm)">{html.escape(title)} '
        + " ".join(chips)
        + "</div>"
    )
    cls = "ag-src ag-src--no" if weak else "ag-src"
    body = f'<div class="{cls}">{html.escape(quote)}</div>' if quote else ""
    return f'<div style="margin-bottom:var(--ag-s4)">{head}{body}</div>'


def sources(items: list[dict], *, weak: bool = False) -> None:
    """items: [{title, version, locator, score, quote?, extra_badge?}]"""
    st.markdown(
        "".join(source_html(weak=weak, **item) for item in items),
        unsafe_allow_html=True,
    )
