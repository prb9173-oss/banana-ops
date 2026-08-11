"""scripts/ 안 독립 실행 스크립트들이 공유하는 코드. Streamlit 앱이 아니라
GitHub Actions 러너에서 `python scripts/xxx.py`로 직접 실행되므로 nav_pages 쪽
(st.secrets 기반) get_supabase_client와는 별도로 둔다."""
import os

from supabase import create_client


def get_supabase_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        import toml
        sb = toml.load(".streamlit/secrets.toml")["supabase"]
        url, key = sb["url"], sb["key"]
    return create_client(url, key)
