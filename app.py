import streamlit as st
import datetime
import time
import hmac
import hashlib
import base64
import requests
import pandas as pd
import json  # 계정 정보를 파일에 저장하기 위해 임포트
import os  # 로컬 저장 파일 경로를 체크하기 위해 임포트

# ==========================================
# [데이터 영구 저장] accounts.json 파일 읽기/쓰기 모듈
# ==========================================
ACCOUNTS_FILE = "accounts.json"

def load_accounts():
    default_accounts = {}
    if os.path.exists(ACCOUNTS_FILE):
        try:
            with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_accounts
    return default_accounts

def save_accounts(accounts):
    try:
        with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
            json.dump(accounts, f, ensure_ascii=False, indent=4)
    except Exception as e:
        pass

# ==========================================
# [세션 상태 관리] 세션 사전에 필요한 상태 키들을 최상단에 안전히 할당
# ==========================================
if 'ad_accounts' not in st.session_state:
    st.session_state['ad_accounts'] = load_accounts()

if 'input_customer_id' not in st.session_state:
    st.session_state['input_customer_id'] = ""
if 'input_api_key' not in st.session_state:
    st.session_state['input_api_key'] = ""
if 'input_secret_key' not in st.session_state:
    st.session_state['input_secret_key'] = ""
if 'reg_name' not in st.session_state:
    st.session_state['reg_name'] = ""

if 'registration_success' not in st.session_state:
    st.session_state['registration_success'] = ""
if 'registration_error' not in st.session_state:
    st.session_state['registration_error'] = False


# ==========================================
# 💡 [콜백 정의] 순서 혼선을 원천 차단하기 위해 파일 최상단에 콜백 함수 정의
# ==========================================
def register_account_callback():
    cust_id = st.session_state.get('input_customer_id', '')
    api_k = st.session_state.get('input_api_key', '')
    sec_k = st.session_state.get('input_secret_key', '')
    r_name = st.session_state.get('reg_name', '')
    
    if r_name and cust_id and api_k and sec_k:
        # 데이터 사전에 계정 정보 등록 및 파일 영구 저장
        st.session_state['ad_accounts'][r_name] = {
            "customer_id": cust_id,
            "api_key": api_k,
            "secret_key": sec_k
        }
        save_accounts(st.session_state['ad_accounts'])
        
        # 저장 직후 입력창 상태 비워주기 수행
        st.session_state['input_customer_id'] = ""
        st.session_state['input_api_key'] = ""
        st.session_state['input_secret_key'] = ""
        st.session_state['reg_name'] = ""
        st.session_state['selected_profile'] = "광고 ID 선택"
        
        st.session_state['registration_success'] = r_name
    else:
        st.session_state['registration_error'] = True


# ==========================================
# 💡 [날짜 계산] NameError 방지를 위해 모듈 최상위에 계산식 배치
# ==========================================
today = datetime.date.today()
current_weekday = today.weekday()  # 월요일=0, ... 일요일=6
last_monday = today - datetime.timedelta(days=current_weekday + 7)  # 지난주 월요일
last_sunday = last_monday + datetime.timedelta(days=6)  # 지난주 일요일


# ==========================================
# 💡 [가변 그리드 엔진] 테마 색상 상태에 맞게 동적 표를 그리는 함수
# ==========================================
def convert_df_to_html_grid(df, is_summary_table=False):
    # 사용자가 선택한 라이트/다크 모드에 맞게 표 텍스트와 보더 색상을 치환합니다.
    is_light = (st.session_state.get('theme_mode', "🌞 라이트 모드") == "🌞 라이트 모드")
    
    if is_light:
        bg_header = "#FFF9C4" if is_summary_table else "#FFFDE7"
        bg_row_sum = "#FFFDE7" if is_summary_table else ""
        text_color = "#000000"
        border_color = "#E0E0E0"
        table_border = "#D0C0A0"
    else:
        # 다크 모드용 저자극 다크그레이/화이트 텍스트 세팅
        bg_header = "#3A3A3C" if is_summary_table else "#2C2C2C"
        bg_row_sum = "#2C2C2C" if is_summary_table else ""
        text_color = "#FFFFFF"
        border_color = "#444444"
        table_border = "#555555"
        
    html = f'<table style="width:100%; border-collapse:collapse; font-family:sans-serif; text-align:center; margin-top:10px; color:{text_color} !important; border:1px solid {table_border};">'
    
    # 헤더 라인 생성
    html += f'<thead><tr style="background-color:{bg_header}; border-bottom:2px solid {border_color}; font-weight:bold; height:36px;">'
    for col in df.columns:
        html += f'<th style="padding:10px; border:1px solid {border_color}; color:{text_color} !important; font-size:14px;">{col}</th>'
    html += '</tr></thead><tbody>'
    
    # 데이터 행 생성
    for i, row in df.iterrows():
        row_style = f"background-color:{bg_row_sum};" if is_summary_table else ""
        html += f'<tr style="{row_style} border-bottom:1px solid {border_color}; height:32px;">'
        
        for col in df.columns:
            val = row[col]
            if isinstance(val, (int, float)):
                if "클릭률" in col:
                    formatted_val = f"{val:.2f}%"
                else:
                    formatted_val = f"{int(val):,}"
            else:
                formatted_val = str(val)
                
            html += f'<td style="padding:8px; border:1px solid {border_color}; color:{text_color} !important; font-size:13px;">{formatted_val}</td>'
        html += '</tr>'
        
    html += '</tbody></table>'
    return html


# ==========================================
# [사이드바 상단 테마 로더] 사용자의 테마 스위치 선언
# ==========================================
st.sidebar.markdown("### 🎨 화면 테마 설정")
# 🌞 라이트 모드와 🌙 다크 모드를 원클릭으로 전환할 수 있습니다.
theme_mode = st.sidebar.selectbox("화면 테마 모드 선택", ["🌞 라이트 모드", "🌙 다크 모드"], key="theme_mode")

# 테마에 따른 동적 가변 CSS 제어 변수 할당
if theme_mode == "🌞 라이트 모드":
    css_bg = "#FFFFFF"
    css_sidebar_bg = "#F8F9FA"
    css_text = "#000000"
    css_border = "#CCCCCC"
else:
    css_bg = "#121212"
    css_sidebar_bg = "#1E1E1E"
    css_text = "#FFFFFF"
    css_border = "#444444"

# 💡 [동적 CSS 주입] 테마 스위치 변경 즉시 브라우저의 배경 및 위젯 글자색이 실시간 반전 처리됩니다.
st.markdown(f"""
    <style>
    .stApp {{
        background-color: {css_bg} !important;
    }}
    section[data-testid="stSidebar"] {{
        background-color: {css_sidebar_bg} !important;
        border-right: 1px solid {css_border} !important;
    }}
    p, span, label, h1, h2, h3, h4, h5, h6, li, strong, th, td {{
        color: {css_text} !important;
    }}
    .stMarkdown, [data-testid="stWidgetLabel"] p, .stCaptionContainer p {{
        color: {css_text} !important;
    }}
    .stTextInput label p, .stSelectbox label p, .stDateInput label p, [data-testid="stSidebar"] label p {{
        color: {css_text} !important;
        font-weight: 700 !important;
    }}
    div[data-baseweb="select"] > div {{
        background-color: {css_bg} !important;
        color: {css_text} !important;
        border: 1px solid {css_border} !important;
    }}
    div[data-baseweb="popover"] {{
        background-color: {css_bg} !important;
    }}
    div[role="listbox"] div, li[role="option"] {{
        background-color: {css_bg} !important;
        color: {css_text} !important;
    }}
    li[role="option"]:hover, div[role="option"]:hover {{
        background-color: #FFF9C4 !important;
        color: #000000 !important;
    }}
    div.stButton > button {{
        background-color: #FFFDE7 !important;
        color: #000000 !important;
        border: 1px solid #C0B090 !important;
        border-radius: 6px !important;
        padding: 0.6rem 1.5rem !important;
        font-weight: bold !important;
        transition: all 0.3s ease;
        width: 100%;
    }}
    div.stButton > button:hover {{
        background-color: #FFF9C4 !important;
        border: 1px solid #888888 !important;
    }}
    </style>
""", unsafe_allow_html=True)


# ==========================================
# [사이드바 본 구조] 광고 ID 선택 및 관리
# ==========================================
st.sidebar.markdown("---")
st.sidebar.markdown("### 📁 1. 광고 ID(계정) 선택")

available_accounts = list(st.session_state['ad_accounts'].keys())
options_list = ["광고 ID 선택"] + available_accounts

def update_inputs_from_profile():
    prof = st.session_state.get('selected_profile')
    if prof == "광고 ID 선택":
        st.session_state['input_customer_id'] = ""
        st.session_state['input_api_key'] = ""
        st.session_state['input_secret_key'] = ""
    elif prof and prof in st.session_state['ad_accounts']:
        keys = st.session_state['ad_accounts'][prof]
        st.session_state['input_customer_id'] = keys["customer_id"]
        st.session_state['input_api_key'] = keys["api_key"]
        st.session_state['input_secret_key'] = keys["secret_key"]

if 'selected_profile' not in st.session_state:
    st.session_state['selected_profile'] = "광고 ID 선택"
    update_inputs_from_profile()

selected_profile = st.sidebar.selectbox(
    "관리 중인 계정을 선택하시면 저장된 API 키를 자동으로 불러옵니다.", 
    options=options_list,
    key='selected_profile',
    on_change=update_inputs_from_profile
)

if st.sidebar.button("🗑️ 선택된 광고 ID 삭제"):
    if selected_profile != "광고 ID 선택":
        del st.session_state['ad_accounts'][selected_profile]
        save_accounts(st.session_state['ad_accounts'])
        st.session_state['selected_profile'] = "광고 ID 선택"
        update_inputs_from_profile()
        st.sidebar.success(f"'{selected_profile}' 계정이 목록에서 성공적으로 삭제되었습니다.")
        time.sleep(0.5)
        st.rerun()
    else:
        st.sidebar.error("기본 안내 가이드 문구('광고 ID 선택')는 삭제할 수 없습니다.")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔑 2. API 인증 키 관리")

st.sidebar.text_input("CUSTOMER_ID", key="input_customer_id")
st.sidebar.text_input("액세스 라이선스 (API KEY)", type="password", key="input_api_key")
st.sidebar.text_input("비밀키 (SECRET_KEY)", type="password", key="input_secret_key")

st.sidebar.markdown("---")
st.sidebar.markdown("### ➕ 3. 새로운 광고 ID(계정) 등록")

st.sidebar.text_input("신규 계정 별칭", placeholder="예: 인하우스 패션몰 C", key="reg_name")

# 등록 콜백 바인딩
st.sidebar.button("💾 위 정보로 광고 ID 등록", on_click=register_account_callback)

if st.session_state['registration_success']:
    st.sidebar.success(f"'{st.session_state['registration_success']}' 계정이 추가되었으며, 기입창이 초기화되었습니다.")
    st.session_state['registration_success'] = ""
    time.sleep(0.5)
    st.rerun()

if st.session_state['registration_error']:
    st.sidebar.error("모든 칸과 별칭을 채운 후 등록을 눌러주세요.")
    st.session_state['registration_error'] = False


# ==========================================
# [가상 광고 통계 API 로직]
# ==========================================
# 가상 모드 작동 여부 결정
is_test_mode = ("mock" in st.session_state['input_customer_id'].lower()) or (st.session_state['input_customer_id'] == "")

# ==========================================
# [메인 화면 UI]
# ==========================================
st.subheader("인하우스 마케팅 주간 데이터 추출기")
st.caption("사이드바에서 등록한 계정은 로컬에 영구 보존됩니다. 브라우저 텍스트 테이블 양식이 직접 화면에 그리드로 그려지므로, 드래그 복사 시 쉼표와 중앙 정렬이 보존됩니다.")

# 계정 선택 가이드 노출
if selected_profile == "광고 ID 선택" or not selected_profile:
    st.info("👈 왼쪽 사이드바에서 조회 및 제어할 광고 ID(계정)를 먼저 선택해 주세요.")
    st.stop()

# 조회 범위 입력 상자
col_date1, col_date2 = st.columns(2)
with col_date1:
    start_date = st.date_input("조회 시작일 (월요일)", value=last_monday)
with col_date2:
    end_date = st.date_input("조회 종료일 (일요일)", value=last_sunday)

formatted_start = start_date.strftime("%Y-%m-%d")
formatted_end = end_date.strftime("%Y-%m-%d")

st.markdown("### 🗂&nbsp;&nbsp;광고 구성 단계별 선택")

selected_ad_type = st.selectbox("1. 광고그룹 유형을 선택해 주세요.", ['플레이스광고', '파워링크광고', '파워컨텐츠광고'])

if is_test_mode:
    campaign_list = get_mock_campaigns(selected_ad_type)
else:
    campaign_list = fetch_campaigns(
        st.session_state['input_customer_id'], 
        st.session_state['input_api_key'], 
        st.session_state['input_secret_key'], 
        selected_ad_type
    )

if not campaign_list:
    st.warning("⚠️ 선택하신 유형에 부합하는 캠페인이 확인되지 않습니다.")
    st.stop()

camp_options = {c['nccCampaignId']: c['name'] for c in campaign_list}
selected_camp_id = st.selectbox("2. 캠페인을 지정해 주세요.", options=list(camp_options.keys()), format_func=lambda x: camp_options[x])

if is_test_mode:
    adgroup_list = get_mock_adgroups(selected_camp_id)
else:
    adgroup_list = fetch_adgroups(
        st.session_state['input_customer_id'], 
        st.session_state['input_api_key'], 
        st.session_state['input_secret_key'], 
        selected_camp_id
    )

if not adgroup_list:
    st.warning("⚠️ 지정된 캠페인 하위에 개설된 광고그룹이 존재하지 않습니다.")
    st.stop()

adg_options = {g['nccAdgroupId']: g['name'] for g in adgroup_list}
selected_adg_id = st.selectbox("3. 상세 광고그룹을 지정해 주세요.", options=list(adg_options.keys()), format_func=lambda x: adg_options[x])


# '평균 광고 노출 입찰가' 가이드 연동
if selected_ad_type == '플레이스광고':
    avg_bid_val = None
    if not is_test_mode:
        avg_bid_val = fetch_place_avg_bid(
            st.session_state['input_customer_id'], 
            st.session_state['input_api_key'], 
            st.session_state['input_secret_key'], 
            selected_adg_id
        )
    else:
        avg_bid_val = 1460
        
    if avg_bid_val is not None:
        st.info(f"💡 **같은 지역 동종 업종 광고들의 평균 광고 노출 입찰가 참고하기 도움말**\n\n"
                f"**평균 광고 노출 입찰가 : {avg_bid_val:,}**")

st.markdown("---")

# 플레이스광고일 때는 키워드 탭 완전 차단 격리
if selected_ad_type == '플레이스광고':
    show_daily_detail = st.button("📊 일별 상세데이터 가져오기")
    show_keyword_rank = False
else:
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        show_daily_detail = st.button("📊 일별 상세데이터 가져오기")
    with col_btn2:
        show_keyword_rank = st.button("🔑 키워드별 성과(상위 10개) 가져오기")

st.markdown("###")


# ==========================================
# [액션 1] 일별 상세데이터 그리드 분할(HTML) 출력
# ==========================================
if show_daily_detail:
    with st.spinner("일자별 성과 데이터를 분석 중..."):
        if is_test_mode:
            raw_df = get_mock_daily_stats(selected_adg_id, start_date, end_date)
        else:
            raw_df = fetch_daily_stats(
                st.session_state['input_customer_id'], 
                st.session_state['input_api_key'], 
                st.session_state['input_secret_key'], 
                selected_adg_id, 
                start_date, 
                end_date
            )
            
        if raw_df is not None and not raw_df.empty:
            total_imp = raw_df["노출수"].sum()
            total_clk = raw_df["클릭수"].sum()
            total_cost = raw_df["총비용"].sum()
            
            total_ctr = round((total_clk / total_imp) * 100, 2) if total_imp > 0 else 0.0
            total_cpc = int(total_cost / total_clk) if total_clk > 0 else 0
            
            # 주간 총 합계표 구성
            summary_df = pd.DataFrame([{
                "총 노출수": total_imp,
                "총 클릭수": total_clk,
                "평균 클릭률(%)": total_ctr,
                "평균 CPC": total_cpc,
                "총비용 합계": total_cost
            }])
            
            # 독립 성과표 쪼개기 가공 [1]
            imp_clk_df = raw_df[["날짜", "노출수", "클릭수"]].copy()
            cpc_df = raw_df[["날짜", "평균 CPC"]].copy()
            cost_df = raw_df[["날짜", "총비용"]].copy()
            
            # 개별 HTML 마크다운 렌더링 호출 [1]
            st.markdown("##### 🏆 주간 총 합계표")
            st.markdown(convert_df_to_html_grid(summary_df, is_summary_table=True), unsafe_allow_html=True)
            
            st.markdown("###") # 표 간의 간격을 주기 위한 여백
            st.markdown("##### 📊 일별 노출수 및 클릭수")
            st.markdown(convert_df_to_html_grid(imp_clk_df), unsafe_allow_html=True)
            
            st.markdown("###")
            st.markdown("##### 💵 일별 평균 CPC")
            st.markdown(convert_df_to_html_grid(cpc_df), unsafe_allow_html=True)
            
            st.markdown("###")
            st.markdown("##### 💰 일별 총비용")
            st.markdown(convert_df_to_html_grid(cost_df), unsafe_allow_html=True)
            
            st.success("✅ 세부 지표 쪼개기가 완료되었습니다! 필요하신 표의 영역만 마우스로 골라 복사한 뒤, 엑셀 템플릿에 맞추어 열 단위로 붙여넣기 하실 수 있습니다 [1].")
        else:
            st.error("해당 광고그룹에 해당하는 일별 상세 통계 정보가 부존재합니다.")


# ==========================================
# [액션 2] 상위 키워드 지표 그리드(HTML) 출력
# ==========================================
if show_keyword_rank:
    with st.spinner("가장 성과가 뛰어난 상위 10개 키워드 지표를 추적하는 중..."):
        if is_test_mode:
            kw_df = get_mock_keyword_stats(selected_adg_id, selected_ad_type, start_date, end_date)
        else:
            kw_df = fetch_keyword_stats(
                st.session_state['input_customer_id'], 
                st.session_state['input_api_key'], 
                st.session_state['input_secret_key'], 
                selected_adg_id, 
                start_date, 
                end_date, 
                selected_ad_type
            )
            
        if kw_df is not None and not kw_df.empty:
            html_table = convert_df_to_html_grid(kw_df, is_summary_table=False)
            st.markdown(html_table, unsafe_allow_html=True)
            st.success("✅ 키워드 성과 보고서 출력이 완료되었습니다! 엑셀 양식에 맞춰 복사해서 사용해 보세요.")
        else:
            st.warning("⚠️ 해당 광고그룹 내에서 수집 가능한 키워드 실적 지표가 존재하지 않습니다.")
