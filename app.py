import streamlit as st
import datetime
import time
import hmac
import hashlib
import base64
import requests
import pandas as pd

# ==========================================
# [다크모드 원천 방어 및 고대비 텍스트 테마 고정]
# ==========================================
# initial_sidebar_state를 expanded로 지정하여 항상 펼쳐진 채로 기동합니다.
st.set_page_config(page_title="광고 데이터 추출기", layout="wide", initial_sidebar_state="expanded")

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
    
    /* 💡 [피드백 적극 반영] 사이드바 무선 라디오를 고급스러운 클릭형 메뉴 카드로 탈바꿈시킵니다. */
    div[data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 6px !important;
        padding: 12px 16px !important;
        margin-bottom: 8px !important;
        width: 100% !important;
        display: flex !important;
        transition: all 0.2s ease-in-out !important;
        cursor: pointer !important;
    }
    
    /* 기존 라디오 동그라미 단추 숨김 처리 */
    div[data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"] div[data-baseweb="radio__input"] {
        display: none !important;
    }
    
    /* 💡 [피드백 적극 반영] 사이드바 선택 목록 텍스트 크기를 15px 볼드로 키우고 기조를 맞춥니다. */
    div[data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"] div[data-testid="stWidgetLabel"] p {
        font-size: 15px !important;
        font-weight: 700 !important;
        color: #000000 !important;
        margin: 0 !important;
    }
    
    /* 💡 [피드백 적극 반영] 선택 시 클릭된 영역처럼 은은한 인디고 블루(#EBF8FF) 배경과 #2B6CB0 보더라인 매핑 */
    div[data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"][aria-checked="true"] {
        background-color: #EBF8FF !important; 
        border: 2px solid #2B6CB0 !important;
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"][aria-checked="true"] div[data-testid="stWidgetLabel"] p {
        color: #2B6CB0 !important; /* 선택 항목 텍스트 딥블루 고정 */
    }
    
    /* 호버(Hover) 시 피드백 이펙트 */
    div[data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"]:hover {
        background-color: #F7FAFC !important;
        border-color: #CBD5E0 !important;
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"][aria-checked="true"]:hover {
        background-color: #EBF8FF !important;
        border-color: #2B6CB0 !important;
    }
    
    /* 날짜 선택 인풋 박스 배경 흰색, 글자색 검정 고정 */
    div[data-testid="stDateInput"] div {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    div[data-testid="stDateInput"] input {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* 데이터 추출 버튼 테두리 제거, 스카이블루 배경, 흰색 고대비 볼드 텍스트 */
    div.stButton > button {
        background-color: #2B6CB0 !important; 
        border: none !important; 
        border-radius: 6px !important;
        padding: 0.8rem 2.0rem !important;
        font-size: 15px !important;
        transition: all 0.3s ease;
        width: 100%;
        box-shadow: 0 4px 6px rgba(43, 108, 176, 0.2) !important;
    }
    div.stButton > button:hover {
        background-color: #3182CE !important; 
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
    
    /* 💡 [피드백 적극 반영 - 사이드바 상시 고정] 접기/열기 버튼을 CSS로 완전히 차단하여 비콜랩서블 형태로 세팅합니다. */
    button[data-testid="stSidebarCollapse"] {
        display: none !important;
    }
    button[data-testid="collapse-sidebar"] {
        display: none !important;
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
    
    # 일반 표 성과 가독성이 훌륭했던 파스텔 블루-그레이 톤으로 세팅합니다.
    header_color = "#D9E2EC" if is_summary_table else "#EDF2F7"
    html += f'<thead><tr style="background-color:{header_color}; border-bottom:2px solid #CCCCCC; font-weight:bold; height:36px; white-space:nowrap !important;">'
    for col in df.columns:
        html += f'<th style="padding:10px; border:1px solid #CBD5E0; color:#000000 !important; font-size:14px; white-space:nowrap !important;">{col}</th>'
    html += '</tr></thead><tbody>'
    
    for i, row in df.iterrows():
        # 데이터 행의 배경색도 블루-그레이 테마에 맞추어 스카이블루 그레이(#F0F4F8) 및 완전화이트로 정립합니다.
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


# [컴포넌트] 신뢰형 인디고 블루 복사 버튼 템플릿 제어 모듈
def render_table_and_button_html(df, title, is_summary_table=False):
    table_html = convert_df_to_html_grid(df, is_summary_table)
    tsv_text = dataframe_to_tsv_string(df)
    
    unique_id = str(int(time.time() * 1000)) + str(abs(hash(title)))
    
    # 복사단추 역시 버튼 외곽 테두리를 없애고 블루계열 채우기와 고대비 텍스트로 보완했습니다.
    html_code = f"""
    <div style="font-family:sans-serif; color:#000000 !important; background-color:#FFFFFF; padding:5px;">
        {table_html}
        <button id="btn-{unique_id}" onclick="copyText()" style="
            background-color: #EBF8FF !important;
            color: #2B6CB0 !important;
            border: none !important;
            border-radius: 6px !important;
            padding: 10px 16px !important;
            font-size: 13px !important;
            font-weight: bold !important;
            cursor: pointer !important;
            width: 100% !important;
            margin-top: 10px !important;
            box-shadow: 0 4px 6px rgba(43, 108, 176, 0.1) !important;
            text-align: center !important;
            display: block !important;
            transition: all 0.2s;
        " onmouseover="this.style.backgroundColor='#BEE3F8'" onmouseout="this.style.backgroundColor='#EBF8FF'">
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
            btn.style.backgroundColor = '#EBF8FF';
            btn.style.borderColor = '#2B6CB0';
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
        # 가로 테두리/여백 영역이 한계에 부딪혀 잘리지 않도록 세로 면적을 최소 140px로 여유롭게 할당했습니다.
        table_html = convert_df_to_html_grid(df, is_summary_table)
        wrapped_html = f"""
        <div style="font-family:sans-serif; color:#000000 !important; background-color:#FFFFFF; padding:5px;">
            {table_html}
        </div>
        """
        iframe_height = max(36 + (32 * len(df)) + 40, 140)
        st.components.v1.html(wrapped_html, height=iframe_height, scrolling=False)


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
# [사이드바 설계 및 Secrets 연동] 
# ==========================================
# 💡 [피드백 반영] 불필요한 라벨 텍스트를 제거하고 세련된 상시 노출식 메뉴로 튜닝했습니다.
selected_menu = st.sidebar.radio(
    label="이동할 서비스를 선택해 주세요.",
    options=["광고 데이터 추출기", "키워드 관리", "추가 확장"],
    key="navigation_menu",
    label_visibility="collapsed" # 라벨을 완벽히 숨겨 텍스트를 삭제 처리합니다.
)


# ==========================================
# [앱 분기 1] 광고 데이터 추출기 프로그램 가동
# ==========================================
if selected_menu == "광고 데이터 추출기":

    # 💡 [피드백 반영] 앱별 최상단 메인 영역에 명시적 타이틀을 각 단독 마킹합니다.
    st.subheader("광고 데이터 추출기")

    # secrets 파싱
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

    # 메인 페이지 내부 상단에 계정 선택 위젯 유지
    selected_profile = st.selectbox(
        "조회할 광고 계정을 선택해 주세요.", 
        options=options_list,
        key='selected_profile'
    )

    # 선택 계정 변경 감지 시 광고유형을 플레이스로 강제 회귀시키는 트리거 장치
    if "last_selected_profile" not in st.session_state:
        st.session_state["last_selected_profile"] = selected_profile

    if st.session_state["last_selected_profile"] != selected_profile:
        st.session_state["selected_ad_type"] = "플레이스광고"
        st.session_state["last_selected_profile"] = selected_profile
        st.rerun()

    # 동적 매핑 수립
    if selected_profile != "광고 ID 선택" and selected_profile in st.secrets:
        active_keys = st.secrets[selected_profile]
        input_customer_id = active_keys["customer_id"]
        input_api_key = active_keys["api_key"]
        input_secret_key = active_keys["secret_key"]
    else:
        input_customer_id = ""
        input_api_key = ""
        input_secret_key = ""

    # 계정 미선택 시 정지
    if selected_profile == "광고 ID 선택" or not selected_profile:
        st.info("👈 상단의 셀렉트 박스에서 조회 및 제어할 광고 ID(계정)를 먼저 선택해 주세요.")
        st.stop()

    # 가상 모드 작동 여부 결정
    is_test_mode = ("mock" in str(input_customer_id).lower()) or (input_customer_id == "")

    # 조회 범위 입력 상자
    col_date1, col_date2 = st.columns(2)
    with col_date1:
        start_date = st.date_input("조회 시작일", value=last_monday)
    with col_date2:
        end_date = st.date_input("조회 종료일", value=last_sunday)

    st.markdown("### 광고 유형")

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

    if not campaign_list:
        if st.session_state.get('api_error_msg'):
            st.error(f"❌ 데이터 추출 과정에서 아래와 같은 원인으로 실패했습니다:\n\n{st.session_state['api_error_msg']}")
            st.session_state['api_error_msg'] = ""  # 리셋
        else:
            st.warning("선택하신 유형에 부합하는 캠페인이 확인되지 않습니다.")
        st.stop()

    camp_options = {c['nccCampaignId']: c['name'] for c in campaign_list}
    selected_camp_id = st.selectbox("캠페인", options=list(camp_options.keys()), format_func=lambda x: camp_options[x])

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
        if st.session_state.get('api_error_msg'):
            st.error(f"❌ 데이터 추출 과정에서 아래와 같은 원인으로 실패했습니다:\n\n{st.session_state['api_error_msg']}")
            st.session_state['api_error_msg'] = ""
        else:
            st.warning("지정된 캠페인 하위에 개설된 광고그룹이 존재하지 않습니다.")
        st.stop()

    adg_options = {g['nccAdgroupId']: g['name'] for g in adgroup_list}
    selected_adg_id = st.selectbox("상세 광고그룹", options=list(adg_options.keys()), format_func=lambda x: adg_options[x])

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

    # 추출 단축 중앙 배열 및 볼드화 가속
    col_btn_left, col_btn_center, col_btn_right = st.columns([1.5, 1, 1.5])
    with col_btn_center:
        show_data = st.button("데이터 추출")

    st.markdown("###")

    # ==========================================
    # [데이터 추출 액션 시작]
    # ==========================================
    if show_data:
        st.session_state['api_error_msg'] = ""
        
        with st.spinner("네이버 광고 서버로부터 원시 데이터를 정합 수집 중입니다..."):
            # 1. 일별 상세 지표 로드
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
            
            # 2. 키워드별 성과 지표 로드 (플레이스광고 아닐 시에만 후행 호출)
            kw_df = None
            if selected_ad_type != '플레이스광고':
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
    # 💡 [피드백 반영] 앱별 최상단 단독 타이틀 마킹합니다.
    st.subheader("키워드 관리")
    st.info("💡 키워드 관리 서비스 준비 중입니다. 핵심 추천 키워드 및 제외 키워드 분석 도구가 탑재될 예정입니다.")


# ==========================================
# [앱 분기 3] 추가 확장 모듈 플레이스홀더
# ==========================================
else:
    # 💡 [피드백 반영] 앱별 최상단 단독 타이틀 마킹합니다.
    st.subheader("추가 확장")
    st.info("💡 추가 위클리 자동화 리포트 및 지표 통합 확장판이 설계될 예정입니다.")
