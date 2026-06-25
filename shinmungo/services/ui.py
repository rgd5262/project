from __future__ import annotations

import html
from dataclasses import dataclass

import streamlit as st

STATUS_LABELS = {
    "RECEIVED": "접수",
    "REVIEWING": "검토중",
    "IN_PROGRESS": "처리중",
    "DONE": "완료",
    "REJECTED": "반려",
    "ON_HOLD": "보류",
}

STATUS_COLORS = {
    "RECEIVED": "#2563eb",
    "REVIEWING": "#7c3aed",
    "IN_PROGRESS": "#d97706",
    "DONE": "#059669",
    "REJECTED": "#dc2626",
    "ON_HOLD": "#64748b",
}


@dataclass
class CurrentUser:
    employee_id: str
    name: str
    branch: str
    role: str


BRANCH_OPTIONS = ["리테일 영업점", "기업금융센터", "WM센터"]
ROLE_OPTIONS = ["직원", "관리자"]
ROLE_LABELS = {"직원": "영업점", "관리자": "본부부서"}
HQ_DEPARTMENT_OPTIONS = ["금융서비스개발부", "퇴직연금사업부"]
HQ_DEPARTMENT_USERS = {
    "금융서비스개발부": ("FSDEV001", "금융서비스개발부 담당자"),
    "퇴직연금사업부": ("RETIRE001", "퇴직연금사업부 담당자"),
}
DEFAULT_BRANCH_EMPLOYEE_ID = "355901"
DEFAULT_BRANCH_EMPLOYEE_NAME = "홍길동"
DEFAULT_HQ_DEPARTMENT = "금융서비스개발부"
HQ_EMPLOYEE_IDS = {employee_id for employee_id, _ in HQ_DEPARTMENT_USERS.values()}
HQ_EMPLOYEE_NAMES = {name for _, name in HQ_DEPARTMENT_USERS.values()}
_PAGE_CONFIG_APPLIED = False
_LAST_UI_USER_STATE = {
    "role": "직원",
    "branch_employee_id": DEFAULT_BRANCH_EMPLOYEE_ID,
    "branch_employee_name": DEFAULT_BRANCH_EMPLOYEE_NAME,
    "branch_name": "리테일 영업점",
    "hq_department": DEFAULT_HQ_DEPARTMENT,
    "hq_employee_id": HQ_DEPARTMENT_USERS[DEFAULT_HQ_DEPARTMENT][0],
    "hq_employee_name": HQ_DEPARTMENT_USERS[DEFAULT_HQ_DEPARTMENT][1],
}


def apply_page_config(title: str = "통합단말 신문고") -> None:
    global _PAGE_CONFIG_APPLIED
    if _PAGE_CONFIG_APPLIED:
        return
    st.set_page_config(page_title=title, layout="wide", initial_sidebar_state="expanded")
    _PAGE_CONFIG_APPLIED = True


def apply_styles() -> None:
    st.html(
        """
        <style>
        :root {
          --terminal-blue: #2363b6;
          --terminal-dark: #263047;
          --terminal-border: #9aa9bc;
          --terminal-bg: #edf1f6;
          --terminal-panel: #f8fafc;
          --terminal-head: #d9e8fb;
        }
        header[data-testid="stHeader"] {
          height: 2.45rem !important;
          min-height: 2.45rem !important;
          visibility: visible !important;
          background: rgba(237, 241, 246, 0.96) !important;
          box-shadow: none !important;
          z-index: 999 !important;
        }
        header[data-testid="stHeader"] * {
          visibility: visible !important;
        }
        div[data-testid="stToolbar"] {
          visibility: hidden !important;
          height: 0 !important;
          position: fixed !important;
          pointer-events: none !important;
        }
        [data-testid="collapsedControl"],
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stExpandSidebarButton"],
        [data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebarCollapseButton"] *,
        [data-testid="stSidebarCollapsedControl"] *,
        [data-testid="stExpandSidebarButton"] *,
        section[data-testid="stSidebar"] [data-testid="stBaseButton-headerNoPadding"],
        section[data-testid="stSidebar"] [data-testid="stBaseButton-headerNoPadding"] *,
        button[kind="header"] {
          visibility: visible !important;
          opacity: 1 !important;
          pointer-events: auto !important;
        }
        [data-testid="stExpandSidebarButton"] {
          z-index: 1001 !important;
          background: #1e3a8a !important;
          border: 1px solid #0f172a !important;
          border-radius: 6px !important;
          box-shadow: 0 2px 8px rgba(15, 23, 42, 0.32) !important;
          color: #ffffff !important;
        }
        [data-testid="stExpandSidebarButton"] *,
        [data-testid="stExpandSidebarButton"] span,
        [data-testid="stExpandSidebarButton"] svg,
        [data-testid="stExpandSidebarButton"] path {
          color: #ffffff !important;
          fill: #ffffff !important;
          stroke: #ffffff !important;
        }
        .stApp, [data-testid="stAppViewContainer"] { background: #edf1f6; color: #111827; }
        .block-container { padding-top: 3.15rem; padding-bottom: 2rem; max-width: 1480px; }
        .stMarkdown, .stText, .stCaption, .stAlert, .stDataFrame, .stMetric,
        .stRadio, .stSelectbox, .stTextInput, .stTextArea, .stFileUploader,
        [data-testid="stWidgetLabel"], [data-testid="stMarkdownContainer"],
        [data-testid="stVerticalBlock"], [data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="stExpander"], [data-testid="stForm"], label, p {
          color: #111827;
        }
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] span,
        [data-testid="stCaptionContainer"],
        [data-testid="stWidgetLabel"] p {
          color: #111827;
        }
        input, textarea, select {
          background: #ffffff !important;
          color: #111827 !important;
          border-color: #cbd5e1 !important;
        }
        input::placeholder, textarea::placeholder {
          color: #64748b !important;
          opacity: 1 !important;
        }
        div[data-baseweb="select"] * { color: #111827 !important; }
        .stSelectbox div[data-baseweb="select"] > div {
          background: #ffffff !important;
          color: #111827 !important;
          border: 1px solid #cbd5e1 !important;
          border-radius: 0.5rem !important;
          min-height: 2.5rem !important;
          box-shadow: none !important;
        }
        .stSelectbox div[data-baseweb="select"] > div:hover {
          border-color: #94a3b8 !important;
        }
        .stSelectbox div[data-baseweb="select"] > div:focus-within {
          border-color: #2563eb !important;
          box-shadow: 0 0 0 1px #2563eb !important;
        }
        .stSelectbox div[data-baseweb="select"] input,
        .stSelectbox div[data-baseweb="select"] span,
        .stSelectbox div[data-baseweb="select"] svg {
          color: #111827 !important;
          fill: #111827 !important;
        }
        div[data-testid="stForm"], div[data-testid="stVerticalBlockBorderWrapper"] {
          background: #f8fafc;
          border-color: #cbd5e1;
        }
        section[data-testid="stSidebar"] { background: #f3f6fb; border-right: 1px solid #cbd5e1; }
        section[data-testid="stSidebar"] * { color: #111827; }
        div.stButton > button {
          border-radius: 4px;
          border: 1px solid #2f5fa7;
          font-weight: 700;
          min-height: 2.15rem;
        }
        div.stButton > button[kind="secondary"] {
          color: #1f2937;
          background: #ffffff;
        }
        div.stButton > button[kind="primary"],
        div[data-testid="stFormSubmitButton"] button,
        div[data-testid="stFormSubmitButton"] button[kind="primary"] {
          background: #2563eb !important;
          border: 1px solid #1d4ed8 !important;
          color: #ffffff !important;
        }
        div.stButton > button[kind="primary"] *,
        div[data-testid="stFormSubmitButton"] button *,
        div[data-testid="stFormSubmitButton"] button[kind="primary"] * {
          color: #ffffff !important;
        }
        div.stButton > button[kind="primary"]:hover,
        div[data-testid="stFormSubmitButton"] button:hover {
          background: #1d4ed8 !important;
          border-color: #1e40af !important;
          color: #ffffff !important;
        }
        .terminal-shell {
          background: var(--terminal-bg);
          border: 1px solid #8ea0b8;
          box-shadow: inset 0 0 0 1px #ffffff;
          color: #1f2937;
        }
        .terminal-topbar {
          background: linear-gradient(90deg, #0f73ce, #4f78bd);
          color: #fff;
          padding: 8px 12px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          font-size: 14px;
          font-weight: 700;
        }
        .terminal-brand { font-size: 18px; letter-spacing: 0; }
        .terminal-user { font-size: 12px; font-weight: 500; opacity: 0.95; }
        .terminal-body { display: grid; grid-template-columns: 214px 1fr; gap: 0; }
        .terminal-left {
          background: #eef2f7;
          border-right: 1px solid var(--terminal-border);
          padding: 8px;
          min-height: 720px;
          color: #111827;
        }
        .terminal-main { padding: 8px 12px 14px; color: #111827; }
        .st-key-screen_search_query {
          position: relative;
        }
        .st-key-screen_search_query::before {
          content: "🔍";
          position: absolute;
          left: 12px;
          top: 50%;
          transform: translateY(-50%);
          z-index: 3;
          font-size: 15px;
          line-height: 1;
          color: #1f2937;
          pointer-events: none;
        }
        .st-key-screen_search_query input {
          background: #ffffff !important;
          color: #111827 !important;
          border: 2px solid #111827 !important;
          border-radius: 3px !important;
          min-height: 2.35rem !important;
          font-weight: 800 !important;
          padding-left: 2.45rem !important;
          box-shadow: inset 0 0 0 1px #ffffff !important;
        }
        .st-key-screen_search_query input:focus {
          border-color: #1d4ed8 !important;
          box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2) !important;
        }
        .st-key-screen_search_query [data-testid="stWidgetLabel"] {
          display: none !important;
        }
        .st-key-screen_search_go {
          display: none !important;
        }
        body.shinmungo-area-selecting [data-shinmungo-target="true"] {
          cursor: crosshair !important;
        }
        div.st-key-area_select_cancel_button {
          position: fixed !important;
          left: calc(50% + 175px) !important;
          top: 24px !important;
          z-index: 2147483004 !important;
          width: 52px !important;
          margin: 0 !important;
          padding: 0 !important;
        }
        div.st-key-area_select_cancel_button button {
          min-height: 28px !important;
          height: 28px !important;
          padding: 0 10px !important;
          border-radius: 999px !important;
          border: 1px solid #1d4ed8 !important;
          background: #2563eb !important;
          color: #ffffff !important;
          font-size: 12px !important;
          font-weight: 900 !important;
          box-shadow: 0 8px 22px rgba(15, 23, 42, 0.22) !important;
        }
        div.st-key-area_select_cancel_button button *,
        div.st-key-area_select_cancel_button button p {
          color: #ffffff !important;
        }
        .mini-rail {
          background: #1f2937;
          color: #dbeafe;
          width: 28px;
          text-align: center;
          padding: 5px 0;
          border-radius: 4px;
          margin-bottom: 6px;
          font-size: 12px;
        }
        .terminal-tab-row { display: flex; gap: 4px; margin-bottom: 8px; }
        .terminal-tab {
          background: #d4dde9;
          border: 1px solid #9aa9bc;
          padding: 5px 14px;
          font-size: 13px;
          font-weight: 700;
          color: #111827;
        }
        .terminal-tab.active { background: #ffffff; border-bottom: 2px solid #2363b6; color: #174ea6; }
        .section-box {
          border: 1px solid var(--terminal-border);
          background: var(--terminal-panel);
          margin-bottom: 9px;
          color: #111827;
        }
        .section-title {
          background: var(--terminal-head);
          border-bottom: 1px solid var(--terminal-border);
          padding: 5px 8px;
          font-weight: 800;
          font-size: 13px;
          color: #102a43;
        }
        .section-content { padding: 8px; font-size: 12px; }
        .kv-grid {
          display: grid;
          grid-template-columns: 120px 1fr 120px 1fr;
          border-top: 1px solid #cbd5e1;
          border-left: 1px solid #cbd5e1;
          font-size: 12px;
        }
        .kv-grid div { border-right: 1px solid #cbd5e1; border-bottom: 1px solid #cbd5e1; padding: 5px 8px; min-height: 29px; color: #111827; }
        .kv-label { background: #d8e6f8; font-weight: 700; }
        .dense-table { width: 100%; border-collapse: collapse; font-size: 12px; }
        .dense-table th { background: #d8e6f8; color: #1f2937; border: 1px solid #9aa9bc; padding: 5px; }
        .dense-table td { border: 1px solid #cbd5e1; padding: 5px; background: #f8fafc; color: #111827; }
        .action-strip {
          display: flex;
          gap: 6px;
          justify-content: flex-end;
          background: #e5e7eb;
          border: 1px solid #cbd5e1;
          padding: 6px;
          margin-bottom: 8px;
          color: #111827;
        }
        .fake-button {
          background: #eff6ff;
          border: 1px solid #93c5fd;
          padding: 4px 9px;
          border-radius: 3px;
          font-size: 12px;
          font-weight: 700;
          color: #1e3a8a;
        }
        .context-card {
          border-left: 5px solid #2563eb;
          background: #eff6ff;
          padding: 12px 14px;
          margin-bottom: 14px;
          color: #1e3a8a;
        }
        .status-badge {
          display: inline-block;
          color: white;
          border-radius: 999px;
          padding: 3px 9px;
          font-size: 12px;
          font-weight: 800;
        }
        .metric-small {
          background: #f8fafc;
          border: 1px solid #cbd5e1;
          padding: 8px;
          text-align: center;
          font-size: 12px;
        }
        .dashboard-metric-card {
          background: #ffffff;
          border: 1px solid #cbd5e1;
          border-left: 6px solid var(--metric-accent, #2563eb);
          border-radius: 8px;
          padding: 14px 16px 13px;
          box-shadow: 0 2px 10px rgba(15, 23, 42, 0.08);
          min-height: 104px;
          color: #111827 !important;
        }
        .dashboard-metric-label {
          color: #334155 !important;
          font-size: 13px;
          font-weight: 800;
          line-height: 1.2;
          margin-bottom: 8px;
        }
        .dashboard-metric-value {
          color: #0f172a !important;
          font-size: 30px;
          font-weight: 950;
          line-height: 1.05;
          letter-spacing: 0;
        }
        .dashboard-metric-note {
          color: #64748b !important;
          font-size: 12px;
          font-weight: 650;
          margin-top: 8px;
          line-height: 1.35;
        }
        .dashboard-cluster-card {
          background: #ffffff;
          border: 1px solid #cbd5e1;
          border-top: 4px solid #2563eb;
          border-radius: 8px;
          padding: 13px 14px;
          color: #111827 !important;
          box-shadow: 0 1px 8px rgba(15, 23, 42, 0.07);
          height: 280px;
          min-height: 280px;
          max-height: 280px;
          margin-bottom: 12px;
          overflow-y: auto;
          overflow-x: hidden;
          overscroll-behavior: contain;
          -webkit-overflow-scrolling: touch;
          box-sizing: border-box;
          scrollbar-gutter: stable;
        }
        .dashboard-cluster-card::-webkit-scrollbar {
          width: 7px;
        }
        .dashboard-cluster-card::-webkit-scrollbar-track {
          background: #f1f5f9;
          border-radius: 999px;
        }
        .dashboard-cluster-card::-webkit-scrollbar-thumb {
          background: #94a3b8;
          border-radius: 999px;
        }
        .dashboard-cluster-card::-webkit-scrollbar-thumb:hover {
          background: #64748b;
        }
        .dashboard-cluster-card * {
          color: #111827 !important;
        }
        .dashboard-cluster-title {
          font-size: 15px;
          font-weight: 900;
          line-height: 1.35;
          margin-bottom: 8px;
          color: #0f172a !important;
        }
        .dashboard-cluster-meta {
          color: #475569 !important;
          font-size: 12px;
          font-weight: 750;
          line-height: 1.45;
          margin-bottom: 9px;
        }
        .dashboard-cluster-status,
        .dashboard-cluster-category {
          min-height: auto;
          max-height: none;
          display: block;
        }
        .dashboard-cluster-pills {
          display: flex;
          flex-wrap: wrap;
          gap: 5px;
          margin: 7px 0 8px;
        }
        .dashboard-cluster-pill {
          display: inline-flex;
          align-items: center;
          border: 1px solid #bfdbfe;
          background: #eff6ff;
          border-radius: 999px;
          padding: 3px 8px;
          font-size: 11px;
          font-weight: 850;
          color: #1e3a8a !important;
          white-space: nowrap;
        }
        .dashboard-cluster-ticket {
          border-top: 1px solid #e2e8f0;
          padding-top: 7px;
          margin-top: 7px;
          color: #334155 !important;
          font-size: 12px;
          line-height: 1.38;
          max-height: none;
          overflow: visible;
          display: block;
        }
        div[class*="st-key-dashboard_chart_"] {
          min-height: 430px !important;
          margin-bottom: 18px !important;
          overflow: visible !important;
          background: #ffffff !important;
          border: 1px solid #dbe3ef !important;
          border-radius: 8px !important;
          padding: 8px 8px 4px !important;
          box-sizing: border-box !important;
        }
        div[class*="st-key-cluster_bubble"] {
          min-height: 700px !important;
          margin-bottom: 18px !important;
          overflow: visible !important;
          background: #ffffff !important;
          border: 1px solid #dbe3ef !important;
          border-radius: 8px !important;
          padding: 8px 8px 4px !important;
          box-sizing: border-box !important;
        }
        div[class*="st-key-dashboard_chart_"] .js-plotly-plot,
        div[class*="st-key-cluster_bubble"] .js-plotly-plot,
        div[class*="st-key-dashboard_chart_"] .plot-container,
        div[class*="st-key-cluster_bubble"] .plot-container,
        div[class*="st-key-dashboard_chart_"] .svg-container,
        div[class*="st-key-cluster_bubble"] .svg-container,
        div[class*="st-key-dashboard_chart_"] .main-svg,
        div[class*="st-key-cluster_bubble"] .main-svg {
          overflow: visible !important;
          max-width: 100% !important;
        }
        .js-plotly-plot .legend text,
        .js-plotly-plot .legendtext,
        .js-plotly-plot .legendtitletext {
          fill: #111827 !important;
          color: #111827 !important;
          font-weight: 750 !important;
        }
        .js-plotly-plot .legend .bg {
          fill: #ffffff !important;
          fill-opacity: 0.96 !important;
          stroke: #cbd5e1 !important;
          stroke-width: 1px !important;
        }
        .js-plotly-plot .legendtoggle {
          fill: rgba(255, 255, 255, 0.01) !important;
          cursor: pointer;
        }
        .js-plotly-plot .xtick text,
        .js-plotly-plot .ytick text,
        .js-plotly-plot .xaxislayer-above text,
        .js-plotly-plot .yaxislayer-above text,
        .js-plotly-plot .xtitle,
        .js-plotly-plot .ytitle,
        .js-plotly-plot .g-xtitle text,
        .js-plotly-plot .g-ytitle text {
          fill: #0f172a !important;
          color: #0f172a !important;
          font-weight: 800 !important;
        }
        .js-plotly-plot .xgrid,
        .js-plotly-plot .ygrid {
          stroke: #cbd5e1 !important;
          stroke-opacity: 1 !important;
        }
        .js-plotly-plot .xlines-above path,
        .js-plotly-plot .ylines-above path,
        .js-plotly-plot .xlines-below path,
        .js-plotly-plot .ylines-below path {
          stroke: #475569 !important;
          stroke-width: 1.25px !important;
        }
        .js-plotly-plot .draglayer .drag,
        .js-plotly-plot .draglayer .ewdrag,
        .js-plotly-plot .draglayer .nsdrag,
        .js-plotly-plot .draglayer .nwdrag,
        .js-plotly-plot .draglayer .nedrag,
        .js-plotly-plot .draglayer .swdrag,
        .js-plotly-plot .draglayer .sedrag,
        .js-plotly-plot .draglayer .wdrag,
        .js-plotly-plot .draglayer .edrag {
          fill: rgba(0, 0, 0, 0) !important;
          stroke: none !important;
          stroke-width: 0 !important;
          pointer-events: all;
        }
        .js-plotly-plot .hovertext text {
          fill: #111827 !important;
        }
        .js-plotly-plot .hovertext path {
          fill: #ffffff !important;
          stroke: #2563eb !important;
        }
        div[data-testid="stTabs"] [role="tablist"] {
          display: grid !important;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)) !important;
          gap: 6px !important;
          align-items: stretch !important;
          border-bottom: 1px solid #cbd5e1 !important;
        }
        div[data-testid="stTabs"] [role="tablist"] > div {
          display: contents !important;
        }
        div[data-testid="stTabs"] button {
          width: 100% !important;
          min-width: 0 !important;
          height: 42px !important;
          min-height: 42px !important;
          max-height: 42px !important;
          background: #f8fafc !important;
          border: 1px solid #cbd5e1 !important;
          border-radius: 6px 6px 0 0 !important;
          color: #334155 !important;
          font-weight: 850 !important;
          justify-content: center !important;
          overflow: hidden !important;
          text-align: center !important;
          box-sizing: border-box !important;
          padding: 0 10px !important;
        }
        div[data-testid="stTabs"] button p,
        div[data-testid="stTabs"] button span {
          overflow: hidden !important;
          text-overflow: ellipsis !important;
          white-space: nowrap !important;
          max-width: 100% !important;
        }
        div[data-testid="stTabs"] button[aria-selected="true"] {
          background: #ffffff !important;
          border-bottom-color: #ffffff !important;
          color: #1d4ed8 !important;
        }
        .internal-nav-button {
          display: block;
          width: 100%;
          box-sizing: border-box;
          margin-top: 0.5rem;
          padding: 0.62rem 0.9rem;
          border-radius: 4px;
          border: 1px solid #1d4ed8;
          background: #2563eb;
          color: #ffffff !important;
          font-weight: 800;
          text-align: center;
          text-decoration: none !important;
        }
        .internal-nav-button:hover {
          background: #1d4ed8;
          color: #ffffff !important;
          text-decoration: none !important;
        }
        div[role="dialog"],
        div[data-testid="stDialog"] {
          width: min(520px, 92vw) !important;
          max-width: min(520px, 92vw) !important;
          height: min(780px, 88vh) !important;
          max-height: min(780px, 88vh) !important;
          background: #f8fafc !important;
          color: #111827 !important;
          border: 1px solid #8ea0b8 !important;
          border-radius: 7px !important;
          box-shadow: 0 24px 80px rgba(15, 23, 42, 0.34) !important;
          overflow: hidden !important;
        }
        div.stDialog {
          position: fixed !important;
          inset: 0 !important;
          width: 100vw !important;
          max-width: none !important;
          height: 100vh !important;
          max-height: none !important;
          display: flex !important;
          align-items: center !important;
          justify-content: center !important;
          padding: 16px !important;
          box-sizing: border-box !important;
          background: rgba(15, 23, 42, 0.42) !important;
        }
        div.stDialog > div {
          width: min(520px, 92vw) !important;
          max-width: min(520px, 92vw) !important;
          height: min(780px, 88vh) !important;
          max-height: min(780px, 88vh) !important;
          display: flex !important;
          align-items: stretch !important;
          justify-content: center !important;
          background: transparent !important;
        }
        div.stDialog div[role="dialog"] {
          width: 100% !important;
          max-width: 100% !important;
          height: 100% !important;
          max-height: 100% !important;
          margin: 0 !important;
          position: relative !important;
          display: flex !important;
          flex-direction: column !important;
        }
        div.stDialog div[role="dialog"] > div:first-child {
          display: flex !important;
          flex: 0 0 58px !important;
          width: 100% !important;
          min-height: 58px !important;
          height: 58px !important;
          align-items: center !important;
          padding: 0 54px 0 16px !important;
          box-sizing: border-box !important;
          background: linear-gradient(90deg, #1457ad, #2563eb) !important;
          border-bottom: 1px solid #0f3d7a !important;
          color: #ffffff !important;
          overflow: hidden !important;
        }
        div.stDialog div[role="dialog"] > div:first-child [data-testid="stMarkdownContainer"],
        div.stDialog div[role="dialog"] > div:first-child [data-testid="stMarkdownContainer"] p,
        div.stDialog div[role="dialog"] > div:first-child p {
          display: block !important;
          margin: 0 !important;
          padding: 0 !important;
          color: #ffffff !important;
          font-size: 18px !important;
          font-weight: 900 !important;
          line-height: 1.2 !important;
          letter-spacing: 0 !important;
          white-space: nowrap !important;
        }
        div.stDialog div[role="dialog"] > div:nth-of-type(2) {
          flex: 1 1 auto !important;
          min-height: 0 !important;
          height: auto !important;
          max-height: 100% !important;
          overflow-y: auto !important;
          overflow-x: hidden !important;
          padding: 16px 16px 18px !important;
          box-sizing: border-box !important;
          scrollbar-gutter: stable;
        }
        div.stDialog div[role="dialog"] > button {
          position: absolute !important;
          top: 16px !important;
          right: 16px !important;
          z-index: 10 !important;
          width: 24px !important;
          height: 24px !important;
          min-height: 24px !important;
          border-radius: 4px !important;
          border: 1px solid rgba(255, 255, 255, 0.55) !important;
          background: rgba(255, 255, 255, 0.18) !important;
          color: #ffffff !important;
        }
        div.stDialog div[role="dialog"] > button svg,
        div.stDialog div[role="dialog"] > button path {
          color: #ffffff !important;
          stroke: #ffffff !important;
        }
        div[role="dialog"] > div,
        div[data-testid="stDialog"] > div {
          background: #f8fafc !important;
          color: #111827 !important;
        }
        div[role="dialog"] [data-testid="stVerticalBlock"],
        div[data-testid="stDialog"] [data-testid="stVerticalBlock"] {
          background: transparent !important;
          color: #111827 !important;
        }
        div[role="dialog"] [data-testid="stMarkdownContainer"],
        div[role="dialog"] [data-testid="stMarkdownContainer"] p,
        div[role="dialog"] [data-testid="stMarkdownContainer"] span,
        div[role="dialog"] [data-testid="stWidgetLabel"],
        div[role="dialog"] [data-testid="stWidgetLabel"] p,
        div[role="dialog"] [data-testid="stCaptionContainer"],
        div[role="dialog"] label,
        div[role="dialog"] p,
        div[data-testid="stDialog"] [data-testid="stMarkdownContainer"],
        div[data-testid="stDialog"] [data-testid="stMarkdownContainer"] p,
        div[data-testid="stDialog"] [data-testid="stMarkdownContainer"] span,
        div[data-testid="stDialog"] [data-testid="stWidgetLabel"],
        div[data-testid="stDialog"] [data-testid="stWidgetLabel"] p,
        div[data-testid="stDialog"] [data-testid="stCaptionContainer"],
        div[data-testid="stDialog"] label,
        div[data-testid="stDialog"] p {
          color: #111827 !important;
        }
        div[role="dialog"] small,
        div[data-testid="stDialog"] small {
          color: #475569 !important;
        }
        div[role="dialog"] input,
        div[role="dialog"] textarea,
        div[data-testid="stDialog"] input,
        div[data-testid="stDialog"] textarea {
          background: #ffffff !important;
          color: #111827 !important;
          border: 1px solid #cbd5e1 !important;
          box-shadow: none !important;
        }
        div[role="dialog"] textarea[disabled],
        div[data-testid="stDialog"] textarea[disabled] {
          background: #eef2f7 !important;
          color: #475569 !important;
          -webkit-text-fill-color: #475569 !important;
          font-size: 12px !important;
          line-height: 1.45 !important;
        }
        div[role="dialog"] input::placeholder,
        div[role="dialog"] textarea::placeholder,
        div[data-testid="stDialog"] input::placeholder,
        div[data-testid="stDialog"] textarea::placeholder {
          color: #64748b !important;
          opacity: 1 !important;
        }
        div[role="dialog"] div[data-baseweb="radio"] label,
        div[role="dialog"] div[data-baseweb="radio"] span,
        div[data-testid="stDialog"] div[data-baseweb="radio"] label,
        div[data-testid="stDialog"] div[data-baseweb="radio"] span {
          color: #111827 !important;
        }
        div[role="dialog"] [data-testid="stVerticalBlockBorderWrapper"],
        div[data-testid="stDialog"] [data-testid="stVerticalBlockBorderWrapper"] {
          background: #ffffff !important;
          border: 1px solid #d1d9e6 !important;
          border-radius: 6px !important;
          color: #111827 !important;
          box-shadow: 0 1px 0 rgba(15, 23, 42, 0.04) !important;
        }
        div[role="dialog"] div.stButton > button,
        div[data-testid="stDialog"] div.stButton > button {
          border-radius: 4px !important;
          min-height: 2.25rem !important;
        }
        div[role="dialog"] div.stButton > button[kind="primary"],
        div[data-testid="stDialog"] div.stButton > button[kind="primary"] {
          background: #2563eb !important;
          border-color: #1d4ed8 !important;
          color: #ffffff !important;
        }
        div[role="dialog"] div.stButton > button[kind="primary"] *,
        div[data-testid="stDialog"] div.stButton > button[kind="primary"] * {
          color: #ffffff !important;
        }
        div[role="dialog"] div.stButton > button[kind="secondary"],
        div[data-testid="stDialog"] div.stButton > button[kind="secondary"] {
          background: #ffffff !important;
          border-color: #94a3b8 !important;
          color: #111827 !important;
        }
        div[role="dialog"] [data-testid="stAlert"],
        div[data-testid="stDialog"] [data-testid="stAlert"] {
          color: #111827 !important;
          border-radius: 5px !important;
        }
        div[role="dialog"] [data-testid="stAlert"] *,
        div[data-testid="stDialog"] [data-testid="stAlert"] * {
          color: #111827 !important;
        }
        div.stDialog:has(.terminal-alert-marker) {
          background: rgba(15, 23, 42, 0.28) !important;
        }
        div.stDialog:has(.terminal-alert-marker) > div,
        div.stDialog > div:has(.terminal-alert-marker) {
          width: min(440px, 90vw) !important;
          max-width: min(440px, 90vw) !important;
          height: 88px !important;
          min-height: 88px !important;
          max-height: 88px !important;
          align-self: center !important;
          align-items: center !important;
          justify-content: center !important;
          background: transparent !important;
        }
        div.stDialog div[role="dialog"]:has(.terminal-alert-marker) {
          width: min(440px, 90vw) !important;
          max-width: min(440px, 90vw) !important;
          height: 88px !important;
          min-height: 88px !important;
          max-height: 88px !important;
          align-self: center !important;
          display: block !important;
          background: #ffffff !important;
          color: #111827 !important;
          border: 1px solid #334155 !important;
          border-radius: 5px !important;
          box-shadow: 0 16px 42px rgba(15, 23, 42, 0.28) !important;
          overflow: hidden !important;
        }
        div.stDialog div[role="dialog"]:has(.terminal-alert-marker) > div:first-child,
        div.stDialog div[role="dialog"]:has(.terminal-alert-marker) > button {
          display: none !important;
        }
        div.stDialog div[role="dialog"]:has(.terminal-alert-marker) > div:nth-of-type(2) {
          height: auto !important;
          max-height: none !important;
          overflow: visible !important;
          padding: 16px 18px !important;
          box-sizing: border-box !important;
        }
        div.stDialog div[role="dialog"]:has(.terminal-alert-marker) [data-testid="stHorizontalBlock"] {
          align-items: center !important;
        }
        .terminal-alert-marker {
          display: none;
        }
        .terminal-alert-text {
          color: #111827 !important;
          font-size: 14px;
          font-weight: 850;
          line-height: 1.4;
          white-space: nowrap;
        }
        .terminal-access-alert-backdrop {
          position: fixed;
          inset: 0;
          z-index: 999990;
          background: rgba(15, 23, 42, 0.28);
        }
        .terminal-access-alert-box {
          position: fixed;
          left: 50%;
          top: 50%;
          z-index: 999991;
          width: min(440px, 90vw);
          height: 88px;
          transform: translate(-50%, -50%);
          box-sizing: border-box;
          padding: 16px 18px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 18px;
          background: #ffffff;
          color: #111827;
          border: 1px solid #334155;
          border-radius: 5px;
          box-shadow: 0 16px 42px rgba(15, 23, 42, 0.28);
        }
        .terminal-access-alert-text {
          color: #111827 !important;
          font-size: 14px;
          font-weight: 850;
          line-height: 1.4;
          white-space: nowrap;
        }
        .terminal-access-alert-button {
          flex: 0 0 82px;
          width: 82px;
          height: 32px;
          min-height: 32px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          box-sizing: border-box;
          border-radius: 4px;
          border: 1px solid #1d4ed8;
          background: #2563eb;
          color: #ffffff !important;
          font-size: 14px;
          font-weight: 850;
          text-decoration: none !important;
          line-height: 1;
        }
        .terminal-access-alert-button:hover,
        .terminal-access-alert-button:visited {
          background: #1d4ed8;
          color: #ffffff !important;
          text-decoration: none !important;
        }
        @media (max-width: 520px) {
          .terminal-access-alert-box {
            width: 90vw;
          }
        }
        div.stDialog div[role="dialog"]:has(.terminal-alert-marker) .stButton button {
          min-height: 2.05rem !important;
          border-radius: 4px !important;
          border: 1px solid #1d4ed8 !important;
          background: #2563eb !important;
          color: #ffffff !important;
          font-weight: 800 !important;
        }
        div.stDialog div[role="dialog"]:has(.terminal-alert-marker) .stButton button * {
          color: #ffffff !important;
        }
        .shinmungo-custom-backdrop {
          position: fixed;
          inset: 0;
          z-index: 2147482500;
          background: rgba(15, 23, 42, 0.42);
        }
        div[data-testid="stLayoutWrapper"]:has(> div.st-key-shinmungo_custom_layer) {
          width: min(520px, 92vw) !important;
          max-width: min(520px, 92vw) !important;
          margin: 0 auto !important;
          padding: 0 !important;
          box-sizing: border-box !important;
          overflow: visible !important;
        }
        div.st-key-shinmungo_custom_layer {
          position: fixed !important;
          left: 50% !important;
          top: 50% !important;
          transform: translate(-50%, -50%) !important;
          z-index: 2147482501 !important;
          width: min(520px, 92vw) !important;
          height: min(780px, 88vh) !important;
          max-width: min(520px, 92vw) !important;
          max-height: min(780px, 88vh) !important;
          overflow-y: auto !important;
          overflow-x: hidden !important;
          background: #f8fafc !important;
          color: #111827 !important;
          border: 1px solid #8ea0b8 !important;
          border-radius: 7px !important;
          box-shadow: 0 24px 80px rgba(15, 23, 42, 0.34) !important;
          padding: 0 16px 18px !important;
          box-sizing: border-box !important;
          scrollbar-gutter: stable;
        }
        div.st-key-shinmungo_custom_layer *,
        div.st-key-shinmungo_custom_layer [data-testid="stLayoutWrapper"],
        div.st-key-shinmungo_custom_layer [data-testid="stElementContainer"] {
          box-sizing: border-box !important;
          max-width: 100% !important;
        }
        div.st-key-shinmungo_custom_layer [data-testid="stLayoutWrapper"],
        div.st-key-shinmungo_custom_layer [data-testid="stElementContainer"],
        div.st-key-shinmungo_custom_layer [data-testid="stVerticalBlock"],
        div.st-key-shinmungo_custom_layer [data-testid="stHorizontalBlock"] {
          width: 100% !important;
          max-width: 100% !important;
          min-width: 0 !important;
          box-sizing: border-box !important;
          height: auto !important;
          min-height: 0 !important;
          overflow: visible !important;
          flex: 0 0 auto !important;
          flex-basis: auto !important;
        }
        div.st-key-shinmungo_custom_layer [data-testid="stVerticalBlock"]:not(.st-key-shinmungo_custom_layer) {
          display: block !important;
        }
        div.st-key-shinmungo_custom_layer [data-testid="stVerticalBlock"] > div,
        div.st-key-shinmungo_custom_layer [data-testid="stHorizontalBlock"] > div {
          max-width: 100% !important;
          min-width: 0 !important;
          box-sizing: border-box !important;
          height: auto !important;
          min-height: 0 !important;
          overflow: visible !important;
          flex: 0 0 auto !important;
          flex-basis: auto !important;
        }
        div.st-key-shinmungo_custom_layer div[class*="st-key-modal_intake_ticket_type"],
        div.st-key-shinmungo_custom_layer div[class*="st-key-modal_intake_ticket_title"],
        div.st-key-shinmungo_custom_layer div[class*="st-key-modal_intake_ticket_content"],
        div.st-key-shinmungo_custom_layer div[class*="st-key-modal_intake_submit"],
        div.st-key-shinmungo_custom_layer div[class*="st-key-modal_intake_helpful_"],
        div.st-key-shinmungo_custom_layer div[class*="st-key-modal_intake_close"],
        div.st-key-shinmungo_custom_layer div[class*="st-key-modal_intake_select_area"] {
          height: auto !important;
          min-height: 0 !important;
          max-height: none !important;
          overflow: visible !important;
          flex: 0 0 auto !important;
          flex-basis: auto !important;
        }
        div.st-key-shinmungo_custom_layer [data-testid="stMarkdownContainer"] {
          margin-bottom: 0 !important;
        }
        div.st-key-shinmungo_custom_layer [data-testid="stElementContainer"]:has(.shinmungo-layer-context),
        div.st-key-shinmungo_custom_layer [data-testid="stElementContainer"]:has(.selected-area-chip),
        div.st-key-shinmungo_custom_layer [data-testid="stElementContainer"]:has(.shinmungo-similar-review-panel),
        div.st-key-shinmungo_custom_layer [data-testid="stElementContainer"]:has(.shinmungo-similar-card-marker) {
          height: auto !important;
          max-height: none !important;
          overflow: visible !important;
          flex: 0 0 auto !important;
          flex-basis: auto !important;
        }
        div.st-key-shinmungo_custom_layer [data-testid="stElementContainer"]:has(.shinmungo-layer-context) {
          min-height: 74px !important;
        }
        div.st-key-shinmungo_custom_layer [data-testid="stElementContainer"]:has(.selected-area-chip) {
          min-height: 72px !important;
        }
        div.st-key-shinmungo_custom_layer [data-testid="stElementContainer"]:has(.shinmungo-similar-review-panel) {
          min-height: 98px !important;
        }
        div.st-key-shinmungo_custom_layer [data-testid="stElementContainer"]:has(.shinmungo-similar-card-marker) {
          min-height: 108px !important;
        }
        .shinmungo-review-action-spacer {
          height: 0;
          margin: 0;
          padding: 0;
        }
        div.st-key-shinmungo_custom_layer [data-testid="stElementContainer"]:has(.shinmungo-review-action-spacer),
        div.st-key-shinmungo_custom_layer [data-testid="stMarkdown"]:has(.shinmungo-review-action-spacer),
        div.st-key-shinmungo_custom_layer [data-testid="stMarkdownContainer"]:has(.shinmungo-review-action-spacer) {
          height: 0 !important;
          min-height: 0 !important;
          max-height: 0 !important;
          margin: 0 !important;
          padding: 0 !important;
          overflow: visible !important;
        }
        div.st-key-shinmungo_custom_layer div[class*="st-key-modal_intake_submit_new_after_review"] {
          margin-top: -8px !important;
        }
        div.st-key-shinmungo_custom_layer [data-testid="stElementContainer"]:has(.shinmungo-popup-header),
        div.st-key-shinmungo_custom_layer [data-testid="stMarkdown"]:has(.shinmungo-popup-header),
        div.st-key-shinmungo_custom_layer [data-testid="stMarkdownContainer"]:has(.shinmungo-popup-header) {
          width: 100% !important;
          max-width: 100% !important;
          min-width: 0 !important;
          flex: 0 0 auto !important;
          align-self: stretch !important;
          margin: 0 !important;
          padding: 0 !important;
          overflow: visible !important;
        }
        div.st-key-shinmungo_custom_layer .shinmungo-popup-header {
          position: sticky;
          top: 0;
          z-index: 4;
          width: calc(100% + 32px) !important;
          max-width: calc(100% + 32px) !important;
          margin: 0 -16px 14px;
          min-height: 58px;
          padding: 0 32px;
          background: linear-gradient(90deg, #1457ad, #2563eb);
          border-bottom: 1px solid #0f3d7a;
          color: #ffffff !important;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
          box-sizing: border-box;
        }
        div.st-key-shinmungo_custom_layer .shinmungo-popup-title {
          color: #ffffff !important;
          margin: 0 !important;
          font-size: 18px;
          font-weight: 900 !important;
          line-height: 1.2 !important;
        }
        div.st-key-shinmungo_custom_layer .shinmungo-popup-close-link,
        div.st-key-shinmungo_custom_layer .shinmungo-popup-close-link:visited {
          min-width: 58px;
          height: 30px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          border-radius: 4px !important;
          border: 1px solid rgba(255, 255, 255, 0.55) !important;
          background: rgba(255, 255, 255, 0.18) !important;
          color: #ffffff !important;
          padding: 0 12px !important;
          font-size: 12px;
          font-weight: 900 !important;
          line-height: 1;
          text-decoration: none !important;
          box-sizing: border-box;
        }
        div.st-key-shinmungo_custom_layer .shinmungo-popup-close-link:hover {
          background: rgba(255, 255, 255, 0.28) !important;
          color: #ffffff !important;
          text-decoration: none !important;
        }
        .shinmungo-intake-loading-layer {
          position: fixed;
          left: 50%;
          top: 50%;
          transform: translate(-50%, -50%);
          z-index: 2147482508;
          width: min(520px, 92vw);
          height: min(780px, 88vh);
          max-width: min(520px, 92vw);
          max-height: min(780px, 88vh);
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 7px;
          background: rgba(15, 23, 42, 0.34);
          backdrop-filter: blur(1.5px);
          pointer-events: all;
          box-sizing: border-box;
        }
        .shinmungo-intake-loading-box {
          min-width: 148px;
          padding: 18px 20px 16px;
          border-radius: 8px;
          border: 1px solid #c7d2fe;
          background: #ffffff;
          box-shadow: 0 18px 50px rgba(15, 23, 42, 0.28);
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 10px;
          color: #111827;
        }
        .shinmungo-intake-loading-spinner {
          width: 30px;
          height: 30px;
          border-radius: 999px;
          border: 4px solid #dbeafe;
          border-top-color: #2563eb;
          animation: shinmungo-intake-spin 0.85s linear infinite;
        }
        .shinmungo-intake-loading-text {
          color: #111827 !important;
          font-size: 13px;
          font-weight: 900;
          line-height: 1.2;
        }
        @keyframes shinmungo-intake-spin {
          to {
            transform: rotate(360deg);
          }
        }
        .shinmungo-helpful-confirm-backdrop {
          position: fixed;
          inset: 0;
          z-index: 2147482600;
          background: rgba(15, 23, 42, 0.42);
        }
        div[data-testid="stLayoutWrapper"]:has(> div.st-key-modal_intake_helpful_confirm_layer) {
          width: min(420px, 86vw) !important;
          max-width: min(420px, 86vw) !important;
          margin: 0 auto !important;
          padding: 0 !important;
          box-sizing: border-box !important;
          overflow: visible !important;
        }
        div.st-key-modal_intake_helpful_confirm_layer {
          position: fixed !important;
          left: 50% !important;
          top: 50% !important;
          transform: translate(-50%, -50%) !important;
          z-index: 2147482601 !important;
          width: min(420px, 86vw) !important;
          max-width: min(420px, 86vw) !important;
          min-height: 176px !important;
          padding: 18px !important;
          background: #ffffff !important;
          color: #111827 !important;
          border: 1px solid #8ea0b8 !important;
          border-radius: 8px !important;
          box-shadow: 0 26px 70px rgba(15, 23, 42, 0.36) !important;
          box-sizing: border-box !important;
          overflow: hidden !important;
        }
        div.st-key-modal_intake_helpful_confirm_layer *,
        div.st-key-modal_intake_helpful_confirm_layer [data-testid="stMarkdownContainer"],
        div.st-key-modal_intake_helpful_confirm_layer p,
        div.st-key-modal_intake_helpful_confirm_layer span {
          color: #111827 !important;
          box-sizing: border-box !important;
        }
        .shinmungo-helpful-confirm-copy {
          margin: 0 0 14px;
          padding: 0;
          color: #111827 !important;
        }
        .shinmungo-helpful-confirm-copy .confirm-eyebrow {
          margin-bottom: 6px;
          color: #1d4ed8 !important;
          font-size: 12px;
          font-weight: 900;
        }
        .shinmungo-helpful-confirm-copy .confirm-title {
          color: #0f172a !important;
          font-size: 18px;
          font-weight: 950;
          line-height: 1.25;
        }
        .shinmungo-helpful-confirm-copy .confirm-desc {
          margin-top: 7px;
          color: #475569 !important;
          font-size: 13px;
          font-weight: 700;
          line-height: 1.4;
        }
        .shinmungo-helpful-confirm-copy .confirm-ticket {
          margin-top: 10px;
          padding: 8px 10px;
          border-radius: 5px;
          background: #f1f5f9;
          color: #334155 !important;
          font-size: 12px;
          font-weight: 800;
          line-height: 1.35;
        }
        div.st-key-modal_intake_helpful_confirm_layer div.stButton > button {
          min-height: 36px !important;
          border-radius: 5px !important;
          font-size: 13px !important;
          font-weight: 900 !important;
        }
        div.st-key-modal_intake_helpful_confirm_layer div.stButton > button[kind="secondary"] {
          background: #ffffff !important;
          border: 1px solid #94a3b8 !important;
          color: #1f2937 !important;
        }
        div.st-key-modal_intake_helpful_confirm_layer div.stButton > button[kind="secondary"] * {
          color: #1f2937 !important;
        }
        .shinmungo-follow-alert-backdrop {
          position: fixed;
          inset: 0;
          z-index: 2147482700;
          background: rgba(15, 23, 42, 0.34);
        }
        div[data-testid="stLayoutWrapper"]:has(> div.st-key-shinmungo_follow_alert_layer) {
          width: min(440px, 88vw) !important;
          max-width: min(440px, 88vw) !important;
          margin: 0 auto !important;
          padding: 0 !important;
          box-sizing: border-box !important;
          overflow: visible !important;
        }
        div.st-key-shinmungo_follow_alert_layer {
          position: fixed !important;
          left: 50% !important;
          top: 50% !important;
          transform: translate(-50%, -50%) !important;
          z-index: 2147482701 !important;
          width: min(440px, 88vw) !important;
          max-width: min(440px, 88vw) !important;
          min-height: 142px !important;
          padding: 18px !important;
          background: #ffffff !important;
          border: 1px solid #8ea0b8 !important;
          border-radius: 8px !important;
          box-shadow: 0 24px 64px rgba(15, 23, 42, 0.34) !important;
          color: #111827 !important;
          box-sizing: border-box !important;
          overflow: hidden !important;
        }
        div.st-key-shinmungo_follow_alert_layer *,
        div.st-key-shinmungo_follow_alert_layer [data-testid="stMarkdownContainer"],
        div.st-key-shinmungo_follow_alert_layer p,
        div.st-key-shinmungo_follow_alert_layer span {
          color: #111827 !important;
          box-sizing: border-box !important;
        }
        div.st-key-shinmungo_follow_alert_layer [data-testid="stAlert"],
        div.st-key-shinmungo_follow_alert_layer .stAlertContainer,
        div.st-key-shinmungo_follow_alert_layer [data-testid="stAlert"] > div {
          width: 100% !important;
          max-width: 100% !important;
          margin: 0 0 14px !important;
          border-radius: 6px !important;
          border-color: #7dd3fc !important;
          background: #eff6ff !important;
          color: #0f172a !important;
          box-sizing: border-box !important;
        }
        div.st-key-shinmungo_follow_alert_layer [data-testid="stAlert"] svg {
          fill: #1d4ed8 !important;
          color: #1d4ed8 !important;
        }
        div.st-key-shinmungo_follow_alert_layer div.stButton > button {
          min-height: 36px !important;
          border-radius: 5px !important;
          border: 1px solid #1d4ed8 !important;
          background: #2563eb !important;
          color: #ffffff !important;
          font-size: 13px !important;
          font-weight: 900 !important;
        }
        div.st-key-shinmungo_follow_alert_layer div.stButton > button *,
        div.st-key-shinmungo_follow_alert_layer div.stButton > button p {
          color: #ffffff !important;
        }
        div.st-key-shinmungo_custom_layer [data-testid="stMarkdownContainer"],
        div.st-key-shinmungo_custom_layer [data-testid="stMarkdownContainer"] p,
        div.st-key-shinmungo_custom_layer [data-testid="stMarkdownContainer"] span,
        div.st-key-shinmungo_custom_layer [data-testid="stWidgetLabel"],
        div.st-key-shinmungo_custom_layer [data-testid="stWidgetLabel"] p,
        div.st-key-shinmungo_custom_layer [data-testid="stCaptionContainer"],
        div.st-key-shinmungo_custom_layer label,
        div.st-key-shinmungo_custom_layer p {
          color: #111827 !important;
        }
        div.st-key-shinmungo_custom_layer input,
        div.st-key-shinmungo_custom_layer textarea {
          background: #ffffff !important;
          color: #111827 !important;
          border: 1px solid #cbd5e1 !important;
          box-shadow: none !important;
        }
        div.st-key-shinmungo_custom_layer input:disabled,
        div.st-key-shinmungo_custom_layer textarea:disabled,
        div.st-key-shinmungo_custom_layer input[disabled],
        div.st-key-shinmungo_custom_layer textarea[disabled] {
          background: #f1f5f9 !important;
          color: #111827 !important;
          border: 1px solid #cbd5e1 !important;
          opacity: 1 !important;
          -webkit-text-fill-color: #111827 !important;
          cursor: not-allowed !important;
        }
        div.st-key-shinmungo_custom_layer input::placeholder,
        div.st-key-shinmungo_custom_layer textarea::placeholder {
          color: #64748b !important;
          opacity: 1 !important;
        }
        div.st-key-shinmungo_custom_layer div[data-baseweb="radio"] label,
        div.st-key-shinmungo_custom_layer div[data-baseweb="radio"] span {
          color: #111827 !important;
        }
        div.st-key-shinmungo_custom_layer div[class*="st-key-modal_intake_ticket_type"] [role="radiogroup"] {
          gap: 8px !important;
          align-items: center !important;
        }
        div.st-key-shinmungo_custom_layer div[class*="st-key-modal_intake_ticket_type"] [role="radiogroup"] label {
          min-height: 30px !important;
          padding: 4px 10px !important;
          border: 1px solid #cbd5e1 !important;
          border-radius: 999px !important;
          background: #ffffff !important;
          color: #111827 !important;
          opacity: 1 !important;
          box-shadow: 0 1px 0 rgba(15, 23, 42, 0.04) !important;
        }
        div.st-key-shinmungo_custom_layer div[class*="st-key-modal_intake_ticket_type"] [role="radiogroup"] label:has(input:disabled),
        div.st-key-shinmungo_custom_layer div[class*="st-key-modal_intake_ticket_type"] [role="radiogroup"] label[aria-disabled="true"] {
          background: #eef4fb !important;
          border-color: #94a3b8 !important;
          color: #111827 !important;
          -webkit-text-fill-color: #111827 !important;
          opacity: 1 !important;
        }
        div.st-key-shinmungo_custom_layer div[class*="st-key-modal_intake_ticket_type"] [role="radiogroup"] label:has(input:checked),
        div.st-key-shinmungo_custom_layer div[class*="st-key-modal_intake_ticket_type"] [role="radiogroup"] label:has([aria-checked="true"]) {
          background: #dbeafe !important;
          border-color: #2563eb !important;
          box-shadow: inset 0 0 0 1px #2563eb !important;
        }
        div.st-key-shinmungo_custom_layer div[class*="st-key-modal_intake_ticket_type"] [role="radiogroup"] label *,
        div.st-key-shinmungo_custom_layer div[class*="st-key-modal_intake_ticket_type"] [role="radiogroup"] label:has(input:disabled) * {
          color: #111827 !important;
          -webkit-text-fill-color: #111827 !important;
          opacity: 1 !important;
        }
        div.st-key-shinmungo_custom_layer [data-testid="stVerticalBlockBorderWrapper"] {
          background: #ffffff !important;
          border: 1px solid #d1d9e6 !important;
          border-radius: 6px !important;
          color: #111827 !important;
          box-shadow: 0 1px 0 rgba(15, 23, 42, 0.04) !important;
        }
        div.st-key-shinmungo_custom_layer [data-testid="stAlert"],
        div.st-key-shinmungo_custom_layer [data-testid="stAlert"] * {
          color: #111827 !important;
        }
        .shinmungo-layer-context {
          background: #ffffff;
          border-left: 5px solid #2563eb;
          border-top: 1px solid #dbe4f0;
          border-right: 1px solid #dbe4f0;
          border-bottom: 1px solid #dbe4f0;
          border-radius: 5px;
          padding: 10px 12px;
          margin-bottom: 12px;
          color: #111827 !important;
        }
        .shinmungo-layer-context b {
          color: #0f172a !important;
          font-size: 14px;
        }
        .shinmungo-layer-context .meta {
          display: block;
          margin-top: 4px;
          color: #475569 !important;
          font-size: 12px;
          font-weight: 650;
        }
        .selected-area-chip {
          background: #f0f7ff;
          border: 1px solid #bfdbfe;
          border-left: 5px solid #2563eb;
          border-radius: 6px;
          padding: 9px 11px;
          margin: 0 0 10px;
          color: #0f172a !important;
          line-height: 1.35;
        }
        .selected-area-chip * {
          color: #0f172a !important;
        }
        .selected-area-chip .selected-area-label {
          display: inline-block;
          margin-right: 6px;
          padding: 2px 7px;
          border-radius: 999px;
          background: #2563eb;
          color: #ffffff !important;
          font-size: 11px;
          font-weight: 900;
        }
        .selected-area-chip b {
          font-size: 13px;
          font-weight: 900;
        }
        .selected-area-chip span:last-child {
          display: block;
          margin-top: 5px;
          color: #475569 !important;
          font-size: 12px;
          font-weight: 650;
        }
        .selected-area-chip.readonly {
          background: #f8fafc;
          border-color: #dbe4f0;
          border-left-color: #64748b;
        }
        .selected-area-chip.readonly .selected-area-label {
          background: #64748b;
        }
        .selected-area-chip.readonly.empty {
          opacity: 0.95;
        }
        .shinmungo-similar-review-panel {
          margin: 12px 0 12px;
          padding: 11px 12px;
          border: 1px solid #bfdbfe;
          border-left: 5px solid #1d4ed8;
          border-radius: 6px;
          background: linear-gradient(180deg, #eff6ff 0%, #ffffff 100%);
          color: #0f172a !important;
          box-shadow: 0 1px 0 rgba(15, 23, 42, 0.04);
        }
        .shinmungo-similar-review-panel * {
          color: #0f172a !important;
        }
        .shinmungo-similar-review-eyebrow {
          margin-bottom: 4px;
          color: #1d4ed8 !important;
          font-size: 11px;
          font-weight: 900;
          letter-spacing: 0;
        }
        .shinmungo-similar-review-title {
          color: #0f172a !important;
          font-size: 15px;
          font-weight: 900;
          line-height: 1.35;
        }
        .shinmungo-similar-review-desc {
          margin-top: 5px;
          color: #475569 !important;
          font-size: 12px;
          font-weight: 650;
          line-height: 1.4;
        }
        .shinmungo-similar-card-marker {
          display: none !important;
        }
        div.st-key-shinmungo_custom_layer div[data-testid="stLayoutWrapper"] > div[data-testid="stVerticalBlock"]:has(.shinmungo-similar-card-marker):not(.st-key-shinmungo_custom_layer),
        div.st-key-shinmungo_custom_layer [data-testid="stVerticalBlockBorderWrapper"]:has(.shinmungo-similar-card-marker) {
          margin: 10px 0 12px !important;
          padding: 0 !important;
          display: block !important;
          flex: 0 0 auto !important;
          flex-basis: auto !important;
          background: #ffffff !important;
          border: 1px solid #c8d7ea !important;
          border-radius: 7px !important;
          box-shadow: 0 5px 16px rgba(15, 23, 42, 0.08) !important;
          height: auto !important;
          min-height: 198px !important;
          max-height: none !important;
          overflow: visible !important;
        }
        div.st-key-shinmungo_custom_layer div[data-testid="stLayoutWrapper"]:has(.shinmungo-similar-card-marker) {
          display: block !important;
          height: auto !important;
          min-height: 206px !important;
          max-height: none !important;
          overflow: visible !important;
          flex: 0 0 auto !important;
          flex-basis: auto !important;
        }
        div.st-key-shinmungo_custom_layer div[data-testid="stLayoutWrapper"] > div[data-testid="stVerticalBlock"]:has(.shinmungo-similar-card-marker):not(.st-key-shinmungo_custom_layer):hover,
        div.st-key-shinmungo_custom_layer [data-testid="stVerticalBlockBorderWrapper"]:has(.shinmungo-similar-card-marker):hover {
          border-color: #93c5fd !important;
          box-shadow: 0 8px 20px rgba(37, 99, 235, 0.13) !important;
        }
        div.st-key-shinmungo_custom_layer div[data-testid="stLayoutWrapper"] > div[data-testid="stVerticalBlock"]:has(.shinmungo-similar-card-marker):not(.st-key-shinmungo_custom_layer) > div,
        div.st-key-shinmungo_custom_layer [data-testid="stVerticalBlockBorderWrapper"]:has(.shinmungo-similar-card-marker) > div {
          padding: 0 !important;
          height: auto !important;
          min-height: 0 !important;
          max-height: none !important;
          overflow: visible !important;
          flex: 0 0 auto !important;
          flex-basis: auto !important;
        }
        div.st-key-shinmungo_custom_layer div[data-testid="stLayoutWrapper"] > div[data-testid="stVerticalBlock"]:has(.shinmungo-similar-card-marker):not(.st-key-shinmungo_custom_layer) [data-testid="stMarkdownContainer"],
        div.st-key-shinmungo_custom_layer [data-testid="stVerticalBlockBorderWrapper"]:has(.shinmungo-similar-card-marker) [data-testid="stMarkdownContainer"] {
          padding: 0 !important;
        }
        .shinmungo-similar-card-head {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 10px;
          padding: 12px 12px 8px;
          background: #f8fbff;
          border-bottom: 1px solid #e2e8f0;
        }
        .shinmungo-similar-card-title {
          color: #0f172a !important;
          font-size: 13px;
          font-weight: 900;
          line-height: 1.35;
        }
        .shinmungo-similar-card-title .ticket-no {
          display: inline-block;
          margin-right: 5px;
          color: #1d4ed8 !important;
          font-weight: 950;
        }
        .shinmungo-similar-card-status {
          flex: 0 0 auto;
        }
        .shinmungo-similar-card-meta {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          padding: 9px 12px 4px;
        }
        .shinmungo-similar-card-meta span {
          display: inline-flex;
          align-items: center;
          min-height: 22px;
          padding: 2px 7px;
          border: 1px solid #dbe4f0;
          border-radius: 999px;
          background: #f8fafc;
          color: #334155 !important;
          font-size: 11px;
          font-weight: 800;
          line-height: 1.2;
        }
        .shinmungo-similar-card-snippet {
          padding: 6px 12px 11px;
          color: #1f2937 !important;
          font-size: 12px;
          font-weight: 600;
          line-height: 1.45;
          word-break: keep-all;
        }
        div.st-key-shinmungo_custom_layer div[data-testid="stLayoutWrapper"] > div[data-testid="stVerticalBlock"]:has(.shinmungo-similar-card-marker):not(.st-key-shinmungo_custom_layer) [data-testid="stExpander"],
        div.st-key-shinmungo_custom_layer [data-testid="stVerticalBlockBorderWrapper"]:has(.shinmungo-similar-card-marker) [data-testid="stExpander"] {
          margin: 0 12px 10px !important;
          width: calc(100% - 24px) !important;
          max-width: calc(100% - 24px) !important;
          height: auto !important;
          min-height: 32px !important;
          max-height: none !important;
          box-sizing: border-box !important;
          border: 1px solid #e2e8f0 !important;
          border-radius: 5px !important;
          background: #f8fafc !important;
          overflow: visible !important;
        }
        div.st-key-shinmungo_custom_layer div[data-testid="stLayoutWrapper"] > div[data-testid="stVerticalBlock"]:has(.shinmungo-similar-card-marker):not(.st-key-shinmungo_custom_layer) [data-testid="stExpander"] details,
        div.st-key-shinmungo_custom_layer [data-testid="stVerticalBlockBorderWrapper"]:has(.shinmungo-similar-card-marker) [data-testid="stExpander"] details {
          width: 100% !important;
          max-width: 100% !important;
          height: auto !important;
          min-height: 32px !important;
          max-height: none !important;
          box-sizing: border-box !important;
          background: #f8fafc !important;
          color: #0f172a !important;
          border: 0 !important;
          overflow: visible !important;
        }
        div.st-key-shinmungo_custom_layer div[data-testid="stLayoutWrapper"] > div[data-testid="stVerticalBlock"]:has(.shinmungo-similar-card-marker):not(.st-key-shinmungo_custom_layer) [data-testid="stExpander"] summary,
        div.st-key-shinmungo_custom_layer [data-testid="stVerticalBlockBorderWrapper"]:has(.shinmungo-similar-card-marker) [data-testid="stExpander"] summary {
          min-height: 32px !important;
          padding: 6px 10px !important;
          background: #f8fafc !important;
          color: #0f172a !important;
          border-radius: 5px !important;
          border: 0 !important;
          box-sizing: border-box !important;
        }
        div.st-key-shinmungo_custom_layer div[data-testid="stLayoutWrapper"] > div[data-testid="stVerticalBlock"]:has(.shinmungo-similar-card-marker):not(.st-key-shinmungo_custom_layer) [data-testid="stExpander"] details[open] summary,
        div.st-key-shinmungo_custom_layer [data-testid="stVerticalBlockBorderWrapper"]:has(.shinmungo-similar-card-marker) [data-testid="stExpander"] details[open] summary {
          background: #eef6ff !important;
          color: #0f172a !important;
          border-bottom: 1px solid #dbeafe !important;
          border-radius: 5px 5px 0 0 !important;
        }
        div.st-key-shinmungo_custom_layer div[data-testid="stLayoutWrapper"] > div[data-testid="stVerticalBlock"]:has(.shinmungo-similar-card-marker):not(.st-key-shinmungo_custom_layer) [data-testid="stExpander"] summary *,
        div.st-key-shinmungo_custom_layer [data-testid="stVerticalBlockBorderWrapper"]:has(.shinmungo-similar-card-marker) [data-testid="stExpander"] summary * {
          color: #0f172a !important;
          fill: #0f172a !important;
          stroke: #0f172a !important;
          font-size: 12px !important;
          font-weight: 850 !important;
        }
        .shinmungo-similar-answer {
          padding: 8px 10px 10px;
          color: #1f2937 !important;
          font-size: 12px !important;
          font-weight: 600 !important;
          line-height: 1.45 !important;
          word-break: keep-all;
        }
        .shinmungo-similar-answer * {
          color: #1f2937 !important;
          font-size: 12px !important;
          line-height: 1.45 !important;
        }
        div.st-key-shinmungo_custom_layer div[data-testid="stLayoutWrapper"] > div[data-testid="stVerticalBlock"]:has(.shinmungo-similar-card-marker):not(.st-key-shinmungo_custom_layer) div[class*="st-key-modal_intake_helpful_"] button,
        div.st-key-shinmungo_custom_layer [data-testid="stVerticalBlockBorderWrapper"]:has(.shinmungo-similar-card-marker) div[class*="st-key-modal_intake_helpful_"] button {
          margin: 0 12px 12px !important;
          width: calc(100% - 24px) !important;
          min-height: 36px !important;
          border: 1px solid #1d4ed8 !important;
          border-radius: 5px !important;
          background: #eff6ff !important;
          color: #1e40af !important;
          font-size: 13px !important;
          font-weight: 900 !important;
        }
        div.st-key-shinmungo_custom_layer div[data-testid="stLayoutWrapper"] > div[data-testid="stVerticalBlock"]:has(.shinmungo-similar-card-marker):not(.st-key-shinmungo_custom_layer) div[class*="st-key-modal_intake_helpful_"] button *,
        div.st-key-shinmungo_custom_layer [data-testid="stVerticalBlockBorderWrapper"]:has(.shinmungo-similar-card-marker) div[class*="st-key-modal_intake_helpful_"] button * {
          color: #1e40af !important;
        }
        div.st-key-shinmungo_custom_layer div[data-testid="stLayoutWrapper"] > div[data-testid="stVerticalBlock"]:has(.shinmungo-similar-card-marker):not(.st-key-shinmungo_custom_layer) div[class*="st-key-modal_intake_helpful_"] button:hover,
        div.st-key-shinmungo_custom_layer [data-testid="stVerticalBlockBorderWrapper"]:has(.shinmungo-similar-card-marker) div[class*="st-key-modal_intake_helpful_"] button:hover {
          background: #dbeafe !important;
          border-color: #1e40af !important;
        }
        div[role="dialog"] .status-badge,
        div[data-testid="stDialog"] .status-badge {
          color: #ffffff !important;
        }
        div[role="dialog"] .status-badge *,
        div[data-testid="stDialog"] .status-badge * {
          color: #ffffff !important;
        }
        html body [data-testid="stAppViewContainer"] div.stSelectbox div[data-baseweb="select"],
        html body [data-testid="stAppViewContainer"] div.stSelectbox div[data-baseweb="select"] > div,
        html body [data-testid="stAppViewContainer"] div.stSelectbox div[data-baseweb="select"] > div > div {
          background: #ffffff !important;
          color: #111827 !important;
          box-shadow: none !important;
        }
        html body [data-testid="stAppViewContainer"] div.stSelectbox div[data-baseweb="select"] > div {
          border: 1px solid #cbd5e1 !important;
          border-radius: 0.5rem !important;
          min-height: 2.5rem !important;
        }
        html body [data-testid="stAppViewContainer"] div.stSelectbox div[data-baseweb="select"] > div:hover {
          border-color: #94a3b8 !important;
        }
        html body [data-testid="stAppViewContainer"] div.stSelectbox div[data-baseweb="select"] > div:focus-within {
          border-color: #2563eb !important;
          box-shadow: 0 0 0 1px #2563eb !important;
        }
        html body [data-testid="stAppViewContainer"] div.stSelectbox div[data-baseweb="select"] *,
        html body [data-testid="stAppViewContainer"] div.stSelectbox div[data-baseweb="select"] svg,
        html body [data-testid="stAppViewContainer"] div.stSelectbox div[data-baseweb="select"] path {
          color: #111827 !important;
          fill: #111827 !important;
          stroke: #111827 !important;
        }
        html body button[data-testid="stBaseButton-primary"],
        html body div.stButton > button[data-testid="stBaseButton-primary"],
        html body div[data-testid="stFormSubmitButton"] button,
        html body div[data-testid="stFormSubmitButton"] button[data-testid="stBaseButton-primary"] {
          background: #2563eb !important;
          border: 1px solid #1d4ed8 !important;
          color: #ffffff !important;
          box-shadow: none !important;
        }
        html body button[data-testid="stBaseButton-primary"] *,
        html body div.stButton > button[data-testid="stBaseButton-primary"] *,
        html body div[data-testid="stFormSubmitButton"] button *,
        html body div[data-testid="stFormSubmitButton"] button[data-testid="stBaseButton-primary"] * {
          color: #ffffff !important;
        }
        html body button[data-testid="stBaseButton-primary"]:hover,
        html body div.stButton > button[data-testid="stBaseButton-primary"]:hover,
        html body div[data-testid="stFormSubmitButton"] button:hover {
          background: #1d4ed8 !important;
          border-color: #1e40af !important;
          color: #ffffff !important;
        }
        div[data-testid="stLayoutWrapper"]:has(> div.st-key-admin_inquiry_workspace) {
          width: 100% !important;
          max-width: 100% !important;
          margin: 12px 0 14px !important;
        }
        div.st-key-admin_inquiry_workspace {
          background: #f8fafc !important;
          border: 1px solid var(--terminal-border) !important;
          color: #111827 !important;
          box-shadow: inset 0 0 0 1px #ffffff;
          box-sizing: border-box !important;
          padding: 0 0 10px !important;
        }
        div.st-key-admin_inquiry_workspace * {
          box-sizing: border-box;
        }
        div.st-key-admin_inquiry_workspace [data-testid="stMarkdownContainer"],
        div.st-key-admin_inquiry_workspace [data-testid="stMarkdownContainer"] p,
        div.st-key-admin_inquiry_workspace [data-testid="stWidgetLabel"],
        div.st-key-admin_inquiry_workspace [data-testid="stWidgetLabel"] p,
        div.st-key-admin_inquiry_workspace label {
          color: #111827 !important;
        }
        div.st-key-admin_inquiry_workspace > div {
          padding-left: 10px !important;
          padding-right: 10px !important;
        }
        div.st-key-admin_inquiry_workspace [data-testid="stElementContainer"]:has(.admin-workspace-title) {
          margin-left: -10px !important;
          margin-right: -10px !important;
          width: calc(100% + 20px) !important;
        }
        .admin-workspace-title {
          margin: 0 0 10px !important;
        }
        .admin-detail-subsection,
        div[class*="st-key-admin_detail_subsection_"] {
          background: #ffffff;
          border: 1px solid #d8e2ef;
          border-radius: 7px;
          padding: 10px 12px 12px;
          margin: 8px 0 12px;
          color: #111827 !important;
        }
        div[class*="st-key-admin_status_inline_"] {
          background: #f8fafc !important;
          border: 1px solid #d8e2ef !important;
          border-radius: 7px !important;
          padding: 8px 9px 7px !important;
          margin: 0 0 10px !important;
        }
        div[class*="st-key-admin_status_inline_"] [data-testid="stHorizontalBlock"] {
          align-items: center !important;
        }
        .admin-status-current {
          display: flex;
          align-items: center;
          gap: 8px;
          min-height: 36px;
          color: #111827 !important;
          margin-bottom: 7px;
        }
        .admin-status-current-label {
          color: #334155 !important;
          font-size: 12px;
          font-weight: 900;
          white-space: nowrap;
        }
        .admin-status-current .status-badge,
        .admin-status-current .status-badge * {
          color: #ffffff !important;
        }
        div[class*="st-key-admin_status_inline_"] [data-testid="stPills"] {
          margin: 0 0 7px !important;
        }
        div[class*="st-key-admin_status_inline_"] [data-testid="stPills"] button {
          min-height: 32px !important;
          border-radius: 999px !important;
          border: 1px solid #94a3b8 !important;
          background: #ffffff !important;
          color: #1f2937 !important;
          font-size: 12px !important;
          font-weight: 900 !important;
        }
        div[class*="st-key-admin_status_inline_"] [data-testid="stPills"] button * {
          color: #1f2937 !important;
        }
        div[class*="st-key-admin_status_inline_"] [data-testid="stPills"] button[aria-pressed="true"],
        div[class*="st-key-admin_status_inline_"] [data-testid="stPills"] button[aria-selected="true"] {
          background: #2563eb !important;
          border-color: #1d4ed8 !important;
          color: #ffffff !important;
        }
        div[class*="st-key-admin_status_inline_"] [data-testid="stPills"] button[aria-pressed="true"] *,
        div[class*="st-key-admin_status_inline_"] [data-testid="stPills"] button[aria-selected="true"] * {
          color: #ffffff !important;
        }
        div[class*="st-key-admin_status_pick_"] button {
          min-height: 32px !important;
          height: 32px !important;
          padding: 0 6px !important;
          border-radius: 999px !important;
          font-size: 12px !important;
          font-weight: 900 !important;
          border: 1px solid #94a3b8 !important;
          background: #ffffff !important;
          color: #1f2937 !important;
          white-space: nowrap !important;
        }
        div[class*="st-key-admin_status_pick_"] button * {
          color: #1f2937 !important;
          white-space: nowrap !important;
        }
        div[class*="st-key-admin_status_pick_"] button[data-testid="stBaseButton-primary"] {
          background: #2563eb !important;
          border-color: #1d4ed8 !important;
          color: #ffffff !important;
        }
        div[class*="st-key-admin_status_pick_"] button[data-testid="stBaseButton-primary"] * {
          color: #ffffff !important;
        }
        div[class*="st-key-admin_status_save_"] button {
          min-height: 32px !important;
          height: 32px !important;
          border-radius: 5px !important;
          font-size: 12px !important;
          font-weight: 950 !important;
          background: #1d4ed8 !important;
          border-color: #1e40af !important;
          color: #ffffff !important;
        }
        div[class*="st-key-admin_status_save_"] button * {
          color: #ffffff !important;
        }
        .admin-detail-subtitle {
          color: #102a43 !important;
          font-size: 14px;
          font-weight: 900;
          line-height: 1.2;
          margin: 14px 0 8px;
          padding: 7px 9px;
          background: #d9e8fb;
          border: 1px solid #b7cbe4;
          border-left: 5px solid #2563eb;
          border-radius: 5px;
        }
        .admin-inquiry-detail {
          font-size: 13px;
          color: #111827 !important;
        }
        .admin-saved-answers {
          margin-top: 12px;
          padding-top: 10px;
          border-top: 1px solid #d8e2ef;
        }
        .admin-saved-answers-title {
          color: #0f172a !important;
          font-size: 13px;
          font-weight: 900;
          margin-bottom: 7px;
        }
        .admin-saved-answer-card {
          background: #f8fafc;
          border: 1px solid #d8e2ef;
          border-left: 4px solid #2563eb;
          border-radius: 7px;
          padding: 9px 10px;
          margin: 7px 0;
          color: #111827 !important;
        }
        .admin-saved-answer-card * {
          color: #111827 !important;
        }
        .admin-saved-answer-date {
          color: #475569 !important;
          font-size: 12px;
          font-weight: 850;
          margin-bottom: 5px;
        }
        .admin-saved-answer-body {
          color: #1f2937 !important;
          font-size: 12px;
          line-height: 1.5;
          white-space: pre-wrap;
        }
        div.st-key-admin_inquiry_workspace div[data-testid="stMetric"] {
          background: #ffffff !important;
          border: 1px solid #d8e2ef !important;
          border-radius: 7px !important;
          padding: 8px 10px !important;
          box-shadow: 0 1px 4px rgba(15, 23, 42, 0.04) !important;
        }
        div.st-key-admin_inquiry_workspace div[data-testid="stMetric"] * {
          color: #111827 !important;
        }
        .admin-history-card {
          background: #ffffff;
          border: 1px solid #d8e2ef;
          border-left: 4px solid #64748b;
          border-radius: 7px;
          padding: 9px 11px;
          margin: 7px 0;
          color: #111827 !important;
        }
        .admin-history-card * {
          color: #111827 !important;
        }
        .admin-history-head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
          color: #0f172a !important;
          font-size: 13px;
        }
        .admin-history-head .status-badge,
        .admin-history-head .status-badge * {
          color: #ffffff !important;
          flex: 0 0 auto;
        }
        .admin-history-meta {
          color: #475569 !important;
          font-size: 12px;
          font-weight: 750;
          margin-top: 5px;
        }
        .admin-history-comment {
          color: #334155 !important;
          font-size: 12px;
          line-height: 1.45;
          margin-top: 5px;
        }
        .admin-similar-inquiry-card {
          background: #ffffff;
          border: 1px solid #cbd5e1;
          border-left: 5px solid #2563eb;
          border-radius: 8px;
          padding: 12px 14px;
          margin: 9px 0;
          color: #111827 !important;
          box-shadow: 0 1px 8px rgba(15, 23, 42, 0.06);
        }
        .admin-similar-inquiry-card * {
          color: #111827 !important;
        }
        .admin-similar-inquiry-head {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 10px;
          margin-bottom: 7px;
        }
        .admin-similar-inquiry-title {
          font-size: 14px;
          font-weight: 900;
          line-height: 1.35;
          color: #0f172a !important;
        }
        .admin-similar-inquiry-head .status-badge,
        .admin-similar-inquiry-head .status-badge * {
          color: #ffffff !important;
          flex: 0 0 auto;
        }
        .admin-similar-inquiry-meta {
          color: #475569 !important;
          font-size: 12px;
          font-weight: 750;
          margin-bottom: 8px;
        }
        .admin-similar-inquiry-answer {
          background: #f8fafc;
          border: 1px solid #e2e8f0;
          border-radius: 6px;
          color: #334155 !important;
          font-size: 12px;
          line-height: 1.5;
          padding: 8px 10px;
        }
        .admin-ai-summary {
          background: #eff6ff;
          border: 1px solid #bfdbfe;
          border-left: 5px solid #2563eb;
          border-radius: 7px;
          color: #172554 !important;
          font-size: 13px;
          line-height: 1.5;
          padding: 11px 13px;
          margin: 8px 0 12px;
        }
        .admin-ai-summary * {
          color: #172554 !important;
        }
        .admin-status-confirm-backdrop {
          position: fixed;
          inset: 0;
          z-index: 999992;
          background: rgba(15, 23, 42, 0.36);
        }
        div[data-testid="stLayoutWrapper"]:has(> div.st-key-admin_status_confirm_layer) {
          position: fixed !important;
          inset: 0 !important;
          z-index: 999993 !important;
          width: 100vw !important;
          max-width: none !important;
          height: 100vh !important;
          pointer-events: none !important;
          background: transparent !important;
        }
        div.st-key-admin_status_confirm_layer {
          position: fixed !important;
          left: 50% !important;
          top: 50% !important;
          transform: translate(-50%, -50%) !important;
          width: min(520px, 92vw) !important;
          max-width: min(520px, 92vw) !important;
          min-height: 330px !important;
          max-height: 80vh !important;
          overflow-y: auto !important;
          pointer-events: auto !important;
          box-sizing: border-box !important;
          background: #ffffff !important;
          border: 1px solid #334155 !important;
          border-radius: 9px !important;
          box-shadow: 0 24px 70px rgba(15, 23, 42, 0.34) !important;
          padding: 18px !important;
          color: #111827 !important;
        }
        div.st-key-admin_status_confirm_layer *,
        div.st-key-admin_status_confirm_layer [data-testid="stMarkdownContainer"],
        div.st-key-admin_status_confirm_layer p,
        div.st-key-admin_status_confirm_layer span,
        div.st-key-admin_status_confirm_layer label {
          color: #111827 !important;
        }
        .admin-status-confirm-copy .confirm-eyebrow {
          color: #2563eb !important;
          font-size: 12px;
          font-weight: 900;
          margin-bottom: 5px;
        }
        .admin-status-confirm-copy .confirm-title {
          color: #0f172a !important;
          font-size: 20px;
          font-weight: 950;
          margin-bottom: 5px;
        }
        .admin-status-confirm-copy .confirm-desc {
          color: #475569 !important;
          font-size: 13px;
          font-weight: 800;
          margin-bottom: 12px;
        }
        div.st-key-admin_status_confirm_layer textarea {
          background: #ffffff !important;
          color: #111827 !important;
          border: 1px solid #cbd5e1 !important;
        }
        div.st-key-admin_status_confirm_layer div.stButton > button {
          min-height: 2.35rem !important;
          border-radius: 5px !important;
          font-weight: 900 !important;
        }
        @media (max-width: 640px) {
          div[role="dialog"],
          div[data-testid="stDialog"],
          div.stDialog > div {
            width: 94vw !important;
            max-width: 94vw !important;
            height: 88vh !important;
            max-height: 88vh !important;
          }
          div.stDialog {
            padding: 10px !important;
          }
          div.stDialog div[role="dialog"] > div:nth-of-type(2) {
            padding: 12px !important;
          }
          div.stDialog div[role="dialog"] > button {
            top: 17px !important;
            right: 16px !important;
          }
        }
        </style>
        """,
    )


def sidebar_user() -> CurrentUser:
    st.sidebar.header("직원 정보")

    _prepare_user_state()

    role = st.sidebar.radio(
        "역할",
        ROLE_OPTIONS,
        horizontal=True,
        key="role",
        format_func=lambda value: ROLE_LABELS.get(value, value),
    )
    _apply_role_navigation_visibility(role)
    role_widget_epoch = _sidebar_role_widget_epoch(role)

    if role == "관리자":
        department = st.sidebar.selectbox("본부부서", HQ_DEPARTMENT_OPTIONS, key="hq_department")
        _sync_hq_employee_defaults(department)
        default_id, default_name = _hq_default_user(department)
        employee_id = (
            st.sidebar.text_input(
                "직원ID",
                value=st.session_state.get("hq_employee_id", default_id),
                key=f"hq_employee_id_input_{role_widget_epoch}",
            ).strip()
            or default_id
        )
        name = (
            st.sidebar.text_input(
                "직원명",
                value=st.session_state.get("hq_employee_name", default_name),
                key=f"hq_employee_name_input_{role_widget_epoch}",
            ).strip()
            or default_name
        )
        st.session_state["hq_employee_id"] = employee_id
        st.session_state["hq_employee_name"] = name
        st.session_state["employee_id"] = employee_id
        st.session_state["employee_name"] = name
        st.session_state["branch"] = department
        _remember_user_state()
        return CurrentUser(employee_id=employee_id, name=name, branch=department, role=role)

    branch = st.sidebar.selectbox("영업점", BRANCH_OPTIONS, key="branch_name")
    employee_id = (
        st.sidebar.text_input(
            "직원ID",
            value=st.session_state.get("branch_employee_id", DEFAULT_BRANCH_EMPLOYEE_ID),
            key=f"branch_employee_id_input_{role_widget_epoch}",
        ).strip()
        or DEFAULT_BRANCH_EMPLOYEE_ID
    )
    name = (
        st.sidebar.text_input(
            "직원명",
            value=st.session_state.get("branch_employee_name", DEFAULT_BRANCH_EMPLOYEE_NAME),
            key=f"branch_employee_name_input_{role_widget_epoch}",
        ).strip()
        or DEFAULT_BRANCH_EMPLOYEE_NAME
    )
    st.session_state["branch_employee_id"] = employee_id
    st.session_state["branch_employee_name"] = name
    st.session_state["employee_id"] = employee_id
    st.session_state["employee_name"] = name
    st.session_state["branch"] = branch
    _remember_user_state()
    return CurrentUser(employee_id=employee_id, name=name, branch=branch, role=role)


def _sidebar_role_widget_epoch(role: str) -> int:
    previous_role = st.session_state.get("_sidebar_previous_role")
    if previous_role != role:
        st.session_state["_sidebar_widget_epoch"] = st.session_state.get("_sidebar_widget_epoch", 0) + 1
        st.session_state["_sidebar_previous_role"] = role
    return int(st.session_state.get("_sidebar_widget_epoch", 0))


def _apply_role_navigation_visibility(role: str) -> None:
    if role != "직원":
        return
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


def _prepare_user_state() -> None:
    if st.session_state.get("role") not in ROLE_OPTIONS:
        st.session_state["role"] = _LAST_UI_USER_STATE["role"]

    previous_employee_id = str(st.session_state.get("employee_id", "")).strip()
    previous_employee_name = str(st.session_state.get("employee_name", "")).strip()
    if not previous_employee_id or previous_employee_id in HQ_EMPLOYEE_IDS:
        previous_employee_id = DEFAULT_BRANCH_EMPLOYEE_ID
    if not previous_employee_name or previous_employee_name in HQ_EMPLOYEE_NAMES:
        previous_employee_name = DEFAULT_BRANCH_EMPLOYEE_NAME

    if "branch_employee_id" not in st.session_state:
        st.session_state["branch_employee_id"] = _LAST_UI_USER_STATE.get("branch_employee_id") or previous_employee_id
    if "branch_employee_name" not in st.session_state:
        st.session_state["branch_employee_name"] = _LAST_UI_USER_STATE.get("branch_employee_name") or previous_employee_name
    if not str(st.session_state.get("branch_employee_id", "")).strip():
        st.session_state["branch_employee_id"] = DEFAULT_BRANCH_EMPLOYEE_ID
    if not str(st.session_state.get("branch_employee_name", "")).strip():
        st.session_state["branch_employee_name"] = DEFAULT_BRANCH_EMPLOYEE_NAME
    if st.session_state.get("branch_name") not in BRANCH_OPTIONS:
        st.session_state["branch_name"] = _LAST_UI_USER_STATE.get("branch_name", "리테일 영업점")
    if st.session_state.get("hq_department") not in HQ_DEPARTMENT_OPTIONS:
        st.session_state["hq_department"] = _LAST_UI_USER_STATE.get("hq_department", DEFAULT_HQ_DEPARTMENT)
    _sync_hq_employee_defaults(st.session_state["hq_department"])


def _hq_default_user(department: str) -> tuple[str, str]:
    return HQ_DEPARTMENT_USERS.get(department, HQ_DEPARTMENT_USERS[DEFAULT_HQ_DEPARTMENT])


def _sync_hq_employee_defaults(department: str) -> None:
    default_id, default_name = _hq_default_user(department)
    previous_department = st.session_state.get("_hq_employee_department")
    previous_default_id, previous_default_name = _hq_default_user(previous_department or department)
    department_changed = previous_department != department

    current_id = str(st.session_state.get("hq_employee_id", "")).strip()
    current_name = str(st.session_state.get("hq_employee_name", "")).strip()

    if department_changed and (not current_id or current_id == previous_default_id):
        current_id = default_id
    if department_changed and (not current_name or current_name == previous_default_name):
        current_name = default_name

    if not current_id:
        current_id = _LAST_UI_USER_STATE.get("hq_employee_id") or default_id
    if not current_name:
        current_name = _LAST_UI_USER_STATE.get("hq_employee_name") or default_name

    st.session_state["hq_employee_id"] = current_id
    st.session_state["hq_employee_name"] = current_name
    st.session_state["_hq_employee_department"] = department


def _remember_user_state() -> None:
    _LAST_UI_USER_STATE["role"] = st.session_state.get("role", "직원")
    _LAST_UI_USER_STATE["branch_employee_id"] = st.session_state.get("branch_employee_id", DEFAULT_BRANCH_EMPLOYEE_ID)
    _LAST_UI_USER_STATE["branch_employee_name"] = st.session_state.get("branch_employee_name", DEFAULT_BRANCH_EMPLOYEE_NAME)
    _LAST_UI_USER_STATE["branch_name"] = st.session_state.get("branch_name", "리테일 영업점")
    _LAST_UI_USER_STATE["hq_department"] = st.session_state.get("hq_department", DEFAULT_HQ_DEPARTMENT)
    _LAST_UI_USER_STATE["hq_employee_id"] = st.session_state.get(
        "hq_employee_id", HQ_DEPARTMENT_USERS[DEFAULT_HQ_DEPARTMENT][0]
    )
    _LAST_UI_USER_STATE["hq_employee_name"] = st.session_state.get(
        "hq_employee_name", HQ_DEPARTMENT_USERS[DEFAULT_HQ_DEPARTMENT][1]
    )


def current_user() -> CurrentUser:
    _prepare_user_state()
    role = st.session_state.get("role", "직원")
    if role == "관리자":
        department = st.session_state.get("hq_department", DEFAULT_HQ_DEPARTMENT)
        _sync_hq_employee_defaults(department)
        employee_id = str(st.session_state.get("hq_employee_id", "")).strip() or _hq_default_user(department)[0]
        name = str(st.session_state.get("hq_employee_name", "")).strip() or _hq_default_user(department)[1]
        st.session_state["employee_id"] = employee_id
        st.session_state["employee_name"] = name
        st.session_state["branch"] = department
        _remember_user_state()
        return CurrentUser(employee_id=employee_id, name=name, branch=department, role=role)

    employee_id = st.session_state.get("branch_employee_id", DEFAULT_BRANCH_EMPLOYEE_ID)
    name = st.session_state.get("branch_employee_name", DEFAULT_BRANCH_EMPLOYEE_NAME)
    branch = st.session_state.get("branch_name", "리테일 영업점")
    st.session_state["employee_id"] = employee_id
    st.session_state["employee_name"] = name
    st.session_state["branch"] = branch
    _remember_user_state()
    return CurrentUser(employee_id=employee_id, name=name, branch=branch, role=role)


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def status_badge(status: str) -> str:
    label = html.escape(status_label(status))
    color = STATUS_COLORS.get(status, "#64748b")
    return f'<span class="status-badge" style="background:{color}">{label}</span>'


def terminal_topbar(user: CurrentUser, subtitle: str = "업무 화면") -> None:
    st.markdown(
        f"""
        <div class="terminal-shell">
          <div class="terminal-topbar">
            <div><span class="terminal-brand">OO은행 통합단말</span> <span style="opacity:.82">| {html.escape(subtitle)}</span></div>
            <div class="terminal-user">{html.escape(user.branch)} · {html.escape(user.name)} [{html.escape(user.employee_id)}]</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def html_escape(value: object) -> str:
    return html.escape("" if value is None else str(value))


def switch_page(path: str) -> None:
    if hasattr(st, "switch_page"):
        st.switch_page(path)
    st.info(f"좌측 페이지 목록에서 `{path}`로 이동해 주세요.")
