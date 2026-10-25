"""배지 — 상태를 한 단어로 보여준다."""
from __future__ import annotations

import html

import streamlit as st

# 상태 문자열 → 색. 여기 없는 값은 neutral 로 떨어진다.
_TONE_BY_TEXT = {
    "현행": "ok", "완료": "ok", "승인": "ok", "승인·실행": "ok", "유효": "ok", "정상": "ok",
    "대기": "wait", "대기중": "wait", "진행 중": "wait", "진행중": "wait", "재임베딩": "wait",
    "만료": "no", "반려": "no", "반려됨": "no", "차단": "no", "위험": "no", "실패": "no",
    "보관": "neutral",
}
_TONES = {"ok", "wait", "no", "accent", "neutral", "count"}


def tone_for(text: str) -> str:
    for key, tone in _TONE_BY_TEXT.items():
        if text.startswith(key):
            return tone
    return "neutral"


def badge_html(text: str, tone: str | None = None) -> str:
    """배지 HTML 문자열. 표 셀 안에 넣을 때 쓴다."""
    tone = tone or tone_for(text)
    if tone not in _TONES:
        tone = "neutral"
    return f'<span class="ag-badge ag-badge--{tone}">{html.escape(str(text))}</span>'


def badge(text: str, tone: str | None = None) -> None:
    st.markdown(badge_html(text, tone), unsafe_allow_html=True)


def badges(items: list[tuple[str, str | None]]) -> None:
    st.markdown(" ".join(badge_html(t, tone) for t, tone in items), unsafe_allow_html=True)
