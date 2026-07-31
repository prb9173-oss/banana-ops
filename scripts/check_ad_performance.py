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

AD_TYPE_CAMPAIGN_TP = {
    "플레이스광고": ["PLACE"],
    "파워링크광고": ["WEB_SITE"],
    "파워컨텐츠광고": ["CONTENTS", "POWER_CONTENT", "POWER_CONTENTS", "INFORMATION"],
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
    찾는다 — creative_viz.py의 계정 드롭다운(available_accounts)과 동일한 기준이라,
    두 곳의 "매장 목록"이 항상 같은 소스에서 나온다."""
    import toml
    secrets = toml.load(".streamlit/secrets.toml")
    accounts = {}
    for key, section in secrets.items():
        if isinstance(section, dict) and {"customer_id", "api_key", "secret_key"} <= section.keys():
            accounts[key] = section
    return accounts


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


def fetch_first_adgroup(customer_id, api_key, secret_key, ad_type):
    """creative_viz.py의 동명 함수와 동일 — extra_adgroups는 항상 ELIGIBLE만 포함한다
    (2026-07-31에 발견: 대표가 없어 상태 무관 전체 목록으로 폴백할 때 그 나머지까지
    "추가 광고그룹"으로 보여주면 PAUSED된 유령 광고그룹이 노출되는 버그가 있었음)."""
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
    if active_adgroups:
        return active_adgroups[0], active_adgroups[1:], None
    return adgroups[0], [], None


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


def upsert_adgroup_snapshot(client, account_key, ad_type, role, ag, week_monday):
    client.table("creative_adgroup_snapshot").upsert({
        "account_key": account_key,
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


def process_adgroup(client, account_key, ad_type, role, ag, week_monday, week_sunday, daily_start, api_key, secret_key, customer_id):
    adgroup_id = ag["nccAdgroupId"]
    upsert_adgroup_snapshot(client, account_key, ad_type, role, ag, week_monday)

    daily_rows, err = fetch_daily_stats(api_key, secret_key, customer_id, adgroup_id, daily_start, week_sunday)
    if err:
        logging.warning("daily stats 실패 %s/%s: %s", account_key, adgroup_id, err)
    else:
        upsert_daily_stats(client, adgroup_id, daily_rows)

    if ad_type != "플레이스광고":
        kw_rows, err = fetch_top_keywords_auto(api_key, secret_key, customer_id, adgroup_id, week_monday, week_sunday)
        if err:
            logging.warning("top keywords 실패 %s/%s: %s", account_key, adgroup_id, err)
        else:
            replace_top_keywords(client, adgroup_id, week_monday, kw_rows)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    client = get_supabase_client()
    accounts = get_naver_accounts()
    logging.info("대상 계정 %d개", len(accounts))

    today = datetime.date.today()
    this_monday = today - datetime.timedelta(days=today.weekday())
    week_monday = this_monday - datetime.timedelta(days=7)  # 지난 한 주(월~일)
    week_sunday = week_monday + datetime.timedelta(days=6)
    daily_start = week_monday - datetime.timedelta(weeks=3)  # 4주 표를 위한 롤링 시작점

    for account_key, section in accounts.items():
        customer_id, api_key, secret_key = section["customer_id"], section["api_key"], section["secret_key"]
        for ad_type in AD_TYPE_CAMPAIGN_TP:
            main_ag, extra_ags, err = fetch_first_adgroup(customer_id, api_key, secret_key, ad_type)
            if err:
                logging.warning("%s %s 대표 광고그룹 조회 실패: %s", account_key, ad_type, err)
                continue
            if not main_ag:
                continue  # 이 매장은 해당 광고 유형 자체가 없음(정상)

            process_adgroup(
                client, account_key, ad_type, "main", main_ag,
                week_monday, week_sunday, daily_start, api_key, secret_key, customer_id,
            )
            time.sleep(0.3)
            for extra_ag in extra_ags:
                process_adgroup(
                    client, account_key, ad_type, "extra", extra_ag,
                    week_monday, week_sunday, daily_start, api_key, secret_key, customer_id,
                )
                time.sleep(0.3)
        logging.info("%s 완료", account_key)


if __name__ == "__main__":
    main()
