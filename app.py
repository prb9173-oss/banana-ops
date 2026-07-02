import streamlit as st
import datetime
import time
import hmac
import hashlib
import base64
import requests
import pandas as pd

# ==========================================
# 💡 [다크모드 원천 방어 및 고대비 텍스트 테마 고정]
# ==========================================
# initial_sidebar_state를 expanded로 지정하여 항상 펼쳐진 채로 기동합니다.
st.set_page_config(page_title="광고 데이터 추출기", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    /* 💡 [피드백 적극 반영] 스트림릿 자체 테마 엔진의 글로벌 변수를 직접 제어하여 빨간 테두리 및 달력 꼬임을 원천 차단합니다. */
    :root {
        --primary-color: #2B6CB0 !important; /* 포커스(액티브) 테두리 선 컬러를 신뢰의 블루톤으로 교체 */
        --background-color: #FFFFFF !important; /* 메인 캔버스 배경 흰색 고정 */
        --secondary-background-color: #F8F9FA !important; /* 사이드바 및 인풋 컨트롤 박스 배경 연회색 고정 */
        --text-color: #000000 !important; /* 메인 글자색 검정 */
    }

    /* 메인 앱 배경 완전 화이트 고정 */
    .stApp {
        background-color: #FFFFFF !important;
    }
    
    /* 사이드바 영역의 은은한 연회색 지정 */
    section[data-testid="stSidebar"] {
        background-color: #F8F9FA !important;
        border-right: 1px solid #E0E0E0 !important;
    }
    
    /* 텍스트 요소들 선명한 검정색 지정 */
    p, span, label, h1, h2, h3, h4, h5, h6, li, strong, th, td {
        color: #000000 !important;
    }
    
    /* 인풋 라벨 영역 글자 강조 */
    .stTextInput label p, .stSelectbox label p, .stDateInput label p, [data-testid="stSidebar"] label p {
        color: #000000 !important;
        font-weight: 700 !important;
    }
    
    /* 셀렉트박스 포커스 시 테두리 색상 보정 */
    div[data-baseweb="select"] > div {
        border: 1px solid #CCCCCC !important;
    }
    
    /* 💡 [피드백 적극 반영] 사이드바 접기/열기 버튼 및 관련 기호를 완전히 숨겨 상시 노출형 사이드바를 만듭니다. */
    button[data-testid="stSidebarCollapse"], 
    button[data-testid="stSidebarCollapse"] *,
    button[aria-label="Collapse sidebar"],
    button[aria-label="Expand sidebar"] {
        display: none !important;
    }
    
    /* 💡 [피드백 적극 반영] 사이드바 무선 라디오를 고급스러운 클릭형 메뉴 카드로 탈바꿈시킵니다. */
    div[data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"] {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E0 !important;
        border-radius: 6px !important;
        padding: 16px 20px !important; /* 클릭 면적 극대화를 위한 내부 패딩 증폭 */
        margin-bottom: 12px !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        cursor: pointer !important;
        transition: all 0.2s ease-in-out !important;
        box-sizing: border-box !important;
    }
    
    /* 기존 라디오 동그라미 단추 숨김 처리 */
    div[data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"] div[data-baseweb="radio__input"] {
        display: none !important;
        width: 0 !important;
        height: 0 !important;
    }
    
    /* 💡 [피드백 적극 반영] 사이드바 선택 목록 텍스트 크기를 17px로 대폭 상향하고 아주 굵은 볼드로 지정합니다. (이모지 완전 배제) */
    div[data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"] div[data-testid="stWidgetLabel"] p {
        font-size: 17px !important;
        font-weight: 800 !important;
        color: #333333 !important;
        margin: 0 !important;
        text-align: center !important;
        width: 100% !important;
    }
    
    /* 💡 [피드백 적극 반영] 선택 시 완전히 다른 진한 색상(딥 네이비 #0A2540)으로 채우고 글씨를 흰색(#FFFFFF)으로 반전시켜 확실한 클릭 인지를 제공합니다. */
    div[data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"][aria-checked="true"] {
        background-color: #0A2540 !important; /* 아주 진한 딥 네이비 배경 */
        border: 1px solid #000000 !important;
        box-shadow: 0 4px 6px rgba(10, 37, 64, 0.2) !important;
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"][aria-checked="true"] div[data-testid="stWidgetLabel"] p {
        color: #FFFFFF !important; /* 선택 완료 시 흰색 텍스트 반전 */
    }
    
    /* 사이드바 메뉴 호버(Hover) 피드백 그레이 강조 */
    div[data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"]:hover {
        background-color: #F7FAFC !important;
        border-color: #718096 !important;
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"][aria-checked="true"]:hover {
        background-color: #0A2540 !important;
        border-color: #000000 !important;
    }
    
    /* 💡 [피드백 적극 반영] 데이터 추출 버튼 외곽선 제거, 딥 네이비(#0A2540) 채우기 */
    div.stButton > button {
        background-color: #0A2540 !important; 
        border: none !important; 
        border-radius: 6px !important;
        padding: 0.8rem 2.0rem !important;
        font-size: 15px !important;
        transition: all 0.3s ease;
        width: 100%;
        box-shadow: 0 4px 6px rgba(43, 108, 176, 0.2) !important;
    }
    div.stButton > button:hover {
        background-color: #1A365D !important; 
        border: none !important;
    }
    
    /* 전역 p 태그 간섭에 의한 색상 덮어쓰기를 방지하도록 명확한 자식 선택자 수립 */
    div.stButton > button p {
        color: #FFFFFF !important; /* 글자색 완전한 흰색 보장 */
        font-weight: 900 !important; /* 가장 두꺼운 강도의 굵은 볼드체 유지 */
    }
    div.stButton > button:hover p {
        color: #FFFFFF !important;
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

# 에러 로깅용 세션 세팅
if 'api_error_msg' not in st.session_state:
    st.session_state['api_error_msg'] = ""


# ==========================================
# 💡 [ NameError 예방 보강 ] 콜백 함수의 선행 정의
# ==========================================
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
    
    st.session_state['selected_ad_type'] = '플레이스광고'


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
    # 반응형 스케일링 중 텍스트가 2줄로 줄 바꿈 되어 표가 깨지지 않도록 white-space: nowrap을 원천 강제 주입합니다.
    html = '<table style="width:100%; border-collapse:collapse; font-family:sans-serif; text-align:center; margin-top:10px; color:#000000 !important; border:1px solid #CBD5E0; white-space:nowrap !important;">'
    
    header_color = "#D9E2EC" if is_summary_table else "#EDF2F7"
    html += f'<thead><tr style="background-color:{header_color}; border-bottom:2px solid #CCCCCC; font-weight:bold; height:36px; white-space:nowrap !important;">'
    for col in df.columns:
        html += f'<th style="padding:10px; border:1px solid #CBD5E0; color:#000000 !important; font-size:14px; white-space:nowrap !important;">{col}</th>'
    html += '</tr></thead><tbody>'
    
    for i, row in df.iterrows():
        row_style = "background-color:#F0F4F8;" if is_summary_table else "background-color:#FFFFFF;"
        html += f'<tr style="{row_style} border-bottom:1px solid #E5E5E5; height:32px; white-space:nowrap !important;">'
        
        for col in df.columns:
            val = row[col]
            if isinstance(val, (int, float)):
                if "클릭률" in col:
                    formatted_val = f"{val:.2f}%"
                else:
                    formatted_val = f"{int(val):,}"
            else:
                formatted_val = str(val)
                
            html += f'<td style="padding:8px; border:1px solid #CBD5E0; color:#000000 !important; font-size:13px; white-space:nowrap !important;">{formatted_val}</td>'
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


# [컴포넌트] 신뢰형 딥 네이비 복사 버튼 템플릿 제어 모듈
def render_table_and_button_html(df, title, is_summary_table=False):
    table_html = convert_df_to_html_grid(df, is_summary_table)
    tsv_text = dataframe_to_tsv_string(df)
    
    unique_id = str(int(time.time() * 1000)) + str(abs(hash(title)))
    
    # 복사단축은 테두리를 제거하고 딥 네이비 배경에 화이트 텍스트를 기용했습니다.
    html_code = f"""
    <div style="font-family:sans-serif; color:#000000 !important; background-color:#FFFFFF; padding:5px;">
        {table_html}
        <button id="btn-{unique_id}" onclick="copyText()" style="
            background-color: #0A2540 !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 6px !important;
            padding: 10px 16px !important;
            font-size: 13px !important;
            font-weight: bold !important;
            cursor: pointer !important;
            width: 100% !important;
            margin-top: 10px !important;
            box-shadow: 0 4px 6px rgba(10,37,64,0.1) !important;
            text-align: center !important;
            display: block !important;
            transition: all 0.2s;
        " onmouseover="this.style.backgroundColor='#1A365D'" onmouseout="this.style.backgroundColor='#0A2540'">
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
            btn.style.backgroundColor = '#0A2540';
            btn.style.borderColor = 'none';
            btn.style.color = '#FFFFFF';
        }}, 2000);
    }}
    </script>
    """
    return html_code


# 표 규격에 따른 실시간 높이 보정 수식 (복사버튼 유무에 맞춰 최적화)
def get_table_iframe_height(df, is_summary=False):
    row_count = len(df)
    if is_summary:
        return 220  
    else:
        # 각 행 35px + 보조 마진 140px
        calc_height = 40 + (35 * row_count) + 140
        return max(calc_height, 160)


# 요약합계표 복사 버튼 제거 및 잘림 현상 방지를 위해 최솟값 140px 보정 완료
def render_table_with_copy_btn(df, title, is_summary_table=False, show_copy_btn=True):
    if title:
        st.markdown(f"##### {title}")
        
    if show_copy_btn:
        html_content = render_table_and_button_html(df, title, is_summary_table)
        iframe_height = get_table_iframe_height(df, is_summary_table)
        st.components.v1.html(html_content, height=iframe_height, scrolling=False)
    else:
        # 가로 테두리/여백 영역이 한계에 부딪혀 잘리지 않도록 세로 면적 최소치를 140px로 여유롭게 할당했습니다.
        table_html = convert_df_to_html_grid(df, is_summary_table)
        wrapped_html = f"""
        <div style="font-family:sans-serif; color:#000000 !important; background-color:#FFFFFF; padding:5px;">
            {table_html}
        </div>
        """
        iframe_height = max(36 + (32 * len(df)) + 40, 140)
        st.components.v1.html(wrapped_html, height=iframe_height, scrolling=False)


# ==========================================
# [네이버 API 통신 모듈]
# ==========================================
def fetch_campaigns(customer_id, api_key, secret_key, ad_type):
    BASE_URL = "https://api.searchad.naver.com"
    uri = "/ncc/campaigns"
    headers = get_header("GET", uri, api_key, secret_key, customer_id)
    response = requests.get(f"{BASE_URL}{uri}", headers=headers)
    
    if response.status_code != 200:
        st.session_state['api_error_msg'] = f"캠페인 데이터 연동 과정에서 통신 응답 오류가 발생했습니다. (HTTP {response.status_code}): {response.text}"
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
        st.session_state['api_error_msg'] = f"광고그룹 목록을 연동하는 데 실패했습니다. (HTTP {response.status_code}): {response.text}"
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
        st.session_state['api_error_msg'] = f"일자별 세부 실적 통계를 가져오는 과정에서 오류가 발생했습니다. (HTTP {response.status_code}): {response.text}"
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
        
        # 날짜 범위 수집 조건에 오류가 나는 버전일 시 기본 30일 범위로 재호출 시도
        if response.status_code != 200:
            params.pop('timeRange', None)
            response = requests.get(f"{BASE_URL}{uri}", params=params, headers=headers)
            
        if response.status_code != 200:
            st.session_state['api_error_msg'] = f"플레이스 키워드 성과를 가져오는 과정에서 오류가 발생했습니다. (HTTP {response.status_code}): {response.text}"
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
            st.session_state['api_error_msg'] = f"광고 키워드 목록을 수집하는 데 실패했습니다. (HTTP {kw_response.status_code}): {kw_response.text}"
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
# 💡 [사이드바 설계 및 Secrets 연동] 로컬 연동 및 영구저장 데이터 완전 소거
# ==========================================
st.sidebar.markdown("### 📁 광고 계정 선택")

# st.secrets로부터 유효한 광고 ID 정보 사전을 가진 키들만 안전하게 필터링하여 리스트업합니다.
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

# 💡 [버그 조치 및 에러 해결]
# 에러가 발생한 st.session_state['ad_accounts'] 참조 코드를 완전히 걷어냈습니다 [1].
# 이제 세션 상태를 전혀 타지 않고 st.secrets 에 담긴 순수 보안 키들의 유효성 목록만을 이용해 리스트를 구성합니다 [1].
selected_profile = st.sidebar.selectbox(
    "조회할 광고 계정을 선택해 주세요.", 
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
# 대제목을 '광고 데이터 추출기'로 간결히 변경했습니다.
st.subheader("광고 데이터 추출기")

# 계정 선택 가이드 노출
if selected_profile == "광고 ID 선택" or not selected_profile:
    st.info("👈 왼쪽 사이드바에서 조회 및 제어할 광고 ID(계정)를 먼저 선택해 주세요.")
    st.stop()

# 가상 모드 작동 여부 결정
is_test_mode = ("mock" in str(input_customer_id).lower()) or (input_customer_id == "")

# 💡 [피드백 반영] 가로로 나열되는 선택 영역에 맞추기 위해, 날짜 조회 입력도 3분할 열과 유사하게 넓게 배치합니다.
# 💡 [피드백 반영] 조회 시작일과 조회 종료일 날짜 선택 창 옆에 붙어있던 요일 정보를 완전히 소거했습니다.
col_date1, col_date2 = st.columns(2)
with col_date1:
    # 요일 정보를 기재 방식에서 완전히 소거했습니다.
    start_date = st.date_input("조회 시작일", value=last_monday)
with col_date2:
    # 요일 정보를 기재 방식에서 완전히 소거했습니다.
    end_date = st.date_input("조회 종료일", value=last_sunday)

# 대제목 이모지를 삭제하고 '광고 유형'으로 개편했습니다.
st.markdown("### 광고 유형")

# 원래 요구하셨던 세로형(수직형) 레이아웃으로 완벽히 복원했습니다.
selected_ad_type = st.selectbox(
    "광고그룹", 
    ['플레이스광고', '파워링크광고', '파워컨텐츠광고'],
    key='selected_ad_type'
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

# 💡 [피드백 반영 - 소실 버그 완치] 
# API 에러나 빈 리스트가 조회되더라도 st.stop()으로 뒷단 위젯(상세 광고그룹, 데이터 추출 버튼)을 숨기거나 
# 정지시키지 않고 플레이스홀더 딕셔너리로 우회하여 화면 구성을 고정적으로 보존하도록 개편했습니다.
if not campaign_list:
    if st.session_state.get('api_error_msg'):
        st.error(f"❌ 캠페인을 가져오지 못했습니다:\n\n{st.session_state['api_error_msg']}")
        st.session_state['api_error_msg'] = ""  # 리셋
    else:
        st.warning("선택하신 유형에 부합하는 캠페인이 확인되지 않습니다.")
    
    camp_options = {"": "선택할 수 있는 캠페인이 없습니다."}
else:
    camp_options = {c['nccCampaignId']: c['name'] for c in campaign_list}

# '캠페인' 라벨 명시 및 복원
selected_camp_id = st.selectbox("캠페인", options=list(camp_options.keys()), format_func=lambda x: camp_options[x])

# 선택한 캠페인이 정상 상태일 때만 연동 조회를 개시합니다.
if selected_camp_id != "" and selected_camp_id:
    if is_test_mode:
        adgroup_list = get_mock_adgroups(selected_camp_id)
    else:
        adgroup_list = fetch_adgroups(
            input_customer_id, 
            input_api_key, 
            input_secret_key, 
            selected_camp_id
        )
else:
    adgroup_list = []

# 💡 [피드백 반영 - 소실 버그 완치] 광고그룹이 존재하지 않거나 빈 상태여도 화면에서 UI를 통째로 숨기지 않습니다.
if not adgroup_list:
    if selected_camp_id != "" and selected_camp_id:
        if st.session_state.get('api_error_msg'):
            st.error(f"❌ 광고그룹을 가져오지 못했습니다:\n\n{st.session_state['api_error_msg']}")
            st.session_state['api_error_msg'] = ""
        else:
            st.warning("지정된 캠페인 하위에 개설된 광고그룹이 존재하지 않습니다.")
            
    adg_options = {"": "선택할 수 있는 광고그룹이 없습니다."}
else:
    adg_options = {g['nccAdgroupId']: g['name'] for g in adgroup_list}

# '상세 광고그룹' 라벨 명시 및 복원
selected_adg_id = st.selectbox("상세 광고그룹", options=list(adg_options.keys()), format_func=lambda x: adg_options[x])


# '평균 광고 노출 입찰가' 가이드 연동
if selected_ad_type == '플레이스광고' and selected_adg_id != "":
    avg_bid_val = fetch_place_avg_bid(
        input_customer_id, 
        input_api_key, 
        input_secret_key, 
        selected_adg_id
    ) if not is_test_mode else 1460
        
    if avg_bid_val is not None:
        st.info(f"💡 **같은 지역 동종 업종 광고들의 평균 광고 노출 입찰가 참고하기 도움말**\n\n"
                f"**평균 광고 노출 입찰가 : {avg_bid_val:,}**")

st.markdown("---")

# 💡 [피드백 반영] 데이터 추출 버튼을 가로로 확장하고 중앙에 정렬하기 위해 분할 컴포넌트를 사용합니다.
col_btn_left, col_btn_center, col_btn_right = st.columns([1.5, 1, 1.5])
with col_btn_center:
    show_data = st.button("데이터 추출")

st.markdown("###")


# ==========================================
# [데이터 추출 액션 시작]
# ==========================================
if show_data:
    # 💡 유효하지 않은 광고그룹 상태에서 버튼 클릭을 예외 차단합니다.
    if selected_adg_id == "" or selected_adg_id == "선택할 수 있는 광고그룹이 없습니다.":
        st.error("데이터를 추출할 상세 광고그룹 대상을 먼저 올바르게 지정해 주세요.")
        st.stop()
        
    st.session_state['api_error_msg'] = ""
    
    with st.spinner("네이버 광고 서버로부터 원시 데이터를 정합 수집 중입니다..."):
        # 1. 일별 상세 지표 로드
        raw_df = fetch_daily_stats(
            input_customer_id, 
            input_api_key, 
            input_secret_key, 
            selected_adg_id, 
            start_date, 
            end_date
        )
            
        # 2. 키워드별 성과 지표 로드 (플레이스광고 아닐 시에만 후행 호출)
        kw_df = None
        if selected_ad_type != '플레이스광고':
            kw_df = fetch_keyword_stats(
                input_customer_id, 
                input_api_key, 
                input_secret_key, 
                selected_adg_id, 
                start_date, 
                end_date, 
                selected_ad_type
            )
                
    if st.session_state.get('api_error_msg'):
        st.error(f"❌ 광고 데이터를 수집하는 과정에서 에러가 감지되었습니다. 원인을 점검해 주세요:\n\n{st.session_state['api_error_msg']}")
        st.session_state['api_error_msg'] = ""  # 리셋
        st.stop()
        
    # 일별 데이터 표출 시작
    if raw_df is not None and not raw_df.empty:
        total_imp = raw_df["노출수"].sum()
        total_clk = raw_df["클릭수"].sum()
        total_cost = raw_df["총비용"].sum()
        
        total_ctr = round((total_clk / total_imp) * 100, 2) if total_imp > 0 else 0.0
        total_cpc = int(total_cost / total_clk) if total_clk > 0 else 0
        
        summary_df = pd.DataFrame([{
            "총 노출수": total_imp,
            "총 클릭수": total_clk,
            "평균 클릭률(%)": total_ctr,
            "평균 CPC": total_cpc,
            "총비용 합계": total_cost
        }])
        
        date_df = raw_df[["날짜"]].copy()
        imp_clk_df = raw_df[["노출수", "클릭수"]].copy()
        cpc_df = raw_df[["평균 CPC"]].copy()
        cost_df = raw_df[["총비용"]].copy()
        
        # 주간 총 합계표 부분은 우측 복사하기 버튼이 나타나지 않도록 처리합니다 (show_copy_btn=False)
        render_table_with_copy_btn(summary_df, "🏆 주간 총 합계표", is_summary_table=True, show_copy_btn=False)
        
        st.markdown("###") # 레이아웃 여백 보정
        
        # 가로 격자 상단에 단 하나의 대제목만 정적 마킹합니다.
        st.markdown("#### 📊 일별 데이터")
        
        # 1:1.2:1.2:1.2 비율 구성
        col_date, col1, col2, col3 = st.columns([1, 1.2, 1.2, 1.2])
        
        # (1) 날짜 표 - 버튼 불필요하므로 convert_df_to_html_grid 후 components.html 로만 렌더링
        with col_date:
            date_html = convert_df_to_html_grid(date_df, is_summary_table=False)
            wrapped_date_html = f"""
            <div style="font-family:sans-serif; color:#000000 !important; background-color:#FFFFFF; padding:5px;">
                {date_html}
            </div>
            """
            iframe_height = get_table_iframe_height(date_df, is_summary=False)
            st.components.v1.html(wrapped_date_html, height=iframe_height, scrolling=False)
            
        # (2) 노출수, 클릭수 표 - 빈 값("")을 주어 타이틀 없이 수치와 복사 단추만 콤팩트하게 출력
        with col1:
            render_table_with_copy_btn(imp_clk_df, "", is_summary_table=False)
            
        # (3) 평균 CPC 표
        with col2:
            render_table_with_copy_btn(cpc_df, "", is_summary_table=False)
            
        # (4) 총비용 표
        with col3:
            render_table_with_copy_btn(cost_df, "", is_summary_table=False)
            
        # 플레이스광고가 아닐 때 2단계 영역(키워드 성과 리포트)도 아래에 연쇄 출력합니다.
        if selected_ad_type != '플레이스광고' and kw_df is not None and not kw_df.empty:
            st.markdown("---")
            render_table_with_copy_btn(kw_df, "📊 키워드별 검색어 성과 (클릭수 상위 10개)", is_summary_table=False)
            
        st.success("조회가 완료되었습니다!")
    else:
        st.error("해당 광고그룹에 해당하는 일별 상세 통계 정보가 부존재합니다.")


# ==========================================
# [앱 분기 2] 키워드 관리 모듈 플레이스홀더
# ==========================================
elif selected_menu == "키워드 관리":
    # 앱별 최상단 단독 타이틀 마킹합니다.
    st.subheader("키워드 관리")
    st.info("💡 키워드 관리 서비스 준비 중입니다. 핵심 추천 키워드 및 제외 키워드 분석 도구가 탑재될 예정입니다.")


# ==========================================
# [앱 분기 3] 추가 확장 모듈 플레이스홀더
# ==========================================
else:
    # 앱별 최상단 단독 타이틀 마킹합니다.
    st.subheader("추가 확장")
    st.info("💡 추가 위클리 자동화 리포트 및 지표 통합 확장판이 설계될 예정입니다.")
