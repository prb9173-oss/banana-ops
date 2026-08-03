import datetime
import hashlib
import hmac
import base64
import logging
import os
import time

import requests

from supabase import create_client

REQUEST_TIMEOUT = 10
BASE_URL = "https://api.searchad.naver.com"

# GitHub Actions 러너는 UTC로 돈다. 이 크론은 매주 월요일 08:00 KST(=일요일 23:00
# UTC)에 실행되는데, datetime.date.today()를 그대로 쓰면 그 시각엔 UTC 기준 날짜가
# 아직 "일요일"이라 "지난주"를 하루(사실상 일주일) 앞당겨 계산해버린다 — 2026-08-03
# 첫 실행에서 실제로 이 버그로 그 주(7월 5주차) 데이터가 통째로 누락됐다. 한국시간
# 기준 날짜로 고정해서 러너의 타임존과 무관하게 항상 올바른 주를 계산하게 한다.
KST = datetime.timezone(datetime.timedelta(hours=9))

AD_TYPE_CAMPAIGN_TP = {
    "플레이스광고": ["PLACE"],
    "파워링크광고": ["WEB_SITE"],
    "파워컨텐츠광고": ["CONTENTS", "POWER_CONTENT", "POWER_CONTENTS", "INFORMATION"],
}

# 캠페인 이름 규칙: "{매장명} {이 라벨}" (예: "선물가게바나나 함덕점 파워컨텐츠") —
# 사용자가 네이버 광고관리센터에서 실제로 이렇게 이름을 맞춰뒀다(2026-07-31 확인).
AD_TYPE_LABEL = {
    "플레이스광고": "플레이스",
    "파워링크광고": "파워링크",
    "파워컨텐츠광고": "파워컨텐츠",
}


def get_supabase_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        import toml
        sb = toml.load(".streamlit/secrets.toml")["supabase"]
        url, key = sb["url"], sb["key"]
    return create_client(url, key)


def get_naver_accounts():
    """.streamlit/secrets.toml에서 customer_id/api_key/secret_key를 가진 섹션을 전부
    찾는다 — 매장이 아니라 "네이버 광고 계정"(고집돌우럭 중문점 계정 하나에 함덕점·
    와인창고 함덕점까지 3개 매장이 같이 걸려있는 식) 기준이라, 계정별 API 인증 정보를
    찾을 때만 쓴다. 실제 "몇 개 매장이 있는지"는 fetch_stores()의 store_campaigns를
    따른다 — 2026-07-31에 계정 기준으로 매장을 순회하다가 계정 하나에 여러 매장이
    묶인 경우 1개만 보이고 나머지가 통째로 누락되는 버그를 발견해 이렇게 분리했다."""
    import toml
    secrets = toml.load(".streamlit/secrets.toml")
    accounts = {}
    for key, section in secrets.items():
        if isinstance(section, dict) and {"customer_id", "api_key", "secret_key"} <= section.keys():
            accounts[key] = section
    return accounts


def fetch_stores(client):
    """store_campaigns(place_rank.py 등 이미 이 앱 전체가 쓰는 매장 마스터 테이블)에서
    매장 목록을 가져온다. 한 계정(naver_account_key)에 매장이 여러 개 묶여 있을 수
    있으므로, 광고 데이터 수집은 반드시 이 매장 단위로 순회해야 한다."""
    res = client.table("store_campaigns").select("*").order("display_order").execute()
    return res.data or []


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


def fetch_first_adgroup(customer_id, api_key, secret_key, ad_type, store_name):
    """이 매장·광고유형의 캠페인을 이름으로 정확히 찾는다 — "{매장명} {라벨}"
    (예: "고집돌우럭 함덕점 플레이스"). 2026-07-31 이전에는 계정 안의 해당 유형
    캠페인 중 아무거나(API 응답 순서상 첫 번째)를 골랐는데, 계정 하나에 매장이 여러
    개 묶여 있으면(예: "고집돌우럭 중문점" 계정에 중문점·함덕점·와인창고 함덕점 3개
    매장의 플레이스 캠페인이 다 있음) 실제로는 매번 같은 매장 하나만 보이고 나머지
    2개는 화면에 아예 나타나지 않는 버그였다. 사용자가 네이버 광고관리센터에서
    캠페인 이름을 "매장명 + 유형"으로 통일해뒀으므로, 이름 매칭이 계정-매장 다대다
    관계를 정확히 풀어준다.

    그 캠페인 안에서, 캠페인명과 완전히 같은 이름의 광고그룹을 "대표"로 삼는다 —
    예를 들어 "보름숲 파워링크" 캠페인 안에는 "보름숲 파워링크"(본업)와
    "보름숲 통대관"(대관 부업) 두 광고그룹이 있는데, 앞의 것만 대표이고 뒤의 것은
    부가(extra)로 따로 돌려준다. 수동으로 꺼둔(userLock=true) 광고그룹은 대표든
    부가든 제외한다 — 단, "예산 소진으로 일시중지"(status=PAUSED,
    statusReason=GROUP_LIMITED_BY_BUDGET)는 정상적인 운영 중 상태라 userLock이
    아니면 그대로 포함한다(2026-07-31에 이 둘을 혼동해서 정상 데이터를 문제처럼
    오판한 적이 있음 — status가 아니라 userLock으로만 판단할 것)."""
    campaigns, err = _get("/ncc/campaigns", api_key, secret_key, customer_id)
    if err:
        return None, [], err
    target_types = AD_TYPE_CAMPAIGN_TP[ad_type]
    target_name = f"{store_name} {AD_TYPE_LABEL[ad_type]}"
    campaign = next(
        (c for c in campaigns if c.get("campaignTp") in target_types and c.get("name") == target_name),
        None,
    )
    if not campaign:
        return None, [], None
    adgroups, err = _get("/ncc/adgroups", api_key, secret_key, customer_id, {"nccCampaignId": campaign["nccCampaignId"]})
    if err:
        return None, [], err
    if not adgroups:
        return None, [], None
    not_locked = [a for a in adgroups if not a.get("userLock", False)]
    pool = not_locked or adgroups
    main_matches = [a for a in pool if a.get("name") == target_name]
    main = main_matches[0] if main_matches else pool[0]
    extras = [a for a in pool if a is not main]
    return main, extras, None


def fetch_daily_stats(api_key, secret_key, customer_id, adgroup_id, start_date, end_date):
    params = {
        'id': adgroup_id,
        'fields': '["impCnt","clkCnt","salesAmt"]',
        'timeRange': f'{{"since":"{start_date.strftime("%Y-%m-%d")}","until":"{end_date.strftime("%Y-%m-%d")}"}}',
        'timeIncrement': '1',
    }
    data, err = _get("/stats", api_key, secret_key, customer_id, params)
    if err:
        return [], err
    rows = []
    if data and 'data' in data:
        expected_days = (end_date - start_date).days + 1
        for i, stat in enumerate(data['data']):
            if i >= expected_days:
                break
            rows.append({
                "stat_date": (start_date + datetime.timedelta(days=i)).isoformat(),
                "impressions": int(stat.get('impCnt', 0)),
                "clicks": int(stat.get('clkCnt', 0)),
                "cost": int(stat.get('salesAmt', 0)),
            })
    return rows, None


def fetch_top_keywords_auto(api_key, secret_key, customer_id, adgroup_id, start_date, end_date):
    """파워링크/파워컨텐츠만 호출 — 플레이스광고는 API가 기간 조회를 지원하지 않아
    관리자가 화면에서 직접 입력하므로 여기서는 아예 건드리지 않는다."""
    keywords, err = _get("/ncc/keywords", api_key, secret_key, customer_id, {"nccAdgroupId": adgroup_id})
    if err or not keywords:
        return [], err
    kw_map = {k.get('nccKeywordId'): k.get('keyword') for k in keywords}
    kw_ids = list(kw_map.keys())

    stats = {}
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
            stats[kw_id] = {
                "keyword": kw_map.get(kw_id, "알 수 없는 키워드"),
                "impressions": int(stat.get('impCnt', 0)),
                "clicks": int(stat.get('clkCnt', 0)),
            }
    ranked = sorted(stats.values(), key=lambda r: r["clicks"], reverse=True)
    return ranked[:10], None


def upsert_adgroup_snapshot(client, store_name, ad_type, role, ag, week_monday):
    # "account_key" 컬럼명은 그대로 두되(스키마 변경 없이), 이제 네이버 광고 계정이
    # 아니라 매장명을 저장한다 — 계정 하나에 매장이 여러 개 묶일 수 있어 계정 단위로는
    # 구분이 안 됐던 문제를 매장 단위로 바꾸면서 값의 의미만 바뀌었다(2026-07-31).
    client.table("creative_adgroup_snapshot").upsert({
        "account_key": store_name,
        "ad_type": ad_type,
        "adgroup_id": ag["nccAdgroupId"],
        "adgroup_name": ag.get("name"),
        "role": role,
        "week_monday": week_monday.isoformat(),
        "bid_amt": ag.get("bidAmt", 0),
        "daily_budget": ag.get("dailyBudget", 0),
    }, on_conflict="adgroup_id,week_monday").execute()


def upsert_daily_stats(client, adgroup_id, rows):
    if not rows:
        return
    for row in rows:
        row["adgroup_id"] = adgroup_id
    client.table("creative_daily_stats").upsert(rows, on_conflict="adgroup_id,stat_date").execute()


def replace_top_keywords(client, adgroup_id, week_monday, keyword_rows):
    client.table("creative_top_keywords") \
        .delete().eq("adgroup_id", adgroup_id).eq("week_monday", week_monday.isoformat()).execute()
    if not keyword_rows:
        return
    payload = [
        {
            "adgroup_id": adgroup_id,
            "week_monday": week_monday.isoformat(),
            "display_order": i,
            "keyword": row["keyword"],
            "impressions": row["impressions"],
            "clicks": row["clicks"],
        }
        for i, row in enumerate(keyword_rows)
    ]
    client.table("creative_top_keywords").insert(payload).execute()


def process_adgroup(client, store_name, ad_type, role, ag, week_monday, week_sunday, daily_start, api_key, secret_key, customer_id):
    adgroup_id = ag["nccAdgroupId"]
    upsert_adgroup_snapshot(client, store_name, ad_type, role, ag, week_monday)

    daily_rows, err = fetch_daily_stats(api_key, secret_key, customer_id, adgroup_id, daily_start, week_sunday)
    if err:
        logging.warning("daily stats 실패 %s/%s: %s", store_name, adgroup_id, err)
    else:
        upsert_daily_stats(client, adgroup_id, daily_rows)

    if ad_type != "플레이스광고":
        kw_rows, err = fetch_top_keywords_auto(api_key, secret_key, customer_id, adgroup_id, week_monday, week_sunday)
        if err:
            logging.warning("top keywords 실패 %s/%s: %s", store_name, adgroup_id, err)
        else:
            replace_top_keywords(client, adgroup_id, week_monday, kw_rows)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    client = get_supabase_client()
    accounts = get_naver_accounts()
    stores = fetch_stores(client)
    logging.info("대상 매장 %d개 (계정 %d개에 분산)", len(stores), len(accounts))

    today = datetime.datetime.now(KST).date()
    this_monday = today - datetime.timedelta(days=today.weekday())
    week_monday = this_monday - datetime.timedelta(days=7)  # 지난 한 주(월~일)
    week_sunday = week_monday + datetime.timedelta(days=6)
    daily_start = week_monday - datetime.timedelta(weeks=3)  # 4주 표를 위한 롤링 시작점

    for store in stores:
        store_name = store["store_name"]
        account_key = store["naver_account_key"]
        section = accounts.get(account_key)
        if not section:
            logging.warning("%s: 계정 '%s'을 secrets.toml에서 못 찾음", store_name, account_key)
            continue
        customer_id, api_key, secret_key = section["customer_id"], section["api_key"], section["secret_key"]

        for ad_type in AD_TYPE_CAMPAIGN_TP:
            main_ag, extra_ags, err = fetch_first_adgroup(customer_id, api_key, secret_key, ad_type, store_name)
            if err:
                logging.warning("%s %s 대표 광고그룹 조회 실패: %s", store_name, ad_type, err)
                continue
            if not main_ag:
                continue  # 이 매장은 해당 광고 유형 캠페인 자체가 없음(정상)

            process_adgroup(
                client, store_name, ad_type, "main", main_ag,
                week_monday, week_sunday, daily_start, api_key, secret_key, customer_id,
            )
            time.sleep(0.3)
            for extra_ag in extra_ags:
                process_adgroup(
                    client, store_name, ad_type, "extra", extra_ag,
                    week_monday, week_sunday, daily_start, api_key, secret_key, customer_id,
                )
                time.sleep(0.3)
        logging.info("%s 완료", store_name)


if __name__ == "__main__":
    main()
