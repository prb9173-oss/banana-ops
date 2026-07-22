import streamlit as st
import pandas as pd

st.subheader("플레이스 순위 추적")
st.caption("매일 정해진 시간에 플레이스 순위를 체크하고 자동으로 기록합니다.")

st.markdown('<span class="status-pill pill-progress">아키텍처 논의 중 · GitHub Actions + Supabase</span>', unsafe_allow_html=True)
st.markdown("###")

mock_rank_df = pd.DataFrame([
    {"타겟 키워드": "제주도 맛집", "현재 플레이스 순위": "3위", "전일 대비 변동": "▲ 2", "추적 시간": "09:00 AM"},
    {"타겟 키워드": "서귀포 카페", "현재 플레이스 순위": "8위", "전일 대비 변동": "▼ 1", "추적 시간": "09:00 AM"},
    {"타겟 키워드": "중문 흑돼지", "현재 플레이스 순위": "1위", "전일 대비 변동": "- (유지)", "추적 시간": "09:00 AM"},
])

st.markdown(
    f'<div class="feature-card">{mock_rank_df.to_html(index=False, border=0)}</div>',
    unsafe_allow_html=True,
)

st.markdown("###")
st.markdown("✅ 매일 정해진 시간에 플레이스 순위를 체크하고 자동으로 기록합니다. (예시 데이터)")
st.markdown("✅ 바로 이전 날짜와 비교해서 순위가 얼마나 올랐고 내려갔는지 직관적으로 보여줍니다.")

st.markdown("###")
st.warning("⚠️ 네이버 검색광고 API에는 플레이스 순위 조회 기능이 없습니다. 이 페이지는 GitHub Actions로 매일 크롤링 → Supabase 저장 → 여기서 조회하는 구조로 별도 구현이 필요합니다 (스크래핑 기반이라 안정성 리스크 있음).")
