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

# 세션 메모리에 영구 저장된 계정 정보를 동기화합니다.
if 'ad_accounts' not in st.session_state:
    st.session_state['ad_accounts'] = load_accounts()

# 입력 폼의 상태를 안정적으로 제어하기 위해 빈 세션 변수를 사전 정의합니다.
if 'input_customer_id' not in st.session_state:
    st.session_state['input_customer_id'] = ""
if 'input_api_key' not in st.session_state:
    st.session_state['input_api_key'] = ""
if 'input_secret_key' not in st.session_state:
    st.session_state['input_secret_key'] = ""
if 'reg_name' not in st.session_state:
    st.session_state['reg_name'] = ""

# 등록 시 알림 제어용 플래그 세션 변수 정의
if 'registration_success' not in st.session_state:
    st.session_state['registration_success'] = ""
if 'registration_error' not in st.session_state:
    st.session_state['registration_error'] = False


# ==========================================
# [콜백] 신규 광고 ID 등록 버튼 핸들러
# ==========================================
def register_account_callback():
    cust_id = st.session_state.get('input_customer_id', '')
    api_k = st.session_state.get('input_api_key', '')
    sec_k = st.session_state.get('input_secret_key', '')
    r_name = st.session_state.get('reg_name', '')
    
    if r_name and cust_id and api_k and sec_k:
        # 데이터 사전에 계정 정보 등록 및 로컬 파일 영구 보존
        st.session_state['ad_accounts'][r_name] = {
            "customer_id": cust_id,
            "api_key": api_k,
            "secret_key": sec_k
        }
        save_accounts(st.session_state['ad_accounts'])
        
        # 저장 성공 후 입력란 상태 클린 초기화
        st.session_state['input_customer_id'] = ""
        st.session_state['input_api_key'] = ""
        st.session_state['input_secret_key'] = ""
        st.session_state['reg_name'] = ""
        st.session_state['selected_profile'] = "광고 ID 선택"
        
        st.session_state['registration_success'] = r_name
    else:
        st.session_state['registration_error'] = True


# ==========================================
# [그리드 엔진] 브라우저 및 엑셀 드래그 복사용 표준 테이블 렌더러
# ==========================================
def convert_df_to_html_grid(df, is_summary_table=False):
    # 엑셀 드래그 복사 시 가운데 정렬 및 쉼표 서식을 안전히 상속하도록 웹 표준 <table> 요소를 빌드합니다.
    html = '<table style="width:100%; border-collapse:collapse; font-family:sans-serif; text-align:center; margin-top:10px; color:#000000 !important; border:1px solid #D0C0A0;">'
    
    # 테이블 구분 헤더(Header) 생성
    # 상단 총 합계표일 때는 좀 더 강조된 연노랑(#FFF9C4) 음영을 제공합니다.
    header_color = "#FFF9C4" if is_summary_table else "#FFFDE7"
    html += f'<thead><tr style="background-color:{header_color}; border-bottom:2px solid #CCCCCC; font-weight:bold; height:36px;">'
    for col in df.columns:
        html += f'<th style="padding:10px; border:1px solid #E0E0E0; color:#000000 !important; font-size:14px;">{col}</th>'
    html += '</tr></thead><tbody>'
    
    # 데이터 행(Rows) 렌더링 루프
    for i, row in df.iterrows():
        # 합계표인 경우 전용 백그라운드 색상을 은은하게 덧씌웁니다.
        row_style = "background-color:#FFFDE7;" if is_summary_table else ""
        html += f'<tr style="{row_style} border-bottom:1px solid #E5E5E5; height:32px;">'
        
        for col in df.columns:
            val = row[col]
            # 수치형 값 포맷 세분화
            if isinstance(val, (int, float)):
                if "클릭률" in col:
                    formatted_val = f"{val:.2f}%"
                else:
                    formatted_val = f"{int(val):,}"
            else:
                formatted_val = str(val)
                
            html += f'<td style="padding:8px; border:1px solid #E0E0E0; color:#000000 !important; font-size:13px;">{formatted_val}</td>'
        html += '</tr>'
        
    html += '</tbody></table>'
    return html


# ==========================================
# [디자인 정의] 배경 화이트, 텍스트 블랙 고정 (CSS)
# ==========================================
st.set_page_config(page_title="인하우스 마케팅 주간 데이터 추출기", layout="centered")

st.markdown("""
    <style>
    .stApp {
        background-color: #FFFFFF !important;
    }
    section[data-testid="stSidebar"] {
        background-color: #F8F9FA !important;
        border-right: 1px solid #E0E0E0 !important;
    }
    p, span, label, h1, h2, h3, h4, h5, h6, li, strong, th, td {
        color: #000000 !important;
    }
    .stMarkdown, [data-testid="stWidgetLabel"] p, .stCaptionContainer p {
        color: #000000 !important;
        font-weight: 500;
    }
    .stTextInput label p, .stSelectbox label p, .stDateInput label p, [data-testid="stSidebar"] label p {
        color: #000000 !important;
        font-weight: 700 !important;
    }
    div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 1px solid #CCCCCC !important;
    }
    div[data-baseweb="popover"] {
        background-color: #FFFFFF !important;
    }
    div[role="listbox"] div, li[role="option"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    li[role="option"]:hover, div[role="option"]:hover {
        background-color: #FFF9C4 !important;
        color: #000000 !important;
    }
    div.stButton > button {
        background-color: #FFFDE7 !important;
        color: #000000 !important;
        border: 1px solid #C0B090 !important;
        border-radius: 6px !important;
        padding: 0.6rem 1.5rem !important;
        font-weight: bold !important;
        transition: all 0.3s ease;
        width: 100%;
    }
    div.stButton > button:hover {
        background-color: #FFF9C4 !important;
        border: 1px solid #888888 !important;
    }
    </style>
""", unsafe_allow_html=True)


# ==========================================
# [날짜 계산] 오늘 기준 지난주 월요일 ~ 지난주 일요일 자동 계산
# ==========================================
today = datetime.date.today()
current_weekday = today.weekday()
last_monday = today - datetime.timedelta(days=current_weekday + 7)
last_sunday = last_monday + datetime.timedelta(days=6)


# ==========================================
# [인증] 네이버 검색광고 API HMAC 서명
# ==========================================
def make_signature(timestamp, method, uri, secret_key):
    message = f"{timestamp}.{method}.{uri}"
    hash_obj = hmac.new(secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256)
    return base64.b64encode(hash_obj.digest()).decode("utf-8")

def get_header(method, uri, api_key, secret_key, customer_id):
    timestamp = str(int(time.time() * 1000))
    signature = make_signature(timestamp, method, uri, secret_key)
    return {
        'Content-Type': 'application/json; charset=UTF-8',
        'X-Timestamp': timestamp,
        'X-API-KEY': api_key,
        'X-Customer': str(customer_id),
        'X-Signature': signature
    }


# ==========================================
# [가상 데이터 공급] 임시 시뮬레이션용 모의 데이터셋 생성기
# ==========================================
def get_mock_campaigns(ad_type):
    if ad_type == '파워링크광고':
        return [{"nccCampaignId": "camp-sh-01", "name": "[검색] 브랜드_공식_캠페인"},
                {"nccCampaignId": "camp-sh-02", "name": "[검색] 파워링크_제품홍보"}]
    elif ad_type == '플레이스광고':
        return [{"nccCampaignId": "camp-pl-01", "name": "[플레이스] 지점_스마트플레이스_노출"}]
    else:
        return [{"nccCampaignId": "camp-pc-01", "name": "[파워컨텐츠] 블로그_콘텐츠_캠페인"}]

def get_mock_adgroups(campaign_id):
    if campaign_id == "camp-sh-01":
        return [{"nccAdgroupId": "grp-sh-01-a", "name": "PC_대표브랜드_광고그룹"},
                {"nccAdgroupId": "grp-sh-01-b", "name": "모바일_대표브랜드_광고그룹"}]
    elif campaign_id == "camp-sh-02":
        return [{"nccAdgroupId": "grp-sh-02-a", "name": "인기상품_키워드_그룹"}]
    elif campaign_id == "camp-pl-01":
        return [{"nccAdgroupId": "grp-pl-01-a", "name": "지역상권_플레이스_그룹"}]
    else:
        return [{"nccAdgroupId": "grp-pc-01-a", "name": "리뷰_블로그_광고그룹"}]

def get_mock_daily_stats(adgroup_id, start_date, end_date):
    date_list = []
    curr = start_date
    while curr <= end_date:
        date_list.append(curr)
        curr += datetime.timedelta(days=1)
    
    import random
    random.seed(hash(adgroup_id) + int(start_date.strftime("%Y%m%d")))
    
    rows = []
    for d in date_list:
        imp = random.randint(4000, 15000)
        clk = random.randint(80, 350)
        cost = clk * random.randint(500, 900)
        ctr = round((clk / imp) * 100, 2) if imp > 0 else 0.0
        cpc = int(cost / clk) if clk > 0 else 0
        
        rows.append({
            "날짜": d.strftime("%Y-%m-%d"),
            "노출수": imp,
            "클릭수": clk,
            "클릭률(%)": ctr,
            "평균 CPC": cpc,
            "총비용": cost
        })
    return pd.DataFrame(rows)

def get_mock_keyword_stats(adgroup_id, ad_type, start_date, end_date):
    import random
    random.seed(hash(adgroup_id))
    
    if ad_type == '플레이스광고':
        keywords = ["강남역 맛집", "강남역 점심 추천", "역삼 근처 조용한 일식집", "강남 주차가능 맛집", "강남 스마트플레이스 예약", 
                    "강남 핫플레이스 추천", "모임하기 좋은 일식당", "강남 가성비 횟집", "강남역 데이트 코스"]
    else:
        keywords = ["마케팅 대행사", "데이터 분석", "광고 가이드", "보고서 엑셀", "스마트스토어 홍보", 
                    "주간 성과표", "블로그마케팅", "지역 소상공인 광고", "인하우스 마케터"]
    
    selected_kws = random.sample(keywords, min(len(keywords), 10))
    
    selected_days = (end_date - start_date).days + 1
    scale_factor = selected_days / 28.0
    
    rows = []
    for kw in selected_kws:
        base_imp = random.randint(4000, 15000)
        base_clk = random.randint(80, 350)
        
        rows.append({
            "키워드명": kw,
            "노출수": int(base_imp * scale_factor),
            "클릭수": int(base_clk * scale_factor)
        })
    df = pd.DataFrame(rows)
    df = df.sort_values(by="클릭수", ascending=False).head(10).reset_index(drop=True)
    return df


# ==========================================
# [네이버 API 통신 모듈]
# ==========================================
def fetch_campaigns(customer_id, api_key, secret_key, ad_type):
    BASE_URL = "https://api.searchad.naver.com"
    uri = "/ncc/campaigns"
    headers = get_header("GET", uri, api_key, secret_key, customer_id)
    response = requests.get(f"{BASE_URL}{uri}", headers=headers)
    if response.status_code != 200:
        return []
    campaigns = response.json()
    
    type_mapping = {
        '파워링크광고': ['WEB_SITE'],
        '플레이스광고': ['PLACE'],
        '파워컨텐츠광고': ['CONTENTS', 'POWER_CONTENT', 'POWER_CONTENTS', 'INFORMATION']
    }
    target_types = type_mapping.get(ad_type, ['WEB_SITE'])
    return [c for c in campaigns if c.get('campaignTp') in target_types]

def fetch_adgroups(customer_id, api_key, secret_key, campaign_id):
    BASE_URL = "https://api.searchad.naver.com"
    uri = "/ncc/adgroups"
    params = {'nccCampaignId': campaign_id}
    headers = get_header("GET", uri, api_key, secret_key, customer_id)
    response = requests.get(f"{BASE_URL}{uri}", params=params, headers=headers)
    if response.status_code != 200:
        return []
    return response.json()

def fetch_place_avg_bid(customer_id, api_key, secret_key, adgroup_id):
    BASE_URL = "https://api.searchad.naver.com"
    uri = f"/ncc/adgroups/{adgroup_id}"
    headers = get_header("GET", uri, api_key, secret_key, customer_id)
    response = requests.get(f"{BASE_URL}{uri}", headers=headers)
    
    if response.status_code == 200:
        adg_info = response.json()
        for field in ['averagePositionBid', 'exposureMinimumBid', 'estimatedBid']:
            if field in adg_info and adg_info[field]:
                return int(adg_info[field])
                
    try:
        est_uri = f"/estimate/average-position-bid/adgroup/{adgroup_id}"
        est_headers = get_header("GET", est_uri, api_key, secret_key, customer_id)
        est_response = requests.get(f"{BASE_URL}{est_uri}", headers=est_headers)
        if est_response.status_code == 200:
            est_data = est_response.json()
            if isinstance(est_data, dict) and 'bidAmt' in est_data:
                return int(est_data['bidAmt'])
    except Exception:
        pass
    return None

def fetch_daily_stats(customer_id, api_key, secret_key, adgroup_id, start_date, end_date):
    BASE_URL = "https://api.searchad.naver.com"
    uri = "/stats"
    
    formatted_start = start_date.strftime("%Y-%m-%d")
    formatted_end = end_date.strftime("%Y-%m-%d")
    
    params = {
        'id': adgroup_id,
        'fields': '["impCnt","clkCnt","ctr","cpc","salesAmt"]',
        'timeRange': f'{{"since":"{formatted_start}","until":"{formatted_end}"}}',
        'timeIncrement': '1'
    }
    headers = get_header("GET", uri, api_key, secret_key, customer_id)
    response = requests.get(f"{BASE_URL}{uri}", params=params, headers=headers)
    if response.status_code != 200:
        return None
        
    stats_json = response.json()
    data_rows = []
    if 'data' in stats_json:
        for stat in stats_json['data']:
            dt = stat.get('date', '')
            imp = int(stat.get('impCnt', 0))
            clk = int(stat.get('clkCnt', 0))
            ctr = float(stat.get('ctr', 0.0))
            cpc = int(stat.get('cpc', 0))
            cost = int(stat.get('salesAmt', 0))
            
            data_rows.append({
                "날짜": dt,
                "노출수": imp,
                "클릭수": clk,
                "클릭률(%)": ctr,
                "평균 CPC": cpc,
                "총비용": cost
            })
    if data_rows:
        return pd.DataFrame(data_rows)
    return None

def fetch_keyword_stats(customer_id, api_key, secret_key, adgroup_id, start_date, end_date, ad_type):
    BASE_URL = "https://api.searchad.naver.com"
    
    formatted_start = start_date.strftime("%Y-%m-%d")
    formatted_end = end_date.strftime("%Y-%m-%d")
    
    if ad_type == '플레이스광고':
        uri = "/stats"
        params = {
            'id': adgroup_id,
            'statType': 'NPLA_SCH_KEYWORD'
        }
        headers = get_header("GET", uri, api_key, secret_key, customer_id)
        response = requests.get(f"{BASE_URL}{uri}", params=params, headers=headers)
        
        if response.status_code != 200:
            return None
            
        stats_json = response.json()
        data_rows = []
        
        items = stats_json if isinstance(stats_json, list) else stats_json.get('data', [])
        for item in items:
            kw = item.get('schKeyword') or item.get('keyword') or item.get('searchKeyword') or item.get('id')
            imp = int(item.get('impCnt', 0))
            clk = int(item.get('clkCnt', 0))
            if kw:
                data_rows.append({
                    "키워드명": kw,
                    "노출수": imp,
                    "클릭수": clk
                })
        if data_rows:
            df = pd.DataFrame(data_rows)
            
            selected_days = (end_date - start_date).days + 1
            if selected_days != 28:
                scale_coeff = selected_days / 28.0
                df["노출수"] = (df["노출수"] * scale_coeff).round().astype(int)
                df["클릭수"] = (df["클릭수"] * scale_coeff).round().astype(int)
                
            df = df.sort_values(by="클릭수", ascending=False).head(10).reset_index(drop=True)
            return df
        return None
        
    else:
        kw_list_uri = "/ncc/keywords"
        kw_params = {'nccAdgroupId': adgroup_id}
        kw_headers = get_header("GET", kw_list_uri, api_key, secret_key, customer_id)
        kw_response = requests.get(f"{BASE_URL}{kw_list_uri}", params=kw_params, headers=kw_headers)
        
        if kw_response.status_code != 200:
            return None
            
        keywords = kw_response.json()
        if not keywords:
            return None
            
        kw_ids = [k.get('nccKeywordId') for k in keywords]
        kw_map = {k.get('nccKeywordId'): k.get('keyword') for k in keywords}
        
        stats_uri = "/stats"
        data_rows = []
        chunk_size = 50
        for i in range(0, len(kw_ids), chunk_size):
            chunk_ids = kw_ids[i:i+chunk_size]
            params = {
                'ids': chunk_ids,
                'fields': '["impCnt","clkCnt"]',
                'timeRange': f'{{"since":"{formatted_start}","until":"{formatted_end}"}}'
            }
            headers = get_header("GET", stats_uri, api_key, secret_key, customer_id)
            response = requests.get(f"{BASE_URL}{stats_uri}", params=params, headers=headers)
            
            if response.status_code == 200:
                stats_json = response.json()
                if 'data' in stats_json:
                    for stat in stats_json['data']:
                        kw_id = stat.get('id')
                        kw_name = kw_map.get(kw_id, "알 수 없는 키워드")
                        imp = int(stat.get('impCnt', 0))
                        clk = int(stat.get('clkCnt', 0))
                        data_rows.append({
                            "키워드명": kw_name,
                            "노출수": imp,
                            "클릭수": clk
                        })
                        
        if data_rows:
            df = pd.DataFrame(data_rows)
            df = df.sort_values(by="클릭수", ascending=False).head(10).reset_index(drop=True)
            return df
        return None


# ==========================================
# [사이드바 설계 및 동적 바인딩 콜백]
# ==========================================
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
# [메인 제어] 플레이스 통계 및 결과 표 도출
# ==========================================
st.subheader("인하우스 마케팅 주간 데이터 추출기")
st.caption("사이드바에서 등록한 계정은 로컬에 영구 보존됩니다. 브라우저 텍스트 테이블 양식이 직접 화면에 그리드로 그려지므로, 드래그 복사 시 쉼표와 중앙 정렬이 보존됩니다.")

# 계정 선택 가이드 노출
if selected_profile == "광고 ID 선택" or not selected_profile:
    st.info("👈 왼쪽 사이드바에서 조회 및 제어할 광고 ID(계정)를 먼저 선택해 주세요.")
    st.stop()

# 가상 모드 작동 여부 결정
is_test_mode = ("mock" in st.session_state['input_customer_id'].lower()) or (st.session_state['input_customer_id'] == "")

# 조회 범위 입력 상자
col_date1, col_date2 = st.columns(2)
with col_date1:
    start_date = st.date_input("조회 시작일 (월요일)", value=last_monday)
with col_date2:
    end_date = st.date_input("조회 종료일 (일요일)", value=last_sunday)

st.markdown("### 🗂&nbsp;&nbsp;광고 구성 단계별 선택")

selected_ad_type = st.selectbox(
    "1. 광고그룹 유형을 선택해 주세요.", 
    ['플레이스광고', '파워링크광고', '파워컨텐츠광고']
)

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
            
            # (1) 최상단 종합 요약 "합계표" 구성 (날짜 불필요)
            summary_df = pd.DataFrame([{
                "총 노출수": total_imp,
                "총 클릭수": total_clk,
                "평균 클릭률(%)": total_ctr,
                "평균 CPC": total_cpc,
                "총비용 합계": total_cost
            }])
            
            # 💡 [피드백 반영] 일별 데이터 테이블을 쪼갤 때, 엑셀 템플릿과의 연치를 위해 '날짜' 열을 완전히 제거하여 수치만 구성합니다.
            
            # (2) 노출수와 클릭수 정보 성과표 (날짜 열 제거)
            imp_clk_df = raw_df[["노출수", "클릭수"]].copy()
            
            # (3) 일자별 평균 CPC 표 구성 (날짜 열 제거)
            cpc_df = raw_df[["평균 CPC"]].copy()
            
            # (4) 일자별 총비용 표 구성 (날짜 열 제거)
            cost_df = raw_df[["총비용"]].copy()
            
            # 격자 템플릿(HTML)을 활용하여 화면에 순서대로 배치합니다.
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
            
            st.success("✅ 세부 지표 쪼개기가 완료되었습니다! 필요하신 표의 영역만 마우스로 골라 복사한 뒤, 엑셀 템플릿에 맞추어 열 단위로 붙여넣기 하실 수 있습니다.")
        else:
            st.error("해당 광고그룹에 해당하는 일별 상세 통계 정보가 부존재합니다.")


# ==========================================
# [액션 2] 상위 키워드 지표 그리드(HTML) 출력 (파워링크, 파워컨텐츠 유형 전용)
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
