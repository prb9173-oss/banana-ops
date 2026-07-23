import time
import hmac
import hashlib
import base64
import requests
import streamlit as st
from supabase import create_client

NAVER_BASE_URL = "https://api.searchad.naver.com"
NAVER_REQUEST_TIMEOUT = 10


@st.cache_resource
def get_supabase_client():
    sb = st.secrets["supabase"]
    return create_client(sb["url"], sb["key"])


def _naver_signature(timestamp, method, uri, secret_key):
    message = f"{timestamp}.{method}.{uri}"
    hash_obj = hmac.new(secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256)
    return base64.b64encode(hash_obj.digest()).decode("utf-8")


def _naver_header(method, uri, api_key, secret_key, customer_id):
    timestamp = str(int(time.time() * 1000))
    signature = _naver_signature(timestamp, method, uri, secret_key)
    return {
        'Content-Type': 'application/json; charset=UTF-8',
        'X-Timestamp': timestamp,
        'X-API-KEY': api_key,
        'X-Customer': str(customer_id),
        'X-Signature': signature,
    }


def fetch_adgroup_keywords_live(customer_id, api_key, secret_key, adgroup_id):
    uri = "/ncc/keywords"
    headers = _naver_header("GET", uri, api_key, secret_key, customer_id)
    r = requests.get(
        f"{NAVER_BASE_URL}{uri}", params={'nccAdgroupId': adgroup_id},
        headers=headers, timeout=NAVER_REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def create_keywords_live(customer_id, api_key, secret_key, adgroup_id, keyword_texts):
    uri = "/ncc/keywords"
    headers = _naver_header("POST", uri, api_key, secret_key, customer_id)
    body = [{"keyword": kw} for kw in keyword_texts]
    r = requests.post(
        f"{NAVER_BASE_URL}{uri}", params={'nccAdgroupId': adgroup_id}, json=body,
        headers=headers, timeout=NAVER_REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def set_keywords_lock_live(customer_id, api_key, secret_key, keyword_objs, lock):
    uri = "/ncc/keywords"
    headers = _naver_header("PUT", uri, api_key, secret_key, customer_id)
    body = []
    for kw in keyword_objs:
        updated = dict(kw)
        updated["userLock"] = lock
        body.append(updated)
    r = requests.put(
        f"{NAVER_BASE_URL}{uri}", params={'fields': 'userLock'}, json=body,
        headers=headers, timeout=NAVER_REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


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
        with st.container(border=True, key=f"bundle_card_{bundle['id']}"):
            col_info, col_actions = st.columns([6, 2], vertical_alignment="center")
            with col_info:
                st.markdown(f"**{bundle['name']}** · 키워드 {len(bundle['keywords'])}개")
                st.markdown(
                    f'<div class="kw-text">{", ".join(bundle["keywords"])}</div>',
                    unsafe_allow_html=True,
                )
            with col_actions:
                with st.container(key=f"actions_{bundle['id']}"):
                    if st.button("수정", key=f"edit_{bundle['id']}"):
                        st.session_state[f"editing_{bundle['id']}"] = not st.session_state.get(f"editing_{bundle['id']}", False)
                    if st.button("삭제", key=f"delete_{bundle['id']}"):
                        get_supabase_client().table("season_keyword_bundles").delete().eq("id", bundle["id"]).execute()
                        st.rerun()

            if st.session_state.get(f"editing_{bundle['id']}", False):
                with st.container(key=f"edit_panel_{bundle['id']}"):
                    st.markdown('<div class="edit-panel-label">✏️ 키워드 수정 (쉼표로 구분)</div>', unsafe_allow_html=True)
                    edited_kw_raw = st.text_area(
                        "키워드 (쉼표로 구분)",
                        value=", ".join(bundle["keywords"]),
                        key=f"edit_kw_{bundle['id']}",
                        height=100,
                        label_visibility="collapsed",
                    )
                    with st.container(key=f"editform_actions_{bundle['id']}"):
                        if st.button("저장", key=f"save_{bundle['id']}"):
                            new_kws = [kw.strip() for kw in edited_kw_raw.split(",") if kw.strip()]
                            if not new_kws:
                                st.warning("키워드를 최소 1개 이상 남겨주세요.")
                            else:
                                deduped = list(dict.fromkeys(new_kws))
                                get_supabase_client().table("season_keyword_bundles").update(
                                    {"keywords": deduped}
                                ).eq("id", bundle["id"]).execute()
                                st.session_state[f"editing_{bundle['id']}"] = False
                                st.rerun()
                        if st.button("취소", key=f"cancel_{bundle['id']}"):
                            st.session_state[f"editing_{bundle['id']}"] = False
                            st.rerun()
        st.markdown("###")

st.markdown("###")


# ==========================================
# [매장 + 묶음 선택]
# ==========================================
st.markdown("#### 🏪 매장별 시즌 키워드 관리")

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

    st.caption(
        f"연결된 계정: {selected_store_row['naver_account_key']} · "
        f"캠페인: {selected_store_row['campaign_id']} · "
        f"광고그룹: {selected_store_row['adgroup_id']}"
    )

    naver_acct = st.secrets[selected_store_row["naver_account_key"]]

    try:
        live_keywords = fetch_adgroup_keywords_live(
            naver_acct["customer_id"], naver_acct["api_key"], naver_acct["secret_key"],
            selected_store_row["adgroup_id"],
        )
        live_error = None
    except Exception as e:
        live_keywords = []
        live_error = str(e)

    if live_error:
        st.error(f"❌ 네이버 계정에서 현재 키워드 상태를 가져오는 데 실패했습니다: {live_error}")
    else:
        live_by_text = {k["keyword"]: k for k in live_keywords}

        status_rows_html = []
        for kw in selected_bundle["keywords"]:
            if kw in live_by_text:
                is_on = not live_by_text[kw]["userLock"]
                pill_class, pill_label = ("pill-kw-on", "ON") if is_on else ("pill-kw-off", "OFF")
            else:
                pill_class, pill_label = "pill-kw-new", "신규"
            status_rows_html.append(
                f'<div class="kw-status-row"><span>{kw}</span>'
                f'<span class="status-pill {pill_class}">{pill_label}</span></div>'
            )

        st.markdown(f"**{selected_store}** 매장 · **'{selected_bundle['name']}'** 묶음 현재 상태 (실시간):")
        st.markdown(
            '<div class="feature-card kw-status-card">' + "".join(status_rows_html) + "</div>",
            unsafe_allow_html=True,
        )

        confirm_key = f"confirm_action_{selected_store_row['id']}_{selected_bundle_id}"

        with st.container(key="onoff_actions"):
            if st.button("키워드 On", key="btn_turn_on"):
                st.session_state[confirm_key] = "on"
            if st.button("키워드 Off", key="btn_turn_off"):
                st.session_state[confirm_key] = "off"

        pending = st.session_state.get(confirm_key)
        if pending:
            action_label = "켜기" if pending == "on" else "끄기"
            with st.container(key="confirm_panel"):
                st.markdown(
                    f'<div class="confirm-text">정말 <b>{selected_store}</b> 매장에 '
                    f"'<b>{selected_bundle['name']}</b>' 묶음을 <b>{action_label}</b> 하시겠습니까?"
                    f'<div class="confirm-subtext">실제 네이버 광고 계정(파워링크)에 바로 반영됩니다.</div></div>',
                    unsafe_allow_html=True,
                )
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("예", key="confirm_yes"):
                        try:
                            if pending == "on":
                                to_create = [kw for kw in selected_bundle["keywords"] if kw not in live_by_text]
                                to_unlock = [
                                    live_by_text[kw] for kw in selected_bundle["keywords"]
                                    if kw in live_by_text and live_by_text[kw]["userLock"]
                                ]
                                if to_create:
                                    create_keywords_live(
                                        naver_acct["customer_id"], naver_acct["api_key"], naver_acct["secret_key"],
                                        selected_store_row["adgroup_id"], to_create,
                                    )
                                if to_unlock:
                                    set_keywords_lock_live(
                                        naver_acct["customer_id"], naver_acct["api_key"], naver_acct["secret_key"],
                                        to_unlock, lock=False,
                                    )
                                st.success(f"✅ {len(to_create)}개 신규 추가, {len(to_unlock)}개 ON 처리했습니다.")
                            else:
                                to_lock = [
                                    live_by_text[kw] for kw in selected_bundle["keywords"]
                                    if kw in live_by_text and not live_by_text[kw]["userLock"]
                                ]
                                if to_lock:
                                    set_keywords_lock_live(
                                        naver_acct["customer_id"], naver_acct["api_key"], naver_acct["secret_key"],
                                        to_lock, lock=True,
                                    )
                                st.success(f"✅ {len(to_lock)}개 OFF 처리했습니다.")
                            st.session_state[confirm_key] = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 적용 중 오류가 발생했습니다: {e}")
                with col_no:
                    if st.button("아니오", key="confirm_no"):
                        st.session_state[confirm_key] = None
                        st.rerun()
