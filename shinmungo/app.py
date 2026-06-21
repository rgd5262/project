from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.db import get_session, init_db
from services.seed import seed_if_empty
from services.ui import apply_page_config, apply_styles, sidebar_user


def bootstrap() -> None:
    init_db()
    session = get_session()
    try:
        seed_if_empty(session)
    finally:
        session.close()


def hide_default_navigation_entry() -> None:
    st.html(
        """
        <style>
        section[data-testid="stSidebar"] a[href$="/"],
        section[data-testid="stSidebar"] li:has(a[href$="/"]) {
          display: none !important;
        }
        </style>
        """
    )


def hide_hq_navigation_for_branch_user() -> None:
    st.html(
        """
        <style>
        section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] > div:has(a[href*="관리자"]),
        section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] > div:has(a[href*="%EA%B4%80%EB%A6%AC%EC%9E%90"]),
        section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] > div:has(a[href*="대시보드"]),
        section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] > div:has(a[href*="%EB%8C%80%EC%8B%9C%EB%B3%B4%EB%93%9C"]),
        section[data-testid="stSidebar"] li:has(a[href*="관리자"]),
        section[data-testid="stSidebar"] li:has(a[href*="%EA%B4%80%EB%A6%AC%EC%9E%90"]),
        section[data-testid="stSidebar"] li:has(a[href*="대시보드"]),
        section[data-testid="stSidebar"] li:has(a[href*="%EB%8C%80%EC%8B%9C%EB%B3%B4%EB%93%9C"]),
        section[data-testid="stSidebar"] a[href*="관리자"],
        section[data-testid="stSidebar"] a[href*="%EA%B4%80%EB%A6%AC%EC%9E%90"],
        section[data-testid="stSidebar"] a[href*="대시보드"],
        section[data-testid="stSidebar"] a[href*="%EB%8C%80%EC%8B%9C%EB%B3%B4%EB%93%9C"] {
          display: none !important;
        }
        </style>
        """
    )


apply_page_config("통합단말 신문고")
apply_styles()
bootstrap()
user = sidebar_user()

hide_default_navigation_entry()
if user.role == "직원":
    hide_hq_navigation_for_branch_user()

common_pages = [
    st.Page("views/0_진입.py", title="진입", default=True),
    st.Page(
        "views/1_통합단말_화면.py",
        title="통합단말 화면",
        icon=":material/desktop_windows:",
        url_path="통합단말_화면",
    ),
    st.Page(
        "views/3_내_접수내역.py",
        title="내 접수내역",
        icon=":material/list_alt:",
        url_path="내_접수내역",
    ),
]

pages = {
    "영업점 업무": common_pages,
    "본부부서 업무": [
        st.Page(
            "views/4_관리자.py",
            title="관리자",
            icon=":material/admin_panel_settings:",
            url_path="관리자",
        ),
        st.Page(
            "views/5_대시보드.py",
            title="대시보드",
            icon=":material/dashboard:",
            url_path="대시보드",
        ),
    ],
}

page = st.navigation(pages, position="sidebar", expanded=True)
page.run()
