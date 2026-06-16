import streamlit as st
import datetime
import time
import hmac
import hashlib
import base64
import requests
import pandas as pd

# ==========================================
# [다크모드 원천 방어] 스트림릿 최초 로드 즉시 화이트 테마 고정
# ==========================================
st.set_page_config(page_title="인하우스 마케팅 주간 데이터 추출기", layout="centered")

st.markdown("""
    <style>
    /* 하단 연동부에서 로직 에러가 나더라도 브라우저 배경이 다크 모드로 반전되지 않도록 최상단에서 화이트를 고정합니다. */
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
# [그리드 엔진] 브라우저 및 엑셀 드래그 복사용 표준 테이블 렌더러
# ==========================================
def convert_df_to_html_grid(df, is_summary_table=False):
    html = '<table style="width:100%; border-collapse:collapse; font-family:sans-serif; text-align:center; margin-top:10px; color:#000000 !important; border:1px solid #D0C0A0;">'
    
    header_color = "#FFF9C4" if is_summary_table else "#FFFDE7"
    html += f'<thead><tr style="background-color:{header_color}; border-bottom:2px solid #CCCCCC; font-weight:bold; height:36px;">'
    for col in df.columns:
        html += f'<th style="padding:10px; border:1px solid #E0E0E0; color:#000000 !important; font-size:14px;">{col}</th>'
    html += '</tr></thead><tbody>'
    
    for i, row in df.iterrows():
        row_style = "background-color:#FFFDE7;" if is_summary_table else ""
        html += f'<tr style="{row_style} border-bottom:1px solid #E5E5E5; height:32px;">'
        
        for col in df.columns:
            val = row[col]
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
# [그리드 엔진] 엑셀 '주변 서식에 맞추기' 연동 텍스트(TSV) 추출 가공 모듈
# ==========================================
def dataframe_to_tsv_string(df):
    lines = []
    for _, row in df.iterrows():
        row_vals = []
        for col in df.columns:
            # 복사용 평문을 만들 때 '날짜' 열은 철저히 스킵하여 수치 데이터만 기입하게 제어합니다.
            if col == "날짜":
                continue
            val = row[col]
            if isinstance(val, (int, float)):
                if "클릭률" in col:
                    formatted_val = f"{val:.2f}%"
                else:
                    formatted_val = f"{int(val):,}"
            else:
                formatted_val = str(val)
            row_vals.append(formatted_val)
        lines.append("\t".join(row_vals))
    return "\n".join(lines)


# [컴포넌트] 고대비 일괄 복사 컴포넌트 템플릿 제어 모듈
def render_table_and_button_html(df, title, is_summary_table=False):
    # 화면용 테이블에는 날짜 정보가 정상 포함된 채로 렌더링을 진행합니다.
    table_html = convert_df_to_html_grid(df, is_summary_table)
    # 복사용 소스에서는 텍스트에 포함된 '날짜' 정보가 조건절을 거쳐 완벽히 배제됩니다.
    tsv_text = dataframe_to_tsv_string(df)
    
    unique_id = str(int(time.time() * 1000)) + str(abs(hash(title)))
    
    html_code = f"""
    <div style="font-family:sans-serif; color:#000000 !important; background-color:#FFFFFF; padding:5px;">
        {table_html}
        <button id="btn-{unique_id}" onclick="copyText()" style="
            background-color: #FFFDE7 !important;
            color: #000000 !important;
            border: 2px solid #000000 !important;
            border-radius: 6px !important;
            padding: 10px 16px !important;
            font-size: 13px !important;
            font-weight: bold !important;
            cursor: pointer !important;
            width: 100% !important;
            margin-top: 10px !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
            text-align: center !important;
            display: block !important;
            transition: all 0.2s;
        " onmouseover="this.style.backgroundColor='#FFF9C4'" onmouseout="this.style.backgroundColor='#FFFDE7'">
            📋 복사하기
        </button>
        <textarea id="area-{unique_id}" style="position:absolute; left:-9999px; width:1px; height:1px;">{tsv_text}</textarea>
    </div>
    
    <script>
    function copyText() {{
        try {{
            var text = document.getElementById('area-{unique_id}').value;
            if (navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(text).then(function() {{
                    showCopied();
                }}).catch(function(err) {{
                    fallbackCopy();
                }});
            }} else {{
                fallbackCopy();
            }}
        }} catch (e) {{
            fallbackCopy();
        }}
    }}
    
    function fallbackCopy() {{
        var copyText = document.getElementById('area-{unique_id}');
        copyText.select();
        copyText.setSelectionRange(0, 99999);
        document.execCommand('copy');
        showCopied();
    }}
    
    function showCopied() {{
        var btn = document.getElementById('btn-{unique_id}');
        btn.innerHTML = '✅ 복사 완료';
        btn.style.backgroundColor = '#C8E6C9'; 
        btn.style.borderColor = '#4CAF50';
        btn.style.color = '#000000';
        setTimeout(function() {{
            btn.innerHTML = '📋 복사하기';
            btn.style.backgroundColor = '#FFFDE7';
            btn.style.borderColor = '#000000';
        }}, 2000);
    }}
    </script>
    """
    return html_code


# 표 규격에 따른 실시간 높이 보정
def get_table_iframe_height(df, is_summary=False):
    row_count = len(df)
    if is_summary:
        return 170
    else:
        calc_height = 36 + (32 * row_count) + 95
        return max(calc_height, 120)


# 공백 제목("") 전달 시 위 공간을 침범하지 않도록 예외 처리
def render_table_with_copy_btn(df, title, is_summary_table=False):
    if title:
        st.markdown(f"##### {title}")
    html_content = render_table_and_button_html(df, title, is_summary_table)
    iframe_height = get_table_iframe_height(df, is_summary_table)
    st.components.v1.html(html_content, height=iframe_height, scrolling=False)


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
        # 네이버 서버가 전달하는 날짜 필드의 결측 에러를 방지하기 위해 
        # python의 enumerate를 통해 i 인덱스를 확보하고 시작일자로부터 1일씩 순회하며 독자적으로 날짜를 생성 및 바인딩합니다.
        for i, stat in enumerate(stats_json['data']):
            dt = (start_date + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            
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
# [사이드바 설계 및 Secrets 연동] 로컬 연동 및 영구저장 데이터 완전 소거
# ==========================================
st.sidebar.markdown("### 📁 1. 광고 ID(계정) 선택")

available_accounts = []
try:
    for k in st.secrets.keys():
        section = st.secrets[k]
        if hasattr(section, "get") or isinstance(section, dict):
            if "customer_id" in section and "api_key" in section and "secret_key" in section:
                available_accounts.append(k)
except Exception:
    pass

options_list = ["광고 ID 선택"] + available_accounts

# 콜백 핸들러 정의
def update_inputs_from_profile():
    prof = st.session_state.get('selected_profile')
    if prof == "광고 ID 선택":
        st.session_state['input_customer_id'] = ""
        st.session_state['input_api_key'] = ""
        st.session_state['input_secret_key'] = ""
    elif prof and prof in st.secrets:
        keys = st.secrets[prof]
        st.session_state['input_customer_id'] = keys["customer_id"]
        st.session_state['input_api_key'] = keys["api_key"]
        st.session_state['input_secret_key'] = keys["secret_key"]

if 'selected_profile' not in st.session_state:
    st.session_state['selected_profile'] = "광고 ID 선택"
    update_inputs_from_profile()

selected_profile = st.sidebar.selectbox(
    "조회할 광고 계정을 선택해 주세요. st.secrets에 등록된 계정 목록이 노출됩니다.", 
    options=options_list,
    key='selected_profile',
    on_change=update_inputs_from_profile
)

# 수동 입력창, 등록/삭제/수정 단추 등을 완벽하게 소거했습니다.
input_customer_id = st.session_state.get('input_customer_id', '')
input_api_key = st.session_state.get('input_api_key', '')
input_secret_key = st.session_state.get('input_secret_key', '')


# ==========================================
# [메인 제어] 플레이스 통계 및 결과 표 도출
# ==========================================
st.subheader("인하우스 마케팅 주간 데이터 추출기")
st.caption("사이드바에서 등록한 계정은 안전한 st.secrets 연동을 통하여 불러옵니다. 브라우저 텍스트 테이블 양식이 직접 화면에 그리드로 그려지므로, 드래그 복사 시 쉼표와 중앙 정렬이 보존됩니다.")

# 계정 선택 가이드 노출
if selected_profile == "광고 ID 선택" or not selected_profile:
    st.info("👈 왼쪽 사이드바에서 조회 및 제어할 광고 ID(계정)를 먼저 선택해 주세요.")
    st.stop()

# 가상 모드 작동 여부 결정
is_test_mode = ("mock" in str(input_customer_id).lower()) or (input_customer_id == "")

# 조회 범위 입력 상자
col_date1, col_date2 = st.columns(2)
with col_date1:
    start_date = st.date_input("조회 시작일 (월요일)", value=last_monday)
with col_date2:
    end_date = st.date_input("조회 종료일 (일요일)", value=last_sunday)

st.markdown("### 🗂&nbsp;&nbsp;광고 구성 단계별 선택")

# 광고유형의 선택 순서 (플레이스광고 ➡️ 파워링크광고 ➡️ 파워컨텐츠광고)
selected_ad_type = st.selectbox(
    "1. 광고그룹 유형을 선택해 주세요.", 
    ['플레이스광고', '파워링크광고', '파워컨텐츠광고']
)

if is_test_mode:
    campaign_list = get_mock_campaigns(selected_ad_type)
else:
    campaign_list = fetch_campaigns(
        input_customer_id, 
        input_api_key, 
        input_secret_key, 
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
        input_customer_id, 
        input_api_key, 
        input_secret_key, 
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
            input_customer_id, 
            input_api_key, 
            input_secret_key, 
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
# [액션 1] 일별 상세데이터 그리드 분할 가로 나열(HTML) 출력
# ==========================================
if show_daily_detail:
    with st.spinner("일자별 성과 데이터를 분석 중..."):
        if is_test_mode:
            raw_df = get_mock_daily_stats(selected_adg_id, start_date, end_date)
        else:
            raw_df = fetch_daily_stats(
                input_customer_id, 
                input_api_key, 
                input_secret_key, 
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
            
            # (1) 최상단 종합 요약 "합계표" 구성
            summary_df = pd.DataFrame([{
                "총 노출수": total_imp,
                "총 클릭수": total_clk,
                "평균 클릭률(%)": total_ctr,
                "평균 CPC": total_cpc,
                "총비용 합계": total_cost
            }])
            
            # 좌측 끝단 배치를 위한 독립된 '날짜' 표 구성
            date_df = raw_df[["날짜"]].copy()
            
            # 우측 세 단에는 날짜 정보를 완벽히 차단하고 오직 실무 수치 정보만 수집한 데이터프레임 구성
            imp_clk_df = raw_df[["노출수", "클릭수"]].copy()
            cpc_df = raw_df[["평균 CPC"]].copy()
            cost_df = raw_df[["총비용"]].copy()
            
            # 최상단 요약 "합계표"는 전체 가로 너비를 넓게 채워 렌더링 및 텍스트 전용 복사 단축 버튼을 매핑합니다.
            render_table_with_copy_btn(summary_df, "🏆 주간 총 합계표", is_summary_table=True)
            
            st.markdown("###") # 레이아웃 공백 보정
            
            # 💡 [피드백 반영] 개별 제목 호출 대신 가로 컬럼 시작 직전 상단에 한 번만 대제목 명시
            st.markdown("#### 📊 일별 데이터")
            
            # 지정해주신 비율인 1:1.2:1.2:1.2 로 4단 그리드를 구축합니다.
            col_date, col1, col2, col3 = st.columns([1, 1.2, 1.2, 1.2])
            
            # (1) 첫 번째 col_date 단 : 오직 '날짜' 정보만 가진 표 렌더링 (복사 단추 미노출)
            with col_date:
                date_html = convert_df_to_html_grid(date_df, is_summary_table=False)
                wrapped_date_html = f"""
                <div style="font-family:sans-serif; color:#000000 !important; background-color:#FFFFFF; padding:5px;">
                    {date_html}
                </div>
                """
                # 💡 [버그 조치 및 피드백 반영] 잘림 현상 방지를 위해 다른 컬럼들과 동일한 동적 높이를 계산하여 June 14일까지 선명히 출력합니다.
                iframe_height = get_table_iframe_height(date_df, is_summary=False)
                st.components.v1.html(wrapped_date_html, height=iframe_height, scrolling=False)
                
            # (2) 우측 3개 단 : 날짜가 완전 배제된 순수 수치 표 매핑 (복사 버튼 유지, 제목 파라미터는 ""로 차단)
            with col1:
                render_table_with_copy_btn(imp_clk_df, "", is_summary_table=False)
                
            with col2:
                render_table_with_copy_btn(cpc_df, "", is_summary_table=False)
                
            with col3:
                render_table_with_copy_btn(cost_df, "", is_summary_table=False)
            
            st.success("✅ 조회가 완료되었습니다! 표 바로 밑단에 준비된 검정색 테두리의 복사하기 단축버튼을 누르시면, 날짜가 제외된 순수 지표 데이터만 엑셀에 주변 서식 맞춤으로 간편하게 붙여넣어집니다.")
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
                input_customer_id, 
                input_api_key, 
                input_secret_key, 
                selected_adg_id, 
                start_date, 
                end_date, 
                selected_ad_type
            )
            
        if kw_df is not None and not kw_df.empty:
            render_table_with_copy_btn(kw_df, "📊 키워드별 검색어 성과 (클릭수 상위 10개)", is_summary_table=False)
            st.success("✅ 키워드 성과 보고서 출력이 완료되었습니다! 엑셀 양식에 맞춰 복사해서 사용해 보세요.")
        else:
            st.warning("⚠️ 해당 광고그룹 내에서 수집 가능한 키워드 실적 지표가 존재하지 않습니다.")
