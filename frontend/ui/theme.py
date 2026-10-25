"""CSS 주입 — 앱 최상단에서 호출한다.

★ 주의: Streamlit 은 재실행할 때마다 화면을 처음부터 다시 그린다.
   "한 번만 주입" 하려고 session_state 로 막으면, 두 번째 실행부터
   스타일이 통째로 사라진다. (실제로 그렇게 만들었다가 화면이 무너졌다)
   그래서 **매 실행마다 주입하고, 파일 읽기만 캐시한다.**
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import streamlit as st

# ui/theme.py 기준으로 ../asset/
ASSETS = Path(__file__).resolve().parent.parent / "asset"
FILES = ("tokens.css", "base.css", "components.css")  # 순서 중요


@lru_cache(maxsize=1)
def load_css() -> str:
    parts = []
    for name in FILES:
        path = ASSETS / name
        if path.exists():
            parts.append(f"/* ===== {name} ===== */\n{path.read_text(encoding='utf-8')}")
        else:  # 배포본에서 파일이 빠져도 앱이 죽지는 않게
            parts.append(f"/* !! {name} 없음 !! */")
    return "\n".join(parts)


def inject_css() -> None:
    """앱 전체에 디자인 시스템을 적용한다. 매 실행마다 호출되어야 한다."""
    st.markdown(f"<style>\n{load_css()}\n</style>", unsafe_allow_html=True)
