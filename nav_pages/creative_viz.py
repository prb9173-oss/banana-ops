import streamlit as st
import datetime
import time
import hmac
import hashlib
import base64
import requests
import pandas as pd
import altair as alt

REQUEST_TIMEOUT = 10
BASE_URL = "https://api.searchad.naver.com"

def month_week_label(monday):
    """월요일 시작 한 주를 "N월 N주차"로 표기한다 — 실무 리포트 관례를 따라, 한 주가
    이틀-오일처럼 두 달에 걸치면 더 많은 날이 속한 달로 그 주를 귀속시키고("과반수"
    규칙), 그 달로 귀속된 주들을 연대순으로 센 게 "N주차"다. 한 주는 최대 두 달까지만
    걸치므로(7일이라 세 달에 걸칠 수 없음) 이 규칙이면 모호함 없이 하나로 정해진다."""
    def majority_month_year(start):
        counts = {}
        for i in range(7):
            d = start + datetime.timedelta(days=i)
            counts[(d.year, d.month)] = counts.get((d.year, d.month), 0) + 1
        return max(counts, key=counts.get)

    target = majority_month_year(monday)
    week_num = 1
    cursor = monday - datetime.timedelta(weeks=1)
    while majority_month_year(cursor) == target:
        week_num += 1
        cursor -= datetime.timedelta(weeks=1)
    return f"{target[1]}월 {week_num}주차"


AD_TYPE_CAMPAIGN_TP = {
    "플레이스광고": ["PLACE"],
    "파워링크광고": ["WEB_SITE"],
    "파워컨텐츠광고": ["CONTENTS", "POWER_CONTENT", "POWER_CONTENTS", "INFORMATION"],
}


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
        'X-Signature': signature,
    }


def _get(uri, api_key, secret_key, customer_id, params=None):
    headers = get_header("GET", uri, api_key, secret_key, customer_id)
    try:
        r = requests.get(f"{BASE_URL}{uri}", headers=headers, params=params, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.RequestException as e:
        return None, str(e)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}: {r.text}"
    return r.json(), None


@st.cache_data(ttl=600, show_spinner=False)
def fetch_first_adgroup(customer_id, api_key, secret_key, ad_type):
    """이 광고 유형(campaignTp)의 캠페인·광고그룹을 대표로 하나 가져온다.
    매장마다 특정 유형 자체가 없을 수 있어(예: 파워컨텐츠 없는 매장), 그 경우 에러가
    아니라 (None, [], None)으로 "그냥 없음"을 구분해서 돌려준다.

    그냥 목록의 첫 번째를 고르면 안 된다 — 일부 매장(예: 보름숲)은 지난 시즌
    프로모션용으로 만들었다가 중지(PAUSED)한 캠페인이 여러 개 남아있고, API가 최신순
    정렬을 보장하지 않아 그 옛날 캠페인이 0번으로 올 수 있다. 실제로 이 문제로 보름숲의
    플레이스 광고가 전부 0으로 나온 적이 있어서, 지금 운영 중(ELIGIBLE)인 캠페인·
    광고그룹을 우선하고 없을 때만 첫 번째로 폴백한다.

    같은 캠페인 안에 대표 광고그룹 말고 다른 운영 중(ELIGIBLE) 광고그룹이 더 있으면
    (예: 보름숲의 "보름숲 통대관", "대관 파워컨텐츠" — 매장 본업과 다른 대관 상품용
    광고그룹) 대표로 삼지 않고 extra_adgroups로 따로 돌려준다 — 호출부에서 플레이스/
    파워링크/파워컨텐츠 3개 구간과 안 섞이게 맨 아래에 별도 이름으로 보여주기 위함."""
    campaigns, err = _get("/ncc/campaigns", api_key, secret_key, customer_id)
    if err:
        return None, [], err
    target_types = AD_TYPE_CAMPAIGN_TP[ad_type]
    matched = [c for c in campaigns if c.get("campaignTp") in target_types]
    if not matched:
        return None, [], None
    active_campaigns = [c for c in matched if c.get("status") == "ELIGIBLE"]
    chosen_campaign = (active_campaigns or matched)[0]
    adgroups, err = _get("/ncc/adgroups", api_key, secret_key, customer_id, {"nccCampaignId": chosen_campaign["nccCampaignId"]})
    if err:
        return None, [], err
    if not adgroups:
        return None, [], None
    active_adgroups = [a for a in adgroups if a.get("status") == "ELIGIBLE"]
    pool = active_adgroups or adgroups
    return pool[0], pool[1:], None


@st.cache_data(ttl=600, show_spinner=False)
def fetch_daily_stats(customer_id, api_key, secret_key, adgroup_id, start_date, end_date):
    """일자별 노출수/클릭수/총비용 — data_extractor.py의 동일 엔드포인트/파라미터를 재사용."""
    params = {
        'id': adgroup_id,
        'fields': '["impCnt","clkCnt","salesAmt"]',
        'timeRange': f'{{"since":"{start_date.strftime("%Y-%m-%d")}","until":"{end_date.strftime("%Y-%m-%d")}"}}',
        'timeIncrement': '1',
    }
    data, err = _get("/stats", api_key, secret_key, customer_id, params)
    if err:
        return None, err

    rows = []
    if data and 'data' in data:
        expected_days = (end_date - start_date).days + 1
        for i, stat in enumerate(data['data']):
            if i >= expected_days:
                break
            rows.append({
                "날짜": start_date + datetime.timedelta(days=i),
                "노출수": int(stat.get('impCnt', 0)),
                "클릭수": int(stat.get('clkCnt', 0)),
                "총비용": int(stat.get('salesAmt', 0)),
            })
    return pd.DataFrame(rows), None


TABLE_BORDER = "#E3E6EB"
TABLE_HEADER_BG = "#EEF3FA"
WON_COLUMNS = {"총비용", "평균 CPC"}


def render_html_table(df):
    """st.dataframe의 흐릿한 기본 스타일 대신, data_extractor.py에서 이미 쓰던 진한
    텍스트+옅은 파란 헤더 조합의 HTML 표를 재사용해서 직관성을 맞춘다. 총비용/평균
    CPC는 숫자 뒤에 '원'을 붙인다."""
    html = (
        '<table style="width:100%; border-collapse:collapse; text-align:center; '
        f'color:#16181D; border:1px solid {TABLE_BORDER}; white-space:nowrap;">'
    )
    html += f'<thead><tr style="background-color:{TABLE_HEADER_BG}; border-bottom:2px solid {TABLE_BORDER}; font-weight:600;">'
    for col in df.columns:
        html += f'<th style="padding:8px; border:1px solid {TABLE_BORDER}; font-size:13px;">{col}</th>'
    html += '</tr></thead><tbody>'
    for _, row in df.iterrows():
        html += f'<tr style="background-color:#FFFFFF; border-bottom:1px solid {TABLE_BORDER};">'
        for col in df.columns:
            val = row[col]
            if col in WON_COLUMNS:
                formatted = f"{int(val):,}원"
            elif "클릭률" in col:
                formatted = f"{val:.2f}%"
            elif isinstance(val, (int, float)):
                formatted = f"{int(val):,}"
            else:
                formatted = str(val)
            html += f'<td style="padding:6px; border:1px solid {TABLE_BORDER}; font-size:12.5px;">{formatted}</td>'
        html += '</tr>'
    html += '</tbody></table>'
    st.markdown(html, unsafe_allow_html=True)


def with_ctr_cpc(df):
    """노출수/클릭수/총비용으로부터 클릭률·평균CPC를 계산해 붙인다 — 일별 값을 그대로
    평균 내지 않고, 합산된 노출/클릭/비용에서 다시 계산해야 주간 합계표에서 정확하다."""
    df = df.copy()
    df["클릭률(%)"] = df.apply(lambda r: round(r["클릭수"] / r["노출수"] * 100, 2) if r["노출수"] else 0.0, axis=1)
    df["평균 CPC"] = df.apply(lambda r: int(r["총비용"] / r["클릭수"]) if r["클릭수"] else 0, axis=1)
    return df


def render_dual_axis_chart(df, x_col):
    """노출수(막대)와 클릭수(선)를 같은 축에 그리면 노출수 규모에 클릭수가 파묻혀
    안 보이므로, 두 지표를 서로 다른(독립) y축에 그린다. .interactive()를 호출하지
    않으면 Altair/Vega-Lite 기본값은 마우스 휠 확대나 드래그 이동이 비활성 상태라,
    st.bar_chart(휠/드래그로 확대·이동 가능)와 달리 정적인 차트가 된다.
    "노출수"/"클릭수" 축 제목을 크게 세로로 박아두는 대신, 차트 아래 작은 범례로만
    표시한다. Vega-Lite 자체 범례(legend=)를 좁은 차트 폭 안에 한글로 넣으면 항목
    두 개가 겹쳐서 깨지는 걸 확인해서, 대신 직접 만든 작은 HTML 범례를 쓴다."""
    base = alt.Chart(df).encode(
        x=alt.X(
            f"{x_col}:N",
            sort=None,
            title=None,
            axis=alt.Axis(labelAngle=0, labelFontSize=10),
        )
    )
    bars = base.mark_bar(size=10, color="#3182F6").encode(
        y=alt.Y("노출수:Q", axis=alt.Axis(title=None)),
        tooltip=[x_col, "노출수"],
    )
    line = base.mark_line(color="#F97316", point=True, strokeWidth=2).encode(
        y=alt.Y("클릭수:Q", axis=alt.Axis(title=None)),
        tooltip=[x_col, "클릭수"],
    )
    chart = alt.layer(bars, line).resolve_scale(y="independent").properties(height=260)
    st.altair_chart(chart, use_container_width=True)
    st.markdown(
        '''
        <div style="display:flex; gap:12px; font-size:11px; color:#5B6472; margin-top:-8px;">
            <span><span style="display:inline-block; width:8px; height:8px; background:#3182F6; border-radius:2px; margin-right:3px;"></span>노출수</span>
            <span><span style="display:inline-block; width:8px; height:8px; background:#F97316; border-radius:2px; margin-right:3px;"></span>클릭수</span>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def build_weekly_table(daily_df):
    """일별 표를 월요일 시작 주 단위로 묶어 주간 합계표를 만든다."""
    if daily_df.empty:
        return daily_df
    df = daily_df.copy()
    df["주 시작"] = df["날짜"].apply(lambda d: d - datetime.timedelta(days=d.weekday()))
    weekly = df.groupby("주 시작", as_index=False)[["노출수", "클릭수", "총비용"]].sum()
    weekly = weekly.sort_values("주 시작")
    # %-m/%-d(유닉스 전용 "0 없는 날짜" 포맷)는 Windows에서 안 먹혀서 로컬 개발 환경이
    # 깨진다 — month/day 정수를 직접 꺼내 조합한다.
    def _fmt(d):
        return f"{d.month}.{d.day}"
    weekly["주차"] = weekly["주 시작"].apply(month_week_label)
    weekly["기간"] = weekly["주 시작"].apply(
        lambda start: f"{month_week_label(start)} ({_fmt(start)}~{_fmt(start + datetime.timedelta(days=6))})"
    )
    return with_ctr_cpc(weekly)[["기간", "주차", "노출수", "클릭수", "클릭률(%)", "평균 CPC", "총비용"]]


@st.cache_data(ttl=600, show_spinner=False)
def fetch_top_keywords(customer_id, api_key, secret_key, adgroup_id, ad_type, start_date, end_date):
    """상위 클릭 10개 키워드. 플레이스광고는 조회 기간을 지원하지 않는 별도
    statType(NPLA_SCH_KEYWORD)를 쓰고, 나머지는 키워드 목록 + /stats 조합으로 뽑는다
    (둘 다 data_extractor.py와 동일한 방식)."""
    if ad_type == "플레이스광고":
        params = {'id': adgroup_id, 'statType': 'NPLA_SCH_KEYWORD'}
        data, err = _get("/stats", api_key, secret_key, customer_id, params)
        if err:
            return None, err
        rows = []
        items = data if isinstance(data, list) else (data or {}).get('data', [])
        for item in items:
            kw = item.get('schKeyword') or item.get('keyword') or item.get('searchKeyword')
            if kw:
                rows.append({
                    "키워드": kw,
                    "노출수": int(item.get('impCnt', 0)),
                    "클릭수": int(item.get('clkCnt', 0)),
                })
        if not rows:
            return None, None
        df = pd.DataFrame(rows).sort_values("클릭수", ascending=False).head(10).reset_index(drop=True)
        return with_ctr_cpc(df.assign(총비용=0))[["키워드", "노출수", "클릭수", "클릭률(%)"]], None

    keywords, err = _get("/ncc/keywords", api_key, secret_key, customer_id, {"nccAdgroupId": adgroup_id})
    if err:
        return None, err
    if not keywords:
        return None, None
    kw_ids = [k.get('nccKeywordId') for k in keywords]
    kw_map = {k.get('nccKeywordId'): k.get('keyword') for k in keywords}

    rows = []
    chunk_size = 50
    for i in range(0, len(kw_ids), chunk_size):
        chunk_ids = kw_ids[i:i + chunk_size]
        params = {
            'ids': chunk_ids,
            'fields': '["impCnt","clkCnt"]',
            'timeRange': f'{{"since":"{start_date.strftime("%Y-%m-%d")}","until":"{end_date.strftime("%Y-%m-%d")}"}}',
        }
        data, err = _get("/stats", api_key, secret_key, customer_id, params)
        if err:
            continue
        for stat in (data or {}).get('data', []):
            kw_id = stat.get('id')
            rows.append({
                "키워드": kw_map.get(kw_id, "알 수 없는 키워드"),
                "노출수": int(stat.get('impCnt', 0)),
                "클릭수": int(stat.get('clkCnt', 0)),
            })
    if not rows:
        return None, None
    df = pd.DataFrame(rows).sort_values("클릭수", ascending=False).head(10).reset_index(drop=True)
    return with_ctr_cpc(df.assign(총비용=0))[["키워드", "노출수", "클릭수", "클릭률(%)"]], None


def render_bid_info(ad_type, adgroup):
    """원본 엑셀 리포트의 좌측 입찰가 박스 + 우측 특이사항 박스를 재현한다.
    현재입찰가·하루예산은 /ncc/adgroups 응답의 실제 값(bidAmt/dailyBudget)이고,
    플레이스광고의 "평균 입찰가"(동종업계 시세)는 API로 못 가져오는 값이라 매주 직접
    확인해서 입력하는 수동 입력칸으로 둔다 — 아직 DB 저장은 없어 새로고침하면
    초기화된다(저장 방식은 나중에 별도로 정한다).
    위젯 key는 store_name+ad_type이 아니라 adgroup_id로 고유하게 잡는다 — 보름숲의
    "보름숲 통대관"처럼 같은 store_name·ad_type인 추가 광고그룹이 하나 더 있으면
    store_name+ad_type만으로는 대표 광고그룹의 입력칸과 key가 겹쳐 버린다."""
    adgroup_id = adgroup["nccAdgroupId"]
    bid_amt = adgroup.get("bidAmt", 0)
    col_bid, col_note = st.columns([1, 2])
    with col_bid:
        if ad_type == "플레이스광고":
            avg_bid = st.number_input(
                "평균 입찰가(경쟁업계 시세, 직접 입력)", min_value=0, step=10,
                key=f"cv_avgbid_{adgroup_id}", label_visibility="collapsed",
            )
            diff = bid_amt - avg_bid
            rows = [("현재 입찰가", f"{bid_amt:,}원"), ("평균 입찰가", f"{avg_bid:,}원"), ("차액", f"{diff:,}원")]
        else:
            daily_budget = adgroup.get("dailyBudget", 0)
            rows = [("현재 입찰가", f"{bid_amt:,}원"), ("하루 예산", f"{daily_budget:,}원")]
        html = f'<table style="width:100%; border-collapse:collapse; border:1px solid {TABLE_BORDER};">'
        for name, val in rows:
            html += (
                f'<tr><td style="padding:6px 10px; border:1px solid {TABLE_BORDER}; background:{TABLE_HEADER_BG}; '
                f'font-weight:600; font-size:12.5px; white-space:nowrap;">{name}</td>'
                f'<td style="padding:6px 10px; border:1px solid {TABLE_BORDER}; font-size:12.5px;">{val}</td></tr>'
            )
        html += '</table>'
        st.markdown(html, unsafe_allow_html=True)
    with col_note:
        st.text_input(
            "특이사항", key=f"cv_note_{adgroup_id}", placeholder="* 특이사항 - 이번 주 특이사항을 입력하세요",
            label_visibility="collapsed",
        )


def render_report_body(customer_id, api_key, secret_key, ad_type, adgroup, last_week_start, last_week_end):
    """입찰가 박스 + 일별/주간/Top10 표·차트 3분할 — 대표 광고그룹이든, 보름숲의
    "보름숲 통대관"처럼 별도로 보여주는 추가 광고그룹이든 똑같이 이 본문을 쓴다."""
    render_bid_info(ad_type, adgroup)

    adgroup_id = adgroup["nccAdgroupId"]
    four_weeks_start = last_week_start - datetime.timedelta(weeks=3)  # 선택한 주 포함 4주 전 월요일

    daily_recent, err = fetch_daily_stats(customer_id, api_key, secret_key, adgroup_id, last_week_start, last_week_end)
    if err:
        st.error(f"❌ 일별 유입 현황을 가져오는 중 오류가 발생했습니다: {err}")
        return
    daily_month, err = fetch_daily_stats(customer_id, api_key, secret_key, adgroup_id, four_weeks_start, last_week_end)
    if err:
        st.error(f"❌ 주간 유입 현황을 가져오는 중 오류가 발생했습니다: {err}")
        return
    top_keywords, err = fetch_top_keywords(customer_id, api_key, secret_key, adgroup_id, ad_type, four_weeks_start, last_week_end)
    if err:
        st.error(f"❌ 상위 클릭 키워드를 가져오는 중 오류가 발생했습니다: {err}")
        return

    col_daily, col_weekly, col_keywords = st.columns(3)

    with col_daily:
        st.markdown("**일별 유입 현황**")
        if daily_recent is not None and not daily_recent.empty:
            display_df = with_ctr_cpc(daily_recent).copy()
            display_df["날짜"] = display_df["날짜"].apply(lambda d: d.strftime("%m/%d"))
            # 원본 리포트와 같은 순서(노출수·클릭수·클릭률·CPC·총비용)로 맞춘다 —
            # 총비용이 클릭률/CPC보다 앞에 있던 걸 뒤로 옮김.
            display_df = display_df[["날짜", "노출수", "클릭수", "클릭률(%)", "평균 CPC", "총비용"]]
            render_html_table(display_df)
            render_dual_axis_chart(display_df, "날짜")
        else:
            st.info("데이터가 없습니다.")

    with col_weekly:
        st.markdown("**주간 유입 현황**")
        weekly_df = build_weekly_table(daily_month) if daily_month is not None else None
        if weekly_df is not None and not weekly_df.empty:
            render_html_table(weekly_df.drop(columns=["주차"]))
            render_dual_axis_chart(weekly_df, "주차")
        else:
            st.info("데이터가 없습니다.")

    with col_keywords:
        st.markdown("**상위 클릭 10개 키워드**")
        if top_keywords is not None and not top_keywords.empty:
            render_html_table(top_keywords)
        else:
            st.info("데이터가 없습니다.")


def render_ad_type_report(customer_id, api_key, secret_key, ad_type, label, last_week_start, last_week_end):
    """플레이스/파워링크/파워컨텐츠 3개 구간 중 하나를 그린다. 대표 광고그룹 외에
    같은 계정에 더 있는 추가(대관 등) 광고그룹은 여기서 안 그리고 그대로 돌려줘서,
    호출부가 페이지 맨 아래에 별도 이름으로 몰아서 보여줄 수 있게 한다."""
    st.markdown(f"### {label}")
    adgroup, extra_adgroups, err = fetch_first_adgroup(customer_id, api_key, secret_key, ad_type)
    if err:
        st.error(f"❌ {label} 데이터를 가져오는 중 오류가 발생했습니다: {err}")
        return []
    if not adgroup:
        st.info(f"이 계정에는 {label}가 없습니다.")
        return []

    render_report_body(customer_id, api_key, secret_key, ad_type, adgroup, last_week_start, last_week_end)
    return [(ad_type, ag) for ag in extra_adgroups]


st.subheader("광고 소재 및 데이터 시각화")

available_accounts = []
try:
    for k in st.secrets.keys():
        section = st.secrets[k]
        if hasattr(section, "get") and "customer_id" in section and "api_key" in section and "secret_key" in section:
            available_accounts.append(k)
except Exception:
    pass

if not available_accounts:
    st.warning("등록된 광고 계정이 없습니다. `.streamlit/secrets.toml`에 계정을 먼저 등록해 주세요.")
else:
    if "cv_account_select" not in st.session_state:
        st.session_state["cv_account_select"] = available_accounts[0]

    def _shift_account(delta):
        idx = available_accounts.index(st.session_state["cv_account_select"])
        st.session_state["cv_account_select"] = available_accounts[(idx + delta) % len(available_accounts)]

    # 회의 중에 매장을 하나씩 넘겨가며 보는 용도라, 드롭다운은 그대로 두고 좌우
    # 버튼으로도 클릭 한 번에 다음/이전 매장으로 바로 넘어가게 한다 — place_rank.py의
    # 날짜 ◀▶ 내비게이션과 같은 패턴(같은 위젯 키를 콜백에서 직접 옮겨준다).
    today = datetime.date.today()
    this_monday = today - datetime.timedelta(days=today.weekday())
    last_completed_monday = this_monday - datetime.timedelta(days=7)
    if "cv_week_monday" not in st.session_state:
        st.session_state["cv_week_monday"] = last_completed_monday

    def _shift_week(delta_weeks):
        st.session_state["cv_week_monday"] += datetime.timedelta(weeks=delta_weeks)

    # 직접 몇 주 전인지 클릭해서 바로 고를 수 있도록 최근 16주(약 4개월) 목록을
    # 드롭다운으로 제공한다 — 그 이전 주는 좌우 버튼으로 하나씩 넘겨서 접근.
    # 오래된 주가 위, 최신 주가 아래(오름차순)로 정렬 — 기본 선택값이 최신 주라
    # 목록 맨 아래에 위치하고, 마우스 휠을 위로 올릴수록 과거 데이터가 나오게 된다.
    week_options = [last_completed_monday - datetime.timedelta(weeks=i) for i in range(15, -1, -1)]
    if st.session_state["cv_week_monday"] not in week_options:
        week_options.append(st.session_state["cv_week_monday"])
        week_options.sort()

    with st.container(key="cv_nav_row"):
        col_acc_prev, col_acc_select, col_acc_next, col_week_prev, col_week_select, col_week_next = st.columns(
            [0.5, 2.5, 0.5, 0.5, 1.8, 0.5]
        )
        with col_acc_prev:
            st.button("◀", key="cv_account_prev", on_click=_shift_account, args=(-1,), width="stretch")
        with col_acc_select:
            st.selectbox(
                "광고 계정", options=available_accounts, key="cv_account_select", label_visibility="collapsed",
            )
        with col_acc_next:
            st.button("▶", key="cv_account_next", on_click=_shift_account, args=(1,), width="stretch")
        with col_week_prev:
            st.button("◀", key="cv_week_prev", on_click=_shift_week, args=(-1,), width="stretch")
        with col_week_select:
            st.selectbox(
                "조회 주차", options=week_options, key="cv_week_monday",
                format_func=month_week_label, label_visibility="collapsed",
            )
        with col_week_next:
            st.button(
                "▶", key="cv_week_next", on_click=_shift_week, args=(1,), width="stretch",
                disabled=(st.session_state["cv_week_monday"] >= last_completed_monday),
            )

    week_monday = st.session_state["cv_week_monday"]
    week_sunday = week_monday + datetime.timedelta(days=6)

    selected_account = st.session_state["cv_account_select"]
    section = st.secrets[selected_account]
    cid, ak, sk = section["customer_id"], section["api_key"], section["secret_key"]

    extra_adgroups = []

    with st.container(border=True, key="section_report_place"):
        extra_adgroups += render_ad_type_report(
            cid, ak, sk, "플레이스광고", "플레이스 광고", week_monday, week_sunday
        ) or []

    with st.container(border=True, key="section_report_weblink"):
        extra_adgroups += render_ad_type_report(
            cid, ak, sk, "파워링크광고", "파워링크 광고", week_monday, week_sunday
        ) or []

    with st.container(border=True, key="section_report_contents"):
        extra_adgroups += render_ad_type_report(
            cid, ak, sk, "파워컨텐츠광고", "파워컨텐츠 광고", week_monday, week_sunday
        ) or []

    # 매장 본업 3구간(플레이스/파워링크/파워컨텐츠)과 섞이면 헷갈리니, 보름숲의
    # "보름숲 통대관"·"대관 파워컨텐츠"처럼 계정에 딸린 추가(대관 등) 광고그룹은
    # 맨 아래에 실제 광고그룹 이름 그대로 따로 몰아서 보여준다.
    for ad_type, ag in extra_adgroups:
        with st.container(border=True, key=f"section_report_extra_{ag['nccAdgroupId']}"):
            st.markdown(f"### 🏛 {ag.get('name') or '추가 광고그룹'}")
            render_report_body(cid, ak, sk, ad_type, ag, week_monday, week_sunday)
