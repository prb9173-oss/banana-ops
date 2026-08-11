"""nav_pages 안 여러 페이지가 똑같이 쓰던 코드를 모아둔 곳 — 페이지가 아니므로
app.py의 st.Page(...) 목록에는 올리지 않는다."""
import streamlit as st
from supabase import create_client


@st.cache_resource
def get_supabase_client():
    sb = st.secrets["supabase"]
    return create_client(sb["url"], sb["key"])
