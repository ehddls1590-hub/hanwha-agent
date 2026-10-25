from __future__ import annotations

import streamlit as st

# 상태 초기값
DEFAULTS: dict = {
    "page": "login",
    "user": None,
    "f_dept": "전체",
    "f_level": "전체",
    "f_status": "현행",
    "f_q": "",
}

# 상태에 초기값 채우기.
def init_state() -> None:
    for key, value in DEFAULTS.items():
        # 화면 리턴되어도 남아있는 데이터 유지되는 변수들 초기화
        st.session_state.setdefault(key, value)
        # 필터 값을 화면 이동 되어도 남도록 기록.
    for key in ("f_dept","f_level", "f_status", "f_q"):
        st.session_state[key] = st.session_state[key]

# 현재 사용자 로그인 여부 체크 : 로그인 -> 사용자 정보, 비 로그인 -> None
def current_user() -> dict | None:
    return st.session_state.get("user")
    

# 로그인 야부 확인 : 로그인하면 True, 아니면 False
def is_authenticated() -> bool:
    return current_user() is not None


# 로그인 상태로 만들고, 문서 목록 화면으로 이동
def login(user: dict) -> None:
    st.session_state["user"] = user
    st.session_state["page"] = "documents"


def logout() -> None:
    st.session_state["user"] = None
    st.session_state["page"] = "login"
    for key in ("f_dept", "f_level", "f_status", "f_q"):
        st.session_state[key] = DEFAULTS[key]

# 지금 사용자의 사번
def emp_no() -> str | None:
    user = current_user()
    return user["emp_no"] if user else None
