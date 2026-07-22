import streamlit as st

st.subheader("통합 회의 자료 수집 기능")
st.caption("팀원들이 자료를 미리 올려두면 하나의 프리젠테이션처럼 볼 수 있게 합니다.")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="feature-card">
        <span class="status-pill pill-planned">기존 방식 (AS-IS)</span>
        <span class="material-symbols-outlined card-icon">visibility_off</span>
        <h4>기존 방식</h4>
        <p>회의에 필요한 이미지나 각자가 준비한 참고 자료를 카톡방에 무작위로 올리고, 회의 시간에 이를 하나씩 넘겨가며 봐야 하는 불편함이 존재합니다.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <span class="status-pill pill-planned">개선 방식 (TO-BE)</span>
        <span class="material-symbols-outlined card-icon">cloud_upload</span>
        <h4>개선 방식</h4>
        <p>자체 웹사이트에 회의 전용 업로드 기능을 구축, 팀원들이 자료를 미리 올려두면 웹 화면에서 하나의 프리젠테이션처럼 끊김 없이 볼 수 있도록 설정합니다.</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("###")
st.info("💡 업로드된 파일도 Streamlit Cloud 로컬 저장은 재배포 시 사라지므로, 외부 저장소(Google Drive, S3 등) 연동이 필요합니다.")
