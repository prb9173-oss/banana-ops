"""플레이스광고 입찰가 조정 판정 로직 프로토타입. 논의한 판정 로직(예산 소진 / 이상
노출 필터 / 클릭 추세 / 시세 대비 배율)이 실제 데이터에 어떻게 적용되는지 확인하는
화면이자, 2026-08-25부터 매장별로 확인 후 추천 입찰가를 실제 네이버 계정에 반영하는
기능도 여기서 제공한다(적용하면 creative_adgroup_snapshot의 최신 주차 bid_amt도 같이
갱신해서 "주간 광고 데이터" 페이지에도 바로 반영됨). 정식 기능으로 확정되면
creative_viz.py 쪽으로 옮기거나 통합할 예정 — 단, 사용자가 2026-08-25에 "주간 광고
데이터 페이지에 바로 합치지 말고 별도 테스트 탭으로 유지해달라"고 명확히 요청했으니,
다음에도 먼저 여쭤보고 합칠 것."""
import datetime
import hashlib
import hmac
import base64
import time
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st

from nav_pages._shared import get_supabase_client

NAVER_BASE_URL = "https://api.searchad.naver.com"
NAVER_REQUEST_TIMEOUT = 10

KST = ZoneInfo("Asia/Seoul")
# Streamlit Cloud 서버는 UTC로 돈다 — datetime.date.today()를 그대로 쓰면 자정 근처
# 몇 시간 동안 "오늘"이 실제 한국 날짜보다 하루 이르게 계산된다(check_ad_performance.py
# 크론이 실제로 이 버그로 데이터를 통째로 하루 놓친 적 있음, 2026-08-03). 항상 KST
# 기준으로 명시 계산한다.

BUDGET_EXHAUST_RATIO = 0.9  # 하루예산의 90% 이상 쓰면 "그날은 예산 소진"으로 봄
BUDGET_EXHAUST_DAY_RATIO = 5 / 7  # 지난주(월~일) 중 이 비율 이상 소진되면 "예산소진형" 매장
ANOMALY_IMPRESSION_MULTIPLIER = 2.0  # 이전 주 평균 대비 노출이 이만큼 튀면 이상치 후보
# 2.5로는 실제 사례(고집돌우럭 중문점 8/17주, 2.08배)를 못 잡아서 2.0으로 낮춤(2026-08-25).
# 12개 매장 9주치 데이터로 스캔해본 결과 2.0에서는 이 건 하나만 걸리고 오탐(클릭도
# 같이 늘어난 정상 증가)은 없음 — 1.6까지 낮추면 오탐이 섞이기 시작해서 2.0으로 결정.
ANOMALY_CLICK_MULTIPLIER = 1.5  # ...근데 클릭은 이만큼도 안 늘었으면 진짜 이상치로 확정
CLICK_DECLINE_THRESHOLD = 0.8  # 최근 3주 평균 클릭이 기준선의 이 비율 밑이면 "하락 추세"
BID_RATIO_HIGH = 3.0  # 시세 대비 이 배율 넘으면 "높다"고 봄
BID_RATIO_LOW = 1.5  # 시세 대비 이 배율 이하면 "차이 없음"
CUT_PCT_BUDGET_EXHAUSTED = 0.20  # 예산소진형(가장 확실한 케이스)은 조금 더 과감하게
CUT_PCT_HIGH_RATIO = 0.15  # 일반 "인하 테스트 권장" 케이스
BID_ROUND_TO = 10  # 추천가를 이 단위로 반올림 (네이버 입찰가 입력 단위에 맞춤)
RECENT_CUT_DROP_THRESHOLD = 0.20  # 직전 입찰가 인하 후 노출·클릭이 "둘 다" 이 비율
# 이상 줄었으면 순위가 밀린 걸로 보고 추가 인하 추천을 멈춘다(2026-09-07, 와인창고
# 본점류에서 노출 -36%·클릭 -35% 동반 하락 확인 — 실제 관찰치의 절반 수준인 20%를
# 기준으로 잡아 보수적으로(더 약한 신호에서도) 잡아낸다).
RAISE_STEP_PCT = 0.30  # 인하가 역효과였던 게 확인되면, 인하 전 입찰가로 한 번에
# 되돌리지 않고 그 차액의 30%만큼만 인상 추천 — 인하할 때와 같은 "조금씩 조정하고
# 지켜본다" 원칙(2026-09-07). 와인창고 본점(1400원→500원 인하)이면 500+900*0.3=770원
# 추천 — 사용자가 직접 검토하던 700~800원대와 맞아떨어진다.


@st.cache_data(ttl=600, show_spinner=False)
def fetch_store_order():
    """"주간 광고 데이터" 페이지의 매장 드롭다운과 항상 같은 순서로 보이도록,
    같은 기준(store_campaigns.display_order)으로 정렬한 매장명 목록을 그대로 쓴다."""
    client = get_supabase_client()
    res = client.table("store_campaigns").select("store_name").order("display_order").execute()
    return [r["store_name"] for r in (res.data or [])]


@st.cache_data(ttl=600, show_spinner=False)
def fetch_store_naver_accounts():
    """매장명 -> secrets.toml의 네이버 계정 섹션 키(naver_account_key). season_keywords.py
    가 이미 같은 필드로 계정을 찾는 것과 동일한 방식이다."""
    client = get_supabase_client()
    res = client.table("store_campaigns").select("store_name, naver_account_key").execute()
    return {r["store_name"]: r["naver_account_key"] for r in (res.data or [])}


def _naver_signature(timestamp, method, uri, secret_key):
    message = f"{timestamp}.{method}.{uri}"
    hash_obj = hmac.new(secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256)
    return base64.b64encode(hash_obj.digest()).decode("utf-8")


def _naver_header(method, uri, api_key, secret_key, customer_id):
    timestamp = str(int(time.time() * 1000))
    signature = _naver_signature(timestamp, method, uri, secret_key)
    return {
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": timestamp,
        "X-API-KEY": api_key,
        "X-Customer": str(customer_id),
        "X-Signature": signature,
    }


def update_adgroup_bid_live(customer_id, api_key, secret_key, adgroup_id, new_bid_amt):
    """네이버 광고그룹의 기본 입찰가(bidAmt)만 수정한다 — fields 파라미터로 그
    필드만 바꾸도록 제한해서, 다른 설정(요일/시간, 매체 등)은 건드리지 않는다."""
    uri = f"/ncc/adgroups/{adgroup_id}"
    headers = _naver_header("PUT", uri, api_key, secret_key, customer_id)
    body = {"nccAdgroupId": adgroup_id, "bidAmt": new_bid_amt}
    r = requests.put(
        f"{NAVER_BASE_URL}{uri}", params={"fields": "bidAmt"}, json=body,
        headers=headers, timeout=NAVER_REQUEST_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def append_bid_change_note(adgroup_id, avg_bid_amt, old_bid_amt, new_bid_amt):
    """입찰가를 실제로 바꾸면 "특이사항"(creative_admin_notes.note, "주간 광고 데이터"
    페이지에 그대로 보임)에 변경 기록을 한 줄 남긴다. 별도 이력 테이블을 두면 계속
    쌓이기만 해서 관리 부담이 된다는 지적(2026-08-26)이 있었고, 이미 있는 주간 메모
    칸이 매주 자연스럽게 새로 시작되니 그대로 재사용하는 게 낫다고 판단했다.

    어느 주(week_monday)에 적을지는 creative_adgroup_snapshot의 최신 주차를 쓰면 안
    된다 — check_ad_performance.py 크론이 월요일에 "지난주" 날짜로 스냅샷을 채워
    넣는 구조라(2026-08-27 확인), 이번 주 스냅샷 행 자체가 다음 주 월요일까지 없다.
    그 최신 스냅샷 주차를 그대로 쓰면, 오늘 조정한 기록이 이미 끝난 지난주 메모에
    붙어버려서 나중에 이번 주 데이터를 봐도 이 기록이 안 보이는 문제가 있었다
    (2026-08-27 지적). creative_admin_notes는 스냅샷과 별개 테이블이라 스냅샷 행이
    없어도 "오늘이 속한 이번 주" 행을 그냥 새로 만들면 된다 — 다음 주 월요일에
    스냅샷이 생기면 이미 이 메모가 그 주에 가 있는 채로 자연스럽게 이어진다.
    관리자가 이미 적어둔 메모가 있으면 절대 안 지우고 뒤에 이어붙인다."""
    today = datetime.datetime.now(KST).date()
    this_monday = (today - datetime.timedelta(days=today.weekday())).isoformat()

    client = get_supabase_client()
    res = (
        client.table("creative_admin_notes")
        .select("note")
        .eq("adgroup_id", adgroup_id)
        .eq("week_monday", this_monday)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    existing_note = (rows[0].get("note") or "") if rows else ""

    change_line = f"{today.month}.{today.day} 입찰가 {old_bid_amt:,}원 → {new_bid_amt:,}원"
    new_note = f"{existing_note} / {change_line}" if existing_note else change_line

    client.table("creative_admin_notes").upsert({
        "adgroup_id": adgroup_id,
        "week_monday": this_monday,
        "avg_bid_amt": int(avg_bid_amt),
        "note": new_note,
    }, on_conflict="adgroup_id,week_monday").execute()


def log_bid_adjustment(adgroup_id, store_name, avg_bid_amt, old_bid_amt, new_bid_amt, snapshot_week_monday):
    """creative_bid_adjustment_log에 구조화된 조정 이력을 남긴다(2026-09-07) —
    특이사항(자유 텍스트)과 달리 나중에 "조정 후 클릭/노출이 실제로 개선됐는지"
    집계 쿼리를 돌릴 수 있게 하는 게 목적이다. 클릭수 등 실적 자체는 여기 저장하지
    않는다 — creative_daily_stats에 이미 쌓이고 있으니 applied_at을 기준으로 전/후
    구간을 나중에 계산하면 된다. 이 페이지는 플레이스광고만 다루므로 ad_type은 고정.

    snapshot_week_monday는 이번에 실제로 덮어쓴 creative_adgroup_snapshot 행의
    week_monday다(2026-09-07 추가) — 크론이 스냅샷을 "지난주" 라벨로 채워 넣는
    구조라, 이번 주(예: 9월 2주차)에 조정해도 그 스냅샷 행은 "9월 1주차"로 찍혀
    있을 수 있다. applied_at(실제 조정한 날짜)만으로는 그 사실을 알 수 없어서
    따로 남긴다 — 나중에 "이 스냅샷 값이 사실 원래 수집값이 아니라 도중에
    수동으로 덮어써진 값"이라는 걸 판정 로직이 감지하는 데 쓴다."""
    client = get_supabase_client()
    client.table("creative_bid_adjustment_log").insert({
        "adgroup_id": adgroup_id,
        "store_name": store_name,
        "ad_type": "플레이스광고",
        "field_changed": "bid_amt",
        "old_value": int(old_bid_amt),
        "new_value": int(new_bid_amt),
        "avg_bid_amt": int(avg_bid_amt) if avg_bid_amt else None,
        "snapshot_week_monday": snapshot_week_monday,
    }).execute()


def apply_bid_change(store_name, adgroup_id, new_bid_amt, week_monday, old_bid_amt, avg_bid_amt):
    """추천 입찰가를 실제 네이버 계정에 반영하고, 성공하면 creative_adgroup_snapshot의
    해당 광고그룹 최신 주차 bid_amt도 같이 갱신한다 — "주간 광고 데이터" 페이지가
    다음 주 월요일 자동 수집을 기다리지 않고 바로 새 입찰가를 보여주도록. 과거 주차
    행은 실제 그 주 당시 값을 나타내는 이력이라 건드리지 않고, week_monday로 지정된
    "지금 보고 있는 최신 스냅샷" 행 하나만 고친다."""
    account_key = fetch_store_naver_accounts().get(store_name)
    if not account_key:
        return False, f"{store_name}의 네이버 계정 정보(naver_account_key)를 찾을 수 없습니다."
    naver_acct = st.secrets.get(account_key)
    if not naver_acct:
        return False, f"secrets.toml에 '{account_key}' 계정이 없습니다."

    try:
        update_adgroup_bid_live(
            naver_acct["customer_id"], naver_acct["api_key"], naver_acct["secret_key"],
            adgroup_id, new_bid_amt,
        )
    except Exception as e:
        return False, f"네이버 반영 실패: {e}"

    try:
        client = get_supabase_client()
        client.table("creative_adgroup_snapshot").update(
            {"bid_amt": new_bid_amt}
        ).eq("adgroup_id", adgroup_id).eq("week_monday", week_monday).execute()
    except Exception as e:
        # 네이버 반영은 이미 성공했으니 실패로 보고하면 안 되고, DB만 안 맞을 수
        # 있다는 걸 알려준다 — 다음 주 크론이 돌면 어차피 다시 맞춰진다.
        return True, f"⚠️ 네이버에는 반영됐지만 화면 갱신 중 오류: {e}"

    try:
        append_bid_change_note(adgroup_id, avg_bid_amt, old_bid_amt, new_bid_amt)
    except Exception:
        # 특이사항 기록은 부가 기능 — 실패해도 입찰가 자체는 이미 정상 반영됐으니
        # 사용자에게는 성공으로 보고한다.
        pass

    try:
        log_bid_adjustment(adgroup_id, store_name, avg_bid_amt, old_bid_amt, new_bid_amt, week_monday)
    except Exception:
        # 이력 기록도 부가 기능 — 실패해도 입찰가 자체는 이미 정상 반영됨.
        pass

    fetch_place_main_adgroups.clear()
    return True, None


@st.cache_data(ttl=300, show_spinner=False)
def fetch_place_main_adgroups():
    """모든 매장의 플레이스광고 대표(main) 광고그룹 중 가장 최근 주차 스냅샷만."""
    client = get_supabase_client()
    res = (
        client.table("creative_adgroup_snapshot")
        .select("*")
        .eq("ad_type", "플레이스광고")
        .eq("role", "main")
        .order("week_monday", desc=True)
        .execute()
    )
    latest = {}
    for r in res.data or []:
        latest.setdefault(r["adgroup_id"], r)
    return list(latest.values())


@st.cache_data(ttl=300, show_spinner=False)
def fetch_daily(adgroup_id, start_date, end_date):
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
    return pd.DataFrame([
        {
            "날짜": datetime.date.fromisoformat(r["stat_date"]),
            "노출수": r.get("impressions", 0),
            "클릭수": r.get("clicks", 0),
            "총비용": r.get("cost", 0),
        }
        for r in (res.data or [])
    ])


@st.cache_data(ttl=300, show_spinner=False)
def fetch_avg_bid(adgroup_id):
    """평균입찰가(동종업계 시세)는 관리자가 보통 매주 월요일(휴무면 화요일)에 수기로
    입력한다 — 그 주 값이 아직 안 들어왔다고 "미입력"으로 잘못 판정하지 않도록, 정확히
    이번 주(week_monday)가 아니라 가장 최근에 입력된 값을 그대로 쓴다."""
    client = get_supabase_client()
    res = (
        client.table("creative_admin_notes")
        .select("avg_bid_amt, week_monday")
        .eq("adgroup_id", adgroup_id)
        .order("week_monday", desc=True)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0]["avg_bid_amt"] if rows else 0


def check_budget_exhaustion(adgroup_id, daily_budget, today):
    """지난주(가장 최근에 끝난 월~일) 중 며칠이나 하루예산의 90%+ 를 썼는지.
    creative_daily_stats 자체가 매주 월요일에 "지난 한 주치"를 한 번에 채워 넣는
    구조라(2026-08-27 확인 — 크론 실행 이력상 매주 월요일 1회, 그 전날까지의 데이터를
    수집), '최근 7일 롤링'으로 계산하면 이번 주가 진행될수록 표본이 줄어(월요일엔
    거의 7일, 목요일엔 4일 정도) 판정이 요일에 따라 흔들리는 문제가 있었다. 대신
    지난주 월~일로 창을 고정하면 이번 주 내내 항상 같은 꽉 찬 7일 데이터로 계산된다."""
    this_monday = today - datetime.timedelta(days=today.weekday())
    start = this_monday - datetime.timedelta(days=7)
    end = this_monday - datetime.timedelta(days=1)
    df = fetch_daily(adgroup_id, start, end)
    if df.empty or not daily_budget:
        return 0, 0, False
    exhausted_days = int((df["총비용"] >= daily_budget * BUDGET_EXHAUST_RATIO).sum())
    total_days = len(df)
    # total_days가 고정 7이 아니라 실제 수집된 일수라서, 크론 지연 등으로 데이터가
    # 3~4일치만 있으면 그 며칠이 우연히 다 소진이어도 비율이 쉽게 기준을 넘어
    # "예산소진형"으로 확정돼버린다(2026-08-25 검토). 최소 5일치는 있어야 판단한다.
    is_exhausted = total_days >= 5 and (exhausted_days / total_days) >= BUDGET_EXHAUST_DAY_RATIO
    return exhausted_days, total_days, is_exhausted


def check_click_trend(adgroup_id, today):
    """최근 9주 일별 데이터를 주 단위로 묶어서, 노출만 튄 이상치 주를 걸러내고
    최근 3주 클릭수가 그 이전 기준선 대비 꾸준히 하락했는지 판단한다."""
    start = today - datetime.timedelta(weeks=9)
    end = today - datetime.timedelta(days=1)
    df = fetch_daily(adgroup_id, start, end)
    if df.empty:
        return {"declining": False, "anomaly_weeks": 0, "note": "데이터 부족"}

    df = df.copy()
    df["주시작"] = df["날짜"].apply(lambda d: d - datetime.timedelta(days=d.weekday()))
    weekly = df.groupby("주시작", as_index=False)[["노출수", "클릭수"]].sum().sort_values("주시작").reset_index(drop=True)

    # prior를 "지금까지의 모든 이전 주"로 잡으면, 이상 노출이 여러 주 연속으로
    # 이어질 때 기준선(평균) 자체가 그 뻥튀기를 따라 같이 올라가버려서 2주차,
    # 3주차는 튄 폭이 점점 작게 계산되고 결국 못 잡을 수 있다(2026-08-25 지적).
    # 그래서 기준선은 "이상치로 확정되지 않은 주"만 누적해서 쓴다 — 이상 노출이
    # 몇 주가 이어지든 기준선은 그 직전의 정상 구간에 계속 고정된다.
    is_anomaly = [False] * len(weekly)
    clean_prior_impr = []
    clean_prior_clk = []
    for i in range(len(weekly)):
        cur = weekly.iloc[i]
        if len(clean_prior_impr) < 2:
            clean_prior_impr.append(cur["노출수"])
            clean_prior_clk.append(cur["클릭수"])
            continue
        avg_impr = sum(clean_prior_impr) / len(clean_prior_impr)
        avg_clk = sum(clean_prior_clk) / len(clean_prior_clk)
        impr_spiked = avg_impr > 0 and cur["노출수"] > avg_impr * ANOMALY_IMPRESSION_MULTIPLIER
        click_flat = avg_clk == 0 or cur["클릭수"] < avg_clk * ANOMALY_CLICK_MULTIPLIER
        if impr_spiked and click_flat:
            is_anomaly[i] = True
        else:
            clean_prior_impr.append(cur["노출수"])
            clean_prior_clk.append(cur["클릭수"])
    weekly["이상치"] = is_anomaly

    clean = weekly[~weekly["이상치"]]
    anomaly_count = int(weekly["이상치"].sum())

    if len(clean) < 5:
        return {"declining": False, "anomaly_weeks": anomaly_count, "note": "정상 주차 데이터 부족"}

    baseline = clean.iloc[:-3]["클릭수"].mean()
    recent = clean.iloc[-3:]["클릭수"].mean()
    declining = baseline > 0 and recent < baseline * CLICK_DECLINE_THRESHOLD
    note = f"최근 3주 평균 클릭 {recent:.0f} / 기준선 {baseline:.0f}"
    return {"declining": declining, "anomaly_weeks": anomaly_count, "note": note}


def check_recent_cut_backfired(adgroup_id, today):
    """이 매장의 가장 최근 입찰가 인하 이후, 노출·클릭이 "둘 다" 확실히 줄었으면
    그 인하가 역효과였던 걸로 보고 (True, 사유, 인하 전 입찰가)를 돌려준다 —
    판단 로직이 같은 매장에 또 인하를 추천하지 않고, 오히려 일부 되돌리는(인상)
    쪽을 제안하도록 하기 위한 안전장치다(2026-09-07). 와인창고
    본점에서 발견된 패턴 대응: 검색량이 적은 키워드는 입찰가를 내리면 순위가
    "더보기" 밖으로 튕겨나가 노출 자체가 확 줄 수 있는데, 배율/예산 신호만 보는
    기존 로직은 이걸 전혀 모르고 계속 인하를 추천했다. 매장명을 코드에 박아두는
    대신 creative_bid_adjustment_log(실제 조정 이력) + creative_daily_stats(실제
    노출/클릭)를 직접 비교해서 판단하므로, 같은 패턴을 보이는 다른 매장에도
    자동으로 적용된다."""
    client = get_supabase_client()
    res = (
        client.table("creative_bid_adjustment_log")
        .select("applied_at, old_value")
        .eq("adgroup_id", adgroup_id)
        .eq("field_changed", "bid_amt")
        .order("applied_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        return False, None, None

    old_bid_amt = rows[0]["old_value"]
    applied_raw = rows[0]["applied_at"]
    applied_at = datetime.datetime.fromisoformat(applied_raw.replace("Z", "+00:00")).date()
    before_start = applied_at - datetime.timedelta(days=7)

    # "이전" 구간 도중에 예산 등 다른 조정이 끼어있으면 그 이후로만 기준선을
    # 다시 잡는다 — 안 그러면 이번 입찰가 인하 효과에 그 전 조정(예: 예산 반토막)
    # 효과까지 섞여서 하락폭이 과장된다(2026-09-07 지적 — 와인가게바나나 중문점·
    # 와인창고 동문시장점이 8/27에 예산도 반으로 줄여서 실제로 이 문제가 있었다).
    other_res = (
        client.table("creative_bid_adjustment_log")
        .select("applied_at")
        .eq("adgroup_id", adgroup_id)
        .gte("applied_at", before_start.isoformat())
        .lt("applied_at", applied_raw)
        .order("applied_at", desc=True)
        .limit(1)
        .execute()
    )
    other_rows = other_res.data or []
    if other_rows:
        other_at = datetime.datetime.fromisoformat(other_rows[0]["applied_at"].replace("Z", "+00:00")).date()
        before_start = max(before_start, other_at)

    before_df = fetch_daily(adgroup_id, before_start, applied_at - datetime.timedelta(days=1))
    after_end = min(today - datetime.timedelta(days=1), applied_at + datetime.timedelta(days=6))
    if after_end < applied_at:
        return False, None, None  # 조정 당일이라 이후 데이터가 아직 없음
    after_df = fetch_daily(adgroup_id, applied_at, after_end)

    # 하루이틀 노이즈로 오판하지 않게 최소 3일치는 있어야 판단한다.
    if len(before_df) < 3 or len(after_df) < 3:
        return False, None, None

    before_impr = before_df["노출수"].sum() / len(before_df)
    before_clk = before_df["클릭수"].sum() / len(before_df)
    after_impr = after_df["노출수"].sum() / len(after_df)
    after_clk = after_df["클릭수"].sum() / len(after_df)
    if before_impr <= 0 or before_clk <= 0:
        return False, None, None

    impr_drop = 1 - (after_impr / before_impr)
    clk_drop = 1 - (after_clk / before_clk)
    if impr_drop >= RECENT_CUT_DROP_THRESHOLD and clk_drop >= RECENT_CUT_DROP_THRESHOLD:
        reason = (
            f"직전 조정({applied_at.month}.{applied_at.day}) 후 노출 {impr_drop*100:.0f}%·"
            f"클릭 {clk_drop*100:.0f}% 동반 감소 — 순위 밀림 의심"
        )
        return True, reason, old_bid_amt
    return False, None, None


def check_snapshot_already_adjusted(adgroup_id, snapshot_week_monday):
    """지금 보고 있는 스냅샷(week_monday)의 bid_amt가 이미 한 번 수동으로 조정된
    값인지 확인한다(2026-09-07) — check_ad_performance.py 크론은 스냅샷을 "지난주"
    라벨로 채워 넣는데(예: 9월 2주차에 조정해도 그 시점의 최신 스냅샷은 "9월 1주차"
    라벨을 달고 있어서, 그 행이 덮어써짐), 그러면 "9월 1주차 데이터"라는 이름이
    붙은 값이 사실은 9월 2주차에 손댄 값이 된다. 지금 판정에는 문제가 없지만(현재
    입찰가는 어차피 최신 실제 값이라 맞게 계산됨), 나중에 이 주차를 복기할 때
    헷갈릴 수 있어 경고 메모를 남긴다."""
    client = get_supabase_client()
    res = (
        client.table("creative_bid_adjustment_log")
        .select("applied_at, old_value, new_value")
        .eq("adgroup_id", adgroup_id)
        .eq("field_changed", "bid_amt")
        .eq("snapshot_week_monday", snapshot_week_monday)
        .order("applied_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        return None
    row = rows[0]
    applied_at = datetime.datetime.fromisoformat(row["applied_at"].replace("Z", "+00:00")).date()
    direction = "인상" if row["new_value"] > row["old_value"] else "인하"
    return f"{applied_at.month}.{applied_at.day} 입찰가 {row['old_value']:,}원 → {row['new_value']:,}원 {direction}"


def suggest_bid(bid_amt, avg_bid, cut_pct):
    """시세까지 한 번에 내리지 않고 소폭만 내린다 — 조정 후 지켜보고 다음 판단에
    반영하는 전제라서, 한 단계 테스트용 값만 계산한다. 시세보다 낮게는 추천하지
    않는다(그 밑으로 내려가면 순위 경쟁에서 불리해질 수 있어 근거가 약해짐)."""
    target = bid_amt * (1 - cut_pct)
    if avg_bid:
        target = max(target, avg_bid)
    target = max(target, 50)  # 네이버 플레이스광고 최저 입찰가
    return int(round(target / BID_ROUND_TO) * BID_ROUND_TO)


VERDICT_BADGE_CLASS = {
    "인하 최우선": "pill-bid-strong",
    "인하 테스트 권장": "pill-bid-mild",
    "보류": "pill-bid-hold",
    "조정 불필요": "pill-bid-neutral",
    "수동 검토": "pill-bid-review",
    "인상 검토": "pill-bid-raise",
    "평균입찰가 미입력": "pill-bid-nodata",
}
TABLE_BORDER = "#E3E6EB"
TABLE_HEADER_BG = "#EEF3FA"


def render_verdict_badge(verdict):
    cls = VERDICT_BADGE_CLASS.get(verdict, "pill-bid-neutral")
    return f'<span class="status-pill {cls}">{verdict}</span>'


def render_results_table(rows):
    """다른 페이지들처럼(place_rank.py 등) 배지+표 톤으로 통일 — st.dataframe(기본
    스프레드시트 느낌)은 판정을 색으로 구분할 수 없어서, 이 페이지만 HTML 표로
    직접 그린다(2026-08-25, 디자인이 조잡해 보인다는 피드백)."""
    # 매장명 → 현재입찰가 → 평균입찰가 → 차이 → 예산소진 → 비고(구 "근거") → 판정
    # 순서로 바꿔달라는 요청(2026-08-25) — 판정(배지)을 맨 뒤로 보내고 숫자 비교값을
    # 앞에 몰아서 한눈에 비교하기 쉽게. 추천입찰가는 아래 "조정 후보 매장" 카드에서
    # 직접 고쳐 넣을 수 있어서 이 표에서는 뺐다.
    cols = ["매장", "현재입찰가", "평균입찰가", "차이", "예산소진", "비고", "판정"]
    html = (
        '<table style="width:100%; border-collapse:collapse; text-align:center; '
        f'color:#16181D; border:1px solid {TABLE_BORDER};">'
    )
    html += f'<thead><tr style="background-color:{TABLE_HEADER_BG}; border-bottom:2px solid {TABLE_BORDER}; font-weight:700;">'
    for col in cols:
        html += f'<th style="padding:10px 8px; border:1px solid {TABLE_BORDER}; font-size:14px;">{col}</th>'
    html += '</tr></thead><tbody>'
    for r in rows:
        html += f'<tr style="background-color:#FFFFFF; border-bottom:1px solid {TABLE_BORDER};">'
        html += (
            f'<td style="padding:9px 8px; border:1px solid {TABLE_BORDER}; font-size:14px; '
            f'font-weight:600; text-align:left;">{r["매장"]}</td>'
        )
        for col in ["현재입찰가", "평균입찰가", "차이", "예산소진"]:
            html += f'<td style="padding:9px 8px; border:1px solid {TABLE_BORDER}; font-size:14px; white-space:nowrap;">{r[col]}</td>'
        html += (
            f'<td style="padding:9px 8px; border:1px solid {TABLE_BORDER}; font-size:12.5px; '
            f'color:#5B6472; text-align:left;">{r["비고"]}</td>'
        )
        html += f'<td style="padding:9px 8px; border:1px solid {TABLE_BORDER}; white-space:nowrap;">{render_verdict_badge(r["판정"])}</td>'
        html += '</tr>'
    html += '</tbody></table>'
    return html


def judge(adgroup_id, bid_amt, daily_budget, avg_bid, today, snapshot_week_monday=None):
    exhausted_days, total_days, budget_exhausted = check_budget_exhaustion(
        adgroup_id=adgroup_id, daily_budget=daily_budget, today=today
    )
    trend = check_click_trend(adgroup_id, today)
    ratio = (bid_amt / avg_bid) if avg_bid else None

    if avg_bid == 0:
        return {
            "verdict": "평균입찰가 미입력", "reason": "비교할 시세 값이 없어 판단 불가",
            "ratio": None, "suggested_bid": None, "exhausted_days": exhausted_days, "total_days": total_days,
            "anomaly_weeks": trend["anomaly_weeks"], "trend_note": trend["note"], "already_adjusted_note": None,
        }

    # 판정은 배지 색으로 구분하고(이모지 없이) — 이모지를 줄여달라는 요청(2026-08-25).
    # "인상 검토"는 시세보다 낮은데 노출/클릭이 빠지는 일반 케이스를 감지하는 게
    # 아니라, 아래 backfired 체크에서 "직전 인하가 실제로 역효과였다"고 실측
    # 확인됐을 때만 나온다(2026-09-07) — 배율/예산만 보고 올리라고 하는 판정은
    # 없다(시세보다 낮다고 무작정 올리면 근거가 약함).
    #
    # 근거는 "판정을 결정한 신호 하나"가 아니라, 해당되는 신호를 전부 짧은 태그로
    # 나열한다(2026-08-25, 사용자 피드백 — 예산 소진 하나만 근거로 뜨면, 사실은
    # 시세 대비 배율도 같이 높은 경우인데 신뢰도가 떨어져 보인다는 지적). 숫자
    # 자체(정확한 차액, 며칠)는 옆의 차이/예산소진 컬럼에 이미 있으니 여기선 카테고리만
    # 짧게 표시해서 셀 안에서 안 넘치게 한다.
    tags = []
    if budget_exhausted:
        tags.append("예산 소진")
    if ratio > BID_RATIO_HIGH:
        tags.append("시세 매우 높음")
    elif ratio > BID_RATIO_LOW:
        tags.append("시세 높음")
    else:
        tags.append("시세 비슷")
    if trend["declining"]:
        tags.append("클릭 하락")
    else:
        tags.append("클릭 안정")
    # 이상노출 제외 자체(클릭 추세 계산에서 뻥튀기된 주 빼는 로직)는 그대로 두되,
    # "이상노출 N주 제외" 태그는 비고에 더 안 보여준다(2026-08-27 요청) — 내부
    # 판단 근거일 뿐 사용자에게 굳이 노출할 필요는 없다고 판단.

    suggested_bid = None
    if budget_exhausted and ratio > BID_RATIO_LOW:
        verdict = "인하 최우선"
        suggested_bid = suggest_bid(bid_amt, avg_bid, CUT_PCT_BUDGET_EXHAUSTED)
    elif ratio > BID_RATIO_HIGH and not trend["declining"]:
        verdict = "인하 테스트 권장"
        suggested_bid = suggest_bid(bid_amt, avg_bid, CUT_PCT_HIGH_RATIO)
    elif trend["declining"]:
        verdict = "보류"
    elif ratio <= BID_RATIO_LOW:
        verdict = "조정 불필요"
    else:
        verdict = "수동 검토"

    # 다른 신호가 뭐라고 하든, 직전 인하가 이미 역효과였던 게 확인되면 무조건
    # 덮어쓴다 — 안 그러면 순위 밀림을 전혀 모르는 배율/예산 신호가 같은 매장에
    # 계속 추가 인하를 추천하게 된다(2026-09-07). 그냥 "보류"로 멈추기보다, 인하
    # 전 값의 일부만큼 되돌리는 인상을 적극적으로 제안한다 — 이미 실측으로 역효과가
    # 확인된 상황이라 "일단 지켜보자"보다 "일부 되돌려보자"가 더 근거 있는 액션이다.
    backfired, backfired_reason, pre_cut_bid_amt = check_recent_cut_backfired(adgroup_id, today)
    if backfired:
        if pre_cut_bid_amt and pre_cut_bid_amt > bid_amt:
            verdict = "인상 검토"
            raise_target = bid_amt + (pre_cut_bid_amt - bid_amt) * RAISE_STEP_PCT
            suggested_bid = int(round(raise_target / BID_ROUND_TO) * BID_ROUND_TO)
        else:
            verdict = "보류"
            suggested_bid = None
        tags.append(backfired_reason)

    # 지금 보고 있는 스냅샷 자체가 이미 도중에 수동으로 덮어써진 값이면, 라벨
    # 주차와 실제 조정 시점이 다르다는 걸 알려준다(2026-09-07 요청). 위쪽 진단
    # 표 "비고"에는 안 넣고, 아래 "입찰가 조정" 카드의 판정 배지 옆에만 따로
    # 보여준다(2026-09-07 재요청) — 실제로 다시 조정 버튼을 누를지 말지 결정하는
    # 그 자리에서만 필요한 경고라서다.
    already_adjusted_note = None
    if snapshot_week_monday:
        already_adjusted_note = check_snapshot_already_adjusted(adgroup_id, snapshot_week_monday)

    reason = " · ".join(tags)

    return {
        "verdict": verdict, "reason": reason, "ratio": ratio, "suggested_bid": suggested_bid,
        "exhausted_days": exhausted_days, "total_days": total_days,
        "anomaly_weeks": trend["anomaly_weeks"], "trend_note": trend["note"],
        "already_adjusted_note": already_adjusted_note,
    }


st.subheader("입찰가 조정 (플레이스광고)")

if not st.session_state.get("is_admin"):
    st.info("🔒 입찰가 실제 반영은 관리자 모드에서만 가능합니다. 판정 표는 그대로 볼 수 있어요.")

today = datetime.datetime.now(KST).date()
adgroups = fetch_place_main_adgroups()

if not adgroups:
    st.info("플레이스광고 데이터가 없습니다.")
else:
    rows = []
    actionable = []  # 추천 입찰가가 있는(=버튼이 필요한) 매장만 따로 모은다
    store_order_map = {name: i for i, name in enumerate(fetch_store_order())}

    for ag in adgroups:
        avg_bid = fetch_avg_bid(ag["adgroup_id"])
        bid_amt = ag.get("bid_amt", 0) or 0
        daily_budget = ag.get("daily_budget", 0) or 0

        result = judge(ag["adgroup_id"], bid_amt, daily_budget, avg_bid, today, ag["week_monday"])
        rows.append({
            "매장": ag["account_key"],
            "판정": result["verdict"],
            "비고": result["reason"],
            "현재입찰가": f"{bid_amt:,}원",
            "평균입찰가": f"{avg_bid:,}원" if avg_bid else "-",
            "차이": f"{bid_amt - avg_bid:+,}원" if avg_bid else "-",
            "예산소진": f"{result['exhausted_days']}/{result['total_days']}일",
            "_순서": store_order_map.get(ag["account_key"], 999),
        })
        if result["suggested_bid"]:
            actionable.append({
                "store_name": ag["account_key"],
                "adgroup_id": ag["adgroup_id"],
                "week_monday": ag["week_monday"],
                "verdict": result["verdict"],
                "bid_amt": bid_amt,
                "avg_bid": avg_bid,
                "suggested_bid": result["suggested_bid"],
                "already_adjusted_note": result["already_adjusted_note"],
                "_순서": store_order_map.get(ag["account_key"], 999),
            })

    rows.sort(key=lambda r: r["_순서"])
    actionable.sort(key=lambda r: r["_순서"])

    with st.container(border=True, key="section_bid_judgment"):
        st.markdown("#### 입찰가 진단")
        st.caption(
            "현재입찰가 vs 평균입찰가(시세) + 예산 소진/클릭 추세를 같이 봐서 인하 여지를 판단합니다."
        )
        st.markdown(render_results_table(rows), unsafe_allow_html=True)
        st.caption(
            f"기준: 지난주(월~일) 7일 중 {BUDGET_EXHAUST_DAY_RATIO*7:.0f}일 이상 하루예산의 "
            f"{BUDGET_EXHAUST_RATIO*100:.0f}%를 넘게 쓰면 '예산 소진'으로 봅니다. 최근 3주 클릭이 "
            f"그 이전보다 {(1-CLICK_DECLINE_THRESHOLD)*100:.0f}% 넘게 줄면 '클릭 하락'으로 봅니다. "
            f"입찰가가 평균(시세)의 {BID_RATIO_HIGH:g}배를 넘으면 '시세 매우 높음', "
            f"{BID_RATIO_LOW:g}배 이하면 시세와 비슷한 걸로 판단합니다."
        )

    # ==========================================
    # [조정 후보 매장 — 개별 적용] HTML 표(위)는 실제 위젯을 못 담아서, 추천
    # 입찰가가 있는 매장만 따로 카드로 뽑아 매장별 적용 버튼을 둔다. 관리자
    # 모드에서만 노출 — 실제 광고비에 영향을 주는 쓰기 작업이라 다른 페이지의
    # 관리자 전용 기능들과 동일한 기준을 따른다.
    # ==========================================
    if actionable and st.session_state.get("is_admin"):
        with st.container(border=True, key="section_bid_actionable"):
            st.markdown("#### 입찰가 조정")
            st.caption(
                "매장별로 확인 후 적용하세요. 한 번에 여러 매장을 일괄 적용하는 기능은 없습니다. "
                "입찰가 칸은 추천값이 기본으로 들어있고, 직접 다른 값으로 고쳐서 적용할 수도 있습니다."
            )

            @st.dialog("입찰가 변경 확인")
            def _confirm_bid_apply(item):
                st.markdown(
                    f"**{item['store_name']}** 플레이스광고 입찰가를 "
                    f"**{item['bid_amt']:,}원 → {item['suggested_bid']:,}원**으로 변경하시겠습니까?"
                )
                st.caption(f"판정: {item['verdict']} · 실제 네이버 광고 계정에 바로 반영됩니다.")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("예", key="confirm_yes", width="stretch"):
                        ok, err = apply_bid_change(
                            item["store_name"], item["adgroup_id"], item["suggested_bid"], item["week_monday"],
                            item["bid_amt"], item["avg_bid"],
                        )
                        st.session_state["bid_apply_result"] = (
                            f"✅ {item['store_name']} 입찰가를 {item['suggested_bid']:,}원으로 변경했습니다."
                            if ok and not err else
                            (f"{'✅' if ok else '❌'} {item['store_name']}: {err}")
                        )
                        st.session_state.pop("bid_apply_pending", None)
                        st.rerun()
                with col_no:
                    if st.button("아니오", key="confirm_no", width="stretch"):
                        st.session_state.pop("bid_apply_pending", None)
                        st.rerun()

            for item in actionable:
                with st.container(key=f"bid_card_{item['adgroup_id']}"):
                    col_store, col_input, col_verdict, col_btn = st.columns(
                        [2.2, 1.8, 1.6, 1], vertical_alignment="center",
                    )
                    with col_store:
                        st.markdown(f"**{item['store_name']}**")
                        st.markdown(
                            f'<span class="bid-change-text">현재 {item["bid_amt"]:,}원 · '
                            f'평균 {item["avg_bid"]:,}원</span>',
                            unsafe_allow_html=True,
                        )
                    with col_input:
                        # 추천 입찰가를 기본값으로 채워두되, 직접 원하는 값으로 고쳐서
                        # 적용할 수 있게 해달라는 요청(2026-08-25). key에 suggested_bid를
                        # 같이 넣어둔다 — key만 고정이면 st.number_input의 value=는 최초
                        # 렌더링 이후로는 무시되고 session_state 값을 그대로 쓰기 때문에,
                        # 세션 중간에 평균입찰가가 바뀌어 추천값이 재계산돼도 입력칸은
                        # 예전 추천값에 멈춰 있는 버그가 있었다(2026-08-25 재검토로 발견).
                        # 추천값이 바뀌면 key도 바뀌어 새 기본값으로 다시 렌더링된다.
                        target_bid = st.number_input(
                            "적용할 입찰가", min_value=50, step=BID_ROUND_TO,
                            value=item["suggested_bid"],
                            key=f"bid_input_{item['adgroup_id']}_{item['suggested_bid']}",
                            label_visibility="collapsed",
                        )
                    with col_verdict:
                        badge_html = render_verdict_badge(item["verdict"])
                        if item.get("already_adjusted_note"):
                            badge_html += (
                                f' <span class="bid-change-text">{item["already_adjusted_note"]}</span>'
                            )
                        st.markdown(badge_html, unsafe_allow_html=True)
                    with col_btn:
                        if st.button("적용", key=f"apply_bid_{item['adgroup_id']}", width="stretch"):
                            st.session_state["bid_apply_pending"] = {**item, "suggested_bid": int(target_bid)}

            pending = st.session_state.get("bid_apply_pending")
            if pending:
                _confirm_bid_apply(pending)

            result_msg = st.session_state.pop("bid_apply_result", None)
            if result_msg:
                st.info(result_msg)
