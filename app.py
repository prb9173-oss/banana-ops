import streamlit as st

# ==========================================
# [내비게이션 셸] 사이드바 기능별 메뉴 + 카드형 콘텐츠 레이아웃
# ==========================================
st.set_page_config(page_title="banana-ops", layout="wide", page_icon="🍌")

PRIMARY = "#1E3A5F"
PRIMARY_HOVER = "#16304C"
BORDER = "#E3E6EB"
MUTED_TEXT = "#5B6472"

st.markdown("""
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,300..500,0..1,-25..0" />
""", unsafe_allow_html=True)

st.markdown(f"""
    <style>
    html, body, [class*="css"] {{
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Malgun Gothic', sans-serif;
    }}

    .material-symbols-outlined {{
        font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
        vertical-align: middle;
    }}
    h1, h2, h3 {{ letter-spacing: -0.02em; font-weight: 700; }}

    div.stButton > button {{
        background-color: {PRIMARY};
        border: none;
        border-radius: 8px;
        padding: 0.45rem 1.4rem;
        font-size: 13.5px;
        letter-spacing: 0.2px;
        white-space: nowrap;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.08);
        transition: background-color 0.15s ease, box-shadow 0.15s ease;
    }}
    div.stButton > button:hover {{
        background-color: {PRIMARY_HOVER};
        box-shadow: 0 4px 10px rgba(16, 24, 40, 0.12);
    }}
    div.stButton > button p {{
        color: #FFFFFF;
        font-weight: 700;
    }}

    div[data-testid="stAlert"] {{ border-radius: 10px; }}

    /* ---- 카드형 콘텐츠 ---- */
    .feature-card {{
        background-color: #FFFFFF;
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 22px 24px;
        margin-bottom: 16px;
        box-shadow: 0 1px 2px rgba(16,24,40,0.04);
        height: 100%;
    }}
    .feature-card .card-icon {{
        font-size: 26px;
        color: {PRIMARY};
        margin-bottom: 10px;
        display: block;
    }}
    .feature-card h4 {{
        margin: 0 0 8px 0;
        font-size: 16px;
        font-weight: 700;
        color: #16181D;
    }}
    .feature-card p {{
        margin: 0;
        font-size: 13.5px;
        color: {MUTED_TEXT};
        line-height: 1.6;
    }}
    .status-pill {{
        display: inline-block;
        font-size: 11.5px;
        font-weight: 700;
        padding: 3px 10px;
        border-radius: 999px;
        margin-bottom: 10px;
    }}
    .pill-ready {{ background:#DCFCE7; color:#166534; }}
    .pill-progress {{ background:#FEF3C7; color:#92400E; }}
    .pill-planned {{ background:#EEF3FA; color:#3B5A8A; }}

    /* 매장별 키워드 on/off 실시간 상태 목록 */
    .kw-status-card {{
        padding: 4px 16px !important;
        margin-bottom: 2px !important;
    }}
    .kw-status-row {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 9px 0;
        border-bottom: 1px solid #EEF0F3;
        font-size: 14px;
        color: #16181D;
    }}
    .kw-status-row:last-child {{ border-bottom: none; }}
    .pill-kw-on {{ background:#DCFCE7; color:#166534; margin-bottom: 0; }}
    .pill-kw-off {{ background:#F1F5F9; color:#64748B; margin-bottom: 0; }}
    .pill-kw-new {{ background:#EEF3FA; color:#3B5A8A; margin-bottom: 0; }}

    /* 플레이스 순위 전일 대비 변동 배지 */
    .pill-rank-up {{ background:#DCFCE7; color:#166534; margin-bottom: 0; }}
    .pill-rank-down {{ background:#FEE2E2; color:#991B1B; margin-bottom: 0; }}
    .pill-rank-same {{ background:#F1F5F9; color:#64748B; margin-bottom: 0; }}
    .pill-rank-unknown {{ background:#FEF3C7; color:#92400E; margin-bottom: 0; }}

    /* 플레이스 순위 결과 목록 (키워드별 현재 순위 + 전일 대비) */
    .rank-status-card {{
        padding: 4px 16px !important;
        margin-bottom: 2px !important;
    }}
    .rank-status-row {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 0;
        border-bottom: 1px solid #EEF0F3;
    }}
    .rank-status-row:last-child {{ border-bottom: none; }}
    .rank-status-info {{ display: flex; flex-direction: column; }}
    .rank-kw {{ font-size: 14px; font-weight: 600; color: #16181D; }}
    .rank-meta {{ font-size: 12px; color: {MUTED_TEXT}; margin-top: 2px; }}
    .rank-status-value {{ display: flex; align-items: center; gap: 6px; }}

    /* On/Off 버튼을 상태 박스 기준 가로 중앙에, 바짝 붙여서 배치 */
    div[class*="st-key-onoff_actions"] {{
        display: flex !important;
        flex-direction: row !important;
        justify-content: center !important;
        gap: 12px !important;
        margin-top: 4px !important;
    }}
    div[class*="st-key-onoff_actions"] > div {{
        width: auto !important;
    }}

    /* 재확인 패널: 경고색 대신 흰 배경 + 좌측 강조선으로 모던하게 구분 */
    div[class*="st-key-confirm_panel"] {{
        background-color: #FFFFFF !important;
        border: 1px solid {BORDER} !important;
        border-left: 4px solid {PRIMARY} !important;
        border-radius: 10px !important;
        padding: 18px 20px !important;
        box-shadow: 0 1px 2px rgba(16,24,40,0.04);
    }}
    .confirm-text {{
        font-size: 15px;
        color: #16181D;
        line-height: 1.6;
        margin-bottom: 14px;
    }}
    .confirm-subtext {{
        font-size: 13px;
        color: {MUTED_TEXT};
        font-weight: 400;
        margin-top: 2px;
    }}
    div[class*="st-key-confirm_yes"] button {{
        background-color: {PRIMARY} !important;
        border: none !important;
    }}
    div[class*="st-key-confirm_yes"] button p {{
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }}
    div[class*="st-key-confirm_no"] button {{
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
    }}
    div[class*="st-key-confirm_no"] button p {{
        color: #475569 !important;
        font-weight: 600 !important;
    }}

    /* 시즌 키워드 페이지의 기능별 구역(매장 관리/묶음 추가/묶음 목록)을
       하나의 카드 박스로 감싸 서로 명확히 분리되도록 함 */
    div[class*="st-key-section_"] {{
        background-color: #FAFBFC;
        border: 1px solid {BORDER};
        border-radius: 14px;
        padding: 20px 22px;
        margin-bottom: 20px !important;
        box-shadow: 0 1px 2px rgba(16,24,40,0.04);
    }}
    div[class*="st-key-section_"] h4 {{
        margin-top: 0 !important;
    }}

    /* 시즌 키워드 묶음 카드: 흰 배경 + 진한 텍스트로 가독성 확보 */
    /* 하단 패딩을 상단과 맞춰 시각적으로 대칭이 되도록 지정
       (마지막 자식 요소의 padding은 Streamlit이 지워버려서 컨테이너 자체에 지정).
       접힌 카드는 헤더 행만 있으므로 펼친 카드보다 하단 패딩을 작게 둔다. */
    div[class*="st-key-bundle_card_"] {{
        background-color: #FFFFFF;
        margin-bottom: 8px !important;
    }}
    div[class*="st-key-bundle_card_"][class*="_closed"] {{
        padding-bottom: 14px !important;
    }}
    div[class*="st-key-bundle_card_"][class*="_open"] {{
        padding-bottom: 26px !important;
    }}
    /* 플레이스 순위 키워드 카드: 시즌 키워드 묶음 카드와 동일한 시각 언어 재사용 */
    div[class*="st-key-pr_kwcard_"] {{
        background-color: #FFFFFF;
        padding-bottom: 14px !important;
        margin-bottom: 8px !important;
    }}
    div[class*="st-key-pr_kwcard_"] div[data-testid="stHorizontalBlock"] {{
        align-items: center !important;
    }}
    /* vertical_alignment="center"가 실제로는 stretch로 렌더링되는 문제 보정:
       제목+줄바꿈된 키워드 텍스트 블록 기준으로 버튼 행을 정확히 세로 중앙에 오도록 강제 */
    div[class*="st-key-bundle_card_"] div[data-testid="stHorizontalBlock"] {{
        align-items: center !important;
    }}
    .kw-text {{
        color: #16181D;
        font-size: 14px;
        line-height: 1.6;
    }}

    /* 묶음 카드의 순서(▲▼)/수정/삭제 버튼: 컴팩트한 크기 + 역할별 색상 구분 */
    div[class*="st-key-up_"] button,
    div[class*="st-key-down_"] button,
    div[class*="st-key-toggle_"] button,
    div[class*="st-key-edit_"] button,
    div[class*="st-key-delete_"] button,
    div[class*="st-key-save_"] button,
    div[class*="st-key-cancel_"] button {{
        display: inline-block !important;
        width: auto !important;
        margin: 0 !important;
        padding: 0.2rem 0.65rem !important;
        font-size: 11.5px !important;
        border-radius: 6px !important;
        box-shadow: none !important;
    }}
    div[class*="st-key-up_"] button,
    div[class*="st-key-down_"] button,
    div[class*="st-key-toggle_"] button {{
        width: 25px !important;
        height: 25px !important;
        min-width: 25px !important;
        min-height: 25px !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}
    div[class*="st-key-up_"] button [data-testid="stIconMaterial"],
    div[class*="st-key-down_"] button [data-testid="stIconMaterial"],
    div[class*="st-key-toggle_"] button [data-testid="stIconMaterial"] {{
        font-size: 15px !important;
    }}
    div[class*="st-key-up_"] button,
    div[class*="st-key-down_"] button {{
        background-color: #475569 !important;
        border: none !important;
    }}
    div[class*="st-key-up_"] button p,
    div[class*="st-key-down_"] button p,
    div[class*="st-key-up_"] button span,
    div[class*="st-key-down_"] button span {{
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }}
    div[class*="st-key-edit_"] button {{
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
    }}
    div[class*="st-key-toggle_"] button {{
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 50% !important;
    }}
    div[class*="st-key-edit_"] button p {{
        color: #475569 !important;
        font-weight: 600 !important;
    }}
    div[class*="st-key-toggle_"] button p,
    div[class*="st-key-toggle_"] button span {{
        color: #475569 !important;
        font-weight: 600 !important;
    }}
    div[class*="st-key-delete_"] button {{
        background-color: #FEF2F2 !important;
        border: 1px solid #FCA5A5 !important;
    }}
    div[class*="st-key-delete_"] button p {{
        color: #DC2626 !important;
        font-weight: 600 !important;
    }}

    /* 플레이스 순위 키워드 삭제: 두꺼운 테두리 박스 대신 옅은 배경만으로 구분,
       가로로 넓게 채워서 클릭 영역을 눈에 띄고 넉넉하게 만든다 */
    div[class*="st-key-kwdel_"] button {{
        background-color: #FEF2F2 !important;
        border: none !important;
        box-shadow: none !important;
        width: 56px !important;
        min-width: unset !important;
        padding: 8px 0 !important;
        margin: 0 0 0 auto !important;
        display: block !important;
        border-radius: 6px !important;
    }}
    div[class*="st-key-kwdel_"] button:hover {{
        background-color: #FEE2E2 !important;
    }}
    div[class*="st-key-kwdel_"] button p {{
        color: #DC2626 !important;
        font-size: 20px !important;
        font-weight: 700 !important;
        line-height: 1 !important;
    }}
    div[class*="st-key-cancel_"] button {{
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
    }}
    div[class*="st-key-cancel_"] button p {{
        color: #475569 !important;
        font-weight: 600 !important;
    }}
    div[class*="st-key-save_"] button {{
        background-color: {PRIMARY} !important;
        border: none !important;
    }}
    div[class*="st-key-save_"] button p {{
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }}

    /* 수정/삭제, 저장/취소 버튼을 나란히 딱 붙여서 배치 (컬럼이 넓어져도 버튼끼리 멀어지지 않도록) */
    /* 수정/삭제는 카드 우측 끝에, 저장/취소는 입력창과 맞춰 좌측에 배치 */
    div[class*="st-key-actions_"] {{
        display: flex !important;
        flex-direction: row !important;
        justify-content: flex-end !important;
        gap: 8px !important;
        align-items: center !important;
    }}
    div[class*="st-key-editform_actions_"] {{
        display: flex !important;
        flex-direction: row !important;
        justify-content: flex-start !important;
        gap: 8px !important;
        align-items: center !important;
    }}
    div[class*="st-key-actions_"] > div,
    div[class*="st-key-editform_actions_"] > div {{
        width: auto !important;
    }}

    /* 묶음 수정 시 나타나는 "키워드 추가" 패널: 기존 키워드 영역과 구분되는 배경/테두리 */
    div[class*="st-key-edit_panel_"] {{
        background-color: #F7F9FB;
        border: 1px dashed #CBD5E1;
        border-radius: 10px;
        padding: 12px 14px;
        margin-top: 10px;
    }}
    .edit-panel-label {{
        font-size: 12.5px;
        font-weight: 700;
        color: #3B5A8A;
        margin-bottom: 6px;
    }}

    /* ---- 사이드바 폭 / 내비게이션 항목 크기 조정 ---- */
    section[data-testid="stSidebar"] {{
        width: 250px !important;
        min-width: 250px !important;
    }}
    a[data-testid="stSidebarNavLink"] {{
        height: 42px !important;
        align-items: center !important;
    }}
    a[data-testid="stSidebarNavLink"] p {{
        font-size: 15.5px !important;
        line-height: 42px !important;
    }}
    </style>
""", unsafe_allow_html=True)

pages = [
    st.Page("nav_pages/data_extractor.py", title="광고 데이터 추출기", icon=":material/monitoring:", default=True),
    st.Page("nav_pages/season_keywords.py", title="시즌 키워드 관리", icon=":material/eco:"),
    st.Page("nav_pages/creative_viz.py", title="광고 소재 · 시각화", icon=":material/dashboard:"),
    st.Page("nav_pages/place_rank.py", title="플레이스 순위 추적", icon=":material/location_on:"),
    st.Page("nav_pages/meeting_docs.py", title="회의 자료 수집", icon=":material/folder_shared:"),
]

pg = st.navigation(pages)
pg.run()
