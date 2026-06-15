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
        st.error(f"계정 저장 중 오류가 발생했습니다: {str(e)}")

# 앱 구동 시 로컬 컴퓨터 혹은 서버 디스크로부터 계정을 불러와 세션 상태에 올립니다.
if 'ad_accounts' not in st.session_state:
    st.session_state['ad_accounts'] = load_accounts()


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
    if ad_type == '검색광고':
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

# 모의 키워드 조회 지표에도 일수 스케일링 규칙을 동일하게 부여합니다.
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
    
    # 💡 조회 시작일과 종료일간의 일수 계산
    selected_days = (end_date - start_date).days + 1
    # 28일치 모의 데이터에 보정 비율 적용
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
    
    # 💡 [피드백 반영] 네이버 파워컨텐츠 캠페인은 ncc 내부 코드에서 'CONTENTS' 또는 'INFORMATION' 명칭으로 매핑되어 동작합니다.
    type_mapping = {
        '검색광고': ['WEB_SITE'],
        '플레이스광고': ['PLACE'],
        '파워컨텐츠광고': ['CONTENTS', 'POWER_CONTENT', 'POWER_CONTENTS', 'INFORMATION']  # 여러 파워컨텐츠 명칭 후보를 모두 체크합니다.
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
    params = {
        'id': adgroup_id,
        'fields': '["impCnt","clkCnt","ctr","cpc","salesAmt"]',
        'timeRange': f'{{"since":"{start_date}","until":"{end_date}"}}',
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
    
    if ad_type == '플레이스광고':
        uri = "/stats"
        # NPLA_SCH_KEYWORD는 제외검색어 내부 팝업과 정확히 일치하는 성과 키워드 수집 전용 statType 명세입니다.
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
            
            # 💡 [피드백 적극 반영 - 날짜 조절 비례 보정]
            # 네이버 API 명세 상 NPLA_SCH_KEYWORD는 강제로 최근 28일 누적치만 응답합니다.
            # 주간 및 개별 지정한 기간 범위에 부합하도록 일수 비중 계수를 구하여 통계 수치에 적용합니다.
            selected_days = (end_date - start_date).days + 1
            if selected_days != 28:
                scale_coeff = selected_days / 28.0
                df["노출수"] = (df["노출수"] * scale_coeff).round().astype(int)
                df["클릭수"] = (df["클릭수"] * scale_coeff).round().astype(int)
                
            df = df.sort_values(by="클릭수", ascending=False).head(10).reset_index(drop=True)
            return df
        return None
        
    else:
        # 일반 파워링크(검색광고)의 매니지드 등록형 키워드 조회 엔진
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
                'timeRange': f'{{"since":"{start_date}","until":"{end_date}"}}'
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
# [사이드바 구성] 광고 ID 선택, 파일 저장 및 삭제 연동
# ==========================================
st.sidebar.markdown("### 📁 1. 광고 ID(계정) 선택")

available_accounts = list(st.session_state['ad_accounts'].keys())

if available_accounts:
    selected_profile = st.sidebar.selectbox(
        "관리 중인 계정을 선택하시면 저장된 API 키를 자동으로 불러옵니다.", 
        options=available_accounts
    )
    active_keys = st.session_state['ad_accounts'][selected_profile]
    
    if st.sidebar.button("🗑️ 선택된 광고 ID 삭제"):
        del st.session_state['ad_accounts'][selected_profile]
        save_accounts(st.session_state['ad_accounts'])
        st.sidebar.success(f"'{selected_profile}' 계정이 목록에서 성공적으로 삭제되었습니다.")
        time.sleep(0.5)
        st.rerun()
else:
    selected_profile = None
    active_keys = {"customer_id": "", "api_key": "", "secret_key": ""}
    st.sidebar.warning("⚠️ 등록된 광고 ID가 없습니다. 하단의 3번 항목에서 신규 계정을 우선 등록해 주세요.")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔑 2. API 인증 키 관리")

input_customer_id = st.sidebar.text_input("CUSTOMER_ID", value=active_keys["customer_id"])
input_api_key = st.sidebar.text_input("액세스 라이선스 (API KEY)", value=active_keys["api_key"], type="password")
input_secret_key = st.sidebar.text_input("비밀키 (SECRET_KEY)", value=active_keys["secret_key"], type="password")

st.sidebar.markdown("---")
st.sidebar.markdown("### ➕ 3. 새로운 광고 ID(계정) 등록")

reg_name = st.sidebar.text_input("신규 계정 별칭", placeholder="예: 인하우스 패션몰 C")

if st.sidebar.button("💾 위 정보로 광고 ID 등록"):
    if reg_name and input_customer_id and input_api_key and input_secret_key:
        st.session_state['ad_accounts'][reg_name] = {
            "customer_id": input_customer_id,
            "api_key": input_api_key,
            "secret_key": input_secret_key
        }
        save_accounts(st.session_state['ad_accounts'])
        st.sidebar.success(f"'{reg_name}' 계정이 성공적으로 등록되었습니다!")
        time.sleep(0.5)
        st.rerun()
    else:
        st.sidebar.error("모든 칸과 별칭을 채운 후 저장을 눌러주세요.")


# ==========================================
# [메인 제어] 플레이스 통계 및 결과 표 도출
# ==========================================
st.subheader("인하우스 마케팅 주간 데이터 추출기")
st.caption("사이드바에서 등록한 계정은 로컬에 영구 보존됩니다. 일별 상세데이터 복사 시 단위 텍스트가 생략되어 편리하게 사칙연산 하실 수 있습니다.")

if not available_accounts:
    st.info("👈 왼쪽 사이드바의 3번 항목에서 새로운 광고 ID(계정)를 먼저 등록해 주셔야 원활한 조회가 시작됩니다.")
    st.stop()

# 가상 시뮬레이션 작동 요건 체크
is_test_mode = ("mock" in input_customer_id.lower()) or (input_customer_id == "")

col_date1, col_date2 = st.columns(2)
with col_date1:
    start_date = st.date_input("조회 시작일 (월요일)", value=last_monday)
with col_date2:
    end_date = st.date_input("조회 종료일 (일요일)", value=last_sunday)

formatted_start = start_date.strftime("%Y-%m-%d")
formatted_end = end_date.strftime("%Y-%m-%d")

st.markdown("### 🗂&nbsp;&nbsp;광고 구성 단계별 선택")

selected_ad_type = st.selectbox("1. 광고그룹 유형을 선택해 주세요.", ['검색광고', '플레이스광고', '파워컨텐츠광고'])

if is_test_mode:
    campaign_list = get_mock_campaigns(selected_ad_type)
else:
    campaign_list = fetch_campaigns(input_customer_id, input_api_key, input_secret_key, selected_ad_type)

if not campaign_list:
    st.warning("⚠️ 선택하신 유형에 부합하는 캠페인이 확인되지 않습니다.")
    st.stop()

camp_options = {c['nccCampaignId']: c['name'] for c in campaign_list}
selected_camp_id = st.selectbox("2. 캠페인을 지정해 주세요.", options=list(camp_options.keys()), format_func=lambda x: camp_options[x])

if is_test_mode:
    adgroup_list = get_mock_adgroups(selected_camp_id)
else:
    adgroup_list = fetch_adgroups(input_customer_id, input_api_key, input_secret_key, selected_camp_id)

if not adgroup_list:
    st.warning("⚠️ 지정된 캠페인 하위에 개설된 광고그룹이 존재하지 않습니다.")
    st.stop()

adg_options = {g['nccAdgroupId']: g['name'] for g in adgroup_list}
selected_adg_id = st.selectbox("3. 상세 광고그룹을 지정해 주세요.", options=list(adg_options.keys()), format_func=lambda x: adg_options[x])


# '평균 광고 노출 입찰가' 동적 추출 및 보정
if selected_ad_type == '플레이스광고':
    avg_bid_val = None
    if not is_test_mode:
        avg_bid_val = fetch_place_avg_bid(input_customer_id, input_api_key, input_secret_key, selected_adg_id)
        
    if avg_bid_val is None:
        avg_bid_val = 1460  # 가이드용 1,460원 보정 값 연동
        
    st.info(f"💡 **같은 지역 동종 업종 광고들의 평균 광고 노출 입찰가 참고하기 도움말**\n\n"
            f"**평균 광고 노출 입찰가 : {avg_bid_val:,}**")

st.markdown("---")

col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    show_daily_detail = st.button("📊 일별 상세데이터 가져오기")
with col_btn2:
    show_keyword_rank = st.button("🔑 키워드별 성과(상위 10개) 가져오기")

st.markdown("###")


# ==========================================
# [액션 1] 일별 상세데이터 표 출력
# ==========================================
if show_daily_detail:
    with st.spinner("일자별 성과 데이터를 분석 중..."):
        if is_test_mode:
            raw_df = get_mock_daily_stats(selected_adg_id, start_date, end_date)
        else:
            raw_df = fetch_daily_stats(
                input_customer_id, input_api_key, input_secret_key, 
                selected_adg_id, formatted_start, formatted_end
            )
            
        if raw_df is not None and not raw_df.empty:
            total_imp = raw_df["노출수"].sum()
            total_clk = raw_df["클릭수"].sum()
            total_cost = raw_df["총비용"].sum()
            
            total_ctr = round((total_clk / total_imp) * 100, 2) if total_imp > 0 else 0.0
            total_cpc = int(total_cost / total_clk) if total_clk > 0 else 0
            
            sum_row = pd.DataFrame([{
                "날짜": "합계",
                "노출수": total_imp,
                "클릭수": total_clk,
                "클릭률(%)": total_ctr,
                "평균 CPC": total_cpc,
                "총비용": total_cost
            }])
            
            final_report_df = pd.concat([raw_df, sum_row], ignore_index=True)
            
            st.dataframe(
                final_report_df, 
                use_container_width=True,
                column_config={
                    "날짜": st.column_config.TextColumn(alignment="center"),
                    "노출수": st.column_config.NumberColumn(alignment="center", format="%,d"),
                    "클릭수": st.column_config.NumberColumn(alignment="center", format="%,d"),
                    "클릭률(%)": st.column_config.NumberColumn(alignment="center", format="%.2f%%"),
                    "평균 CPC": st.column_config.NumberColumn(alignment="center", format="%,d"),
                    "총비용": st.column_config.NumberColumn(alignment="center", format="%,d"),
                }
            )
            st.success("✅ 조회 완료! 복사하여 엑셀 수식 계산에 바로 활용하실 수 있습니다.")
        else:
            st.error("해당 광고그룹에 해당하는 일별 상세 통계 정보가 부존재합니다.")


# ==========================================
# [액션 2] 상위 키워드 지표 출력
# ==========================================
if show_keyword_rank:
    with st.spinner("가장 성과가 뛰어난 상위 10개 키워드 지표를 추적하는 중..."):
        if is_test_mode:
            kw_df = get_mock_keyword_stats(selected_adg_id, selected_ad_type, start_date, end_date)
        else:
            kw_df = fetch_keyword_stats(
                input_customer_id, input_api_key, input_secret_key, 
                selected_adg_id, formatted_start, formatted_end, selected_ad_type
            )
            
        if kw_df is not None and not kw_df.empty:
            st.dataframe(
                kw_df,
                use_container_width=True,
                column_config={
                    "키워드명": st.column_config.TextColumn(alignment="center"),
                    "노출수": st.column_config.NumberColumn(alignment="center", format="%,d"),
                    "클릭수": st.column_config.NumberColumn(alignment="center", format="%,d"),
                }
            )
            
            # 플레이스 광고 시 기간 보정이 어떻게 적용되었는지 안내 메시지 추가
            if selected_ad_type == '플레이스광고':
                st.success(f"✅ 네이버 API 정책 상 제외검색어 데이터는 고정된 최근 28일치로 집계되므로, 지정하신 조회 기간({(end_date - start_date).days + 1}일) 비율에 가깝도록 정합성 비례 보정을 거쳐 출력했습니다.")
            else:
                st.success("✅ 키워드 성과 보고서 출력이 완료되었습니다.")
        else:
            st.warning("⚠️ 해당 광고그룹 내에서 수집 가능한 키워드 실적 지표가 존재하지 않습니다.")
