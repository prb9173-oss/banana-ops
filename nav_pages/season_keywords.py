import streamlit as st

st.subheader("시즌 키워드 운용 고도화")
st.caption("복잡한 시스템 접속 없이 시즌에 맞는 키워드를 관리합니다.")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="feature-card">
        <span class="status-pill pill-planned">기획 중</span>
        <span class="material-symbols-outlined card-icon">power_settings_new</span>
        <h4>원클릭 일괄 제어</h4>
        <p>복잡한 시스템 접속 없이, 단순 클릭 한두 번만으로 현재 시즌에 맞는 키워드를 한 번에 껐다 켤 수 있는 통합 제어 기능을 제공합니다.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <span class="status-pill pill-planned">기획 중</span>
        <span class="material-symbols-outlined card-icon">database</span>
        <h4>시즌별 키워드 자산화</h4>
        <p>봄, 여름 휴가, 겨울 등 시즌별 핵심 키워드를 체계적으로 보관하고 관리합니다. (구글 스프레드시트 또는 Supabase 연동 예정)</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("###")
st.info("💡 일괄 제어는 네이버 API의 쓰기(write) 권한이 필요하고, 실제 광고 지출에 영향을 주는 기능이라 확인 절차를 함께 설계할 예정입니다.")
