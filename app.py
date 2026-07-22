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
        padding: 0.75rem 2.5rem;
        font-size: 15px;
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
    st.Page("nav_pages/season_keywords.py", title="시즌 키워드 운용", icon=":material/eco:"),
    st.Page("nav_pages/creative_viz.py", title="광고 소재 · 시각화", icon=":material/dashboard:"),
    st.Page("nav_pages/place_rank.py", title="플레이스 순위 추적", icon=":material/location_on:"),
    st.Page("nav_pages/meeting_docs.py", title="회의 자료 수집", icon=":material/folder_shared:"),
]

pg = st.navigation(pages)
pg.run()
