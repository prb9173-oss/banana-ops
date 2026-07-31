import streamlit as st
import datetime
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
def fetch_first_adgroup(account_key, ad_type):
    """creative_adgroup_snapshot 캐시 테이블에서 이 계정·광고유형의 대표/부가
    광고그룹을 가져온다 — 2026-07-31부터 라이브 API 호출 없이 매주 월요일 자동
    수집 스크립트(scripts/check_ad_performance.py)가 채워둔 값만 읽는다(회의 중
    페이지를 빠르게 넘겨볼 때 API 왕복 지연이 없도록).

    "가장 최신 week_monday" 행을 대표/부가 판단 기준으로 삼는다 — 현재 입찰가는
    조회 중인 주차와 무관하게 항상 최신값을 보여준다(라이브 API였을 때도 조회
    주차와 무관하게 "현재" 입찰가만 보여줬으므로 동일한 동작). extra_adgroups는
    role='extra'인 행 전부 — 자동 수집 스크립트가 이미 ELIGIBLE만 걸러서 저장하므로
    (2026-07-31에 발견한 PAUSED 유령 광고그룹 버그 수정 로직 그대로) 여기서 다시
    걸러낼 필요는 없다."""
    client = get_supabase_client()
    res = (
        client.table("creative_adgroup_snapshot")
        .select("*")
        .eq("account_key", account_key)
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
                f'<td style="padding:6px 10px; border:1px solid {TABLE_BORDER}; background:{TABLE_HEADER_BG}; '
                f'font-weight:600; font-size:12.5px; white-space:nowrap;">{name}</td>'
            )
            if extra is not None:
                html += f'<td style="padding:6px 10px; border:1px solid {TABLE_BORDER}; font-size:12.5px;">{val}</td>'
                html += (
                    f'<td style="padding:6px 10px; border:1px solid {TABLE_BORDER}; font-size:12.5px; '
                    f'text-align:right;">{extra}</td>'
                )
            else:
                html += (
                    f'<td colspan="2" style="padding:6px 10px; border:1px solid {TABLE_BORDER}; '
                    f'font-size:12.5px;">{val}</td>'
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
                    f'<div style="font-size:13px; color:#16181D; padding-top:8px;">'
                    f'<b>* 특이사항</b> - {note_text or "없음"}</div>',
                    unsafe_allow_html=True,
                )


def render_report_body(ad_type, adgroup, last_week_start, last_week_end):
    """입찰가 박스 + 일별/주간/Top10 표·차트 3분할 — 대표 광고그룹이든, 보름숲의
    "보름숲 통대관"처럼 별도로 보여주는 추가 광고그룹이든 똑같이 이 본문을 쓴다."""
    render_bid_info(ad_type, adgroup, last_week_start)

    adgroup_id = adgroup["nccAdgroupId"]
    four_weeks_start = last_week_start - datetime.timedelta(weeks=3)  # 선택한 주 포함 4주 전 월요일

    daily_recent, err = fetch_daily_stats(adgroup_id, last_week_start, last_week_end)
    if err:
        st.error(f"❌ 일별 유입 현황을 가져오는 중 오류가 발생했습니다: {err}")
        return
    daily_month, err = fetch_daily_stats(adgroup_id, four_weeks_start, last_week_end)
    if err:
        st.error(f"❌ 주간 유입 현황을 가져오는 중 오류가 발생했습니다: {err}")
        return
    top_keywords, err = fetch_top_keywords(adgroup_id, last_week_start)
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


def render_ad_type_report(account_key, ad_type, label, last_week_start, last_week_end):
    """플레이스/파워링크/파워컨텐츠 3개 구간 중 하나를 그린다. 대표 광고그룹 외에
    같은 계정에 더 있는 추가(대관 등) 광고그룹은 여기서 안 그리고 그대로 돌려줘서,
    호출부가 페이지 맨 아래에 별도 이름으로 몰아서 보여줄 수 있게 한다."""
    st.markdown(f"### {label}")
    adgroup, extra_adgroups, err = fetch_first_adgroup(account_key, ad_type)
    if err:
        st.error(f"❌ {label} 데이터를 가져오는 중 오류가 발생했습니다: {err}")
        return []
    if not adgroup:
        st.info(f"이 계정에는 {label}가 없습니다. (아직 자동 수집이 안 됐을 수도 있어요 — 매주 월요일 수집됩니다.)")
        return []

    render_report_body(ad_type, adgroup, last_week_start, last_week_end)
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

    extra_adgroups = []

    with st.container(border=True, key="section_report_place"):
        extra_adgroups += render_ad_type_report(
            selected_account, "플레이스광고", "플레이스 광고", week_monday, week_sunday
        ) or []

    with st.container(border=True, key="section_report_weblink"):
        extra_adgroups += render_ad_type_report(
            selected_account, "파워링크광고", "파워링크 광고", week_monday, week_sunday
        ) or []

    with st.container(border=True, key="section_report_contents"):
        extra_adgroups += render_ad_type_report(
            selected_account, "파워컨텐츠광고", "파워컨텐츠 광고", week_monday, week_sunday
        ) or []

    # 매장 본업 3구간(플레이스/파워링크/파워컨텐츠)과 섞이면 헷갈리니, 보름숲의
    # "보름숲 통대관"·"대관 파워컨텐츠"처럼 계정에 딸린 추가(대관 등) 광고그룹은
    # 맨 아래에 실제 광고그룹 이름 그대로 따로 몰아서 보여준다.
    for ad_type, ag in extra_adgroups:
        with st.container(border=True, key=f"section_report_extra_{ag['nccAdgroupId']}"):
            st.markdown(f"### 🏛 {ag.get('name') or '추가 광고그룹'}")
            render_report_body(ad_type, ag, week_monday, week_sunday)
