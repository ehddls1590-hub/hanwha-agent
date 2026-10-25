import pathlib
import sys
# 프로젝트 실행을 root에서 하기 때문에 frontend 경로 등록해주기 
sys.path.insert(0, str(pathlib.Path(__file__).parent)) # frontend/를 모듈 검색 경로에 넣는다. 

import streamlit as st 
from ui.theme import inject_css

# 가장먼저 부르는 st 함수여야 한다. 최상위에 배치 
st.set_page_config(
    page_title="화면 그리기 연습",
    layout="wide", 
    initial_sidebar_state="expanded",
)

inject_css() # css 적용 






