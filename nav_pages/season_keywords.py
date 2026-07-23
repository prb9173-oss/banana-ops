import streamlit as st
from supabase import create_client


@st.cache_resource
def get_supabase_client():
    sb = st.secrets["supabase"]
    return create_client(sb["url"], sb["key"])


def fetch_bundles():
    client = get_supabase_client()
    res = client.table("season_keyword_bundles").select("*").order("created_at", desc=True).execute()
    return res.data or []


def fetch_stores():
    client = get_supabase_client()
    res = client.table("store_campaigns").select("*").order("display_order").execute()
    return res.data or []


st.subheader("시즌 키워드 운용 고도화")
st.caption("시즌별 키워드 묶음을 저장해두고, 매장에 적용할 준비를 합니다.")

try:
    bundles = fetch_bundles()
    supabase_error = None
except Exception as e:
    bundles = []
    supabase_error = str(e)

if supabase_error:
    st.error(f"❌ Supabase 연결 중 오류가 발생했습니다: {supabase_error}")
    st.stop()


# ==========================================
# [묶음 추가]
# ==========================================
st.markdown("#### 📝 시즌 키워드 묶음 추가")

with st.form("add_bundle_form", clear_on_submit=True):
    bundle_name = st.text_input("묶음 이름", placeholder="예: 봄 시즌")
    bundle_keywords_raw = st.text_area(
        "키워드 (한 줄에 하나씩 입력)",
        placeholder="벚꽃 맛집\n봄나들이 코스\n봄 데이트 코스",
        height=120,
    )
    submitted = st.form_submit_button("묶음 추가")

    if submitted:
        keywords = [kw.strip() for kw in bundle_keywords_raw.splitlines() if kw.strip()]
        if not bundle_name.strip():
            st.warning("묶음 이름을 입력해 주세요.")
        elif not keywords:
            st.warning("키워드를 최소 1개 이상 입력해 주세요.")
        else:
            get_supabase_client().table("season_keyword_bundles").insert({
                "name": bundle_name.strip(),
                "keywords": keywords,
            }).execute()
            st.success(f"'{bundle_name.strip()}' 묶음이 추가되었습니다.")
            st.rerun()

st.markdown("---")


# ==========================================
# [묶음 목록 / 삭제]
# ==========================================
st.markdown("#### 📚 저장된 시즌 키워드 묶음")

if not bundles:
    st.info("아직 저장된 시즌 키워드 묶음이 없습니다. 위에서 먼저 추가해 주세요.")
else:
    for bundle in bundles:
        with st.container():
            col_info, col_delete = st.columns([5, 1])
            with col_info:
                st.markdown(f"**{bundle['name']}** · 키워드 {len(bundle['keywords'])}개")
                st.caption(", ".join(bundle["keywords"]))
            with col_delete:
                if st.button("삭제", key=f"delete_{bundle['id']}"):
                    get_supabase_client().table("season_keyword_bundles").delete().eq("id", bundle["id"]).execute()
                    st.rerun()
            st.markdown("<hr style='margin:8px 0; opacity:0.3;'>", unsafe_allow_html=True)

st.markdown("###")


# ==========================================
# [매장 + 묶음 선택]
# ==========================================
st.markdown("#### 🏪 매장에 시즌 키워드 적용 (선택 화면)")

stores = fetch_stores()

if not stores:
    st.warning("등록된 매장이 없습니다. `store_campaigns` 테이블에 매장을 먼저 등록해 주세요.")
elif not bundles:
    st.warning("적용할 시즌 키워드 묶음이 없습니다. 위에서 먼저 추가해 주세요.")
else:
    store_options = {s["store_name"]: s for s in stores}

    col_store, col_bundle = st.columns(2)
    with col_store:
        selected_store = st.selectbox("매장 선택", options=list(store_options.keys()))
    with col_bundle:
        bundle_options = {b["id"]: b["name"] for b in bundles}
        selected_bundle_id = st.selectbox(
            "키워드 묶음 선택",
            options=list(bundle_options.keys()),
            format_func=lambda x: bundle_options[x],
        )

    selected_bundle = next(b for b in bundles if b["id"] == selected_bundle_id)
    selected_store_row = store_options[selected_store]

    st.markdown(f"**{selected_store}** 매장에 **'{selected_bundle['name']}'** 묶음을 적용하면 아래 키워드가 추가되거나(신규) 켜집니다(기존 OFF 상태):")
    st.markdown(
        '<div class="feature-card">' + ", ".join(selected_bundle["keywords"]) + "</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        f"연결된 계정: {selected_store_row['naver_account_key']} · "
        f"캠페인: {selected_store_row['campaign_id']} · "
        f"광고그룹: {selected_store_row['adgroup_id']}"
    )

    st.markdown("###")
    st.info("💡 실제 네이버 광고 계정에 키워드를 추가/on 하는 기능은 다음 단계에서 구현 예정입니다. 지금은 선택 화면까지만 완성된 상태입니다.")
