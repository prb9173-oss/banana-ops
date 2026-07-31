"""1회성 과거 데이터 백필 스크립트.

check_ad_performance.py(매주 월요일 자동 실행)와 별개로, 처음 도입할 때 과거
16주치를 미리 채워 넣기 위한 스크립트 — 사람이 직접 한 번 실행한다(자동 스케줄
없음). 아래는 의도적으로 백필하지 않는다:
  - 현재입찰가/하루예산(creative_adgroup_snapshot): 네이버 API가 과거 값을 안 주고
    "오늘 기준 현재값"만 알려주므로, 과거 주차에 채워 넣으면 그 주 당시 값처럼
    보여 오해를 부른다.
  - 플레이스광고 상위 클릭 키워드: 애초에 관리자가 직접 입력하는 항목이라 과거
    값 자체가 없다.
  - 평균입찰가/특이사항(creative_admin_notes): 마찬가지로 수동 입력 전용.
"""
import datetime
import logging
import time

from check_ad_performance import (
    AD_TYPE_CAMPAIGN_TP,
    fetch_daily_stats,
    fetch_first_adgroup,
    fetch_top_keywords_auto,
    get_naver_accounts,
    get_supabase_client,
    replace_top_keywords,
    upsert_daily_stats,
)

BACKFILL_WEEKS = 16
MAX_RANGE_DAYS = 90  # 네이버 /stats는 92일 넘는 기간을 한 번에 조회하면 400 에러(실측 확인) — 여유 있게 90일 단위로 쪼갠다


def _chunk_date_range(start, end, max_days=MAX_RANGE_DAYS):
    cursor = start
    while cursor <= end:
        chunk_end = min(cursor + datetime.timedelta(days=max_days - 1), end)
        yield cursor, chunk_end
        cursor = chunk_end + datetime.timedelta(days=1)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    client = get_supabase_client()
    accounts = get_naver_accounts()
    logging.info("대상 계정 %d개, 과거 %d주 백필", len(accounts), BACKFILL_WEEKS)

    today = datetime.date.today()
    this_monday = today - datetime.timedelta(days=today.weekday())
    last_completed_monday = this_monday - datetime.timedelta(days=7)
    backfill_start = last_completed_monday - datetime.timedelta(weeks=BACKFILL_WEEKS - 1)
    backfill_end = last_completed_monday + datetime.timedelta(days=6)  # 지난주 일요일

    for account_key, section in accounts.items():
        customer_id, api_key, secret_key = section["customer_id"], section["api_key"], section["secret_key"]
        for ad_type in AD_TYPE_CAMPAIGN_TP:
            main_ag, extra_ags, err = fetch_first_adgroup(customer_id, api_key, secret_key, ad_type)
            if err:
                logging.warning("%s %s 대표 광고그룹 조회 실패: %s", account_key, ad_type, err)
                continue
            if not main_ag:
                continue

            for ag in [main_ag] + extra_ags:
                adgroup_id = ag["nccAdgroupId"]

                # 일별 지표는 92일 제한 때문에 90일 단위로 쪼개서 요청
                for chunk_start, chunk_end in _chunk_date_range(backfill_start, backfill_end):
                    daily_rows, err = fetch_daily_stats(
                        api_key, secret_key, customer_id, adgroup_id, chunk_start, chunk_end,
                    )
                    if err:
                        logging.warning(
                            "daily stats 백필 실패 %s/%s (%s~%s): %s",
                            account_key, adgroup_id, chunk_start, chunk_end, err,
                        )
                    else:
                        upsert_daily_stats(client, adgroup_id, daily_rows)
                    time.sleep(0.3)

                if ad_type == "플레이스광고":
                    continue  # 수동 입력 대상, 백필 제외

                # 키워드는 주차마다 상위 10개가 달라지므로 한 주씩 따로 조회
                for i in range(BACKFILL_WEEKS):
                    week_monday = backfill_start + datetime.timedelta(weeks=i)
                    week_sunday = week_monday + datetime.timedelta(days=6)
                    kw_rows, err = fetch_top_keywords_auto(
                        api_key, secret_key, customer_id, adgroup_id, week_monday, week_sunday,
                    )
                    if err:
                        logging.warning(
                            "keywords 백필 실패 %s/%s %s: %s", account_key, adgroup_id, week_monday, err,
                        )
                        continue
                    replace_top_keywords(client, adgroup_id, week_monday, kw_rows)
                    time.sleep(0.3)

        logging.info("%s 백필 완료", account_key)


if __name__ == "__main__":
    main()
