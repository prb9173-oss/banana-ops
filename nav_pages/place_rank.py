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

    return f'<div>{name_bits} {value_pill}{delta_pill}</div>'


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

        # 실무 보고서와 동일하게, 제주도 맛집의 3주 스냅샷은 매장별 순위 카드들과 섞지 않고
        # 최상단에 별도 구역으로 분리한다.
        for snap_idx, (keyword_text, rows) in enumerate(keyword_groups):
            if keyword_text not in WEEKLY_SNAPSHOT_KEYWORDS:
                continue
            with st.container(border=True, key=f"pr_snapshot_{snap_idx}"):
                st.markdown(f"**{keyword_text}** — 최근 3주")
                rep_checks = checks_by_keyword.get(rows[0]["id"], [])
                with st.container(key=f"pr_snapshot_weeks_{snap_idx}"):
                    snap_cols = st.columns(3, vertical_alignment="top")
                    for i, weeks_back in enumerate([2, 1, 0]):
                        snap_date = selected_date - timedelta(days=7 * weeks_back)
                        snap_check = find_check_for_date(rep_checks, snap_date)
                        with snap_cols[i]:
                            st.markdown(f"**{snap_date.strftime('%m/%d')}**")
                            snap_places = (snap_check or {}).get("top_places")
                            if snap_places:
                                top14 = snap_places[:14]
                                half = (len(top14) + 1) // 2
                                left_col, right_col = st.columns(2)
                                with left_col:
                                    for j, p in enumerate(top14[:half], start=1):
                                        st.markdown(f'<div class="rank-snapshot-item">{j}. {p.get("name", "")}</div>', unsafe_allow_html=True)
                                with right_col:
                                    for j, p in enumerate(top14[half:], start=half + 1):
                                        st.markdown(f'<div class="rank-snapshot-item">{j}. {p.get("name", "")}</div>', unsafe_allow_html=True)
                            else:
                                st.caption("데이터 없음")

        for group_idx, (keyword_text, rows) in enumerate(keyword_groups):
            with st.container(border=True, key=f"pr_kwgroup_{group_idx}"):
                col_title, col_order = st.columns([9, 1], vertical_alignment="center")
                with col_title:
                    title_top10_html = ""
                    if keyword_text in TOP10_KEYWORDS:
                        rep_check = find_check_for_date(checks_by_keyword.get(rows[0]["id"], []), selected_date)
                        title_top10_html = build_top10_html((rep_check or {}).get("top_places"))
                    st.markdown(f"**{keyword_text}**{title_top10_html}", unsafe_allow_html=True)
                with col_order:
                    with st.container(key=f"actions_prkwgroup_{group_idx}"):
                        if st.button(
                            ":material/arrow_upward:", key=f"up_pr_kwgroup_{group_idx}",
                            disabled=(group_idx == 0),
                        ):
                            swap_keyword_group_order(keyword_groups, group_idx, group_idx - 1)
                            fetch_all_keywords.clear()
                            st.rerun()
                        if st.button(
                            ":material/arrow_downward:", key=f"down_pr_kwgroup_{group_idx}",
                            disabled=(group_idx == len(keyword_groups) - 1),
                        ):
                            swap_keyword_group_order(keyword_groups, group_idx, group_idx + 1)
                            fetch_all_keywords.clear()
                            st.rerun()

                for kw in rows:
                    store_name = (kw.get("store_campaigns") or {}).get("store_name", "")
                    checks = checks_by_keyword.get(kw["id"], [])
                    selected_check = find_check_for_date(checks, selected_date)
                    previous_check = find_check_for_date(checks, previous_date)

                    with st.container(key=f"pr_kwrow_{kw['id']}"):
                        col_info, col_delete = st.columns([20, 1], vertical_alignment="center")
                        with col_info:
                            st.markdown(
                                build_rank_info_html(store_name, kw, selected_check, previous_check),
                                unsafe_allow_html=True,
                            )
                        with col_delete:
                            # 완전 삭제(DELETE)하면 place_rank_checks가 ON DELETE CASCADE라
                            # 그동안 쌓인 체크 이력까지 같이 사라진다. 대신 비활성화만 해서
                            # 목록/자동 체크에서는 빠지되 이력은 그대로 보존한다.
                            if st.button("-", key=f"kwdel_{kw['id']}"):
                                get_supabase_client().table("place_rank_keywords").update(
                                    {"is_active": False}
                                ).eq("id", kw["id"]).execute()
                                fetch_all_keywords.clear()
                                st.rerun()
