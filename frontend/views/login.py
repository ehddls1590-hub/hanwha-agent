from __future__ import annotations

import streamlit as st
from core import session

# 화면 그리기 
def render() -> None:
    st.title("사내 업무 에이전트")
    st.write("사번과 비밀번호로 로그인하세요. 계정은 강사가 나눠 준 목록에 있습니다.")

    st.text_input("사번", key="login_emp_no", placeholder="예) 2016-0231")
    st.text_input("비밀번호", type="password", key="login_pw")

    if not st.button("로그인"):
        return

    try:
        from core import api_client
    except ImportError:
        st.info("백엔드 호출 통로(core/api_client.py)는 02번에서 붙입니다.")
        return

    try:
        user = api_client.login(
            st.session_state["login_emp_no"],
            st.session_state["login_pw"],
        )
    except api_client.ApiError as exc:
        st.error(str(exc))
        return

    session.login(user)

    st.rerun()
