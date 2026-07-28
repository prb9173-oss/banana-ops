from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import streamlit as st
from supabase import create_client

KST = ZoneInfo("Asia/Seoul")


@st.cache_resource
def get_supabase_client():
    sb = st.secrets["supabase"]
    return create_client(sb["url"], sb["key"])


@st.cache_data(ttl=300, show_spinner=False)
def fetch_stores():
    client = get_supabase_client()
    res = client.table("store_campaigns").select("*").order("display_order").execute()
    return res.data or []


@st.cache_data(ttl=60, show_spinner=False)
def fetch_all_keywords():
    client = get_supabase_client()
    res = (
        client.table("place_rank_keywords")
        .select("*, store_campaigns(store_name, naver_place_id, naver_place_name, display_order)")
        .eq("is_active", True)
        .order("display_order")
        .execute()
    )
    return res.data or []


@st.cache_data(ttl=60, show_spinner=False)
def fetch_all_checks(keyword_ids):
    if not keyword_ids:
        return {}
    client = get_supabase_client()
    res = (
        client.table("place_rank_checks")
        .select("*")
        .in_("keyword_id", list(keyword_ids))
        .order("checked_at", desc=True)
        .execute()
    )
    by_keyword = {}
    for row in res.data or []:
        by_keyword.setdefault(row["keyword_id"], []).append(row)
    return by_keyword


def group_by_keyword(keyword_rows):
    """키워드 텍스트가 같은 행들을 묶는다 — 같은 키워드를 여러 매장(지점)에
    등록해두면 실무 보고서처럼 한 줄에 지점별 순위를 나란히 볼 수 있게 하기 위함.
    그룹 자체의 순서는 최초 등장 순서를 유지하되, 그룹 안 매장 순서는 별도 버튼 없이
    매장 자체의 display_order("매장 선택" 드롭다운과 동일한 순서)를 따르게 해서
    키워드마다 매장 순서가 제각각이 되는 걸 막는다."""
    groups = {}
    order = []
    for row in keyword_rows:
        kw = row["keyword"]
        if kw not in groups:
            groups[kw] = []
            order.append(kw)
        groups[kw].append(row)
    for rows in groups.values():
        rows.sort(key=lambda r: (r.get("store_campaigns") or {}).get("display_order") or 0)
    return [(kw, groups[kw]) for kw in order]


def filter_groups_for_report(keyword_groups):
    """보고용 표에는 is_report_keyword=True로 표시된 매장 행만 남긴다.
    그룹 안의 모든 행이 걸러지면 그 키워드 그룹 자체를 표에서 뺀다."""
    filtered = []
    for keyword_text, rows in keyword_groups:
        report_rows = [r for r in rows if r.get("is_report_keyword")]
        if report_rows:
            filtered.append((keyword_text, report_rows))
    return filtered


# 표 전체에서 쓰는 선/배경 색 — 한 곳에서만 정의해서 "어떤 선은 굵고 어떤 선은 얇은"
# 불일치가 다시 생기지 않게 한다. 브랜드 구분은 왼쪽 병합 셀(배경색+굵은 글씨)만으로
# 표시하고, 그 외 내용 칸은 항상 흰 배경으로 통일한다.
TABLE_BORDER = "#000000"  # 테스트: 표를 더 직관적으로 보이게 구분선을 검은색으로 시도
BRAND_CELL_BG = "#EEF3FA"


def build_snapshot_rows_html(keyword_groups, checks_by_keyword, selected_date, weekly_snapshot_keywords):
    """제주도 맛집처럼 지정된 키워드는 브랜드 표 바로 위에 최근 3주 경쟁 현황을
    보여준다 — build_brand_rows_html과 같은 <table> 안에 이어붙일 <tr> 목록만
    돌려줘서 두 구역이 서로 다른 표가 아니라 한 표처럼 보이게 한다."""
    rows_html = ""
    for keyword_text, rows in keyword_groups:
        if keyword_text not in weekly_snapshot_keywords:
            continue
        rep_checks = checks_by_keyword.get(rows[0]["id"], [])
        # border는 <tr>가 아니라 각 <td>에 직접 준다 — border-collapse + rowspan이
        # 섞이면 <table> 자체의 outer border나 <tr> border는 브라우저에서 잘려 보이는
        # 경우가 있어서, 표 바깥 네 변도 가장자리 <td>에 각각 명시적으로 그어준다.
        # 이 스냅샷 행이 항상 표의 첫 행이라 top border도 여기서 같이 준다.
        rows_html += '<tr>'
        rows_html += (
            f'<td style="background:{BRAND_CELL_BG}; font-weight:700; padding:10px; '
            f'vertical-align:middle; text-align:center; border-right:1px solid {TABLE_BORDER}; '
            f'border-bottom:1px solid {TABLE_BORDER}; border-top:1px solid {TABLE_BORDER}; '
            f'border-left:1px solid {TABLE_BORDER}; white-space:nowrap;">{keyword_text}<br>'
            f'<span style="font-size:11px; font-weight:500; color:#5B6472;">최근 3주</span></td>'
        )
        for col_idx, weeks_back in enumerate([2, 1, 0]):
            snap_date = selected_date - timedelta(days=7 * weeks_back)
            snap_check = find_check_for_date(rep_checks, snap_date)
            snap_places = (snap_check or {}).get("top_places")
            border_right = f"border-right:1px solid {TABLE_BORDER};"
            date_label = f'<div style="font-weight:700; margin-bottom:6px;">{snap_date.strftime("%m/%d")}</div>'
            if snap_places:
                top14 = snap_places[:14]
                half = (len(top14) + 1) // 2
                left_items = "".join(f'<div class="rank-snapshot-item">{j}. {p.get("name", "")}</div>' for j, p in enumerate(top14[:half], start=1))
                right_items = "".join(f'<div class="rank-snapshot-item">{j}. {p.get("name", "")}</div>' for j, p in enumerate(top14[half:], start=half + 1))
                body = f'<div style="display:flex; gap:10px;"><div style="flex:1;">{left_items}</div><div style="flex:1;">{right_items}</div></div>'
            else:
                body = '<span class="rank-meta">데이터 없음</span>'
            rows_html += (
                f'<td style="padding:8px 10px; vertical-align:top; width:33%; '
                f'border-bottom:1px solid {TABLE_BORDER}; border-top:1px solid {TABLE_BORDER}; {border_right}">'
                f'{date_label}{body}</td>'
            )
        rows_html += '</tr>'
    return rows_html


def build_brand_rows_html(groups, checks_by_keyword, selected_date, previous_date, top10_keywords, add_top_border=False):
    """실무 보고서와 동일한 브랜드 병합 표 — 회의용/보고용 둘 다 이 함수로 렌더링해서
    형식을 통일한다. build_snapshot_rows_html과 같은 <table> 안에 이어붙일 <tr>
    목록만 돌려준다. 순위/증감은 카드뷰와 같은 배지(pill) 스타일을 그대로 쓴다.
    add_top_border=True는 이 표 앞에 스냅샷 구역이 없어서 이 부분이 표의 맨 첫
    행이 되는 경우(top border를 직접 그어줘야 함)를 위한 것."""
    brand_buckets = {}
    brand_order = []
    for keyword_text, rows in groups:
        brand = get_brand((rows[0].get("store_campaigns") or {}).get("store_name", ""))
        if brand not in brand_buckets:
            brand_buckets[brand] = []
            brand_order.append(brand)
        brand_buckets[brand].append((keyword_text, rows))

    rows_html = ""
    for brand_idx, brand in enumerate(brand_order):
        brand_groups = brand_buckets[brand]
        for i, (keyword_text, rows) in enumerate(brand_groups):
            is_very_first_row = add_top_border and brand_idx == 0 and i == 0
            top_border = f"border-top:1px solid {TABLE_BORDER};" if is_very_first_row else ""
            rows_html += '<tr>'
            if i == 0:
                # 브랜드 셀은 rowspan이라 border-bottom을 주면 그 브랜드 블록 전체가
                # 끝나는 시점(마지막 키워드 행)에만 선이 그어진다 — 의도한 동작.
                # 왼쪽 가장자리 셀이라 border-left도 항상 준다(표 바깥 왼쪽 테두리).
                rows_html += (
                    f'<td rowspan="{len(brand_groups)}" style="background:{BRAND_CELL_BG}; '
                    f'font-weight:700; padding:10px; vertical-align:middle; text-align:center; '
                    f'border-right:1px solid {TABLE_BORDER}; border-bottom:1px solid {TABLE_BORDER}; '
                    f'border-left:1px solid {TABLE_BORDER}; {top_border} white-space:nowrap;">{brand}</td>'
                )
            title_top10_html = ""
            if keyword_text in top10_keywords:
                rep_check = find_check_for_date(checks_by_keyword.get(rows[0]["id"], []), selected_date)
                title_top10_html = build_top10_html((rep_check or {}).get("top_places"))

            store_cells = []
            for kw in rows:
                store_name = (kw.get("store_campaigns") or {}).get("store_name", "")
                checks = checks_by_keyword.get(kw["id"], [])
                selected_check = find_check_for_date(checks, selected_date)
                previous_check = find_check_for_date(checks, previous_date)
                store_cells.append(build_rank_info_html(store_name, kw, selected_check, previous_check))

            rows_html += (
                # colspan="3" — 스냅샷 행이 이 표에 "라벨 1칸 + 날짜 3칸"짜리 4열 구조를
                # 만들어두기 때문에, 여기서도 폭을 맞춰 3칸을 다 차지하게 하지 않으면
                # 브라우저가 이 칸을 스냅샷의 첫 날짜 칸 너비로만 좁혀버린다.
                f'<td colspan="3" style="padding:8px 10px; vertical-align:top; '
                f'border-bottom:1px solid {TABLE_BORDER}; border-right:1px solid {TABLE_BORDER}; {top_border}">'
                f'<div style="font-size:15px; font-weight:700; color:#0F172A; margin-bottom:6px;">{keyword_text}{title_top10_html}</div>'
                f'<div style="display:flex; flex-direction:column; gap:5px;">{"".join(store_cells)}</div></td>'
            )
            rows_html += '</tr>'
    return rows_html


def render_rank_tables(snapshot_rows_html, brand_rows_html):
    """3주 스냅샷 + 브랜드 표를 하나의 <table> 안에 이어붙여서 렌더링한다 — 표를
    두 개로 나누면(별도 <table> 태그) 그 사이에 브라우저가 여백을 넣어 두 표가
    분리돼 보이므로, 반드시 하나의 <table> 태그 안에서 합쳐야 한다.
    이 표를 감싸는 st.container(section_rank_results)가 이미 카드(테두리+패딩)라
    표 자체에는 별도 테두리 박스를 씌우지 않는다 — 카드 안에 카드가 겹치면
    아래쪽에 불필요한 빈 공간만 늘어난다."""
    inner = snapshot_rows_html + brand_rows_html
    if not inner:
        return
    st.markdown(
        # 표를 매번 카드(브라우저) 전체 폭까지 늘리면 실제 글자 내용은 얼마 안 되는데
        # 넓은 모니터에서 옆으로 크게 늘어나 버려서, 한 화면에 캡처하려고 축소하면
        # 여백만 같이 줄고 글자만 작아지는 문제가 있었다 — max-width로 내용에 맞는
        # 고정폭을 둬서 캡처하기 좋은 비율(옛 엑셀 보고서와 비슷한 폭)로 맞춘다.
        f'<table style="width:100%; max-width:960px; border-collapse:collapse; font-size:13px; '
        f'color:#16181D; border:1px solid {TABLE_BORDER};">{inner}</table>',
        unsafe_allow_html=True,
    )


def get_brand(store_name):
    """매장명 앞부분을 브랜드로 쓴다 (예: '고집돌우럭 중문점' -> '고집돌우럭').
    store_campaigns에 별도 브랜드 필드가 없어서, 지금 등록된 매장명 규칙(브랜드+공백+지점명)에
    맞춰 이렇게 파생한다."""
    return store_name.split(" ")[0] if store_name else "기타"


def swap_keyword_group_order(keyword_groups, idx_a, idx_b):
    """키워드 그룹(카드) 두 개의 표시 순서를 통째로 맞바꾼다. place_rank_keywords의
    display_order는 원래 매장별로 독립적이었는데, 여기서는 '그룹을 순서대로 쭉 이어
    붙였을 때의 위치'로 전체를 다시 매겨서 그룹 단위 정렬을 보장한다. 그룹 안에서
    매장별 순서(같은 그룹 내 행 순서)는 그대로 유지한다."""
    client = get_supabase_client()
    reordered = list(keyword_groups)
    reordered[idx_a], reordered[idx_b] = reordered[idx_b], reordered[idx_a]
    counter = 0
    for _, rows in reordered:
        for row in rows:
            client.table("place_rank_keywords").update({"display_order": counter}).eq("id", row["id"]).execute()
            counter += 1


def format_checked_at(checked_at):
    """서버가 어느 타임존에서 돌든(Streamlit Cloud는 UTC) 항상 한국 시간 기준으로
    보이도록 시스템 로컬 타임존(astimezone())이 아니라 Asia/Seoul로 명시 변환한다."""
    try:
        dt = datetime.fromisoformat(checked_at.replace("Z", "+00:00")).astimezone(KST)
        return dt.strftime("%m월 %d일 %H:%M")
    except Exception:
        return checked_at


def find_check_for_date(checks, target_date):
    for c in checks:
        try:
            checked_date = datetime.fromisoformat(c["checked_at"].replace("Z", "+00:00")).astimezone(KST).date()
        except Exception:
            continue
        if checked_date == target_date:
            return c
    return None


def build_top10_html(top_places):
    if not top_places:
        return ""
    names = " ".join(f"{i}.{p.get('name', '')}" for i, p in enumerate(top_places[:10], start=1))
    return f' <span class="rank-top10">{names}</span>'


def build_rank_info_html(store_name, keyword_row, selected_check, previous_check):
    is_active = keyword_row.get("is_active", True)

    name_bits = f'<span class="rank-kw">{store_name}</span>'
    if not is_active:
        name_bits += ' <span class="status-pill pill-rank-unknown">추적 중지됨</span>'
        return f'<div>{name_bits}</div>'

    if not selected_check:
        name_bits += ' <span class="status-pill pill-rank-unknown">미확인</span>'
        return f'<div>{name_bits}</div><div class="rank-meta">선택한 날짜에 체크된 데이터 없음</div>'

    if selected_check["status"] == "error":
        value_pill = '<span class="status-pill pill-rank-unknown">체크 실패</span>'
        delta_pill = ""
    elif selected_check["status"] == "not_found" or selected_check["rank"] is None:
        scanned = selected_check.get("results_scanned")
        label = f"{scanned}위 밖" if scanned else "순위권 밖"
        value_pill = f'<span class="status-pill pill-rank-unknown">{label}</span>'
        delta_pill = ""
    else:
        value_pill = f'<span class="status-pill pill-rank-same">{selected_check["rank"]}위</span>'
        delta_pill = ""
        if previous_check and previous_check["status"] == "ok" and previous_check["rank"] is not None:
            diff = previous_check["rank"] - selected_check["rank"]
            if diff > 0:
                delta_pill = f'<span class="status-pill pill-rank-up">▲ {diff}</span>'
            elif diff < 0:
                delta_pill = f'<span class="status-pill pill-rank-down">▼ {abs(diff)}</span>'
            else:
                delta_pill = '<span class="status-pill pill-rank-same">- (유지)</span>'

    return f'<div>{name_bits} {value_pill} {delta_pill}</div>'


st.subheader("플레이스 순위 추적")
st.caption("매장별 타겟 키워드의 네이버 플레이스 검색 순위를 매일 체크하고 전일/전주 대비 변동을 확인합니다.")

try:
    stores = fetch_stores()
    supabase_error = None
except Exception as e:
    stores = []
    supabase_error = str(e)

if supabase_error:
    st.error(f"❌ Supabase 연결 중 오류가 발생했습니다: {supabase_error}")
    st.stop()

if not stores:
    st.info("등록된 매장이 없습니다. `store_campaigns` 테이블에 매장을 먼저 등록해 주세요.")
    st.stop()

all_keywords = fetch_all_keywords()
checks_by_keyword = fetch_all_checks(tuple(k["id"] for k in all_keywords))

with st.container(border=True, key="section_add_keyword"):
    st.markdown("#### 📝 추적 키워드 추가")

    store_options = {s["store_name"]: s for s in stores}
    selected_store = st.selectbox(
        "매장 선택", options=list(store_options.keys()), key="pr_selected_store"
    )
    selected_store_row = store_options[selected_store]

    if selected_store_row.get("naver_place_id"):
        st.caption(f"네이버 플레이스 ID: {selected_store_row['naver_place_id']}")
    else:
        st.warning(
            "이 매장은 아직 네이버 플레이스 ID가 등록되지 않았습니다 — "
            "Supabase `store_campaigns` 테이블에서 `naver_place_id`를 입력해 주세요."
        )

    with st.form("add_place_keyword_form", clear_on_submit=True):
        new_keyword = st.text_input("키워드", placeholder="예: 중문 흑돼지")
        submitted = st.form_submit_button("키워드 추가")

        if submitted:
            if not new_keyword.strip():
                st.warning("키워드를 입력해 주세요.")
            else:
                # 같은 매장 안에서만 순서를 매기면, 그룹 재정렬(swap_keyword_group_order)로
                # display_order가 이미 전체 기준으로 다시 매겨진 뒤라 새 키워드가 목록
                # 중간에 끼어들 수 있다. 전체 최댓값 기준으로 매겨서 항상 맨 아래(새
                # 그룹)로 추가되게 한다.
                next_order = max([k.get("display_order") or 0 for k in all_keywords], default=0) + 1
                try:
                    get_supabase_client().table("place_rank_keywords").insert({
                        "store_id": selected_store_row["id"],
                        "keyword": new_keyword.strip(),
                        "display_order": next_order,
                    }).execute()
                    fetch_all_keywords.clear()
                    st.success(f"'{selected_store}'에 '{new_keyword.strip()}' 키워드가 추가되었습니다.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 키워드 추가 중 오류가 발생했습니다: {e}")

with st.container(border=True, key="section_rank_results"):
    if not all_keywords:
        st.markdown("#### 📍 전체 순위 현황")
        st.info("추적 중인 타겟 키워드가 없습니다. 위에서 키워드를 추가해 주세요.")
    else:
        if "pr_selected_date" not in st.session_state:
            st.session_state["pr_selected_date"] = datetime.now(KST).date()

        # 키워드마다 개별로 체크 시각을 표시하는 대신, 이 조회 날짜에 대해 실제로 체크된
        # 것들 중 가장 늦은 시각 하나만 헤더 옆에 대표로 보여준다.
        latest_checked_at = None
        for kw in all_keywords:
            c = find_check_for_date(checks_by_keyword.get(kw["id"], []), st.session_state["pr_selected_date"])
            if c and (not latest_checked_at or c["checked_at"] > latest_checked_at):
                latest_checked_at = c["checked_at"]

        header_meta = (
            f'<span class="rank-meta" style="font-size:13px; margin-left:10px;">'
            f'체크 시각: {format_checked_at(latest_checked_at)}</span>'
        ) if latest_checked_at else ""
        st.markdown(
            f'<div style="display:flex; align-items:baseline;">'
            f'<span style="font-size:1.3rem; font-weight:700; letter-spacing:-0.02em;">📍 전체 순위 현황</span>'
            f'{header_meta}</div>',
            unsafe_allow_html=True,
        )

        def _shift_selected_date(delta_days):
            st.session_state["pr_selected_date"] += timedelta(days=delta_days)

        with st.container(key="pr_date_nav"):
            col_prev, col_date, col_next, col_basis = st.columns([0.25, 1.15, 0.25, 2], vertical_alignment="top")
            with col_prev:
                st.button(
                    "◀", key="pr_date_prev",
                    on_click=_shift_selected_date, args=(-1,),
                )
            with col_date:
                selected_date = st.date_input("조회할 날짜", key="pr_selected_date")
            with col_next:
                st.button(
                    "▶", key="pr_date_next",
                    on_click=_shift_selected_date, args=(1,),
                    disabled=st.session_state["pr_selected_date"] >= datetime.now(KST).date(),
                )
            with col_basis:
                compare_basis = st.radio(
                    "비교 기준", ["전날 대비", "일주일 전 대비"], horizontal=True, key="pr_compare_basis"
                )
        previous_date = selected_date - timedelta(days=1 if compare_basis == "전날 대비" else 7)

        # 이 두 표시는 모든 키워드에 일괄 적용하는 범용 기능이 아니라, 실무 보고서에서
        # 실제로 그렇게 쓰이는 특정 키워드 텍스트에만 조건부로 바로 보이게 한다(펼치기 없음).
        WEEKLY_SNAPSHOT_KEYWORDS = {"제주도 맛집"}
        TOP10_KEYWORDS = {"함덕 맛집", "중문 맛집"}

        keyword_groups = group_by_keyword(all_keywords)

        # 보고용(캡처 공유용) / 회의용(전체 키워드) — 둘 다 같은 브랜드 병합 표 형식을
        # 쓰고, 보고용은 is_report_keyword로 표시된 키워드만 걸러서 보여준다.
        tab_report, tab_meeting = st.tabs(["📊 보고용", "📋 회의용"])

        with tab_report:
            snapshot_rows = build_snapshot_rows_html(keyword_groups, checks_by_keyword, selected_date, WEEKLY_SNAPSHOT_KEYWORDS)
            report_groups = filter_groups_for_report(keyword_groups)
            if report_groups:
                brand_rows = build_brand_rows_html(
                    report_groups, checks_by_keyword, selected_date, previous_date, TOP10_KEYWORDS,
                    add_top_border=not snapshot_rows,
                )
                render_rank_tables(snapshot_rows, brand_rows)
            else:
                render_rank_tables(snapshot_rows, "")
                st.info("보고용으로 표시할 키워드가 없습니다.")

        with tab_meeting:
            snapshot_rows = build_snapshot_rows_html(keyword_groups, checks_by_keyword, selected_date, WEEKLY_SNAPSHOT_KEYWORDS)
            brand_rows = build_brand_rows_html(
                keyword_groups, checks_by_keyword, selected_date, previous_date, TOP10_KEYWORDS,
                add_top_border=not snapshot_rows,
            )
            render_rank_tables(snapshot_rows, brand_rows)
