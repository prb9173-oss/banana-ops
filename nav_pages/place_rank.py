from datetime import date, datetime, timedelta

import streamlit as st
from supabase import create_client


@st.cache_resource
def get_supabase_client():
    sb = st.secrets["supabase"]
    return create_client(sb["url"], sb["key"])


def fetch_stores():
    client = get_supabase_client()
    res = client.table("store_campaigns").select("*").order("display_order").execute()
    return res.data or []


def fetch_keywords_for_store(store_id):
    client = get_supabase_client()
    res = (
        client.table("place_rank_keywords")
        .select("*")
        .eq("store_id", store_id)
        .order("display_order")
        .execute()
    )
    return res.data or []


def fetch_all_checks(keyword_ids):
    if not keyword_ids:
        return {}
    client = get_supabase_client()
    res = (
        client.table("place_rank_checks")
        .select("*")
        .in_("keyword_id", keyword_ids)
        .order("checked_at", desc=True)
        .execute()
    )
    by_keyword = {}
    for row in res.data or []:
        by_keyword.setdefault(row["keyword_id"], []).append(row)
    return by_keyword


def format_checked_at(checked_at):
    try:
        dt = datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%m/%d %H:%M")
    except Exception:
        return checked_at


def find_check_for_date(checks, target_date):
    for c in checks:
        try:
            checked_date = datetime.fromisoformat(c["checked_at"].replace("Z", "+00:00")).astimezone().date()
        except Exception:
            continue
        if checked_date == target_date:
            return c
    return None


def build_rank_info_html(keyword_row, selected_check, previous_check):
    keyword = keyword_row["keyword"]
    is_active = keyword_row.get("is_active", True)

    name_bits = f'<span class="rank-kw">{keyword}</span>'
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
        value_pill = '<span class="status-pill pill-rank-unknown">권외</span>'
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

    meta_text = f"체크 시각: {format_checked_at(selected_check['checked_at'])}"
    return (
        f'<div>{name_bits} {value_pill}{delta_pill}</div>'
        f'<div class="rank-meta">{meta_text}</div>'
    )


st.subheader("플레이스 순위 추적")
st.caption("매장별 타겟 키워드의 네이버 플레이스 검색 순위를 매일 체크하고 전일 대비 변동을 확인합니다.")

try:
    stores = fetch_stores()
    supabase_error = None
except Exception as e:
    stores = []
    supabase_error = str(e)

if supabase_error:
    st.error(f"❌ Supabase 연결 중 오류가 발생했습니다: {supabase_error}")
    st.stop()

st.sidebar.markdown("### 🏪 매장 선택")

if not stores:
    st.sidebar.warning("등록된 매장이 없습니다.")
    st.info("등록된 매장이 없습니다. `store_campaigns` 테이블에 매장을 먼저 등록해 주세요.")
    st.stop()

store_options = {s["store_name"]: s for s in stores}
selected_store = st.sidebar.selectbox(
    "순위를 추적할 매장을 선택해 주세요.", options=list(store_options.keys()), key="pr_selected_store"
)
selected_store_row = store_options[selected_store]

if selected_store_row.get("naver_place_id"):
    st.sidebar.caption(f"네이버 플레이스 ID: {selected_store_row['naver_place_id']}")
else:
    st.sidebar.warning(
        "이 매장은 아직 네이버 플레이스 ID가 등록되지 않았습니다 — "
        "Supabase `store_campaigns` 테이블에서 `naver_place_id`를 입력해 주세요."
    )

keywords = fetch_keywords_for_store(selected_store_row["id"])
checks_by_keyword = fetch_all_checks([k["id"] for k in keywords])

with st.container(border=True, key="section_add_keyword"):
    st.markdown("#### 📝 추적 키워드 추가")
    with st.form("add_place_keyword_form", clear_on_submit=True):
        new_keyword = st.text_input("키워드", placeholder="예: 중문 흑돼지")
        submitted = st.form_submit_button("키워드 추가")

        if submitted:
            if not new_keyword.strip():
                st.warning("키워드를 입력해 주세요.")
            else:
                next_order = max([k.get("display_order") or 0 for k in keywords], default=0) + 1
                try:
                    get_supabase_client().table("place_rank_keywords").insert({
                        "store_id": selected_store_row["id"],
                        "keyword": new_keyword.strip(),
                        "display_order": next_order,
                    }).execute()
                    st.success(f"'{new_keyword.strip()}' 키워드가 추가되었습니다.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 키워드 추가 중 오류가 발생했습니다: {e}")

with st.container(border=True, key="section_rank_results"):
    st.markdown(f"#### 📍 {selected_store} · 순위 현황")
    if not keywords:
        st.info("추적 중인 타겟 키워드가 없습니다. 위에서 키워드를 추가해 주세요.")
    else:
        selected_date = st.date_input("조회할 날짜", value=date.today(), key="pr_selected_date")
        previous_date = selected_date - timedelta(days=1)

        for kw in keywords:
            checks = checks_by_keyword.get(kw["id"], [])
            selected_check = find_check_for_date(checks, selected_date)
            previous_check = find_check_for_date(checks, previous_date)

            with st.container(border=True, key=f"pr_kwcard_{kw['id']}"):
                col_info, col_delete = st.columns([7, 1], vertical_alignment="center")
                with col_info:
                    st.markdown(
                        build_rank_info_html(kw, selected_check, previous_check),
                        unsafe_allow_html=True,
                    )
                with col_delete:
                    if st.button("-", key=f"kwdel_{kw['id']}"):
                        get_supabase_client().table("place_rank_keywords").delete().eq(
                            "id", kw["id"]
                        ).execute()
                        st.rerun()
    st.caption(
        "⚠️ 실제 순위 체크(스크래핑)는 아직 연결되지 않았습니다 — "
        "이 화면은 데이터 구조와 표시 방식만 준비된 상태입니다."
    )
