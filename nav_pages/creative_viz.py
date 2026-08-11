import streamlit as st
import streamlit.components.v1 as components
import datetime
from urllib.parse import quote
import pandas as pd
import altair as alt
from supabase import create_client


@st.cache_resource
def get_supabase_client():
    sb = st.secrets["supabase"]
    return create_client(sb["url"], sb["key"])


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


@st.cache_data(ttl=600, show_spinner=False)
def fetch_first_adgroup(store_name, ad_type):
    """creative_adgroup_snapshot 캐시 테이블에서 이 매장·광고유형의 대표/부가
    광고그룹을 가져온다 — 2026-07-31부터 라이브 API 호출 없이 매주 월요일 자동
    수집 스크립트(scripts/check_ad_performance.py)가 채워둔 값만 읽는다(회의 중
    페이지를 빠르게 넘겨볼 때 API 왕복 지연이 없도록).

    DB 컬럼명은 여전히 "account_key"이지만(스키마 변경 없이 값의 의미만 바꿈),
    이제 네이버 광고 계정이 아니라 매장명을 저장한다 — 계정 하나(예: "고집돌우럭
    중문점")에 실제로는 중문점·함덕점·와인창고 함덕점 3개 매장의 캠페인이 같이
    걸려 있는 경우가 있어서, 계정 단위로는 나머지 매장이 통째로 안 보이는 버그가
    있었다(2026-07-31 발견). 수집 스크립트가 캠페인 이름("{매장명} {유형}")으로
    매장을 정확히 구분해 저장하므로, 여기서도 매장명으로 조회한다.

    "가장 최신 week_monday" 행을 대표/부가 판단 기준으로 삼는다 — 현재 입찰가는
    조회 중인 주차와 무관하게 항상 최신값을 보여준다. extra_adgroups는
    role='extra'인 행 전부(예: "보름숲 파워링크" 캠페인 안의 "보름숲 통대관")."""
    client = get_supabase_client()
    res = (
        client.table("creative_adgroup_snapshot")
        .select("*")
        .eq("account_key", store_name)
        .eq("ad_type", ad_type)
        .order("week_monday", desc=True)
        .execute()
    )
    rows = res.data or []
    if not rows:
        return None, [], None
    latest_week = rows[0]["week_monday"]
    latest_rows = [r for r in rows if r["week_monday"] == latest_week]
    mains = [r for r in latest_rows if r["role"] == "main"]
    extras = [r for r in latest_rows if r["role"] == "extra"]
    if not mains:
        return None, [], None

    def _to_adgroup(r):
        return {
            "nccAdgroupId": r["adgroup_id"],
            "name": r.get("adgroup_name"),
            "bidAmt": r.get("bid_amt", 0),
            "dailyBudget": r.get("daily_budget", 0),
        }
    return _to_adgroup(mains[0]), [_to_adgroup(e) for e in extras], None


@st.cache_data(ttl=600, show_spinner=False)
def fetch_daily_stats(adgroup_id, start_date, end_date):
    """일자별 노출수/클릭수/총비용 — creative_daily_stats 캐시 테이블 조회
    (2026-07-31부터 라이브 API 호출 없음)."""
    client = get_supabase_client()
    res = (
        client.table("creative_daily_stats")
        .select("*")
        .eq("adgroup_id", adgroup_id)
        .gte("stat_date", start_date.isoformat())
        .lte("stat_date", end_date.isoformat())
        .order("stat_date")
        .execute()
    )
    rows = [
        {
            "날짜": datetime.date.fromisoformat(r["stat_date"]),
            "노출수": r.get("impressions", 0),
            "클릭수": r.get("clicks", 0),
            "총비용": r.get("cost", 0),
        }
        for r in (res.data or [])
    ]
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
    html += f'<thead><tr style="background-color:{TABLE_HEADER_BG}; border-bottom:2px solid {TABLE_BORDER}; font-weight:700;">'
    for col in df.columns:
        html += f'<th style="padding:10px 6px; border:1px solid {TABLE_BORDER}; font-size:16px;">{col}</th>'
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
            html += f'<td style="padding:8px 6px; border:1px solid {TABLE_BORDER}; font-size:16px; font-weight:500;">{formatted}</td>'
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
            axis=alt.Axis(labelAngle=0, labelFontSize=13),
        )
    )
    bars = base.mark_bar(size=14, color="#3182F6").encode(
        y=alt.Y("노출수:Q", axis=alt.Axis(title=None, labelFontSize=12)),
        tooltip=[x_col, "노출수"],
    )
    line = base.mark_line(color="#F97316", point=True, strokeWidth=2).encode(
        y=alt.Y("클릭수:Q", axis=alt.Axis(title=None, labelFontSize=12)),
        tooltip=[x_col, "클릭수"],
    )
    chart = alt.layer(bars, line).resolve_scale(y="independent").properties(height=280)
    st.altair_chart(chart, use_container_width=True)
    st.markdown(
        '''
        <div style="display:flex; gap:16px; font-size:14px; color:#5B6472; margin-top:-4px;">
            <span><span style="display:inline-block; width:10px; height:10px; background:#3182F6; border-radius:2px; margin-right:4px;"></span>노출수</span>
            <span><span style="display:inline-block; width:10px; height:10px; background:#F97316; border-radius:2px; margin-right:4px;"></span>클릭수</span>
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
def fetch_top_keywords(adgroup_id, week_monday):
    """그 주(선택한 주차)의 상위 클릭 10개 키워드 — creative_top_keywords 캐시
    조회(2026-07-31부터). 예전 라이브 API 버전은 실수로 "최근 4주 합산" 클릭수로
    뽑고 있었는데, 실제 리포트 양식은 그 주만의 순위라 이번 전환에서 바로잡았다.
    파워링크/파워컨텐츠는 매주 자동 수집, 플레이스광고는 API가 기간 조회를 지원
    안 해서 관리자가 화면에서 직접 입력한 값만 있다(입력 전이면 빈 결과)."""
    client = get_supabase_client()
    res = (
        client.table("creative_top_keywords")
        .select("*")
        .eq("adgroup_id", adgroup_id)
        .eq("week_monday", week_monday.isoformat())
        .order("display_order")
        .execute()
    )
    rows = [
        {"키워드": r["keyword"], "노출수": r.get("impressions", 0), "클릭수": r.get("clicks", 0)}
        for r in (res.data or [])
        if r.get("keyword")  # 플레이스는 관리자가 아직 입력 전이면 빈 문자열일 수 있음
    ]
    if not rows:
        return None, None
    df = pd.DataFrame(rows)
    return with_ctr_cpc(df.assign(총비용=0))[["키워드", "노출수", "클릭수", "클릭률(%)"]], None


def save_top_keywords(adgroup_id, week_monday, rows):
    """플레이스광고 상위 클릭 10개 키워드 — 관리자가 화면에서 입력한 값을 저장한다.
    scripts/check_ad_performance.py의 replace_top_keywords()와 동일한 방식(그 주차
    기존 행을 전부 지우고 다시 넣음)이라 몇 개를 입력하든 순서/개수가 항상 맞는다."""
    client = get_supabase_client()
    client.table("creative_top_keywords") \
        .delete().eq("adgroup_id", adgroup_id).eq("week_monday", week_monday.isoformat()).execute()
    if rows:
        payload = [
            {
                "adgroup_id": adgroup_id,
                "week_monday": week_monday.isoformat(),
                "display_order": i,
                "keyword": r["키워드"],
                # 숫자 칸도 셀을 지우면 None이 될 수 있어(빈 문자열이 아니라) 0으로
                # 대체 — int(None)은 그냥 에러가 난다.
                "impressions": int(r["노출수"] or 0),
                "clicks": int(r["클릭수"] or 0),
            }
            for i, r in enumerate(rows)
        ]
        client.table("creative_top_keywords").insert(payload).execute()
    fetch_top_keywords.clear()


@st.cache_data(ttl=30, show_spinner=False)
def fetch_admin_note(adgroup_id, week_monday):
    """관리자가 입력하는 평균입찰가/특이사항 — creative_admin_notes에서 그 주(week_monday)
    값을 읽는다. 예전엔 st.session_state에만 있어서 새로고침(관리자 모드 켜고 끄기는
    내부적으로 페이지 전체를 새로고침한다)하면 그대로 날아갔는데, 이제 DB에 저장해
    다른 지점을 봤다 돌아와도, 관리자 모드를 껐다 켜도 값이 유지된다."""
    client = get_supabase_client()
    res = (
        client.table("creative_admin_notes")
        .select("*")
        .eq("adgroup_id", adgroup_id)
        .eq("week_monday", week_monday.isoformat())
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if rows:
        return rows[0].get("avg_bid_amt", 0), rows[0].get("note", "")
    return 0, ""


def upsert_admin_note(adgroup_id, week_monday, avg_bid_amt, note):
    client = get_supabase_client()
    client.table("creative_admin_notes").upsert({
        "adgroup_id": adgroup_id,
        "week_monday": week_monday.isoformat(),
        "avg_bid_amt": int(avg_bid_amt),
        "note": note,
    }, on_conflict="adgroup_id,week_monday").execute()
    fetch_admin_note.clear()  # 다음 조회부터 바로 새 값 반영되도록 캐시 비움


def render_bid_info(ad_type, adgroup, week_monday):
    """원본 엑셀 리포트의 좌측 입찰가 박스 + 우측 특이사항 박스를 재현한다.
    현재입찰가·하루예산은 매주 자동 수집된 실제 값(creative_adgroup_snapshot)이고,
    플레이스광고의 "평균 입찰가"(동종업계 시세)는 API로 못 가져오는 값이라 매주 직접
    확인해서 입력하는 수동 입력칸으로 둔다 — creative_admin_notes에 (광고그룹, 주차)
    단위로 저장되어 새로고침/관리자 모드 전환/지점 이동에도 값이 유지된다.
    위젯 key는 store_name+ad_type이 아니라 adgroup_id+week_monday로 고유하게 잡는다 —
    보름숲의 "보름숲 통대관"처럼 같은 store_name·ad_type인 추가 광고그룹이 하나 더
    있으면 store_name+ad_type만으로는 대표 광고그룹의 입력칸과 key가 겹쳐 버리고,
    주차가 바뀌면 그 주만의 값을 새로 보여줘야 하기 때문이다.
    이 페이지의 목표는 광고 데이터를 한 화면에 컴팩트하게 보여주는 것이라, 평균
    입찰가·특이사항을 "적는" 입력창 자체는 관리자 모드에서만 그린다 — 일반 사용자는
    입력 위젯 없이 표/텍스트로 결과값만 보므로 이 칸 때문에 세로로 늘어나지 않는다."""
    is_admin = st.session_state.get("is_admin")
    adgroup_id = adgroup["nccAdgroupId"]
    bid_amt = adgroup.get("bidAmt", 0)
    avg_key = f"cv_avgbid_{adgroup_id}_{week_monday.isoformat()}"
    note_key = f"cv_note_{adgroup_id}_{week_monday.isoformat()}"

    if avg_key not in st.session_state or note_key not in st.session_state:
        db_avg, db_note = fetch_admin_note(adgroup_id, week_monday)
        st.session_state.setdefault(avg_key, db_avg)
        st.session_state.setdefault(note_key, db_note)

    def _save_admin_note():
        upsert_admin_note(adgroup_id, week_monday, st.session_state[avg_key], st.session_state[note_key])

    def _build_table(rows):
        html = f'<table style="border-collapse:collapse; border:1px solid {TABLE_BORDER};">'
        for name, val, extra in rows:
            html += '<tr>'
            html += (
                f'<td style="padding:9px 12px; border:1px solid {TABLE_BORDER}; background:{TABLE_HEADER_BG}; '
                f'font-weight:700; font-size:16px; white-space:nowrap;">{name}</td>'
            )
            if extra is not None:
                html += f'<td style="padding:9px 12px; border:1px solid {TABLE_BORDER}; font-size:16px; font-weight:500;">{val}</td>'
                html += (
                    f'<td style="padding:9px 12px; border:1px solid {TABLE_BORDER}; font-size:16px; font-weight:500; '
                    f'text-align:right;">{extra}</td>'
                )
            else:
                html += (
                    f'<td colspan="2" style="padding:9px 12px; border:1px solid {TABLE_BORDER}; '
                    f'font-size:16px; font-weight:500;">{val}</td>'
                )
            html += '</tr>'
        html += '</table>'
        return html

    with st.container(key=f"cv_bid_row_{adgroup_id}"):
        col_bid, col_note = st.columns([1, 2])
        with col_bid:
            if ad_type == "플레이스광고":
                avg_bid = st.session_state.get(avg_key, 0)
                diff = bid_amt - avg_bid
                diff_color = "#E03131" if diff < 0 else "#16181D"
                diff_html = f'<span style="color:{diff_color};">{diff:,}원</span>'
                # 관리자 모드에서는 "평균 입찰가" 행을 표에 정적으로 넣는 대신, 표를
                # 현재입찰가(+차액) 한 줄로 컴팩트하게 줄이고 그 바로 아래에 실제
                # 입력 위젯을 붙인다 — 예전처럼 입력창을 표 위 별도 블록으로 얹지
                # 않고, 표가 그 자리(위쪽)를 그대로 차지하도록.
                rows = [("현재 입찰가", f"{bid_amt:,}원", diff_html)]
                if not is_admin:
                    rows.append(("평균 입찰가", f"{avg_bid:,}원", None))
                st.markdown(_build_table(rows), unsafe_allow_html=True)
                if is_admin:
                    st.number_input(
                        "평균 입찰가", min_value=0, step=10, key=avg_key, on_change=_save_admin_note,
                    )
            else:
                daily_budget = adgroup.get("dailyBudget", 0)
                rows = [("현재 입찰가", f"{bid_amt:,}원", None), ("하루 예산", f"{daily_budget:,}원", None)]
                st.markdown(_build_table(rows), unsafe_allow_html=True)
        with col_note:
            if is_admin:
                st.text_input(
                    "특이사항", key=note_key, placeholder="* 특이사항 - 이번 주 특이사항을 입력하세요",
                    label_visibility="collapsed", on_change=_save_admin_note,
                )
            else:
                note_text = st.session_state.get(note_key, "").strip()
                st.markdown(
                    f'<div style="font-size:16px; color:#16181D; padding-top:10px;">'
                    f'<b>* 특이사항</b> - {note_text or "없음"}</div>',
                    unsafe_allow_html=True,
                )


# cv_kwsave_result 플래그는 Top10 키워드 저장·소재 캡처 업로드(플레이스/파워링크/
# 파워컨텐츠 각 섹션, 추가 광고그룹까지) 여러 지점에서 공유해서 쓴다. 예전엔 각
# 저장 지점 바로 아래에서 "플래그가 True면 다이얼로그 열기"를 각자 체크했는데,
# 한 지점에서만 저장해도 플래그가 True가 되는 순간 나머지 모든 지점이 똑같이
# _kwsave_result_dialog()를 부르려고 해서 StreamlitDuplicateElementId 에러가 났다
# (2026-08-04 발견). 이제 페이지 스크립트 맨 끝, 모든 섹션을 다 그린 뒤 딱 한
# 곳에서만 체크한다 — 같은 다이얼로그를 여러 번 열려고 시도하는 일이 구조적으로
# 불가능해진다.
@st.dialog("완료")
def _kwsave_result_dialog():
    st.markdown("저장했습니다.")
    if st.button("확인", key="result_ok", width="stretch"):
        st.session_state["cv_kwsave_result"] = False
        st.rerun()


CREATIVE_SCREENSHOT_BUCKET = "creative-screenshots"


@st.cache_data(ttl=60, show_spinner=False)
def fetch_creative_screenshot(adgroup_id):
    """소재 실제 화면 캡처 — creative_screenshots 테이블에서 이 광고그룹의 최신
    1행(있으면)을 가져온다. 주차 구분 없이 광고그룹당 최대 1행만 존재하고, 소재가
    바뀔 때만 관리자가 수동으로 새로 올린다(주간 자동 수집 대상이 아님)."""
    client = get_supabase_client()
    res = client.table("creative_screenshots").select("*").eq("adgroup_id", adgroup_id).execute()
    return res.data[0] if res.data else None


def upload_creative_screenshot(adgroup_id, uploaded_file):
    """업로드된 파일을 Storage 버킷에 저장(같은 경로면 덮어씀)하고, 그 경로를
    creative_screenshots 테이블에 upsert한다."""
    client = get_supabase_client()
    ext = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else "png"
    storage_path = f"{adgroup_id}.{ext}"
    client.storage.from_(CREATIVE_SCREENSHOT_BUCKET).upload(
        storage_path, uploaded_file.getvalue(),
        {"content-type": uploaded_file.type or "image/png", "upsert": "true"},
    )
    client.table("creative_screenshots").upsert({
        "adgroup_id": adgroup_id,
        "storage_path": storage_path,
        "uploaded_at": datetime.datetime.utcnow().isoformat(),
    }).execute()
    fetch_creative_screenshot.clear()


def get_screenshot_url(storage_path, uploaded_at=None):
    """소재를 교체해도 storage_path(파일명)가 항상 adgroup_id 그대로라 URL이 똑같이
    유지된다 — 그래서 실제 파일은 바뀌어도 브라우저(및 Supabase Storage 앞단 CDN)가
    예전 URL의 캐시를 계속 보여주는 문제가 있었다(2026-08-04 실측 확인). 캡처를
    새로 올릴 때마다 바뀌는 uploaded_at을 쿼리 파라미터로 붙여 URL 자체를 다르게
    만들어서 캐시를 무효화한다."""
    client = get_supabase_client()
    url = client.storage.from_(CREATIVE_SCREENSHOT_BUCKET).get_public_url(storage_path)
    if uploaded_at:
        url = f"{url}?v={quote(str(uploaded_at))}"
    return url


def render_creative_screenshot_slot(adgroup_id):
    """일별 유입 현황 표는 그대로 두고, 그 아래 차트 자리(세 유형 모두)를 실제
    노출 화면 캡처로 대체한다(2026-07-31 실물 리포트 비교로 확인한 자리, 2026-08-04
    플레이스도 통일) — API로 가져온 소재는 실제 노출 화면(사진/평점/태그 등 플레이스
    프로필 데이터)과 시각적 차이가 커서 재현을 포기하고, 담당자가 직접 캡처해
    올리는 방식으로 대체했다."""
    st.markdown("**광고 소재**")
    row = fetch_creative_screenshot(adgroup_id)
    if row:
        # width="stretch"는 컬럼 폭에 꽉 채워서 세로로 긴 캡처(플레이스처럼 모바일
        # 화면 전체를 찍은 경우)가 비율 그대로 세로로 아주 커진다. 반대로 고정 폭
        # (예: 260px)으로 다 맞추면 이번엔 가로로 넓은 캡처(파워컨텐츠처럼 짧고
        # 넓은 경우)가 너무 작아진다(2026-08-04, 둘 다 실측으로 확인). 폭 대신
        # 세로 높이만 상한을 두고 폭은 비율대로(최대 컬럼 폭까지) 자동으로 맞춘다 —
        # st.image는 높이 상한을 못 걸어서 raw <img>로 직접 그린다.
        img_url = get_screenshot_url(row["storage_path"], row.get("uploaded_at"))
        st.markdown(
            f'<img src="{img_url}" style="max-width:100%; max-height:340px; '
            f'width:auto; height:auto; display:block;">',
            unsafe_allow_html=True,
        )
    elif not st.session_state.get("is_admin"):
        st.info("등록된 소재 캡처가 없습니다.")

    if st.session_state.get("is_admin"):
        st.caption("소재 캡처 이미지 교체" if row else "소재 캡처 이미지 등록")
        uploaded_file = st.file_uploader(
            "캡처 이미지", type=["png", "jpg", "jpeg"],
            key=f"cv_creative_upload_{adgroup_id}", label_visibility="collapsed",
        )
        if uploaded_file:
            # st.file_uploader는 한 번 선택된 파일을 리런마다 계속 그대로 돌려주므로,
            # "저장" 버튼 없이 선택 즉시 업로드하면 이후 아무 리런에서나 같은 파일을
            # 계속 재업로드해버린다 — file_id(선택될 때마다 새로 발급되는 고유값)를
            # 마지막으로 처리한 값과 비교해서, 새로 선택된 파일일 때만 한 번 업로드한다.
            last_id_key = f"cv_creative_last_upload_id_{adgroup_id}"
            file_identity = getattr(uploaded_file, "file_id", None) or f"{uploaded_file.name}:{uploaded_file.size}"
            if st.session_state.get(last_id_key) != file_identity:
                upload_creative_screenshot(adgroup_id, uploaded_file)
                st.session_state[last_id_key] = file_identity
                st.session_state["cv_kwsave_result"] = True
                st.rerun()


def render_place_keyword_editor(adgroup_id, week_monday, existing_df):
    """플레이스광고 상위 클릭 10개 키워드 — 관리자가 st.data_editor(엑셀처럼 셀
    단위로 편집 가능한 표)로 직접 입력한다. API가 이 항목만 기간 조회를 지원하지
    않아서 유일하게 수동 입력이 필요한 칸이다. 표 자체는 st.markdown 기반 HTML이
    아니라 진짜 Streamlit 위젯이라 raw <div>로 표를 흉내 내려다 겪었던 collapse
    버그(2026-07-31, 평균입찰가 입력 UI 항목 참고)가 여기서는 발생하지 않는다."""
    if existing_df is not None and not existing_df.empty:
        rows = existing_df[["키워드", "노출수", "클릭수"]].to_dict("records")
    else:
        rows = []
    rows += [{"키워드": "", "노출수": 0, "클릭수": 0}] * (10 - len(rows))
    df = pd.DataFrame(rows[:10])

    editor_key = f"cv_kwedit_{adgroup_id}_{week_monday.isoformat()}"
    edited = st.data_editor(
        df, hide_index=True, num_rows="fixed", key=editor_key,
        column_config={
            "노출수": st.column_config.NumberColumn(min_value=0, step=1),
            "클릭수": st.column_config.NumberColumn(min_value=0, step=1),
        },
    )
    if st.button("저장", key=f"cv_kwsave_{adgroup_id}_{week_monday.isoformat()}", width="stretch"):
        # r["키워드"]가 None일 수 있다 — 셀을 지우면 빈 문자열이 아니라 None이 되는데,
        # str(None)은 "None"이라는 글자라서 마치 값이 있는 것처럼 잘못 걸러지지 않게
        # r.get(...)의 falsy 여부를 먼저 확인한다(2026-07-31, 지운 행이 안 지워지는
        # 버그로 발견).
        clean_rows = [r for r in edited.to_dict("records") if r.get("키워드") and str(r["키워드"]).strip()]
        clean_rows.sort(key=lambda r: r["클릭수"] or 0, reverse=True)
        save_top_keywords(adgroup_id, week_monday, clean_rows)
        st.session_state["cv_kwsave_result"] = True
        st.rerun()


@st.dialog("일별 유입 현황", width="large")
def _render_daily_stats_dialog(display_df):
    render_html_table(display_df)


def render_report_body(title, ad_type, adgroup, last_week_start, last_week_end):
    """제목 줄 + 입찰가 박스 + 일별/주간/Top10 표·차트 3분할 — 대표 광고그룹이든,
    보름숲의 "보름숲 통대관"처럼 별도로 보여주는 추가 광고그룹이든 똑같이 이
    본문을 쓴다."""
    adgroup_id = adgroup["nccAdgroupId"]
    four_weeks_start = last_week_start - datetime.timedelta(weeks=3)  # 선택한 주 포함 4주 전 월요일

    daily_recent, err = fetch_daily_stats(adgroup_id, last_week_start, last_week_end)

    st.markdown(f"### {title}")

    # 일별 유입 현황 팝업 버튼용 데이터 — 버튼 자체는 아래 "주간 유입 현황"
    # 제목 옆에 작게 그린다(2026-08-11, 처음엔 광고 블록 제목 옆에 큰 버튼으로
    # 뒀는데 너무 커 보인다는 피드백을 받아 위치/크기를 다시 조정).
    display_df = None
    if daily_recent is not None and not daily_recent.empty:
        display_df = with_ctr_cpc(daily_recent).copy()
        display_df["날짜"] = display_df["날짜"].apply(lambda d: d.strftime("%m/%d"))
        # 원본 리포트와 같은 순서(노출수·클릭수·클릭률·CPC·총비용)로 맞춘다 —
        # 총비용이 클릭률/CPC보다 앞에 있던 걸 뒤로 옮김.
        display_df = display_df[["날짜", "노출수", "클릭수", "클릭률(%)", "평균 CPC", "총비용"]]

    if err:
        st.error(f"❌ 일별 유입 현황을 가져오는 중 오류가 발생했습니다: {err}")
        return

    render_bid_info(ad_type, adgroup, last_week_start)

    daily_month, err = fetch_daily_stats(adgroup_id, four_weeks_start, last_week_end)
    if err:
        st.error(f"❌ 주간 유입 현황을 가져오는 중 오류가 발생했습니다: {err}")
        return
    top_keywords, err = fetch_top_keywords(adgroup_id, last_week_start)
    if err:
        st.error(f"❌ 상위 클릭 키워드를 가져오는 중 오류가 발생했습니다: {err}")
        return

    with st.container(key=f"cv_report_row_{adgroup_id}"):
        col_weekly, col_keywords, col_creative = st.columns(3)

    with col_weekly:
        # 이 작은 제목+버튼 줄은 반드시 별도 key로 감싼다 — cv_report_row에 걸린
        # flex-wrap/최소폭 CSS가 후손 선택자(space)라서, 감싸지 않으면 이 안쪽의
        # 중첩 컬럼에도 그대로 적용되어 버튼이 강제로 줄바꿈되며 전체 폭으로
        # 늘어나는 버그가 있었다(2026-08-11).
        with st.container(key=f"cv_weekly_header_{adgroup_id}"):
            sub_title, sub_daily_btn = st.columns([3, 1.4])
            with sub_title:
                st.markdown("**주간 유입 현황**")
            with sub_daily_btn:
                if display_df is not None:
                    if st.button("일별 보기", key=f"cv_daily_btn_{adgroup_id}"):
                        _render_daily_stats_dialog(display_df)
        weekly_df = build_weekly_table(daily_month) if daily_month is not None else None
        if weekly_df is not None and not weekly_df.empty:
            render_html_table(weekly_df.drop(columns=["주차"]))
            render_dual_axis_chart(weekly_df, "주차")
        else:
            st.info("데이터가 없습니다.")

    with col_keywords:
        st.markdown("**상위 클릭 10개 키워드**")
        if ad_type == "플레이스광고" and st.session_state.get("is_admin"):
            render_place_keyword_editor(adgroup_id, last_week_start, top_keywords)
        elif top_keywords is not None and not top_keywords.empty:
            render_html_table(top_keywords)
        else:
            st.info("데이터가 없습니다.")

    with col_creative:
        render_creative_screenshot_slot(adgroup_id)


def render_ad_type_report(store_name, ad_type, label, section_key, last_week_start, last_week_end):
    """플레이스/파워링크/파워컨텐츠 3개 구간 중 하나를 그린다. 대표 광고그룹 외에
    같은 캠페인에 더 있는 추가(대관 등) 광고그룹은 여기서 안 그리고 그대로 돌려줘서,
    호출부가 페이지 맨 아래에 별도 이름으로 몰아서 보여줄 수 있게 한다.
    이 매장에 그 광고 유형 캠페인 자체가 없으면 제목·테두리 박스까지 통째로 안
    그린다(2026-07-31, 빈 제목만 남는 대신 완전히 생략해달라는 요청) — 그래서
    st.container(border=True)를 호출부가 아니라 여기서 직접 만든다."""
    adgroup, extra_adgroups, err = fetch_first_adgroup(store_name, ad_type)
    if not err and not adgroup:
        return []  # 캠페인 자체가 없음 — 제목/박스 없이 완전히 생략

    with st.container(border=True, key=section_key):
        if err:
            st.markdown(f"### {label}")
            st.error(f"❌ {label} 데이터를 가져오는 중 오류가 발생했습니다: {err}")
            return []
        render_report_body(label, ad_type, adgroup, last_week_start, last_week_end)
    return [(ad_type, ag) for ag in extra_adgroups]


@st.cache_data(ttl=600, show_spinner=False)
def fetch_stores():
    """store_campaigns(place_rank.py 등 앱 전체가 쓰는 매장 마스터 테이블)에서 매장
    목록을 가져온다. 예전엔 .streamlit/secrets.toml의 네이버 광고 계정(7개)을 그대로
    "매장" 선택지로 썼는데, 계정 하나에 매장이 여러 개 묶인 경우(예: "고집돌우럭
    중문점" 계정에 중문점·함덕점·와인창고 함덕점 3개 매장) 나머지 매장이 화면에
    아예 안 보이는 버그가 있었다(2026-07-31 발견) — 이제 실제 매장 단위(12개)로
    보여준다."""
    client = get_supabase_client()
    res = client.table("store_campaigns").select("store_name").order("display_order").execute()
    return [r["store_name"] for r in (res.data or [])]


st.subheader("주간 광고 데이터")

# 맨 아래 매장 이동 버튼을 누르면 다음 매장의 자료를 처음부터 봐야 하니, 브라우저
# 스크롤을 페이지 맨 위로 되돌린다 — 그대로 두면 새 매장 데이터가 로드돼도 스크롤
# 위치는 그대로라 여전히 맨 아래(다음 매장 이동 버튼 근처)에 머물러 있게 된다.
# Streamlit은 <html>/<body>가 아니라 section[data-testid="stMain"] 안에서 자체
# 스크롤한다 — document.documentElement.scrollTop = 0은 그 컨테이너를 안 건드려서
# 효과가 없었다(2026-08-01 실측 확인). st.markdown에 넣은 <script>는 Streamlit이
# 실행 안 해줘서, components.html의 iframe에서 window.parent를 통해 실제 스크롤
# 컨테이너를 찾아 스크롤한다(이 앱의 클립보드 복사 버튼 등에서 이미 쓰던 패턴).
#
# 간헐적으로 스크롤이 전혀 안 되는 버그가 실측 확인됐다(2026-08-05) — 재현/로깅해보니
# 몇 초를 기다려도 scrollTop이 단 한 번도 변하지 않는 경우가 있었다(재시도 루프를
# 넣어봐도 동일) — 즉 "실행됐다가 되돌려지는" 게 아니라 스크립트 자체가 아예 실행
# 안 된 것으로 보인다. 이 컴포넌트의 HTML 내용이 매번 완전히 동일한 문자열이라,
# Streamlit이 이전 실행에서 마운트했던 것과 "같은" iframe으로 보고 새로 마운트/실행을
# 건너뛰는 것으로 추정된다(직접 만든 동일 iframe을 수동으로 새로 만들면 항상 성공하는
# 것으로 확인 — 스크립트 자체 로직은 문제 없음). 매번 다른 타임스탬프를 주석으로 끼워
# 넣어 내용을 매번 다르게 만들어서, Streamlit이 "이전과 다른 새 컴포넌트"로 인식해
# 매번 확실히 새로 마운트/실행하도록 강제한다.
if st.session_state.pop("cv_scroll_top_pending", False):
    components.html(
        f"""
        <script>
        // {datetime.datetime.now().isoformat()} (매번 값이 달라야 재마운트가 보장됨)
        (function() {{
            var tries = 0;
            var timer = setInterval(function() {{
                var m = window.parent.document.querySelector('section[data-testid="stMain"]');
                if (m) {{ m.scrollTop = 0; }}
                if (++tries > 20) {{ clearInterval(timer); }}
            }}, 100);
        }})();
        </script>
        """,
        height=0,
    )

available_accounts = fetch_stores()

if not available_accounts:
    st.warning("등록된 매장이 없습니다. `store_campaigns` 테이블에 매장을 먼저 등록해 주세요.")
else:
    if "cv_account_select" not in st.session_state:
        st.session_state["cv_account_select"] = available_accounts[0]

    def _shift_account(delta):
        idx = available_accounts.index(st.session_state["cv_account_select"])
        st.session_state["cv_account_select"] = available_accounts[(idx + delta) % len(available_accounts)]

    def _shift_account_and_scroll_top(delta):
        _shift_account(delta)
        st.session_state["cv_scroll_top_pending"] = True

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
                "매장", options=available_accounts, key="cv_account_select", label_visibility="collapsed",
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

    extra_adgroups = []

    extra_adgroups += render_ad_type_report(
        selected_account, "플레이스광고", f"{selected_account} 플레이스 광고",
        "section_report_place", week_monday, week_sunday,
    ) or []

    extra_adgroups += render_ad_type_report(
        selected_account, "파워링크광고", f"{selected_account} 파워링크 광고",
        "section_report_weblink", week_monday, week_sunday,
    ) or []

    extra_adgroups += render_ad_type_report(
        selected_account, "파워컨텐츠광고", f"{selected_account} 파워컨텐츠 광고",
        "section_report_contents", week_monday, week_sunday,
    ) or []

    # 매장 본업 3구간(플레이스/파워링크/파워컨텐츠)과 섞이면 헷갈리니, 보름숲의
    # "보름숲 통대관"·"대관 파워컨텐츠"처럼 계정에 딸린 추가(대관 등) 광고그룹은
    # 맨 아래에 실제 광고그룹 이름 그대로 따로 몰아서 보여준다.
    for ad_type, ag in extra_adgroups:
        with st.container(border=True, key=f"section_report_extra_{ag['nccAdgroupId']}"):
            render_report_body(ag.get("name") or "추가 광고그룹", ad_type, ag, week_monday, week_sunday)

    # 모든 섹션을 다 그린 뒤 딱 한 곳에서만 체크 — 이유는 _kwsave_result_dialog
    # 정의부 주석 참고.
    if st.session_state.get("cv_kwsave_result"):
        _kwsave_result_dialog()

    # 회의 중 자료를 끝까지 읽고 나면 다음 매장으로 넘기기 위해 맨 위로 다시
    # 스크롤해야 하는 게 불편하다는 요청(2026-07-31) — 맨 아래에도 매장 이동
    # 버튼을 둔다. 매장명 텍스트 없이 ◀▶ 버튼만(선택은 위 드롭다운에서 이미 하니
    # 여기선 그냥 순수 이동 기능만). 위 버튼과 달리 클릭 후 페이지 맨 위로
    # 스크롤도 같이 시켜서(_shift_account_and_scroll_top) 다음 매장 자료를
    # 처음부터 보게 한다 — 위 버튼은 이미 맨 위에 있으니 그럴 필요 없음.
    st.divider()
    with st.container(key="cv_nav_row_bottom"):
        col_bottom_prev, col_bottom_next = st.columns([0.5, 0.5])
        with col_bottom_prev:
            st.button(
                "◀", key="cv_account_prev_bottom",
                on_click=_shift_account_and_scroll_top, args=(-1,), width="stretch",
            )
        with col_bottom_next:
            st.button(
                "▶", key="cv_account_next_bottom",
                on_click=_shift_account_and_scroll_top, args=(1,), width="stretch",
            )
