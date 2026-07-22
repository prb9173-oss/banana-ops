import streamlit as st
import datetime
import time
import hmac
import hashlib
import base64
import requests
import pandas as pd

# ==========================================
# 💡 [테마 고정 방식 전환]
# 라이트/다크 모드에 따라 컴포넌트별로 색이 흔들리던 문제의 원인은, 테마를
# CSS로 "땜질"해서 강제하고 있었기 때문입니다 (일부 요소는 덮어써지고,
# 셀렉트박스 등 내부 컴포넌트는 놓쳐서 다크 배경이 그대로 노출됨).
#
# 이제 앱의 기준 테마 자체를 .streamlit/config.toml 에서 라이트로 고정합니다.
# 이렇게 하면 사용자의 OS/브라우저가 다크모드여도 모든 기본 컴포넌트(셀렉트박스,
# 날짜입력, 사이드바 등)가 항상 같은 라이트 테마로 렌더링되어, 요소마다 서로
# 다른 톤이 섞이는 일이 없어집니다. 아래 CSS는 config.toml이 다루지 않는
# "브랜드 디테일"(폰트, 버튼 스타일, 여백)만 최소한으로 얹습니다.
# ==========================================
st.set_page_config(page_title="광고 데이터 추출기", layout="wide", page_icon="📊")

PRIMARY = "#1E3A5F"        # 딥 네이비 (버튼, 강조) — config.toml의 primaryColor와 동일하게 유지
PRIMARY_HOVER = "#16304C"

st.markdown(f"""
    <style>
    html, body, [class*="css"] {{
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Malgun Gothic', sans-serif;
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
        display: block;
        margin: 0 auto;
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
TABLE_BORDER = "#E3E6EB"
TABLE_HEADER_BG = "#EEF3FA"          # 일반 표 헤더
TABLE_HEADER_BG_SUMMARY = "#DCE4F0"  # 합계표 헤더 (한 톤 진하게)
TABLE_ROW_ALT_BG = "#F7F9FB"

def convert_df_to_html_grid(df, is_summary_table=False):
    # color/white-space는 상속되는 속성이므로 최상위 table에서 한 번만 지정합니다.
    html = (
        '<table style="width:100%; border-collapse:collapse; font-family:inherit; '
        f'text-align:center; margin-top:10px; color:#16181D; border:1px solid {TABLE_BORDER}; white-space:nowrap;">'
    )

    header_bg = TABLE_HEADER_BG_SUMMARY if is_summary_table else TABLE_HEADER_BG
    html += f'<thead><tr style="background-color:{header_bg}; border-bottom:2px solid {TABLE_BORDER}; font-weight:600; height:36px;">'
    for col in df.columns:
        html += f'<th style="padding:10px; border:1px solid {TABLE_BORDER}; font-size:14px;">{col}</th>'
    html += '</tr></thead><tbody>'

    for i, row in df.iterrows():
        row_bg = TABLE_ROW_ALT_BG if is_summary_table else "#FFFFFF"
        html += f'<tr style="background-color:{row_bg}; border-bottom:1px solid {TABLE_BORDER}; height:32px;">'

        for col in df.columns:
            val = row[col]
            if isinstance(val, (int, float)):
                formatted_val = f"{val:.2f}%" if "클릭률" in col else f"{int(val):,}"
            else:
                formatted_val = str(val)

            html += f'<td style="padding:8px; border:1px solid {TABLE_BORDER}; font-size:13px;">{formatted_val}</td>'
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


# ==========================================
# 💡 [복사 버튼 방식: 고정 높이로 되돌림]
# 지난 버전의 문제는 "버튼이 있다는 것" 자체가 아니라, iframe이 스스로 자기 크기를
# 조절하려다가 Streamlit이 미리 예약해 둔 자리와 어긋나서 다음 요소와 겹쳤던 거였습니다.
# 그래서 자동 조절 스크립트는 완전히 빼고, 표+버튼에 필요한 높이를 미리 정확히 계산해서
# "고정값"으로 넘깁니다. 고정값은 항상 Streamlit이 예약하는 자리와 정확히 같기 때문에
# (스스로 늘어나거나 줄어들지 않으므로) 겹치거나 잘리는 문제 자체가 구조적으로 없습니다.
# ==========================================

def render_plain_table(df, is_summary_table=False):
    table_html = convert_df_to_html_grid(df, is_summary_table)
    st.markdown(
        f'<div style="background-color:#FFFFFF; border:1px solid #E3E6EB; '
        f'border-radius:10px; padding:12px; margin-bottom:6px;">{table_html}</div>',
        unsafe_allow_html=True,
    )


def render_table_and_button_html(df, is_summary_table=False):
    table_html = convert_df_to_html_grid(df, is_summary_table)
    tsv_text = dataframe_to_tsv_string(df)
    unique_id = str(int(time.time() * 1000)) + str(abs(hash(tsv_text)))

    return f"""
    <div style="font-family:inherit; color:#16181D; background-color:#FFFFFF; padding:5px;">
        {table_html}
        <button id="btn-{unique_id}" onclick="copyText()" style="
            background-color: #1E3A5F;
            color: #FFFFFF;
            border: none;
            border-radius: 8px;
            padding: 10px 16px;
            font-size: 13px;
            font-weight: 700;
            cursor: pointer;
            width: 100%;
            margin-top: 10px;
            box-shadow: 0 1px 2px rgba(16,24,40,0.08);
            text-align: center;
            display: block;
            transition: background-color 0.15s ease;
        " onmouseover="this.style.backgroundColor='#16304C'" onmouseout="this.style.backgroundColor='#1E3A5F'">
            📋 복사하기
        </button>
        <textarea id="area-{unique_id}" style="position:absolute; left:-9999px; width:1px; height:1px;">{tsv_text}</textarea>
    </div>
    <script>
    function copyText() {{
        try {{
            var text = document.getElementById('area-{unique_id}').value;
            if (navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(text).then(showCopied).catch(fallbackCopy);
            }} else {{
                fallbackCopy();
            }}
        }} catch (e) {{ fallbackCopy(); }}
    }}
    function fallbackCopy() {{
        var t = document.getElementById('area-{unique_id}');
        t.select();
        t.setSelectionRange(0, 99999);
        document.execCommand('copy');
        showCopied();
    }}
    function showCopied() {{
        var btn = document.getElementById('btn-{unique_id}');
        btn.innerHTML = '✅ 복사 완료';
        btn.style.backgroundColor = '#DCFCE7';
        btn.style.color = '#166534';
        setTimeout(function() {{
            btn.innerHTML = '📋 복사하기';
            btn.style.backgroundColor = '#1E3A5F';
            btn.style.color = '#FFFFFF';
        }}, 2000);
    }}
    </script>
    """


# 표+버튼이 실제로 차지하는 높이를 미리 계산합니다 (헤더 40 + 행당 34 + 버튼/여백 영역 70).
# 여유를 살짝 더 둬서, 혹시 오차가 나더라도 "겹침"이 아니라 "약간의 빈 여백" 쪽으로만
# 벗어나도록 했습니다 — 안전한 쪽으로만 오차가 나게 하는 게 핵심입니다.
def get_table_iframe_height(row_count):
    return min(600, 50 + (34 * row_count) + 70)


def render_table_with_copy_btn(df, title, is_summary_table=False, show_copy_btn=True):
    if title:
        st.markdown(f"##### {title}")

    if show_copy_btn:
        html_content = render_table_and_button_html(df, is_summary_table)
        height = get_table_iframe_height(len(df))
        st.components.v1.html(html_content, height=height, scrolling=(height >= 600))
    else:
        render_plain_table(df, is_summary_table)


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
# [네이버 API 통신 캐싱 및 모듈 구조 설계]
# Streamlit 세션 상태(session_state) 쓰기 오동작을 원천 방지하기 위해 
# 순수 통신부만 안전하게 캐싱 처리한 뒤 메인 프레임워크와 결합합니다.
# ==========================================
@st.cache_data(ttl=600, show_spinner=False)
def _fetch_campaigns_cached(customer_id, api_key, secret_key):
    BASE_URL = "https://api.searchad.naver.com"
    uri = "/ncc/campaigns"
    headers = get_header("GET", uri, api_key, secret_key, customer_id)
    response = requests.get(f"{BASE_URL}{uri}", headers=headers)
    return response.status_code, response.text, response.json() if response.status_code == 200 else None

def fetch_campaigns(customer_id, api_key, secret_key, ad_type):
    status_code, res_text, campaigns = _fetch_campaigns_cached(customer_id, api_key, secret_key)
    
    if status_code != 200:
        st.session_state['api_error_msg'] = f"캠페인 데이터 연동 과정에서 통신 응답 오류가 발생했습니다. (HTTP {status_code}): {res_text}"
        return []
    
    type_mapping = {
        '파워링크광고': ['WEB_SITE'],
        '플레이스광고': ['PLACE'],
        '파워컨텐츠광고': ['CONTENTS', 'POWER_CONTENT', 'POWER_CONTENTS', 'INFORMATION']
    }
    target_types = type_mapping.get(ad_type, ['WEB_SITE'])
    return [c for c in campaigns if c.get('campaignTp') in target_types]


@st.cache_data(ttl=600, show_spinner=False)
def _fetch_adgroups_cached(customer_id, api_key, secret_key, campaign_id):
    BASE_URL = "https://api.searchad.naver.com"
    uri = "/ncc/adgroups"
    params = {'nccCampaignId': campaign_id}
    headers = get_header("GET", uri, api_key, secret_key, customer_id)
    response = requests.get(f"{BASE_URL}{uri}", params=params, headers=headers)
    return response.status_code, response.text, response.json() if response.status_code == 200 else None

def fetch_adgroups(customer_id, api_key, secret_key, campaign_id):
    status_code, res_text, data = _fetch_adgroups_cached(customer_id, api_key, secret_key, campaign_id)
    
    if status_code != 200:
        st.session_state['api_error_msg'] = f"광고그룹 목록을 연동하는 데 실패했습니다. (HTTP {status_code}): {res_text}"
        return []
    return data


@st.cache_data(ttl=600, show_spinner=False)
def _fetch_daily_stats_cached(customer_id, api_key, secret_key, adgroup_id, start_date, end_date):
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
    return response.status_code, response.text, response.json() if response.status_code == 200 else None

def fetch_daily_stats(customer_id, api_key, secret_key, adgroup_id, start_date, end_date):
    status_code, res_text, stats_json = _fetch_daily_stats_cached(customer_id, api_key, secret_key, adgroup_id, start_date, end_date)
    
    if status_code != 200:
        st.session_state['api_error_msg'] = f"일자별 세부 실적 통계를 가져오는 과정에서 오류가 발생했습니다. (HTTP {status_code}): {res_text}"
        return None
        
    data_rows = []
    if stats_json and 'data' in stats_json:
        # 안전성 강화: API 응답 배열 크기와 조회 날짜 간의 매핑 정합성 검증 추가
        data_len = len(stats_json['data'])
        expected_days = (end_date - start_date).days + 1
        
        for i, stat in enumerate(stats_json['data']):
            if i < expected_days:
                dt = (start_date + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            else:
                dt = "계산불가"
                
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


@st.cache_data(ttl=600, show_spinner=False)
def _fetch_keyword_stats_place_cached(customer_id, api_key, secret_key, adgroup_id):
    BASE_URL = "https://api.searchad.naver.com"
    uri = "/stats"
    params = {
        'id': adgroup_id,
        'statType': 'NPLA_SCH_KEYWORD'
    }
    headers = get_header("GET", uri, api_key, secret_key, customer_id)
    response = requests.get(f"{BASE_URL}{uri}", params=params, headers=headers)
    return response.status_code, response.text, response.json() if response.status_code == 200 else None


@st.cache_data(ttl=600, show_spinner=False)
def _fetch_keyword_list_cached(customer_id, api_key, secret_key, adgroup_id):
    BASE_URL = "https://api.searchad.naver.com"
    kw_list_uri = "/ncc/keywords"
    kw_params = {'nccAdgroupId': adgroup_id}
    kw_headers = get_header("GET", kw_list_uri, api_key, secret_key, customer_id)
    response = requests.get(f"{BASE_URL}{kw_list_uri}", params=kw_params, headers=kw_headers)
    return response.status_code, response.text, response.json() if response.status_code == 200 else None


@st.cache_data(ttl=600, show_spinner=False)
def _fetch_keyword_stats_chunk_cached(customer_id, api_key, secret_key, chunk_ids_tuple, formatted_start, formatted_end):
    BASE_URL = "https://api.searchad.naver.com"
    stats_uri = "/stats"
    params = {
        'ids': list(chunk_ids_tuple),
        'fields': '["impCnt","clkCnt"]',
        'timeRange': f'{{"since":"{formatted_start}","until":"{formatted_end}"}}'
    }
    headers = get_header("GET", stats_uri, api_key, secret_key, customer_id)
    response = requests.get(f"{BASE_URL}{stats_uri}", params=params, headers=headers)
    return response.status_code, response.json() if response.status_code == 200 else None


def fetch_keyword_stats(customer_id, api_key, secret_key, adgroup_id, start_date, end_date, ad_type):
    if ad_type == '플레이스광고':
        status_code, res_text, stats_json = _fetch_keyword_stats_place_cached(customer_id, api_key, secret_key, adgroup_id)
        
        if status_code != 200:
            st.session_state['api_error_msg'] = f"플레이스 키워드 성과를 가져오는 과정에서 오류가 발생했습니다. (HTTP {status_code}): {res_text}"
            return None
            
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
        status_code, res_text, keywords = _fetch_keyword_list_cached(customer_id, api_key, secret_key, adgroup_id)
        
        if status_code != 200:
            st.session_state['api_error_msg'] = f"광고 키워드 목록을 수집하는 데 실패했습니다. (HTTP {status_code}): {res_text}"
            return None
            
        if not keywords:
            return None
            
        kw_ids = [k.get('nccKeywordId') for k in keywords]
        kw_map = {k.get('nccKeywordId'): k.get('keyword') for k in keywords}
        
        formatted_start = start_date.strftime("%Y-%m-%d")
        formatted_end = end_date.strftime("%Y-%m-%d")
        
        data_rows = []
        chunk_size = 50
        for i in range(0, len(kw_ids), chunk_size):
            chunk_ids = tuple(kw_ids[i:i+chunk_size])
            c_status_code, stats_json = _fetch_keyword_stats_chunk_cached(customer_id, api_key, secret_key, chunk_ids, formatted_start, formatted_end)
            
            if c_status_code == 200:
                if stats_json and 'data' in stats_json:
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
st.sidebar.markdown("### 📁 광고 계정 선택")

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
    if prof == "광고 ID 선택" or not prof:
        st.session_state['input_customer_id'] = ""
        st.session_state['input_api_key'] = ""
        st.session_state['input_secret_key'] = ""
    elif prof in st.secrets:
        keys = st.secrets[prof]
        st.session_state['input_customer_id'] = keys["customer_id"]
        st.session_state['input_api_key'] = keys["api_key"]
        st.session_state['input_secret_key'] = keys["secret_key"]
    
    st.session_state['selected_ad_type'] = '플레이스광고'

if 'selected_profile' not in st.session_state:
    st.session_state['selected_profile'] = "광고 ID 선택"
    update_inputs_from_profile()

selected_profile = st.sidebar.selectbox(
    "조회할 광고 계정을 선택해 주세요.", 
    options=options_list,
    key='selected_profile',
    on_change=update_inputs_from_profile
)

input_customer_id = st.session_state.get('input_customer_id', '')
input_api_key = st.session_state.get('input_api_key', '')
input_secret_key = st.session_state.get('input_secret_key', '')


# ==========================================
# [메인 제어] 
# ==========================================
st.subheader("광고 데이터 추출기")

# 계정 선택 가이드 노출
if selected_profile == "광고 ID 선택" or not selected_profile:
    st.info("👈 왼쪽 사이드바에서 조회 및 제어할 광고 ID(계정)를 먼저 선택해 주세요.")
    st.stop()

# 가상 모드 작동 여부 결정
is_test_mode = ("mock" in str(input_customer_id).lower()) or (input_customer_id == "")

# 조회 범위 입력 상자
col_date1, col_date2 = st.columns(2)
with col_date1:
    start_date = st.date_input("조회 시작일", value=last_monday)
with col_date2:
    end_date = st.date_input("조회 종료일", value=last_sunday)

# [보완 가이드 적용] 날짜 무결성 실시간 선후 검증 로직 추가
if start_date > end_date:
    st.error("⚠️ 조회 시작일은 종료일보다 이전 날짜여야 합니다.")
    st.stop()

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
        st.session_state['api_error_msg'] = ""  
    else:
        st.warning("선택하신 유형에 부합하는 캠페인이 확인되지 않습니다.")
    st.stop()

# '캠페인' 라벨 명시 및 복원
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

# '상세 광고그룹' 라벨 명시 및 복원
adg_options = {g['nccAdgroupId']: g['name'] for g in adgroup_list}
selected_adg_id = st.selectbox("상세 광고그룹", options=list(adg_options.keys()), format_func=lambda x: adg_options[x])


st.markdown("---")

# 데이터 추출 버튼을 가로로 확장하고 중앙에 정렬하기 위해 분할 컴포넌트를 사용합니다.
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
        st.session_state['api_error_msg'] = ""  
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
        
        # 날짜 제외 복사 기능을 위한 지표별 개별 슬라이싱 데이터 프레임셋 분리
        date_df = raw_df[["날짜"]].copy()
        imp_clk_df = raw_df[["노출수", "클릭수"]].copy()
        cpc_df = raw_df[["평균 CPC"]].copy()
        cost_df = raw_df[["총비용"]].copy()
        
        # 주간 총 합계표 부분은 우측 복사하기 버튼이 나타나지 않도록 처리합니다 (show_copy_btn=False)
        render_table_with_copy_btn(summary_df, "🏆 주간 총 합계표", is_summary_table=True, show_copy_btn=False)
        
        st.markdown("###") # 레이아웃 여백 보정
        
        # 가로 격자 상단에 단 하나의 대제목만 정적 마킹합니다.
        st.markdown("#### 📊 일별 데이터")
        
        # 1:1.2:1.2:1.2 비율 구성 (엑셀 템플릿 복사용 고유 열분할 뷰 유지)
        col_date, col1, col2, col3 = st.columns([1, 1.2, 1.2, 1.2])
        
        # (1) 날짜 표 - 버튼이 필요 없으므로 iframe 없이 바로 렌더링합니다.
        with col_date:
            render_plain_table(date_df, is_summary_table=False)
            
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
