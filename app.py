import streamlit as st
import streamlit.components.v1 as components

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

    /* Streamlit 기본 페이지 좌우 여백(80px)이 넓어 콘텐츠 폭을 많이 잡아먹는다 —
       와이드 레이아웃을 실제로 넓게 쓰도록 줄인다 */
    div[data-testid="stMainBlockContainer"] {{
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }}

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
    .rank-kw {{ font-size: 13px; font-weight: 500; color: #5B6472; }}
    .rank-meta {{ font-size: 12px; color: {MUTED_TEXT}; margin-top: 2px; }}
    .rank-status-value {{ display: flex; align-items: center; gap: 6px; }}
    .rank-top10 {{ font-size: 12px; color: #2563EB; }}
    .rank-snapshot-item {{ font-size: 12px; color: #16181D; line-height: 1.6; }}

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
    /* 플레이스 순위 키워드 그룹 카드: 시즌 키워드 묶음 카드와 동일한 시각 언어 재사용.
       같은 키워드를 여러 매장에 등록해두면 카드 하나에 지점별 행이 여러 개 쌓인다. */
    div[class*="st-key-pr_kwgroup_"] {{
        background-color: #FFFFFF;
        padding-bottom: 14px !important;
        margin-bottom: 8px !important;
    }}
    div[class*="st-key-pr_kwgroup_"] div[data-testid="stHorizontalBlock"] {{
        align-items: center !important;
    }}
    /* 한 그룹 카드 안에서 지점별 행을 구분선으로 분리 */
    div[class*="st-key-pr_kwrow_"] {{
        padding: 4px 0 !important;
        border-bottom: 1px solid #EEF0F3;
    }}
    div[class*="st-key-pr_kwrow_"]:last-of-type {{
        border-bottom: none;
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
    /* 플레이스 순위 날짜 이동(◀▶) 버튼: 옆에 붙는 날짜 입력창과 간격을 좁히고, 입력창 위 라벨
       높이만큼 버튼을 아래로 밀어서 "입력창 박스" 자체와 세로 중앙이 맞도록 함 */
    div[class*="st-key-pr_date_nav"] div[data-testid="stHorizontalBlock"] {{
        gap: 0.4rem !important;
        align-items: flex-start !important;
    }}
    /* 버튼/입력창이 실제 렌더링 크기보다 넓은 컬럼 박스 안에 들어있어 양옆에 빈 공간이
       남던 문제 보정 — 세 컬럼(◀ / 날짜 입력 / ▶) 모두 내용물 크기에 맞춰 줄인다
       (화면 폭이 바뀌어도 안정적으로 동작) */
    div[class*="st-key-pr_date_nav"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(1),
    div[class*="st-key-pr_date_nav"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2),
    div[class*="st-key-pr_date_nav"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(3) {{
        flex: 0 0 auto !important;
        width: auto !important;
        min-width: auto !important;
    }}
    div[class*="st-key-pr_date_prev"] button,
    div[class*="st-key-pr_date_next"] button {{
        width: 25px !important;
        height: 25px !important;
        min-width: 25px !important;
        min-height: 25px !important;
        margin-top: 34px !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        background-color: #475569 !important;
        border: none !important;
        border-radius: 6px !important;
        box-shadow: none !important;
    }}
    div[class*="st-key-pr_date_prev"] button p,
    div[class*="st-key-pr_date_next"] button p {{
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

    /* 플레이스 순위 키워드 삭제 버튼을 오른쪽 끝에 딱 붙는 작은 크기로 줄이고,
       그만큼 남는 폭을 왼쪽 정보(경쟁업체 목록 등 긴 텍스트)가 쓸 수 있게 컬럼도 같이 줄인다 */
    div[class*="st-key-pr_kwrow_"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:last-child {{
        flex: 0 0 auto !important;
        width: auto !important;
        min-width: auto !important;
    }}
    div[class*="st-key-kwdel_"] button {{
        background-color: #FEF2F2 !important;
        border: none !important;
        box-shadow: none !important;
        width: 20px !important;
        height: 20px !important;
        min-width: unset !important;
        min-height: unset !important;
        padding: 0 !important;
        margin: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        border-radius: 6px !important;
    }}
    div[class*="st-key-kwdel_"] button:hover {{
        background-color: #FEE2E2 !important;
    }}
    div[class*="st-key-kwdel_"] button p {{
        color: #DC2626 !important;
        font-size: 15px !important;
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

    /* 플레이스 순위 "보고용" 탭 전용 복사 버튼: 탭 목록(회의용/보고용 라벨)과 같은
       줄의 우측 끝에 겹쳐 보이도록 stTabs 컨테이너를 기준으로 절대 위치를 준다.
       버튼 자체는 보고용 탭 콘텐츠 안에서 렌더링되므로, 탭이 st.tabs 표준 동작으로
       숨겨지면(회의용 선택 시) 이 버튼도 같이 숨겨진다 — 별도 조건 분기가 필요 없다. */
    div[data-testid="stTabs"] {{
        position: relative;
    }}
    /* Streamlit이 st.markdown 하나마다 감싸는 stElementContainer에 기본으로
       position:relative를 걸어두는데, 이게 stTabs보다 버튼에 더 가까운 조상이라
       버튼이 탭 줄이 아니라 자기 자신의 좁은 박스 기준으로 위치잡혀 버린다 —
       복사 버튼을 담은 그 wrapper만 콕 집어 static으로 되돌려서, absolute
       위치 기준이 진짜로 stTabs까지 올라가게 한다. */
    div[data-testid="stElementContainer"]:has(.rank-copy-btn-wrap) {{
        position: static !important;
    }}
    .rank-copy-btn-wrap {{
        position: absolute;
        top: 0;
        right: 0;
        height: 40px;
        display: flex;
        align-items: center;
        z-index: 10;
    }}
    .rank-copy-btn {{
        background-color: #FFFFFF;
        border: 1px solid {BORDER};
        border-radius: 8px;
        padding: 5px 14px;
        font-size: 12.5px;
        font-weight: 600;
        color: {PRIMARY};
        cursor: pointer;
        box-shadow: 0 1px 2px rgba(16,24,40,0.04);
    }}
    .rank-copy-btn:hover {{
        background-color: #F4F6F9;
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

# ==========================================
# [관리자 모드] 조회는 누구나, 실제 데이터를 바꾸는 버튼/폼만 각 페이지에서
# st.session_state.get("is_admin")로 가려서 관리자만 쓰게 한다.
#
# 원래는 브라우저 쿠키(document.cookie + st.context.cookies)로 로그인 상태를
# 남겼는데, 배포 환경(Streamlit Cloud)에서 쿠키는 분명히 브라우저에 저장되는데도
# (개발자도구로 확인함) 서버가 재접속 시 그 쿠키를 못 읽는 문제가 실측 확인됐다 —
# 아마 배포 인프라가 웹소켓 재연결 시 쿠키 헤더를 그대로 안 넘겨주는 것으로 추정
# (원인 100% 특정은 못 함). 그래서 서버가 "무조건 확실하게" 받는 값인 URL 쿼리
# 파라미터로 방식을 바꿨다: 로그인하면 URL에 ?admin=1을 붙이고, 그 값은
# st.query_params로 어떤 배포 환경에서도 항상 정확히 읽힌다. 다음에 다시 열었을 때도
# 유지되도록, 그 쿼리 파라미터가 붙는 순간 브라우저 localStorage에도 같이 기록해두고,
# 페이지를 열 때마다(쿼리 파라미터가 아직 없으면) localStorage를 확인해서 있으면
# 쿼리 파라미터를 자동으로 붙여 새로고침하는 방식으로 "기억"을 흉내낸다.
# ==========================================
ADMIN_QUERY_KEY = "admin"
ADMIN_QUERY_VALUE = "1"
ADMIN_LOCALSTORAGE_KEY = "banana_admin"


def _set_admin_persisted(logged_in):
    """localStorage에 로그인 상태를 남기고, URL의 admin 쿼리 파라미터를 그에 맞게
    설정한 뒤 그 URL로 이동(replace)한다. 이동 자체가 곧 "새로고침 + 상태 반영"
    역할을 하므로 별도의 st.rerun()이 필요 없다."""
    if logged_in:
        js_body = f"""
            localStorage.setItem('{ADMIN_LOCALSTORAGE_KEY}', '{ADMIN_QUERY_VALUE}');
            var url = new URL(window.location.href);
            url.searchParams.set('{ADMIN_QUERY_KEY}', '{ADMIN_QUERY_VALUE}');
            window.location.replace(url.toString());
        """
    else:
        js_body = f"""
            localStorage.removeItem('{ADMIN_LOCALSTORAGE_KEY}');
            var url = new URL(window.location.href);
            url.searchParams.delete('{ADMIN_QUERY_KEY}');
            window.location.replace(url.toString());
        """
    components.html(
        f"""
        <script>
        (function() {{
            var doc = window.parent.document;
            var s = doc.createElement('script');
            s.text = `{js_body}`;
            doc.body.appendChild(s);
        }})();
        </script>
        """,
        height=0,
    )


if st.query_params.get(ADMIN_QUERY_KEY) == ADMIN_QUERY_VALUE:
    st.session_state["is_admin"] = True
elif "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False

if not st.session_state["is_admin"]:
    # 쿼리 파라미터가 없는 상태로 열렸을 때, 예전에 로그인해서 localStorage에 흔적이
    # 남아있으면 쿼리 파라미터를 자동으로 붙여 새로고침해서 로그인 상태를 이어간다.
    components.html(
        f"""
        <script>
        (function() {{
            var doc = window.parent.document;
            var s = doc.createElement('script');
            s.text = `
                if (localStorage.getItem('{ADMIN_LOCALSTORAGE_KEY}') === '{ADMIN_QUERY_VALUE}') {{
                    var url = new URL(window.location.href);
                    if (url.searchParams.get('{ADMIN_QUERY_KEY}') !== '{ADMIN_QUERY_VALUE}') {{
                        url.searchParams.set('{ADMIN_QUERY_KEY}', '{ADMIN_QUERY_VALUE}');
                        window.location.replace(url.toString());
                    }}
                }}
            `;
            doc.body.appendChild(s);
        }})();
        </script>
        """,
        height=0,
    )


@st.dialog("관리자 로그인")
def _admin_login_dialog():
    # 버튼 클릭 대신 st.form을 써서, 비밀번호 입력 후 엔터만 쳐도(폼 안 위젯에서 엔터 ==
    # 폼의 기본 제출 버튼 클릭) 로그인되게 한다 — 매번 마우스로 "확인"을 눌러야 하는
    # 불편함을 없앤다.
    with st.form("admin_login_form"):
        pw = st.text_input("비밀번호", type="password", key="admin_pw_input")
        submitted = st.form_submit_button("확인")
    if submitted:
        admin_secret = st.secrets.get("admin", {}).get("password")
        if pw and admin_secret and pw == admin_secret:
            st.session_state["is_admin"] = True
            _set_admin_persisted(True)
            st.success("로그인되었습니다. 새로고침 중...")
        else:
            st.error("비밀번호가 올바르지 않습니다.")


# pg.run() 앞에 둬야 한다 — data_extractor.py 등 일부 페이지가 특정 상태에서
# st.stop()을 호출하는데, st.stop()은 (그 페이지만이 아니라) app.py 스크립트
# 실행 자체를 그 자리에서 완전히 멈춰버린다. pg.run() 뒤에 두면 그런 페이지에서는
# 이 블록이 아예 렌더링되지 않아 관리자 버튼이 사라지는 문제가 있었다 — 대신 항상
# 내비게이션 링크 바로 아래(페이지별로 사이드바에 뭔가 더 추가하지 않는 한 사실상
# 맨 아래)에 고정해 어느 페이지에서도 항상 보이게 한다.
with st.sidebar:
    st.divider()
    if st.session_state["is_admin"]:
        st.markdown(
            '<div style="margin-bottom:8px;"><span class="status-pill pill-kw-on">🔓 관리자 모드</span></div>',
            unsafe_allow_html=True,
        )
        if st.button("로그아웃", key="admin_logout", width="stretch"):
            st.session_state["is_admin"] = False
            _set_admin_persisted(False)
    else:
        if st.button("🔒 관리자 모드", key="admin_login_btn", width="stretch"):
            _admin_login_dialog()

pg.run()
