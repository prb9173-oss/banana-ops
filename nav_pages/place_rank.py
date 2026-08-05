from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit.components.v1 as components
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


def filter_groups_for_report(keyword_groups):
    """보고용 표에는 is_report_keyword=True로 표시된 매장 행만 남긴다.
    그룹 안의 모든 행이 걸러지면 그 키워드 그룹 자체를 표에서 뺀다."""
    filtered = []
    for keyword_text, rows in keyword_groups:
        report_rows = [r for r in rows if r.get("is_report_keyword")]
        if report_rows:
            filtered.append((keyword_text, report_rows))
    return filtered


def filter_groups_for_meeting(keyword_groups):
    """회의용 표에는 is_meeting_keyword=True로 표시된 매장 행만 남긴다.
    이 컬럼은 기본값이 true라서(모두 회의용에 나옴), 특정 키워드만 회의에서
    굳이 안 다뤄도 될 때 개별적으로 체크를 해제해서 빼는 용도다."""
    filtered = []
    for keyword_text, rows in keyword_groups:
        meeting_rows = [r for r in rows if r.get("is_meeting_keyword", True)]
        if meeting_rows:
            filtered.append((keyword_text, meeting_rows))
    return filtered


# 표 전체에서 쓰는 선/배경 색 — 한 곳에서만 정의해서 "어떤 선은 굵고 어떤 선은 얇은"
# 불일치가 다시 생기지 않게 한다. 브랜드 구분은 왼쪽 병합 셀(배경색+굵은 글씨)만으로
# 표시하고, 그 외 내용 칸은 항상 흰 배경으로 통일한다.
TABLE_BORDER = "#000000"  # 테스트: 표를 더 직관적으로 보이게 구분선을 검은색으로 시도
BRAND_CELL_BG = "#EEF3FA"


def build_snapshot_rows_html(keyword_groups, checks_by_keyword, selected_date, weekly_snapshot_keywords):
    """제주도 맛집처럼 지정된 키워드는 브랜드 표 바로 위에 최근 3주 경쟁 현황을
    보여준다 — build_brand_rows_html과 같은 <table> 안에 이어붙일 <tr> 목록만
    돌려줘서 두 구역이 서로 다른 표가 아니라 한 표처럼 보이게 한다."""
    rows_html = ""
    for keyword_text, rows in keyword_groups:
        if keyword_text not in weekly_snapshot_keywords:
            continue
        rep_checks = checks_by_keyword.get(rows[0]["id"], [])
        # border는 <tr>가 아니라 각 <td>에 직접 준다 — border-collapse + rowspan이
        # 섞이면 <table> 자체의 outer border나 <tr> border는 브라우저에서 잘려 보이는
        # 경우가 있어서, 표 바깥 네 변도 가장자리 <td>에 각각 명시적으로 그어준다.
        # 이 스냅샷 행이 항상 표의 첫 행이라 top border도 여기서 같이 준다.
        rows_html += '<tr>'
        rows_html += (
            f'<td style="background:{BRAND_CELL_BG}; font-weight:700; padding:10px; '
            f'vertical-align:middle; text-align:center; border-right:1px solid {TABLE_BORDER}; '
            f'border-bottom:1px solid {TABLE_BORDER}; border-top:1px solid {TABLE_BORDER}; '
            f'border-left:1px solid {TABLE_BORDER}; white-space:nowrap;">{keyword_text}<br>'
            f'<span style="font-size:11px; font-weight:500; color:#5B6472;">최근 3주</span></td>'
        )
        for col_idx, weeks_back in enumerate([2, 1, 0]):
            snap_date = selected_date - timedelta(days=7 * weeks_back)
            snap_check = find_check_for_date(rep_checks, snap_date)
            snap_places = (snap_check or {}).get("top_places")
            border_right = f"border-right:1px solid {TABLE_BORDER};"
            date_label = f'<div style="font-weight:700; margin-bottom:6px;">{snap_date.strftime("%m/%d")}</div>'
            if snap_places:
                top14 = snap_places[:14]
                half = (len(top14) + 1) // 2
                left_items = "".join(f'<div class="rank-snapshot-item">{j}. {p.get("name", "")}</div>' for j, p in enumerate(top14[:half], start=1))
                right_items = "".join(f'<div class="rank-snapshot-item">{j}. {p.get("name", "")}</div>' for j, p in enumerate(top14[half:], start=half + 1))
                body = f'<div style="display:flex; gap:10px;"><div style="flex:1;">{left_items}</div><div style="flex:1;">{right_items}</div></div>'
            else:
                body = '<span class="rank-meta">데이터 없음</span>'
            rows_html += (
                f'<td style="padding:8px 10px; vertical-align:top; width:33%; '
                f'border-bottom:1px solid {TABLE_BORDER}; border-top:1px solid {TABLE_BORDER}; {border_right}">'
                f'{date_label}{body}</td>'
            )
        rows_html += '</tr>'
    return rows_html


def build_brand_rows_html(groups, checks_by_keyword, selected_date, previous_date, top_n_field, add_top_border=False):
    """실무 보고서와 동일한 브랜드 병합 표 — 회의용/보고용 둘 다 이 함수로 렌더링해서
    형식을 통일한다. build_snapshot_rows_html과 같은 <table> 안에 이어붙일 <tr>
    목록만 돌려준다. 순위/증감은 카드뷰와 같은 배지(pill) 스타일을 그대로 쓴다.
    add_top_border=True는 이 표 앞에 스냅샷 구역이 없어서 이 부분이 표의 맨 첫
    행이 되는 경우(top border를 직접 그어줘야 함)를 위한 것.
    top_n_field는 "report_top_n" 또는 "meeting_top_n" — 같은 키워드라도 보고용/회의용
    표에서 경쟁업체 목록 개수를 다르게 줄 수 있어서, 그룹의 대표 행(rows[0])에서
    이 탭에 해당하는 컬럼 값을 읽어 그만큼만 보여준다."""
    brand_buckets = {}
    brand_order = []
    for keyword_text, rows in groups:
        brand = get_brand((rows[0].get("store_campaigns") or {}).get("store_name", ""))
        if brand not in brand_buckets:
            brand_buckets[brand] = []
            brand_order.append(brand)
        brand_buckets[brand].append((keyword_text, rows))

    rows_html = ""
    for brand_idx, brand in enumerate(brand_order):
        brand_groups = brand_buckets[brand]
        for i, (keyword_text, rows) in enumerate(brand_groups):
            is_very_first_row = add_top_border and brand_idx == 0 and i == 0
            top_border = f"border-top:1px solid {TABLE_BORDER};" if is_very_first_row else ""
            rows_html += '<tr>'
            if i == 0:
                # 브랜드 셀은 rowspan이라 border-bottom을 주면 그 브랜드 블록 전체가
                # 끝나는 시점(마지막 키워드 행)에만 선이 그어진다 — 의도한 동작.
                # 왼쪽 가장자리 셀이라 border-left도 항상 준다(표 바깥 왼쪽 테두리).
                rows_html += (
                    f'<td rowspan="{len(brand_groups)}" style="background:{BRAND_CELL_BG}; '
                    f'font-weight:700; padding:10px; vertical-align:middle; text-align:center; '
                    f'border-right:1px solid {TABLE_BORDER}; border-bottom:1px solid {TABLE_BORDER}; '
                    f'border-left:1px solid {TABLE_BORDER}; {top_border} white-space:nowrap;">{brand}</td>'
                )
            title_top10_html = ""
            top_n = rows[0].get(top_n_field) or 0
            if top_n > 0:
                rep_check = find_check_for_date(checks_by_keyword.get(rows[0]["id"], []), selected_date)
                title_top10_html = build_top10_html((rep_check or {}).get("top_places"), top_n)

            store_cells = []
            for kw in rows:
                store_name = (kw.get("store_campaigns") or {}).get("store_name", "")
                checks = checks_by_keyword.get(kw["id"], [])
                selected_check = find_check_for_date(checks, selected_date)
                previous_check = find_check_for_date(checks, previous_date)
                store_cells.append(build_rank_info_html(store_name, kw, selected_check, previous_check))

            rows_html += (
                # colspan="3" — 스냅샷 행이 이 표에 "라벨 1칸 + 날짜 3칸"짜리 4열 구조를
                # 만들어두기 때문에, 여기서도 폭을 맞춰 3칸을 다 차지하게 하지 않으면
                # 브라우저가 이 칸을 스냅샷의 첫 날짜 칸 너비로만 좁혀버린다.
                f'<td colspan="3" style="padding:8px 10px; vertical-align:top; '
                f'border-bottom:1px solid {TABLE_BORDER}; border-right:1px solid {TABLE_BORDER}; {top_border}">'
                f'<div style="font-size:15px; font-weight:700; color:#0F172A; margin-bottom:6px;">{keyword_text}{title_top10_html}</div>'
                f'<div style="display:flex; flex-direction:column; gap:5px;">{"".join(store_cells)}</div></td>'
            )
            rows_html += '</tr>'
    return rows_html


def render_rank_tables(snapshot_rows_html, brand_rows_html, container_id=None):
    """3주 스냅샷 + 브랜드 표를 하나의 <table> 안에 이어붙여서 렌더링한다 — 표를
    두 개로 나누면(별도 <table> 태그) 그 사이에 브라우저가 여백을 넣어 두 표가
    분리돼 보이므로, 반드시 하나의 <table> 태그 안에서 합쳐야 한다.
    이 표를 감싸는 st.container(section_rank_results)가 이미 카드(테두리+패딩)라
    표 자체에는 별도 테두리 박스를 씌우지 않는다 — 카드 안에 카드가 겹치면
    아래쪽에 불필요한 빈 공간만 늘어난다.
    container_id를 주면 표를 그 id의 <div>로 감싼다 — "복사하기" 버튼이 캡처할
    대상을 정확히 지목하기 위한 용도(회의용 표까지 같이 잡히지 않도록)."""
    inner = snapshot_rows_html + brand_rows_html
    if not inner:
        return
    table_html = (
        # 표를 매번 카드(브라우저) 전체 폭까지 늘리면 실제 글자 내용은 얼마 안 되는데
        # 넓은 모니터에서 옆으로 크게 늘어나 버려서, 한 화면에 캡처하려고 축소하면
        # 여백만 같이 줄고 글자만 작아지는 문제가 있었다 — max-width로 내용에 맞는
        # 고정폭을 둬서 캡처하기 좋은 비율(옛 엑셀 보고서와 비슷한 폭)로 맞춘다.
        f'<table style="width:100%; max-width:960px; border-collapse:collapse; font-size:13px; '
        f'color:#16181D; border:1px solid {TABLE_BORDER};">{inner}</table>'
    )
    if container_id:
        # 표(<table>)의 테두리가 이 div의 바깥 경계선에 딱 붙어 있으면, html2canvas가
        # 캡처 경계를 계산할 때 그 1px 테두리 줄까지 함께 잘라버리는 경우가 있다.
        # 여기에 테두리를 하나 더 그어서 이중으로 두껍게 만드는 대신(내부 격자선과
        # 두께가 달라져 어색해 보였다), 흰 여백만 살짝 둬서 캡처 경계와 실제 테두리
        # 사이에 여유를 준다 — 두께는 그대로 1px 유지.
        # display:inline-block이 없으면 이 div가 일반 block으로 부모(넓은 화면일수록
        # 더 넓어짐) 폭 전체를 차지해버려서, 표는 960px에서 멈추는데 캡처 범위(=이 div)는
        # 그보다 훨씬 넓어져 오른쪽에 빈 공백까지 같이 캡처되는 문제가 있었다 —
        # inline-block으로 표 실제 너비만큼만 감싸도록 만든다.
        table_html = (
            f'<div id="{container_id}" style="background:#FFFFFF; padding:3px; '
            f'display:inline-block;">{table_html}</div>'
        )
    st.markdown(table_html, unsafe_allow_html=True)


def render_copy_button(target_id, button_id):
    """표를 이미지로 캡처해 클립보드에 바로 복사하는 버튼 + 스크립트.
    st.markdown으로 넣은 <script>는 브라우저가 실행해주지 않으므로(innerHTML 삽입은
    script 태그를 무시함), 보이지 않는 components.html 안에서 부모 문서에 진짜
    <script> 엘리먼트를 만들어(createElement+appendChild) 주입한다 — 이렇게 만든
    스크립트는 그 스크립트가 속한 문서(부모, 즉 메인 페이지)의 컨텍스트에서
    실행되므로, html2canvas와 클립보드 API 모두 메인 페이지 기준으로 정상 동작한다.
    버튼 클릭 이벤트는 document 레벨에서 위임 방식으로 잡아서, Streamlit이 매
    rerun마다 버튼 DOM을 새로 그려도(엘리먼트 참조가 바뀌어도) 계속 동작하게 한다."""
    st.markdown(
        f'<div class="rank-copy-btn-wrap">'
        f'<button id="{button_id}" type="button" class="rank-copy-btn">📋 복사하기</button>'
        f'</div>',
        unsafe_allow_html=True,
    )
    components.html(
        f"""
        <script>
        (function() {{
            var doc = window.parent.document;
            if (doc.getElementById('rank-copy-injected-script')) return;
            var s = doc.createElement('script');
            s.id = 'rank-copy-injected-script';
            s.text = `
                (function() {{
                    function ensureLib(cb) {{
                        if (window.html2canvas) {{ cb(); return; }}
                        var existing = document.getElementById('html2canvas-lib');
                        if (existing) {{ existing.addEventListener('load', cb); return; }}
                        var lib = document.createElement('script');
                        lib.id = 'html2canvas-lib';
                        lib.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
                        lib.onload = cb;
                        document.head.appendChild(lib);
                    }}
                    document.addEventListener('click', function(e) {{
                        var btn = e.target.closest('#{button_id}');
                        if (!btn) return;
                        var original = btn.innerText;
                        ensureLib(function() {{
                            var target = document.getElementById('{target_id}');
                            if (!target) return;
                            btn.innerText = '캡처 중...';
                            // 폰트가 늦게 로드되면 그사이 셀 너비가 바뀌면서 캡처 시점에
                            // 표 오른쪽 테두리가 잘리는 경우가 있어, 폰트 로딩이 끝난
                            // 뒤에 캡처하도록 기다린다.
                            document.fonts.ready.then(function() {{
                            window.html2canvas(target, {{backgroundColor: '#ffffff', scale: 2}}).then(function(canvas) {{
                                canvas.toBlob(function(blob) {{
                                    navigator.clipboard.write([
                                        new ClipboardItem({{'image/png': blob}})
                                    ]).then(function() {{
                                        btn.innerText = '복사 완료!';
                                        setTimeout(function() {{ btn.innerText = original; }}, 1500);
                                    }}).catch(function(err) {{
                                        btn.innerText = '복사 실패';
                                        console.error(err);
                                        setTimeout(function() {{ btn.innerText = original; }}, 1500);
                                    }});
                                }});
                            }}).catch(function(err) {{
                                btn.innerText = '캡처 실패';
                                console.error(err);
                                setTimeout(function() {{ btn.innerText = original; }}, 1500);
                            }});
                            }});
                        }});
                    }});
                }})();
            `;
            doc.body.appendChild(s);
        }})();
        </script>
        """,
        height=0,
    )


def get_brand(store_name):
    """매장명 앞부분을 브랜드로 쓴다 (예: '고집돌우럭 중문점' -> '고집돌우럭').
    store_campaigns에 별도 브랜드 필드가 없어서, 지금 등록된 매장명 규칙(브랜드+공백+지점명)에
    맞춰 이렇게 파생한다."""
    return store_name.split(" ")[0] if store_name else "기타"


def swap_keyword_group_order(keyword_groups, idx_a, idx_b):
    """키워드 그룹(카드) 두 개의 표시 순서를 맞바꾼다. ▲▼ 버튼은 항상 바로 옆
    그룹과만 교환하므로(idx_a/idx_b가 항상 인접), 두 그룹 바깥의 나머지 그룹은
    상대적 순서가 전혀 바뀌지 않는다 — 두 그룹에 속한 행들끼리만 display_order
    값을 맞바꾸면 충분하다. (예전엔 전체 활성 키워드를 처음부터 다시 순번 매겨
    매번 모든 행에 개별 update를 날렸는데, 키워드가 70개+인 상황에서 그룹 하나
    옮길 때마다 최대 70여 번의 순차 네트워크 호출이 나가는 불필요한 비용이었다.)"""
    client = get_supabase_client()
    earlier_idx, later_idx = min(idx_a, idx_b), max(idx_a, idx_b)
    rows_earlier = keyword_groups[earlier_idx][1]
    rows_later = keyword_groups[later_idx][1]
    orders = sorted(row["display_order"] for row in rows_earlier + rows_later)
    # 원래 뒤에 있던 그룹이 앞으로 오므로 더 작은 order 값들을 받는다
    for row, order in zip(rows_later, orders[:len(rows_later)]):
        client.table("place_rank_keywords").update({"display_order": order}).eq("id", row["id"]).execute()
    for row, order in zip(rows_earlier, orders[len(rows_later):]):
        client.table("place_rank_keywords").update({"display_order": order}).eq("id", row["id"]).execute()


def _toggle_report_keyword_group(checkbox_key, keyword_ids):
    """같은 키워드 그룹의 매장들은 항상 다 같이 보고용에 포함되거나 다 같이 빠지지,
    지점별로 다르게 쓸 일이 없어서 그룹(키워드) 전체 행에 한 번에 적용한다."""
    get_supabase_client().table("place_rank_keywords").update(
        {"is_report_keyword": st.session_state[checkbox_key]}
    ).in_("id", keyword_ids).execute()
    fetch_all_keywords.clear()


def _toggle_meeting_keyword_group(checkbox_key, keyword_ids):
    get_supabase_client().table("place_rank_keywords").update(
        {"is_meeting_keyword": st.session_state[checkbox_key]}
    ).in_("id", keyword_ids).execute()
    fetch_all_keywords.clear()


# 키워드 제목 옆 경쟁업체 목록 개수 — 실무에서 실제로 쓰는 값이 "안 보여줌 / Top 2 /
# Top 10" 세 가지뿐이라 자유 입력 숫자칸 대신 선택형으로 제한한다.
TOP_N_OPTIONS = [("경쟁업체 미표시", 0), ("Top 2", 2), ("Top 10", 10)]
TOP_N_LABELS = [label for label, _ in TOP_N_OPTIONS]
TOP_N_VALUE_TO_LABEL = {value: label for label, value in TOP_N_OPTIONS}
TOP_N_LABEL_TO_VALUE = dict(TOP_N_OPTIONS)


def _set_top_n_group(field_name, select_key, keyword_ids):
    value = TOP_N_LABEL_TO_VALUE[st.session_state[select_key]]
    get_supabase_client().table("place_rank_keywords").update(
        {field_name: value}
    ).in_("id", keyword_ids).execute()
    fetch_all_keywords.clear()


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


def build_top10_html(top_places, top_n):
    if not top_places or top_n <= 0:
        return ""
    names = " ".join(f"{i}.{p.get('name', '')}" for i, p in enumerate(top_places[:top_n], start=1))
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
        value_pill = '<span class="status-pill pill-rank-unknown">누락</span>'
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
                delta_pill = '<span class="status-pill pill-rank-same">동일</span>'

    return f'<div>{name_bits} {value_pill} {delta_pill}</div>'


st.subheader("플레이스 순위 추적")

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
keyword_groups = group_by_keyword(all_keywords)

# 조회(전체 순위 현황)는 누구나, 추적 키워드 추가/순서변경/비활성화/보고용 표시
# 여부처럼 실제 구성을 바꾸는 관리 기능은 관리자만 — season_keywords.py와 같은 패턴.
tab_view, tab_manage = st.tabs(["📍 전체 순위 현황", "⚙️ 추적 키워드 관리"])

with tab_view:
    with st.container(border=True, key="section_rank_results"):
        if not all_keywords:
            st.info("추적 중인 타겟 키워드가 없습니다. '⚙️ 추적 키워드 관리' 탭에서 키워드를 추가해 주세요.")
        else:
            if "pr_selected_date" not in st.session_state:
                st.session_state["pr_selected_date"] = datetime.now(KST).date()

            # 키워드마다 개별로 체크 시각을 표시하는 대신, 이 조회 날짜에 대해 실제로 체크된
            # 것들 중 가장 늦은 시각 하나만 대표로 보여준다.
            latest_checked_at = None
            for kw in all_keywords:
                c = find_check_for_date(checks_by_keyword.get(kw["id"], []), st.session_state["pr_selected_date"])
                if c and (not latest_checked_at or c["checked_at"] > latest_checked_at):
                    latest_checked_at = c["checked_at"]

            def _shift_selected_date(delta_days):
                st.session_state["pr_selected_date"] += timedelta(days=delta_days)

            with st.container(key="pr_date_nav"):
                col_prev, col_date, col_next, col_basis, col_checked = st.columns(
                    [0.25, 1.15, 0.25, 1.5, 1.5], vertical_alignment="top"
                )
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
                with col_checked:
                    if latest_checked_at:
                        st.markdown("&nbsp;")  # 라디오 그룹의 레이블 줄 높이와 맞춰 같은 줄에 나란히 보이게
                        st.caption(f"체크 시각: {format_checked_at(latest_checked_at)}")
            previous_date = selected_date - timedelta(days=1 if compare_basis == "전날 대비" else 7)

            # 이 스냅샷 표시는 모든 키워드에 일괄 적용하는 범용 기능이 아니라, 실무
            # 보고서에서 실제로 그렇게 쓰이는 특정 키워드 텍스트에만 조건부로 바로
            # 보이게 한다(펼치기 없음). 경쟁업체 Top N 표시는 키워드마다 하드코딩하지
            # 않고 "추적 키워드 관리" 탭에서 report_top_n/meeting_top_n으로 개별 설정한다.
            WEEKLY_SNAPSHOT_KEYWORDS = {"제주도 맛집"}

            # 보고용(캡처 공유용) / 회의용(전체 키워드) — 둘 다 같은 브랜드 병합 표 형식을
            # 쓰고, 보고용은 is_report_keyword로 표시된 키워드만 걸러서 보여준다.
            tab_report, tab_meeting = st.tabs(["📊 보고용", "📋 회의용"])

            with tab_report:
                render_copy_button(target_id="rank-table-capture-report", button_id="copy-rank-btn-report")
                snapshot_rows = build_snapshot_rows_html(keyword_groups, checks_by_keyword, selected_date, WEEKLY_SNAPSHOT_KEYWORDS)
                report_groups = filter_groups_for_report(keyword_groups)
                if report_groups:
                    brand_rows = build_brand_rows_html(
                        report_groups, checks_by_keyword, selected_date, previous_date, "report_top_n",
                        add_top_border=not snapshot_rows,
                    )
                    render_rank_tables(snapshot_rows, brand_rows, container_id="rank-table-capture-report")
                else:
                    render_rank_tables(snapshot_rows, "", container_id="rank-table-capture-report")
                    st.info("보고용으로 표시할 키워드가 없습니다.")

            with tab_meeting:
                snapshot_rows = build_snapshot_rows_html(keyword_groups, checks_by_keyword, selected_date, WEEKLY_SNAPSHOT_KEYWORDS)
                meeting_groups = filter_groups_for_meeting(keyword_groups)
                if meeting_groups:
                    brand_rows = build_brand_rows_html(
                        meeting_groups, checks_by_keyword, selected_date, previous_date, "meeting_top_n",
                        add_top_border=not snapshot_rows,
                    )
                    render_rank_tables(snapshot_rows, brand_rows)
                else:
                    render_rank_tables(snapshot_rows, "")
                    st.info("회의용으로 표시할 키워드가 없습니다.")

with tab_manage:
    if not st.session_state.get("is_admin"):
        st.info("🔒 이 기능은 관리자 모드에서만 사용할 수 있습니다.")
    else:
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
                        new_kw_text = new_keyword.strip()
                        insert_payload = {
                            "store_id": selected_store_row["id"],
                            "keyword": new_kw_text,
                            "display_order": next_order,
                        }
                        # 이미 있는 키워드 그룹에 매장을 추가하는 경우, 그 그룹의 보고용/회의용
                        # 포함 여부·Top N 설정을 그대로 물려받는다 — 매번 기본값(꺼짐)으로
                        # 시작해서 새로 추가한 매장만 따로 켜줘야 하는 번거로움을 없앤다.
                        existing_group = dict(keyword_groups).get(new_kw_text)
                        if existing_group:
                            rep_row = existing_group[0]
                            insert_payload.update({
                                "is_report_keyword": bool(rep_row.get("is_report_keyword")),
                                "is_meeting_keyword": rep_row.get("is_meeting_keyword", True),
                                "report_top_n": rep_row.get("report_top_n") or 0,
                                "meeting_top_n": rep_row.get("meeting_top_n") or 0,
                            })
                        try:
                            get_supabase_client().table("place_rank_keywords").insert(insert_payload).execute()
                            fetch_all_keywords.clear()
                            st.success(f"'{selected_store}'에 '{new_keyword.strip()}' 키워드가 추가되었습니다.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 키워드 추가 중 오류가 발생했습니다: {e}")

        with st.container(border=True, key="section_manage_keywords"):
            # 시즌 키워드 관리 페이지의 "저장된 시즌 키워드 묶음" 검색창과 동일한 형식
            # (제목 옆 오른쪽에 라벨 없는 검색창) — 앱 전체에서 이 배치를 일관되게 쓴다.
            col_title, col_search = st.columns([3, 2], vertical_alignment="center")
            with col_title:
                st.markdown("#### 📋 추적 키워드 목록")
            with col_search:
                # 키워드가 70개+로 늘어나면서 원하는 걸 찾으려면 계속 스크롤해야 하는
                # 문제 — 키워드/매장명으로 걸러서 원하는 카드만 바로 보이게 한다.
                search_query = st.text_input(
                    "키워드 검색",
                    placeholder="🔍 키워드 또는 매장명 검색",
                    key="pr_kw_search",
                    label_visibility="collapsed",
                ).strip()

            if not keyword_groups:
                st.info("추적 중인 키워드가 없습니다. 위에서 먼저 추가해 주세요.")
            else:
                # 순서변경(▲▼)은 검색 여부와 무관하게 항상 전체 목록 기준 group_idx로
                # 동작해야 하므로(swap_keyword_group_order가 keyword_groups 전체를
                # 다시 정렬), 목록 자체는 그대로 두고 렌더링만 건너뛰는 방식으로 필터링한다.
                matched_count = 0

                for group_idx, (keyword_text, rows) in enumerate(keyword_groups):
                    if search_query:
                        store_names = " ".join(
                            (r.get("store_campaigns") or {}).get("store_name", "") for r in rows
                        )
                        haystack = f"{keyword_text} {store_names}".lower()
                        if search_query.lower() not in haystack:
                            continue
                    matched_count += 1
                    keyword_ids = [r["id"] for r in rows]
                    # 그룹 내 모든 매장 행은 항상 같은 값을 갖는 게 정상이라(지점별로 다르게
                    # 쓸 일이 없음), 대표로 첫 번째 행 값만 읽어서 그룹 공용 컨트롤에 쓴다.
                    rep_row = rows[0]
                    # 위젯 key를 group_idx로 만들면, 순서 변경(▲▼)으로 그룹 순서가 바뀔 때
                    # 같은 key를 다른 키워드 그룹이 재사용하게 되어 session_state에 남아있던
                    # 이전 그룹의 체크 상태를 그대로 물려받는 버그가 생긴다(실제로 겪음 —
                    # 순서를 바꾸자 다른 그룹의 체크 상태가 그대로 옮겨붙었음). rep_row["id"]는
                    # 순서가 바뀌어도 그 키워드 그룹 고유의 값이라 안전하다.
                    group_key = rep_row["id"]
                    with st.container(border=True, key=f"pr_kwgroup_{group_idx}"):
                        col_title, col_order = st.columns([9, 1], vertical_alignment="center")
                        with col_title:
                            st.markdown(f"**{keyword_text}**")
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

                        # 보고용/회의용 포함 여부·경쟁업체 Top N은 매장(지점)별이 아니라
                        # 키워드 그룹 전체에 한 번만 적용되는 설정이라, 매장 행이 아니라
                        # 그룹 헤더에 딱 한 번만 두고 바꾸면 그룹의 모든 매장 행에 반영한다.
                        with st.container(key=f"pr_kwcontrols_{group_key}"):
                            col_report_chk, col_report_topn, col_meeting_chk, col_meeting_topn = st.columns(
                                [3, 3, 3, 3], vertical_alignment="center"
                            )
                            with col_report_chk:
                                report_chk_key = f"report_chk_{group_key}"
                                st.checkbox(
                                    "보고용",
                                    value=bool(rep_row.get("is_report_keyword")),
                                    key=report_chk_key,
                                    on_change=_toggle_report_keyword_group,
                                    args=(report_chk_key, keyword_ids),
                                )
                            with col_report_topn:
                                report_topn_key = f"report_topn_{group_key}"
                                st.selectbox(
                                    "보고용 경쟁업체",
                                    options=TOP_N_LABELS,
                                    index=TOP_N_LABELS.index(TOP_N_VALUE_TO_LABEL.get(rep_row.get("report_top_n") or 0, "경쟁업체 미표시")),
                                    key=report_topn_key,
                                    label_visibility="collapsed",
                                    on_change=_set_top_n_group,
                                    args=("report_top_n", report_topn_key, keyword_ids),
                                )
                            with col_meeting_chk:
                                meeting_chk_key = f"meeting_chk_{group_key}"
                                st.checkbox(
                                    "회의용",
                                    value=rep_row.get("is_meeting_keyword", True),
                                    key=meeting_chk_key,
                                    on_change=_toggle_meeting_keyword_group,
                                    args=(meeting_chk_key, keyword_ids),
                                )
                            with col_meeting_topn:
                                meeting_topn_key = f"meeting_topn_{group_key}"
                                st.selectbox(
                                    "회의용 경쟁업체",
                                    options=TOP_N_LABELS,
                                    index=TOP_N_LABELS.index(TOP_N_VALUE_TO_LABEL.get(rep_row.get("meeting_top_n") or 0, "경쟁업체 미표시")),
                                    key=meeting_topn_key,
                                    label_visibility="collapsed",
                                    on_change=_set_top_n_group,
                                    args=("meeting_top_n", meeting_topn_key, keyword_ids),
                                )

                        for kw in rows:
                            store_name = (kw.get("store_campaigns") or {}).get("store_name", "")
                            with st.container(key=f"pr_kwrow_{kw['id']}"):
                                col_name, col_delete = st.columns([10, 2], vertical_alignment="center")
                                with col_name:
                                    st.markdown(f'<span class="rank-kw">{store_name}</span>', unsafe_allow_html=True)
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

                if search_query and matched_count == 0:
                    st.info(f"'{search_query}'와(과) 일치하는 키워드가 없습니다.")
