import logging
import os
import time

import requests

from supabase import create_client

GRAPHQL_URL = "https://api.place.naver.com/graphql"
# 네이버가 위치 권한 없을 때 쓰는 기본 좌표(서울시청 부근). 기존 Selenium 스크래퍼도
# headless 브라우저에 위치 권한을 준 적이 없어 항상 이 기본 좌표 기준으로 순위가
# 매겨졌으므로, 과거 데이터와의 연속성을 위해 동일한 값을 그대로 쓴다.
DEFAULT_X = "126.9783882"
DEFAULT_Y = "37.5666103"
MAX_DISPLAY = 100  # 서버가 한 응답당 최대 100개까지만 돌려줌(display를 늘려도 동일) —
# 더 보려면 start를 옮겨 여러 번 호출해야 하는데, 그만큼 짧은 시간에 호출이 늘어나
# 429(요청 제한)에 걸리는 것도 실측 확인됨 (2026-07-27). 늘리려면 별도로 리스크 검증 필요.
REQUEST_TIMEOUT = 15
MAX_ATTEMPTS_PER_KEYWORD = 3

MOBILE_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 13; SM-S911N) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
)

# 실제 모바일 페이지가 스크롤할 때 호출하는 내부 GraphQL 요청을 그대로 재현한다
# (2026-07-27, DevTools 네트워크 로그로 확인). 불필요한 쿠폰/리뷰/예약 필드는 빼고
# 순위 판정에 필요한 id/name/businessCategory만 요청한다.
PLACE_LIST_QUERY = """
query getRestaurants($input: PlaceListInput) {
  restaurants: placeList(input: $input) {
    businesses {
      total
      items {
        id
        name
        businessCategory
        __typename
      }
      __typename
    }
    __typename
  }
}
"""


def get_supabase_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        import toml
        sb = toml.load(".streamlit/secrets.toml")["supabase"]
        url, key = sb["url"], sb["key"]
    return create_client(url, key)


def fetch_active_keyword_rows(client):
    res = (
        client.table("place_rank_keywords")
        .select("*, store_campaigns(store_name, naver_place_id, naver_place_name)")
        .eq("is_active", True)
        .execute()
    )
    return res.data or []


def fetch_place_list(keyword, display=MAX_DISPLAY):
    payload = [{
        "operationName": "getRestaurants",
        "variables": {
            "input": {
                "query": keyword,
                "x": DEFAULT_X,
                "y": DEFAULT_Y,
                "start": 1,
                "display": display,
                "isNmap": False,
                "deviceType": "mobile",
            },
        },
        "query": PLACE_LIST_QUERY,
    }]
    headers = {
        "Content-Type": "application/json",
        "User-Agent": MOBILE_USER_AGENT,
        "Referer": "https://m.place.naver.com/",
        "Accept-Language": "ko-KR,ko;q=0.9",
    }
    response = requests.post(GRAPHQL_URL, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    result = data[0]
    if "errors" in result:
        raise RuntimeError(f"GraphQL 오류: {result['errors']}")
    return result["data"]["restaurants"]["businesses"]["items"]


def fetch_place_list_with_retries(keyword, max_attempts=MAX_ATTEMPTS_PER_KEYWORD):
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fetch_place_list(keyword)
        except Exception as e:
            last_error = e
            logging.warning("API 호출 실패 (시도 %d/%d): %s", attempt, max_attempts, e)
            time.sleep(2)
    raise RuntimeError(f"플레이스 목록을 가져오지 못함: {last_error}")


def check_place_rank(keyword, target_place_id, target_name):
    """조직 키워드에 대해 target_place_id(우선) 또는 target_name으로 매장을 찾아
    순위를 계산한다. getRestaurants 쿼리는 광고 목록(getAdBusinessList)과 별도라
    결과에 광고가 섞이지 않는다 — 기존 스크래퍼의 '광고 제외 오가닉 순위'와 동일한 정의."""
    items = fetch_place_list_with_retries(keyword)

    for rank, item in enumerate(items, start=1):
        matched = False
        if target_place_id:
            matched = str(item.get("id")) == str(target_place_id)
        elif target_name:
            matched = (item.get("name") or "").strip() == target_name.strip()

        if matched:
            return {"rank": rank, "results_scanned": rank, "status": "ok"}

    return {"rank": None, "results_scanned": len(items), "status": "not_found"}


def record_result(client, keyword_id, result):
    client.table("place_rank_checks").insert({"keyword_id": keyword_id, **result}).execute()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    client = get_supabase_client()
    rows = fetch_active_keyword_rows(client)
    logging.info("추적할 키워드 %d개", len(rows))

    for row in rows:
        store = row.get("store_campaigns") or {}
        target_place_id = store.get("naver_place_id")
        target_name = store.get("naver_place_name") or store.get("store_name")
        keyword = row["keyword"]

        try:
            result = check_place_rank(keyword, target_place_id, target_name)
            logging.info("keyword_id=%s '%s' -> %s", row["id"], keyword, result)
        except Exception as e:
            logging.exception("keyword_id=%s '%s' 체크 실패", row["id"], keyword)
            result = {"rank": None, "results_scanned": None, "status": "error", "error_message": str(e)}

        record_result(client, row["id"], result)
        time.sleep(1)


if __name__ == "__main__":
    main()
