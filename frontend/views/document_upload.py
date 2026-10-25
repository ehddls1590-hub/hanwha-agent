from __future__ import annotations
import time
import streamlit as st
from core import api_client, router, session
from core.api_client import ApiError
from ui.badge import badge_html
from ui.card import page_header
from ui.status import progress, steps

DEPTS = {'HR': '경영지원팀', 'HRGA': '인사총무', 'INFRA2': '인프라사업부 2팀', 'PMO': 'PMO', 'PU': '구매팀', 'SE': '보안팀'}
LEVELS = ['일반', '3급', '대외비']
ACCEPT = ['docx', 'pdf']

# 화면 그리기 함수 
def render() -> None:
    page_header("문서 업로드", crumb="문서 관리 > 업로드", subtitle="DOCX · PDF 를 파싱해 조항 단위와 표 단위로 나눠 저장합니다. ")
    if st.button("← 문서 관리"):
        router.go('documents')
    job_id = st.session_state.get('upload_job')
    # job_id가 유무에 따른 화면 분기 
    if job_id:
        _render_progress(job_id) # 업로드 과정 나타내는 화면 
    else:
        _render_form()  # 업로드 폼페이지 화면 


# 문서 등록 폼 화면 그리기 
def _render_form() -> None:
    up = st.file_uploader('파일을 끌어다 놓으세요', type=ACCEPT)
    doc_id = st.text_input('문서번호', value='DOC-FI-009')
    title = st.text_input('문서명', value='법인카드 사용 지침')
    version = st.text_input('판 번호', value='v1.4')
    effective_from = st.text_input('시행일', value='2025-07-01')
    dept_id = st.selectbox('소관 부서', options=list(DEPTS), format_func=DEPTS.get)
    security_level = st.selectbox('보안등급', options=LEVELS)
    if st.button('등록', type='primary') and up is not None:
        try:
            res = api_client.upload_document(doc_id=doc_id, title=title, dept_id=dept_id, security_level=security_level, version=version, effective_from=effective_from, filename=up.name, content=up.getvalue(), emp_no=session.emp_no())
        except ApiError as exc:
            st.error(str(exc))
            return
        st.session_state['upload_job'] = res['job_id']
        st.rerun()
    st.caption('현행/만료를 고르는 일은 금주 버전 관리 챕터에서 진행할 예정입니다.')
    
    
# 1초에 한번씩 요청, 업로드 진행 되는 화면 그리기. 업로드 완료되면 멈추기 
def _render_progress(job_id: str) -> None:
    try:
        job = api_client.get_job(job_id, emp_no=session.emp_no())
    except ApiError as exc:
        st.error(str(exc))
        job = None
    if job is not None:
        st.markdown(badge_html(f"{job['status']} · {job['chunk_count']}청크"), unsafe_allow_html=True)
        steps(job['steps'])
        progress(job['progress'])
        if job['status'] == '완료':
            st.markdown(f"**{job['message']}**")
            st.caption('표 1개가 청크 1개로 저장됩니다.')
        if job['status'] not in ('완료', '실패'):
            time.sleep(1)
            st.rerun()
    if st.button('문서 하나 더 올리기'):
        st.session_state.pop('upload_job', None)
        st.rerun()