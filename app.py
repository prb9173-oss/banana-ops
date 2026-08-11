import streamlit as st
import streamlit.components.v1 as components

# ==========================================
# [내비게이션 셸] 사이드바 기능별 메뉴 + 카드형 콘텐츠 레이아웃
# ==========================================
st.set_page_config(page_title="BananaWorks", layout="wide", page_icon="🍌")

PRIMARY = "#3182F6"
PRIMARY_HOVER = "#1B64DA"
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
        padding-top: 20px !important;
    }}

    /* st.dialog 팝업은 기본적으로 세로로는 화면 위쪽에 붙어서 뜬다
       (align-items: flex-start) — 사용자 입장에서 화면 정중앙에 뜨도록
       세로 중앙 정렬로 바꾼다. 앱 안의 모든 dialog(관리자 로그인 포함)에 적용됨 */
    div[data-testid="stDialog"] {{
        align-items: center !important;
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
    .pill-planned {{ background:#EEF3FA; color:{PRIMARY_HOVER}; }}

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
    .pill-kw-new {{ background:#EEF3FA; color:{PRIMARY_HOVER}; margin-bottom: 0; }}

    /* 플레이스 순위 전일 대비 변동 배지 */
    .pill-rank-up {{ background:#DCFCE7; color:#166534; margin-bottom: 0; }}
    .pill-rank-down {{ background:#FEE2E2; color:#991B1B; margin-bottom: 0; }}
    .pill-rank-same {{ background:#F1F5F9; color:#64748B; margin-bottom: 0; }}
    .pill-rank-unknown {{ background:#FEF3C7; color:#92400E; margin-bottom: 0; }}

    .rank-kw {{ font-size: 13px; font-weight: 500; color: #5B6472; }}
    .rank-meta {{ font-size: 12px; color: {MUTED_TEXT}; margin-top: 2px; }}
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

    /* 팝업(st.dialog) 안 버튼들은 배경색을 !important로 고정 지정하다 보니
       전역 hover 규칙(div.stButton > button:hover)이 덮어쓰지 못해 hover해도
       색이 그대로였다 — 페이지의 다른 버튼들처럼 hover 시 더 진해지도록
       각 버튼마다 :hover 규칙을 따로 지정한다 */
    div[class*="st-key-confirm_yes"] button {{
        background-color: {PRIMARY} !important;
        border: none !important;
    }}
    div[class*="st-key-confirm_yes"] button:hover {{
        background-color: {PRIMARY_HOVER} !important;
    }}
    div[class*="st-key-confirm_yes"] button p {{
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }}
    div[class*="st-key-confirm_no"] button {{
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
    }}
    div[class*="st-key-confirm_no"] button:hover {{
        background-color: #F1F5F9 !important;
    }}
    div[class*="st-key-confirm_no"] button p {{
        color: #475569 !important;
        font-weight: 600 !important;
    }}
    /* 묶음 삭제 확인창의 "삭제" 버튼: 되돌릴 수 없는 파괴적 동작이므로
       On/Off 확인창의 파란 "예"와 구분되게 빨간색으로 표시 */
    div[class*="st-key-confirm_delete_yes_"] button {{
        background-color: #DC2626 !important;
        border: none !important;
    }}
    div[class*="st-key-confirm_delete_yes_"] button:hover {{
        background-color: #B91C1C !important;
    }}
    div[class*="st-key-confirm_delete_yes_"] button p {{
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }}
    div[class*="st-key-result_ok"] button {{
        background-color: {PRIMARY} !important;
        border: none !important;
    }}
    div[class*="st-key-result_ok"] button:hover {{
        background-color: {PRIMARY_HOVER} !important;
    }}
    div[class*="st-key-result_ok"] button p {{
        color: #FFFFFF !important;
        font-weight: 700 !important;
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
        margin-bottom: 4px !important;
    }}
    div[class*="st-key-bundle_card_"][class*="_open"] {{
        padding-bottom: 26px !important;
    }}
    /* 펼친 카드는 그대로 두고, 목록 스크롤의 실제 원인인 "접힌" 카드만 압축한다 —
       패딩과 위/아래·수정·삭제·펼치기 버튼, 제목 글자 크기를 전부 줄인다. */
    div[class*="st-key-bundle_card_"][class*="_closed"] {{
        padding: 11px 17px 9px !important;
    }}
    div[class*="st-key-bundle_card_"][class*="_closed"] [data-testid="stMarkdownContainer"] p {{
        font-size: 13px !important;
    }}
    /* 위/아래·펼치기·수정·삭제 버튼 크기는 접힌 카드든 펼친 카드든 항상 동일하게
       — class*="st-key-bundle_card_"는 _open/_closed 둘 다에 걸리므로 상태와 무관하게
       적용된다. */
    div[class*="st-key-bundle_card_"] div[class*="st-key-up_"] button,
    div[class*="st-key-bundle_card_"] div[class*="st-key-down_"] button,
    div[class*="st-key-bundle_card_"] div[class*="st-key-toggle_"] button,
    div[class*="st-key-bundle_card_"] div[class*="st-key-edit_"] button,
    div[class*="st-key-bundle_card_"] div[class*="st-key-delete_"] button {{
        width: 20px !important;
        height: 20px !important;
        min-width: 20px !important;
        min-height: 20px !important;
    }}
    div[class*="st-key-bundle_card_"] div[class*="st-key-up_"] button p,
    div[class*="st-key-bundle_card_"] div[class*="st-key-down_"] button p,
    div[class*="st-key-bundle_card_"] div[class*="st-key-toggle_"] button p {{
        font-size: 13px !important;
    }}
    /* 박스 없이 아이콘만 보이는 수정/삭제는 다른 아이콘보다 좀 더 크게 키워서
       눈에 잘 띄게 한다. 접힌 카드의 제목 글자를 줄이는 규칙([data-testid=
       "stMarkdownContainer"] p, 이 파일 위쪽)이 명시도(specificity)가 더 높아서
       버튼 안의 아이콘 <p>까지 덩달아 13px로 눌러버리므로, data-testid 선택자를
       추가해 명시도를 그 규칙보다 높여야 실제로 적용된다. */
    div[class*="st-key-bundle_card_"] div[class*="st-key-edit_"] button [data-testid="stMarkdownContainer"] p,
    div[class*="st-key-bundle_card_"] div[class*="st-key-delete_"] button [data-testid="stMarkdownContainer"] p {{
        font-size: 18px !important;
    }}
    /* 플레이스 순위 키워드 그룹 카드: 시즌 키워드 묶음 카드와 동일한 시각 언어 재사용.
       같은 키워드를 여러 매장에 등록해두면 카드 하나에 지점별 행이 여러 개 쌓인다. */
    div[class*="st-key-pr_kwgroup_"] {{
        background-color: #FFFFFF;
        padding: 10px 15px 6px !important;
        margin-bottom: 4px !important;
        /* Streamlit 기본 세로 블록 간격(16px)이 카드 하나의 높이 대부분을 차지해서,
           키워드가 많아질수록(현재 70개+) 관리 탭 스크롤이 감당 안 되는 문제 —
           제목행/컨트롤행/매장행 사이 간격을 확 줄여 카드 하나의 높이를 압축한다. */
        gap: 4px !important;
    }}
    div[class*="st-key-pr_kwgroup_"] div[data-testid="stHorizontalBlock"] {{
        align-items: center !important;
    }}
    /* 한 그룹 카드 안에서 지점별 행을 구분선으로 분리 */
    div[class*="st-key-pr_kwrow_"] {{
        padding: 1px 0 !important;
        border-bottom: 1px solid #EEF0F3;
    }}
    div[class*="st-key-pr_kwrow_"]:last-of-type {{
        border-bottom: none;
    }}
    /* 보고용/회의용 포함·Top N 4개 컨트롤이 그냥 여백으로만 구분돼서 표처럼 안 보이던
       문제 — 엑셀/장고 어드민 그리드처럼 칸 사이에 실선을 그어 표 형태로 보이게 한다.
       (실제 <table>은 못 씀 — 안에 들어가는 게 콜백이 달린 진짜 st.checkbox/selectbox라
       Streamlit 위젯은 Streamlit 레이아웃 함수를 통해서만 배치 가능) */
    div[class*="st-key-pr_kwcontrols_"] {{
        border-top: 1px solid {BORDER};
        border-bottom: 1px solid {BORDER};
        margin: 2px 0;
        padding: 4px 0;
    }}
    div[class*="st-key-pr_kwcontrols_"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {{
        border-right: 1px solid {BORDER};
        padding-left: 12px !important;
    }}
    div[class*="st-key-pr_kwcontrols_"] div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:last-child {{
        border-right: none;
    }}
    /* 체크박스/드롭다운 글자 크기 및 내부 여백도 줄여서 줄어든 행 간격과 비율이
       맞도록(글자만 그대로면 오히려 더 답답하고 어색해 보인다) */
    div[class*="st-key-pr_kwcontrols_"] label p {{
        font-size: 12.5px !important;
    }}
    div[class*="st-key-pr_kwcontrols_"] div[data-testid="stSelectbox"] input {{
        font-size: 12.5px !important;
        padding: 2px 6px !important;
    }}
    div[class*="st-key-pr_kwcontrols_"] div[data-testid="stSelectbox"] div[role="group"] {{
        min-height: unset !important;
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
    div[class*="st-key-toggle_"] button,
    div[class*="st-key-edit_"] button,
    div[class*="st-key-delete_"] button {{
        width: 25px !important;
        height: 25px !important;
        min-width: 25px !important;
        min-height: 25px !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}
    div[class*="st-key-up_"] button p,
    div[class*="st-key-down_"] button p,
    div[class*="st-key-toggle_"] button p,
    div[class*="st-key-edit_"] button p,
    div[class*="st-key-delete_"] button p {{
        font-size: 15px !important;
    }}
    div[class*="st-key-up_"] button,
    div[class*="st-key-down_"] button {{
        background-color: {PRIMARY} !important;
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
        background-color: {PRIMARY} !important;
        border: none !important;
        border-radius: 6px !important;
        box-shadow: none !important;
    }}
    div[class*="st-key-pr_date_prev"] button p,
    div[class*="st-key-pr_date_next"] button p {{
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }}
    /* 광고 소재·시각화 페이지의 매장/주차 이동 버튼 — 기본 st.button 크기(꽤 큼)라
       나머지 컴팩트한 UI와 어울리지 않아서, 위 pr_date_prev/next와 동일하게 작은
       정사각형 버튼으로 맞춘다. */
    div[class*="st-key-cv_account_prev"] button,
    div[class*="st-key-cv_account_next"] button,
    div[class*="st-key-cv_week_prev"] button,
    div[class*="st-key-cv_week_next"] button {{
        width: 25px !important;
        height: 25px !important;
        min-width: 25px !important;
        min-height: 25px !important;
        margin-top: 8px !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        background-color: {PRIMARY} !important;
        border: none !important;
        border-radius: 6px !important;
        box-shadow: none !important;
    }}
    div[class*="st-key-cv_account_prev"] button p,
    div[class*="st-key-cv_account_next"] button p,
    div[class*="st-key-cv_week_prev"] button p,
    div[class*="st-key-cv_week_next"] button p {{
        color: #FFFFFF !important;
        font-weight: 600 !important;
        font-size: 13px !important;
    }}
    /* cv_nav_row: 버튼 컬럼은 내용물(25px 버튼) 크기에 딱 맞추고 드롭다운 두 개만
       고정 폭을 줘서, 넓은 모니터에서도 버튼이 드롭다운/텍스트와 멀리 떨어지지
       않게 한다(예전 비율 기반 st.columns는 화면이 넓을수록 버튼 주변 여백도
       같이 넓어지는 문제가 있었음). */
    div[class*="st-key-cv_nav_row"] div[data-testid="stHorizontalBlock"] {{
        gap: 0.5rem !important;
    }}
    div[class*="st-key-cv_nav_row"] div[data-testid="stColumn"] {{
        flex: 0 0 auto !important;
        width: auto !important;
        min-width: auto !important;
    }}
    div[class*="st-key-cv_nav_row"] div[data-testid="stColumn"]:has(div[class*="st-key-cv_account_select"]) {{
        flex: 0 0 200px !important;
        width: 200px !important;
    }}
    div[class*="st-key-cv_nav_row"] div[data-testid="stColumn"]:has(div[class*="st-key-cv_week_monday"]) {{
        flex: 0 0 160px !important;
        width: 160px !important;
    }}
    /* 매장 그룹(◀드롭다운▶)과 주차 그룹(◀드롭다운▶) 사이 여백은 주차 그룹의
       ◀ 버튼 컬럼에 줘야 두 그룹 "사이"에 들어간다 — 드롭다운 컬럼에 주면 그
       그룹 안의 ◀버튼-드롭다운 간격만 벌어지고 그룹 경계는 그대로라 오히려
       드롭다운 좌우 간격이 서로 달라 보이는 버그가 났었다. */
    div[class*="st-key-cv_nav_row"] div[data-testid="stColumn"]:has(div[class*="st-key-cv_week_prev"]) {{
        margin-left: 16px !important;
    }}
    /* "기본"/"회의" 보기 모드 토글도 주차 그룹과 같은 방식으로 구분한다 — N월
       N주차 선택 영역 바로 오른쪽에 여백을 두고 붙인다(2026-08-11). */
    div[class*="st-key-cv_nav_row"] div[data-testid="stColumn"]:has(div[class*="st-key-cv_view_mode"]) {{
        margin-left: 16px !important;
    }}
    /* selectbox 드롭다운 팝업(포털이라 특정 위젯만 콕 집어 타겟팅 불가, 앱 전체
       적용) 세로 길이를 줄여서 목록이 많아도 화면을 과하게 덮지 않게 한다. */
    div[data-testid="stSelectboxVirtualDropdown"] div[role="listbox"] {{
        max-height: 180px !important;
    }}
    /* 평균 입찰가 입력칸: -/+ 스테퍼 버튼을 없애고 숫자만 입력→엔터로 확정하는
       단순한 필드로 — 값 입력/확정 동작 자체는 그대로(st.number_input 유지),
       버튼만 시각적으로 숨긴다. */
    div[class*="st-key-cv_avgbid_"] button[data-testid="stNumberInputStepUp"],
    div[class*="st-key-cv_avgbid_"] button[data-testid="stNumberInputStepDown"] {{
        display: none !important;
    }}
    /* 입찰가 표 컬럼(cv_bid_row)은 비율 기반 st.columns([1,2])라 화면이 넓을수록
       표가 불필요하게 같이 넓어졌다 — 표는 고정 폭으로 작게 두고, 특이사항 칸이
       남는 폭을 전부 가져가게 한다. 두 컬럼 모두 명시적으로 재지정해야
       한다 — 한쪽만 auto로 바꾸면 다른 쪽이 예전 비율 기반 flex-basis를 그대로
       써서 합산 폭이 컨테이너보다 미세하게(수 px) 넘쳐 자동으로 줄바꿈되는
       버그가 났었다(플레이스광고의 평균입찰가 입력칸이 있을 때만 재현됨). */
    div[class*="st-key-cv_bid_row"] div[data-testid="stColumn"]:first-child {{
        flex: 0 0 300px !important;
        width: 300px !important;
        min-width: 300px !important;
    }}
    div[class*="st-key-cv_bid_row"] div[data-testid="stColumn"]:last-child {{
        flex: 1 1 0% !important;
        width: auto !important;
        min-width: 0 !important;
    }}
    /* "기본" 모드(2026-08-11 가독성 개선 이전 원본 레이아웃)의 입찰가 표 — 글자가
       12.5px로 작아서 원본 그대로 230px 고정폭이면 충분하다. 위 cv_bid_row 규칙과
       똑같이 "표는 작게, 특이사항 칸이 남는 폭 전부"로 재지정해야 한다(한쪽만
       고치면 나머지가 비율 기반 flex-basis를 그대로 써서 줄바꿈되는 버그 재발). */
    div[class*="st-key-cv_bidinfo_legacy_"] div[data-testid="stColumn"]:first-child {{
        flex: 0 0 230px !important;
        width: 230px !important;
        min-width: 230px !important;
    }}
    div[class*="st-key-cv_bidinfo_legacy_"] div[data-testid="stColumn"]:last-child {{
        flex: 1 1 0% !important;
        width: auto !important;
        min-width: 0 !important;
    }}
    /* 관리자 모드에서 표 바로 아래 붙는 평균 입찰가 입력창 — 위젯 기본 상단
       여백을 줄여서 표와 더 가까이 붙게 한다. */
    div[class*="st-key-cv_avgbid_"] {{
        margin-top: 2px !important;
    }}
    /* cv_report_row: 주간(표+차트)/키워드(표)/광고소재(이미지) 3칸 — 빔프로젝터로
       회의 때 다 같이 보므로 글자를 키웠다. flex-wrap을 켜서, 화면이 충분히 넓으면
       3칸이 나란히 있다가 좁아지면 자동으로 세로로 쌓이게 한다. 일별 유입 현황
       표는 팝업(맨 아래 버튼)으로 옮겨서(2026-08-11) 이 행에서 빠졌다. 표 글자는
       18px에서 다시 16px로 되돌렸고(2026-08-11), 광고소재 칸은 이미지가 너무
       작게 나온다는 피드백을 받아 최소 폭을 200px→340px로 넉넉하게 키웠다 —
       가로로 넓은 캡처(파워컨텐츠 등)가 좁은 칸 폭에 눌려 작아지는 문제였다. */
    div[class*="st-key-cv_report_row"] div[data-testid="stHorizontalBlock"] {{
        flex-wrap: wrap !important;
    }}
    div[class*="st-key-cv_report_row"] div[data-testid="stColumn"]:nth-child(1) {{
        flex: 1 1 495px !important;
        min-width: 495px !important;
    }}
    div[class*="st-key-cv_report_row"] div[data-testid="stColumn"]:nth-child(2) {{
        flex: 1 1 325px !important;
        min-width: 325px !important;
    }}
    div[class*="st-key-cv_report_row"] div[data-testid="stColumn"]:nth-child(3) {{
        flex: 1 1 340px !important;
        min-width: 340px !important;
    }}
    /* cv_weekly_header: "주간 유입 현황" 제목 + 작은 일별 유입 현황 팝업 버튼을
       한 줄에 담는 중첩 컬럼. cv_report_row의 flex-wrap/최소폭 규칙이 후손
       선택자라 이 안쪽 중첩 컬럼에도 그대로 걸려서 버튼이 줄바꿈되고 전체 폭
       으로 늘어나는 버그가 있었다(2026-08-11) — 이 컨테이너 안에서는 명시적으로
       다시 nowrap/자동폭으로 되돌린다. */
    div[class*="st-key-cv_weekly_header_"] div[data-testid="stHorizontalBlock"] {{
        flex-wrap: nowrap !important;
        gap: 6px !important;
        align-items: center !important;
    }}
    /* 컬럼을 [3, 1.4] 비율 그대로 두면 제목 텍스트가 짧아도 버튼이 그 비율의
       고정 시작 지점(컬럼 경계)에서만 시작해 텍스트와 버튼 사이에 큰 여백이
       생긴다 — "바로 옆에 붙여달라"는 요청(2026-08-11)에 맞춰 두 컬럼 모두
       내용물 크기만큼만 차지하게(hug content) 바꿔서 텍스트 바로 뒤에 버튼이
       붙게 한다. cv_nav_row에서 이미 쓰던 것과 같은 패턴.
       **실제 버그**: 처음엔 `:nth-child` 없이 이 선택자를 썼는데, cv_report_row의
       `div[...] div[...]:nth-child(1)` 규칙(특이도 0,3,2)이 이 규칙(특이도 0,2,2,
       nth-child 없음)보다 특이도가 더 높아서 !important끼리 붙어도 특이도가 낮은
       쪽이 졌다 — 소스 순서상 이 규칙이 더 뒤에 있어도 특이도가 우선이라 안
       먹혔다. `:nth-child(1)`/`:nth-child(2)`를 그대로 붙여 특이도를 맞추고,
       그제서야(소스 순서가 더 뒤이므로) 이 규칙이 이긴다. */
    div[class*="st-key-cv_weekly_header_"] div[data-testid="stColumn"]:nth-child(1),
    div[class*="st-key-cv_weekly_header_"] div[data-testid="stColumn"]:nth-child(2) {{
        flex: 0 0 auto !important;
        width: auto !important;
        min-width: unset !important;
    }}
    /* 일별 유입 현황 팝업 버튼 — "주간 유입 현황" 제목 바로 옆에 작게 붙인다.
       처음엔 광고 블록 제목 옆에 기본 크기 버튼으로 뒀는데 너무 커 보인다는
       피드백을 받아(2026-08-11) 위치를 옮기고, 이어서 이모지를 빼고 파란
       배경 대신 테두리만 있는 모던한 고스트 스타일로 바꿨다. min-height를
       같이 unset해야 Streamlit 기본 버튼의 숨은 최소 높이가 작은 height를
       무시하지 않는다. */
    div[class*="st-key-cv_daily_btn_"] button {{
        background-color: transparent !important;
        border: 1px solid {BORDER} !important;
        border-radius: 6px !important;
        padding: 0.32rem 0.6rem !important;
        font-size: 11.5px !important;
        min-height: unset !important;
        height: auto !important;
        line-height: 1 !important;
        box-shadow: none !important;
    }}
    div[class*="st-key-cv_daily_btn_"] button:hover {{
        background-color: #F1F5F9 !important;
        border-color: {PRIMARY} !important;
    }}
    div[class*="st-key-cv_daily_btn_"] button p {{
        color: {MUTED_TEXT} !important;
        font-weight: 600 !important;
    }}
    /* 수정/삭제는 감싸는 박스(배경+테두리) 없이 아이콘만 — 대신 아이콘을 outline이
       아니라 채워진(filled) 스타일로 바꿔서 박스 없이도 잘 보이게 한다. */
    div[class*="st-key-edit_"] button,
    div[class*="st-key-delete_"] button {{
        background-color: transparent !important;
        border: none !important;
    }}
    div[class*="st-key-toggle_"] button {{
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 50% !important;
    }}
    div[class*="st-key-edit_"] button p {{
        color: #475569 !important;
    }}
    div[class*="st-key-edit_"] button p span,
    div[class*="st-key-delete_"] button p span {{
        font-variation-settings: 'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24 !important;
    }}
    div[class*="st-key-toggle_"] button p {{
        color: #475569 !important;
    }}
    div[class*="st-key-delete_"] button p {{
        color: #DC2626 !important;
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
    div[class*="st-key-cancel_"] button:hover {{
        background-color: #F1F5F9 !important;
    }}
    div[class*="st-key-cancel_"] button p {{
        color: #475569 !important;
        font-weight: 600 !important;
    }}
    div[class*="st-key-save_"] button {{
        background-color: {PRIMARY} !important;
        border: none !important;
    }}
    div[class*="st-key-save_"] button:hover {{
        background-color: {PRIMARY_HOVER} !important;
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
    div[class*="st-key-editpanel_"] {{
        background-color: #F7F9FB;
        border: 1px dashed #CBD5E1;
        border-radius: 10px;
        padding: 12px 14px;
        margin-top: 10px;
    }}
    .edit-panel-label {{
        font-size: 12.5px;
        font-weight: 700;
        color: {PRIMARY_HOVER};
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
    /* aria-expanded="true"일 때만 폭을 강제해야 한다 — 조건 없이 항상 min-width를
       강제하면, 사이드바를 접었을 때도 Streamlit이 이 트랙(사이드바가 차지하는
       레이아웃 공간)을 250px로 계속 잡아둬서, 펼치기(>>) 버튼과 본문 전체가
       왼쪽 끝으로 안 붙고 예전 사이드바 자리만큼 오른쪽에 밀려나 있는 문제가 있었다. */
    section[data-testid="stSidebar"][aria-expanded="true"] {{
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
    /* 선택 안 된 메뉴 항목은 Streamlit 기본값이 글자 80%/아이콘 60% 불투명도라 옅게
       보인다 — 선택 여부와 상관없이 전부 진한 검정으로 통일해서 가독성을 올린다.
       (현재 페이지 구분은 아래 색상만으로 이미 되므로 두께 차이를 크게 안 둬도 된다) */
    a[data-testid="stSidebarNavLink"] p,
    a[data-testid="stSidebarNavLink"] [data-testid="stIconMaterial"] {{
        color: #000000 !important;
        opacity: 1 !important;
        font-weight: 400 !important;
    }}
    /* 현재 페이지만 포인트 컬러로 강조 — 안 그러면 전부 같은 진한 회색이라
       지금 보고 있는 메뉴가 뭔지 구분이 잘 안 된다. */
    a[data-testid="stSidebarNavLink"][aria-current="page"] p,
    a[data-testid="stSidebarNavLink"][aria-current="page"] [data-testid="stIconMaterial"] {{
        color: {PRIMARY} !important;
        font-weight: 600 !important;
    }}
    /* 관리자 모드 블록을 사이드바 맨 아래에 고정 — stSidebarContent가 뷰포트 높이만큼
       position:relative로 잡혀 있어서, 그 안에서 절대 위치로 띄우면 스크립트상 위치와
       무관하게 항상 바닥에 붙는다. */
    div[class*="st-key-admin_sidebar_block"] {{
        position: absolute !important;
        bottom: 20px;
        left: 0;
        right: 0;
        padding: 0 20px;
    }}
    </style>
""", unsafe_allow_html=True)

pages = [
    st.Page("nav_pages/season_keywords.py", title="시즌 키워드 관리", icon=":material/eco:"),
    st.Page("nav_pages/creative_viz.py", title="주간 광고 데이터", icon=":material/dashboard:", default=True),
    st.Page("nav_pages/place_rank.py", title="플레이스 순위 추적", icon=":material/location_on:"),
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
    # 다이얼로그가 열리자마자 비밀번호 입력창에 자동으로 포커스를 줘서, 버튼을 누른
    # 뒤 바로 키보드로 입력할 수 있게 한다. 다이얼로그는(components.html과 달리)
    # 별도 iframe이 아니라 최상위 문서에 바로 렌더링되지만, 이 스크립트 자체는
    # components.html의 iframe 안에서 실행되므로 window.parent.document에서 찾아야
    # 한다. 다이얼로그 열림 애니메이션 중에는 아직 input이 없을 수 있어 짧게 재시도한다.
    components.html(
        """
        <script>
        (function() {
            var doc = window.parent.document;
            var tries = 0;
            var timer = setInterval(function() {
                var input = doc.querySelector('input[type="password"][aria-label="비밀번호"]');
                if (input) {
                    input.focus();
                    clearInterval(timer);
                } else if (++tries > 20) {
                    clearInterval(timer);
                }
            }, 50);
        })();
        </script>
        """,
        height=0,
    )
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


# pg.run() 앞에 둬야 한다 — place_rank.py 등 일부 페이지가 특정 상태에서
# st.stop()을 호출하는데, st.stop()은 (그 페이지만이 아니라) app.py 스크립트
# 실행 자체를 그 자리에서 완전히 멈춰버린다. pg.run() 뒤에 두면 그런 페이지에서는
# 이 블록이 아예 렌더링되지 않아 관리자 버튼이 사라지는 문제가 있었다 — 대신 항상
# 내비게이션 링크 바로 아래(페이지별로 사이드바에 뭔가 더 추가하지 않는 한 사실상
# 맨 아래)에 고정해 어느 페이지에서도 항상 보이게 한다.
with st.sidebar:
    # 스크립트상 위치는 여전히 pg.run() 앞이지만(위 주석 이유 그대로), 시각적으로는
    # CSS 절대 위치로 사이드바 맨 아래에 고정한다 — DOM 순서와 무관하게 항상 바닥에
    # 붙어 보이도록. stSidebarContent가 position:relative + 뷰포트 높이라 이 안에서
    # bottom:0 기준으로 띄우면 된다 (아래 st-key-admin_sidebar_block CSS 참고).
    with st.container(key="admin_sidebar_block"):
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
