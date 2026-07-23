import logging
import os
import re
import time
import urllib.parse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from supabase import create_client

SEARCH_URL = "https://m.search.naver.com/search.naver?where=m&sm=mtp_hty&query={query}"
MOBILE_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 13; SM-S911N) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
)
MAX_ORGANIC_SCAN = 400
MAX_SCROLLS = 60
STABLE_SCROLLS_TO_STOP = 3


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


def build_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=430,900")
    options.add_argument(f"user-agent={MOBILE_USER_AGENT}")
    options.add_argument("--lang=ko-KR")
    return webdriver.Chrome(options=options)


def resolve_place_list_url(driver, keyword):
    """일반 검색 결과 페이지에서 네이버가 자동으로 분류해준 '장소 더보기' 링크에서
    업종 경로만 추출한다. 링크에 딸려오는 x/y/level(지도 좌표) 파라미터를 그대로 쓰면
    지도 바텀시트용 축약 레이아웃(카드 16개, 링크에 업체 ID 없음)이 렌더링되는 문제가
    있어, query만 남기고 좌표 파라미터는 버린 뒤 목록 전용 URL을 직접 구성한다."""
    query = urllib.parse.quote(keyword)
    driver.get(SEARCH_URL.format(query=query))
    time.sleep(2)
    link = driver.find_element("css selector", 'a[href*="m.place.naver.com"][href*="/list?"]')
    href = link.get_attribute("href")
    m = re.match(r"https://m\.place\.naver\.com/([a-zA-Z]+)/list", href)
    category = m.group(1) if m else "place"
    return f"https://m.place.naver.com/{category}/list?query={query}&entry=pll"


def scroll_to_load_more(driver, max_scrolls=MAX_SCROLLS):
    """네이버 지도 앱에서 여러 페이지(수백 개)까지 순위가 나오므로, 카드 개수가
    변하지 않는 상태가 몇 번 연속 이어질 때까지 끝까지 스크롤한다. 딱 한 번만
    안 늘었다고 멈추면 로딩 텀 때문에 중간에 끊길 수 있어 STABLE_SCROLLS_TO_STOP
    만큼 연속으로 확인한다."""
    last_count = -1
    stable = 0
    for _ in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)
        new_count = len(driver.find_elements("class name", "CHC5F"))
        if new_count == last_count:
            stable += 1
            if stable >= STABLE_SCROLLS_TO_STOP:
                break
        else:
            stable = 0
        last_count = new_count
    return driver.find_elements("class name", "CHC5F")


def extract_place_id(card):
    """카드 내부 링크는 상대경로(/restaurant/12345?entry=pll)라서 raw href 속성
    문자열에 도메인이 없다. get_attribute("href")로 절대경로로 변환된 값을 받아
    정규식으로 숫자 ID를 뽑는다 (xpath의 contains(@href, ...)는 raw 속성값만 보므로
    상대경로에는 걸리지 않아 항상 실패했었다)."""
    try:
        li = card.find_element("xpath", "ancestor::li[1]")
        anchors = li.find_elements("tag name", "a")
    except Exception:
        anchors = []
    for a in anchors:
        href = a.get_attribute("href") or ""
        m = re.search(r"/[a-zA-Z]+/(\d+)(?:\?|$)", href)
        if m:
            return m.group(1)
    return None


def is_ad_card(card):
    return len(card.find_elements("xpath", ".//*[text()='광고']")) > 0


def check_place_rank(driver, keyword, target_place_id, target_name):
    """조직 키워드에 대해 target_place_id(우선) 또는 target_name으로 매장을 찾아
    광고를 제외한 오가닉 순위를 계산한다. 반환값은 place_rank_checks insert용 dict."""
    list_url = resolve_place_list_url(driver, keyword)
    driver.get(list_url)
    time.sleep(2)

    cards = scroll_to_load_more(driver)
    if not cards:
        # 페이지 로딩이 늦었을 수 있으니 한 번 더 기다렸다 재시도.
        # 그래도 0개면 "결과 없음"이 아니라 스크래핑 자체가 실패한 것으로 본다
        # (흔한 키워드에서 결과가 진짜 0개일 가능성은 거의 없음).
        time.sleep(3)
        cards = scroll_to_load_more(driver)
        if not cards:
            raise RuntimeError("결과 목록을 로드하지 못함 (카드 0개)")

    organic_rank = 0
    for card in cards:
        if is_ad_card(card):
            continue
        organic_rank += 1

        matched = False
        if target_place_id:
            pid = extract_place_id(card)
            if pid == str(target_place_id):
                matched = True
        elif target_name:
            try:
                name = card.find_element("class name", "TYaxT").text
            except Exception:
                name = ""
            if name.strip() == target_name.strip():
                matched = True

        if matched:
            return {"rank": organic_rank, "results_scanned": organic_rank, "status": "ok"}

        if organic_rank >= MAX_ORGANIC_SCAN:
            break

    return {"rank": None, "results_scanned": organic_rank, "status": "not_found"}


def record_result(client, keyword_id, result):
    client.table("place_rank_checks").insert({"keyword_id": keyword_id, **result}).execute()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    client = get_supabase_client()
    rows = fetch_active_keyword_rows(client)
    logging.info("추적할 키워드 %d개", len(rows))

    driver = build_driver()
    try:
        for row in rows:
            store = row.get("store_campaigns") or {}
            target_place_id = store.get("naver_place_id")
            target_name = store.get("naver_place_name") or store.get("store_name")
            keyword = row["keyword"]

            try:
                result = check_place_rank(driver, keyword, target_place_id, target_name)
                logging.info("keyword_id=%s '%s' -> %s", row["id"], keyword, result)
            except Exception as e:
                logging.exception("keyword_id=%s '%s' 체크 실패", row["id"], keyword)
                result = {"rank": None, "results_scanned": None, "status": "error", "error_message": str(e)}

            record_result(client, row["id"], result)
            time.sleep(3)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
