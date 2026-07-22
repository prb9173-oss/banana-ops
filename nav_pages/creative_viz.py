import streamlit as st

st.subheader("광고 소재 및 데이터 시각화")
st.caption("복잡한 성과 데이터를 화면 자체가 보고서 역할을 하도록 정리합니다.")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div class="feature-card">
        <span class="status-pill pill-planned">기획 중</span>
        <span class="material-symbols-outlined card-icon">image</span>
        <h4>광고 소재 파악</h4>
        <p>현재 송출되고 있는 네이버 광고 소재(이미지, 텍스트)를 웹 화면에 바로 가져와서 보여줍니다.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <span class="status-pill pill-planned">기획 중</span>
        <span class="material-symbols-outlined card-icon">table_chart</span>
        <h4>자동 포맷팅</h4>
        <p>복잡한 광고 성과 데이터도 보고서 형식에 맞게 화면에 한 번에 노출시켜 직관적인 파악을 돕습니다.</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="feature-card">
        <span class="status-pill pill-planned">기획 중</span>
        <span class="material-symbols-outlined card-icon">grid_off</span>
        <h4>탈(脫) 엑셀 프로세스</h4>
        <p>화면 자체가 보고서 역할을 수행하여 엑셀로 굳이 만들 필요가 없게 실무 리소스를 대폭 줄여줍니다.</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("###")
st.info("💡 '광고 소재 파악'은 등록된 소재(텍스트·이미지 URL)를 API로 가져오는 것인지, 검색결과 화면 그대로의 노출 모습을 보여주는 것인지 범위 확인이 필요합니다.")
