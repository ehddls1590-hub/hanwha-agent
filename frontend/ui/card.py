"""카드 · 안내 노트 · 메시지 블록 · 페이지 헤더."""
from __future__ import annotations

import html
from contextlib import contextmanager

import streamlit as st

from ui.badge import badge_html


def inline_md(text: str) -> str:
    """**굵게** 와 줄바꿈만 HTML 로 바꾼다.

    HTML 블록(.ag-note 등) 안에 넣는 문장은 Streamlit 이 마크다운을 처리해 주지 않는다.
    전체 마크다운 파서를 넣을 일은 아니라서 두 가지만 처리한다.
    """
    out = html.escape(text or "")
    while out.count("**") >= 2:
        out = out.replace("**", "<b>", 1).replace("**", "</b>", 1)
    return out.replace("\n\n", "<br><br>").replace("\n", "<br>")


def card_html(body: str, *, label: str | None = None, title: str | None = None) -> str:
    parts = ['<div class="ag-card">']
    if label:
        parts.append(f'<div class="ag-card-label">{html.escape(label)}</div>')
    if title:
        parts.append(f'<div class="ag-card-title">{html.escape(title)}</div>')
    parts.append(body)
    parts.append("</div>")
    return "".join(parts)


def card(body: str, *, label: str | None = None, title: str | None = None) -> None:
    st.markdown(card_html(body, label=label, title=title), unsafe_allow_html=True)


@contextmanager
def bordered(label: str | None = None):
    """Streamlit 위젯(버튼 등)을 안에 넣어야 할 때 쓰는 테두리 컨테이너."""
    box = st.container(border=True)
    with box:
        if label:
            st.markdown(f'<div class="ag-card-label">{html.escape(label)}</div>',
                        unsafe_allow_html=True)
        yield box


def note(text: str, tone: str = "", *, markdown: bool = False) -> None:
    """왼쪽 세로선이 있는 안내 블록. tone: '' | 'ok' | 'wait' | 'no'

    markdown=True 면 **굵게** 와 줄바꿈을 해석한다.
    """
    cls = f"ag-note ag-note--{tone}" if tone else "ag-note"
    body = inline_md(text) if markdown else text
    st.markdown(f'<div class="{cls}">{body}</div>', unsafe_allow_html=True)


def message_block(text: str) -> None:
    """Slack 전송 문구처럼 '그대로 나갈 텍스트'를 보여주는 블록."""
    st.markdown(f'<div class="ag-msg">{html.escape(text)}</div>', unsafe_allow_html=True)


def log_block(lines: list[str]) -> None:
    """감사 로그 — 모노스페이스."""
    body = html.escape("\n".join(lines))
    st.markdown(f'<div class="ag-log">{body}</div>', unsafe_allow_html=True)


def meta_footer(text: str) -> None:
    """응답 하단 메타: 3.1s · 입력 4,120 tok · 42원 · haiku-4.5"""
    st.markdown(f'<div class="ag-meta">{html.escape(text)}</div>', unsafe_allow_html=True)


def page_header(
    title: str,
    *,
    crumb: str | None = None,
    subtitle: str | None = None,
    badges: list[tuple[str, str | None]] | None = None,
) -> None:
    out = []
    if crumb:
        out.append(f'<div class="ag-crumb">{html.escape(crumb)}</div>')
    chips = " ".join(badge_html(t, tone) for t, tone in (badges or []))
    out.append(
        f'<div class="ag-head"><h1 style="margin:0">{html.escape(title)}</h1>{chips}</div>'
    )
    if subtitle:
        out.append(f'<div class="ag-sub">{html.escape(subtitle)}</div>')
    st.markdown("".join(out), unsafe_allow_html=True)
