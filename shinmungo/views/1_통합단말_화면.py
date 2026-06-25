from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote_plus

import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.area_selector_component import area_selector_component
from services.db import get_session, init_db
from services.intake_form import (
    clear_intake_state,
    clear_selected_area,
    render_helpful_confirm_layer,
    render_intake_form,
)
from services.models import Screen
from services.seed import seed_if_empty
from services.ui import CurrentUser, apply_page_config, apply_styles, current_user, html_escape


def ensure_data() -> None:
    init_db()
    session = get_session()
    try:
        seed_if_empty(session)
    finally:
        session.close()


def screen_options() -> list[Screen]:
    session = get_session()
    try:
        return session.query(Screen).order_by(Screen.screen_code).all()
    finally:
        session.close()


def screen_display_name(screen: Screen) -> str:
    display_names = {
        "111": "계좌/카드 동시신규",
        "827": "퇴직연금 보유상품 변경",
    }
    return display_names.get(screen.screen_code, screen.screen_name)


def screen_search_value(screen: Screen) -> str:
    return f"{screen.screen_code} - {screen_display_name(screen)}"


def area_attrs(area_id: str, area_name: str, area_type: str) -> str:
    return (
        'data-shinmungo-target="true" '
        f'data-area-id="{html_escape(area_id)}" '
        f'data-area-name="{html_escape(area_name)}" '
        f'data-area-type="{html_escape(area_type)}"'
    )


def extract_screen_code(query: str) -> str:
    match = re.search(r"\d+", query.strip())
    return match.group(0) if match else ""


def normalize_screen_query(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]", "", value).lower()


def resolve_screen_code(query: str, screen_names: dict[str, str]) -> str:
    normalized_query = normalize_screen_query(query)
    if not normalized_query:
        return ""
    aliases = {
        "111": ["111", "계좌카드동시신규", "계좌카드", "카드동시신규", "동시신규"],
        "827": ["827", "퇴직연금보유상품변경", "보유상품변경", "퇴직연금"],
    }
    for code, screen_name in screen_names.items():
        normalized_name = normalize_screen_query(screen_name)
        if normalized_query == code or normalized_query in normalized_name or normalized_name in normalized_query:
            return code
    for code, keywords in aliases.items():
        if any(normalize_screen_query(keyword) in normalized_query for keyword in keywords):
            return code
    return ""


def handle_screen_search_submit(valid_codes: list[str], screen_names: dict[str, str]) -> None:
    query = str(st.session_state.get("screen_search_query") or "")
    requested_code = resolve_screen_code(query, screen_names)
    st.session_state["show_shinmungo_dialog"] = False
    st.session_state["terminal_area_select_mode"] = False
    if requested_code in valid_codes:
        st.session_state["selected_terminal_screen_code"] = requested_code
        st.session_state["screen_search_pending_value"] = ""
        st.session_state["screen_access_denied"] = False
        return
    st.session_state["screen_access_denied"] = True
    st.session_state["screen_access_denied_query"] = query


def handle_screen_search_query_param(valid_codes: list[str], screen_names: dict[str, str]) -> None:
    raw_query = st.query_params.get("screen_query")
    if not raw_query:
        return
    if isinstance(raw_query, list):
        raw_query = raw_query[0] if raw_query else ""
    query = str(raw_query)
    requested_code = resolve_screen_code(query, screen_names)
    st.session_state["screen_search_query"] = ""
    st.session_state["screen_search_pending_value"] = ""
    st.session_state["show_shinmungo_dialog"] = False
    st.session_state["terminal_area_select_mode"] = False
    if requested_code in valid_codes:
        st.session_state["selected_terminal_screen_code"] = requested_code
        st.session_state["screen_access_denied"] = False
    else:
        st.session_state["screen_access_denied"] = True
        st.session_state["screen_access_denied_query"] = query
    del st.query_params["screen_query"]


def apply_area_selection_payload(raw_payload: object) -> bool:
    if isinstance(raw_payload, dict):
        payload = raw_payload
    else:
        if isinstance(raw_payload, list):
            raw_payload = raw_payload[0] if raw_payload else ""
        raw_payload = str(raw_payload)
        raw_payload = unquote_plus(raw_payload)
        try:
            payload = json.loads(raw_payload)
        except json.JSONDecodeError:
            st.session_state["terminal_area_selection_error"] = raw_payload[:300]
            return False
    if not isinstance(payload, dict) or not payload.get("area_name"):
        st.session_state["terminal_area_selection_error"] = str(raw_payload)[:300]
        return False
    st.session_state["current_selected_area"] = payload
    st.session_state["current_selected_area_json"] = json.dumps(payload, ensure_ascii=False)
    st.session_state["terminal_area_select_mode"] = False
    st.session_state["screen_access_denied"] = False
    st.session_state["show_shinmungo_dialog"] = True
    st.session_state["current_screen_code"] = str(payload.get("screen_code") or "")
    st.session_state["current_screen_name"] = str(payload.get("screen_name") or "")
    st.session_state["current_business_category"] = str(payload.get("business_category") or "")
    st.session_state["selected_terminal_screen_code"] = str(payload.get("screen_code") or "")
    st.session_state.pop("terminal_area_selection_error", None)
    return True


def cancel_area_selection() -> None:
    st.session_state["terminal_area_select_mode"] = False
    st.session_state["screen_access_denied"] = False
    st.session_state["show_shinmungo_dialog"] = True


def clear_dialog_state() -> None:
    st.session_state["screen_access_denied"] = False
    st.session_state["show_shinmungo_dialog"] = False
    st.session_state["terminal_area_select_mode"] = False


def clear_access_denied_state() -> None:
    clear_dialog_state()
    st.session_state["screen_search_reset_requested"] = True
    st.session_state["screen_search_force_clear_dom"] = True
    st.session_state.pop("screen_access_denied_query", None)


def render_frontend_state_guard() -> None:
    components.html(
        """
        <script>
        (() => {
          const win = window.parent;
          const doc = win.document;
          const version = "shinmungo-layer-popup-v2";
          const storageKey = "shinmungo_app_ui_version";

          const removeStaleDialogException = () => {
            doc.querySelectorAll('[data-testid="stException"]').forEach((node) => {
              const text = node.innerText || "";
              const isOldDialogError =
                text.includes("Only one dialog is allowed") ||
                text.includes("render_shinmungo_dialog") ||
                text.includes("dialog_decorator.py");
              if (isOldDialogError) {
                node.style.display = "none";
                const wrapper = node.closest('[data-testid="stElementContainer"], .element-container');
                if (wrapper) wrapper.style.display = "none";
              }
            });
          };

          const removeDuplicateAccessAlerts = () => {
            const roots = Array.from(doc.querySelectorAll('.terminal-access-alert-root'));
            roots.slice(0, -1).forEach((node) => node.remove());
            const layers = Array.from(doc.querySelectorAll('.st-key-access_denied_layer'));
            layers.forEach((node) => node.remove());
            doc.querySelectorAll('.terminal-access-alert-overlay').forEach((node) => node.remove());
          };

          removeStaleDialogException();
          removeDuplicateAccessAlerts();
          let runs = 0;
          const timer = win.setInterval(() => {
            removeStaleDialogException();
            removeDuplicateAccessAlerts();
            runs += 1;
            if (runs > 20) win.clearInterval(timer);
          }, 150);

          try {
            const currentVersion = win.localStorage.getItem(storageKey);
            if (currentVersion !== version) {
              win.localStorage.setItem(storageKey, version);
              win.setTimeout(() => win.location.reload(), 50);
            }
          } catch (error) {
            // localStorage can be unavailable in restricted browser modes.
          }
        })();
        </script>
        """,
        height=0,
    )


def handle_area_selection_query_params() -> None:
    area_payload = st.query_params.get("area_payload")
    area_cancel = st.query_params.get("area_select_cancel")
    if area_payload:
        applied = apply_area_selection_payload(area_payload)
        del st.query_params["area_payload"]
        if applied:
            st.rerun()
    if area_cancel:
        cancel_area_selection()
        del st.query_params["area_select_cancel"]
        st.rerun()


def handle_access_denied_query_params() -> None:
    if not st.query_params.get("access_denied_clear"):
        return
    clear_access_denied_state()
    del st.query_params["access_denied_clear"]
    st.rerun()


def handle_shinmungo_close_query_params() -> None:
    if not st.query_params.get("shinmungo_close"):
        return
    clear_intake_state("modal_intake", clear_inputs=True)
    clear_selected_area()
    clear_dialog_state()
    del st.query_params["shinmungo_close"]
    st.rerun()


def render_access_denied_layer() -> None:
    st.markdown(
        """
        <div class="terminal-access-alert-root">
          <div class="terminal-access-alert-backdrop"></div>
          <div class="terminal-access-alert-box">
            <div class="terminal-access-alert-text">접근 권한이 없는 화면입니다.</div>
            <a class="terminal-access-alert-button" href="?access_denied_clear=1" target="_self">확인</a>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_follow_completion_layer() -> None:
    clear_key = "shinmungo_completion_alert"
    payload = st.session_state.get(clear_key)
    if isinstance(payload, dict):
        message = str(
            payload.get("message")
            or "접수가 완료되었습니다. 진행 상황은 '내 접수내역'에서 확인 가능합니다."
        )
    else:
        clear_key = "shinmungo_follow_alert"
        payload = st.session_state.get(clear_key)
        if not isinstance(payload, dict):
            return

        created = bool(payload.get("created", True))
        mode = str(payload.get("mode") or "share")
        if mode == "completed":
            message = "통합 단말 개선을 위해 관심을 가져주셔서 감사합니다."
        elif not created:
            message = (
                "이미 선택하신 요청사항의 진행 상황을 공유받고 있습니다. "
                "진행 상황은 '내 접수내역'에서 확인하실 수 있습니다."
            )
        else:
            message = (
                "선택하신 요청사항의 진행 상황을 공유받도록 등록했습니다. "
                "진행 상황은 '내 접수내역'에서 확인하실 수 있습니다."
            )

    if not isinstance(payload, dict):
        return

    st.html('<div class="shinmungo-follow-alert-backdrop"></div>')
    with st.container(key="shinmungo_follow_alert_layer"):
        st.success(message)
        if st.button("확인", key="shinmungo_follow_alert_ok", type="primary", use_container_width=True):
            st.session_state.pop(clear_key, None)
            st.rerun()


def render_shinmungo_layer(screen: Screen, user: CurrentUser, error_log: str) -> None:
    st.html('<div class="shinmungo-custom-backdrop"></div>')
    with st.container(key="shinmungo_custom_layer"):
        st.markdown(
            """
            <div class="shinmungo-popup-header">
              <div class="shinmungo-popup-title">통합단말 신문고</div>
              <a class="shinmungo-popup-close-link" href="?shinmungo_close=1" target="_self">닫기</a>
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_intake_form(
            screen=screen,
            user=user,
            error_log=error_log,
            namespace="modal_intake",
            completion_mode="dialog",
        )
    render_helpful_confirm_layer("modal_intake", employee_id=user.employee_id)


def render_terminal_header(user_name: str, employee_id: str, branch: str, screen: Screen) -> None:
    st.html(
        f"""
        <div class="terminal-shell">
          <div class="terminal-topbar">
            <div><span class="terminal-brand">OO은행 통합단말</span>
              <span style="opacity:.82"> | {html_escape(screen.screen_code)} {html_escape(screen.screen_name)}</span>
            </div>
            <div class="terminal-user">{html_escape(branch)} · {html_escape(user_name)} [{html_escape(employee_id)}]</div>
          </div>
        </div>
        """,
    )


def render_left_panel(screen: Screen) -> None:
    st.markdown(
        f"""
        <div class="terminal-left">
          <div class="mini-rail">☰</div>
          <div class="section-box" {area_attrs("left-screen-info", "화면 정보", "좌측패널")}>
            <div class="section-title">화면 정보</div>
            <div class="section-content">
              <table class="dense-table">
                <tr><th>화면번호</th><td>{html_escape(screen.screen_code)}</td></tr>
                <tr><th>업무영역</th><td>{html_escape(screen.business_category)}</td></tr>
                <tr><th>상태</th><td>조회 가능</td></tr>
              </table>
            </div>
          </div>
          <div class="section-box" {area_attrs("left-customer-search", "고객/계약 검색", "좌측패널")}>
            <div class="section-title">고객/계약 검색</div>
            <div class="section-content">
              <table class="dense-table">
                <tr><th>고객번호</th><td>401623510</td></tr>
                <tr><th>실명번호</th><td>******-1******</td></tr>
                <tr><th>거래일자</th><td>{datetime.now().strftime("%Y.%m.%d")}</td></tr>
                <tr><th>창구</th><td>일반</td></tr>
              </table>
            </div>
          </div>
          <div class="section-box" {area_attrs("left-quick-actions", "빠른 거래", "좌측패널")}>
            <div class="section-title">빠른 거래</div>
            <div class="section-content">
              <div class="fake-button">고객정보 조회</div>
              <div style="height:5px"></div>
              <div class="fake-button">전자문서</div>
              <div style="height:5px"></div>
              <div class="fake-button">통합인자</div>
              <div style="height:5px"></div>
              <div class="fake-button">거래 정정</div>
            </div>
          </div>
          <div class="section-box" {area_attrs("left-kyc-info", "KYC 정보", "좌측패널")}>
            <div class="section-title">KYC 정보</div>
            <div class="section-content">
              <table class="dense-table">
                <tr><th>CDD</th><td>완료</td></tr>
                <tr><th>EDD</th><td>대상아님</td></tr>
                <tr><th>FATCA</th><td>확인</td></tr>
              </table>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_screen_111() -> None:
    st.markdown(
        f"""
        <div class="terminal-main">
          <div class="terminal-tab-row" {area_attrs("111-tabs", "업무 탭", "탭영역")}>
            <div class="terminal-tab active">기업/개인현황</div>
            <div class="terminal-tab">전자금융</div>
            <div class="terminal-tab">체크카드</div>
            <div class="terminal-tab">처리 History</div>
          </div>
          <div class="action-strip" {area_attrs("111-actions", "상단 거래 버튼", "액션버튼")}>
            <div class="fake-button">초기화</div><div class="fake-button">조회</div>
            <div class="fake-button">고객통합정보</div><div class="fake-button">통합인자</div>
          </div>
          <div class="section-box" {area_attrs("111-basic-new", "계좌 + 카드 동시신규", "업무패널")}>
            <div class="section-title">[111] 계좌 + 카드 동시신규</div>
            <div class="section-content">
              <div class="kv-grid">
                <div class="kv-label">고객번호</div><div>401623510</div>
                <div class="kv-label">실명확인</div><div>주민등록증 확인</div>
                <div class="kv-label">거래흐름</div><div>유동성 → 전자금융 → 체크카드</div>
                <div class="kv-label">오류처리</div><div>재거래 후 통합인자</div>
                <div class="kv-label">전자금융</div><div>모바일OTP / 실물OTP</div>
                <div class="kv-label">체크카드</div><div>일반 / 학생증 / 글로벌</div>
              </div>
            </div>
          </div>
          <div class="section-box" {area_attrs("111-progress", "거래 진행 상태", "업무패널")}>
            <div class="section-title">거래 진행 상태</div>
            <div class="section-content">
              <table class="dense-table">
                <tr><th>단계</th><th>업무</th><th>처리상태</th><th>비고</th></tr>
                <tr><td>1</td><td>유동성 신규</td><td>정상</td><td>입출금 계좌 개설</td></tr>
                <tr><td>2</td><td>전자금융 신규</td><td>확인중</td><td>모바일OTP 선택</td></tr>
                <tr><td>3</td><td>체크카드 신규</td><td>대기</td><td>상품조회 후 진행</td></tr>
                <tr><td>4</td><td>통합인자</td><td>대기</td><td>초기화 전 가능</td></tr>
              </table>
            </div>
          </div>
          <div class="section-box" {area_attrs("111-extra-transactions", "부가 거래", "업무패널")}>
            <div class="section-title">부가 거래</div>
            <div class="section-content">
              <table class="dense-table">
                <tr><th>CDD/EDD/FATCA</th><td>실명번호 기준 대상 거래 제공</td><th>태블릿뱅킹</th><td>방문판매 후 비밀번호등록 연계</td></tr>
                <tr><th>나라사랑카드</th><td>발급자격조회 기관 전문 제공</td><th>상품조회</th><td>#941260 제공 상품과 일부 상이</td></tr>
              </table>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_screen_827() -> None:
    st.markdown(
        f"""
        <div class="terminal-main">
          <div class="terminal-tab-row" {area_attrs("827-tabs", "업무 탭", "탭영역")}>
            <div class="terminal-tab active">보유상품변경</div>
            <div class="terminal-tab">상품조회</div>
            <div class="terminal-tab">매도/매수</div>
            <div class="terminal-tab">처리 History</div>
          </div>
          <div class="action-strip" {area_attrs("827-actions", "상단 거래 버튼", "액션버튼")}>
            <div class="fake-button">조회</div><div class="fake-button">상품검색</div>
            <div class="fake-button">투자성향</div><div class="fake-button">처리결과</div>
          </div>
          <div class="section-box" {area_attrs("827-product-change", "퇴직연금 보유상품변경", "업무패널")}>
            <div class="section-title">[827] 퇴직연금 보유상품변경</div>
            <div class="section-content">
              <div class="kv-grid">
                <div class="kv-label">계약유형</div><div>DB / DC / IRP</div>
                <div class="kv-label">거래구분</div><div>기본: 비율 / 상세: 금액</div>
                <div class="kv-label">상품범위</div><div>원리금보장 / 원리금비보장</div>
                <div class="kv-label">상품개수</div><div>매도·매수 최대 5개</div>
                <div class="kv-label">ETF</div><div>통합단말 거래 불가</div>
                <div class="kv-label">매수일</div><div>지정일 매수 / 분할매수</div>
              </div>
            </div>
          </div>
          <div class="section-box" {area_attrs("827-holdings", "보유상품 현황", "업무패널")}>
            <div class="section-title">보유상품 현황</div>
            <div class="section-content">
              <table class="dense-table">
                <tr><th>상품명</th><th>구분</th><th>평가금액</th><th>만기</th><th>변경가능</th></tr>
                <tr><td>정기예금 12M</td><td>원리금보장</td><td>35,000,000</td><td>2026.07.15</td><td>가능</td></tr>
                <tr><td>TDF 2045</td><td>원리금비보장</td><td>12,500,000</td><td>-</td><td>상품조회 필요</td></tr>
                <tr><td>ELB 6M</td><td>원리금보장</td><td>8,000,000</td><td>2026.06.30</td><td>현금성 대기자산 거래</td></tr>
              </table>
            </div>
          </div>
          <div class="section-box" {area_attrs("827-buy-settings", "매수 지정", "업무패널")}>
            <div class="section-title">매수 지정</div>
            <div class="section-content">
              <table class="dense-table">
                <tr><th>거래구분</th><td>상세</td><th>매수방식</th><td>금액 지정</td></tr>
                <tr><th>분할매수</th><td>사용</td><th>지정일 매수</th><td>2026.07.01</td></tr>
                <tr><th>선행조건</th><td colspan="3">원리금비보장 상품 조회 전 투자자성향분석 완료 필요</td></tr>
              </table>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_area_selection_bridge(screen: Screen) -> None:
    active = (
        bool(st.session_state.get("terminal_area_select_mode"))
        and str(st.session_state.get("terminal_area_select_screen_code") or "") == screen.screen_code
    )
    if not active:
        components.html(
            """
            <script>
            const win = window.parent;
            const doc = win.document;
            if (win.__shinmungoAreaSelectorCleanup) {
              win.__shinmungoAreaSelectorCleanup();
            }
            doc.querySelector('#shinmungo-area-selection-box')?.remove();
            doc.querySelector('#shinmungo-area-selection-label')?.remove();
            doc.querySelector('#shinmungo-area-selection-guide')?.remove();
            doc.body.classList.remove('shinmungo-area-selecting');
            </script>
            """,
            height=0,
        )
        return
    if st.button("취소", key="area_select_cancel_button"):
        cancel_area_selection()
        st.rerun()
    selection_value = area_selector_component(
        active=True,
        screen={
            "screen_code": screen.screen_code,
            "screen_name": screen.screen_name,
            "business_category": screen.business_category,
        },
        key=f"area_selector_{screen.screen_code}",
        default=None,
    )
    if not selection_value:
        return
    if isinstance(selection_value, dict) and selection_value.get("cancelled"):
        cancel_area_selection()
        st.rerun()
    if apply_area_selection_payload(selection_value):
        st.rerun()


def main() -> None:
    apply_page_config("통합단말 화면")
    apply_styles()
    render_frontend_state_guard()
    ensure_data()
    user = current_user()
    screens = screen_options()
    if not screens:
        st.error("화면 기준정보가 없습니다.")
        return
    handle_area_selection_query_params()
    handle_access_denied_query_params()
    handle_shinmungo_close_query_params()

    screen_by_code = {screen.screen_code: screen for screen in screens}
    screen_search_names = {
        screen.screen_code: screen.screen_name
        for screen in screens
    }
    valid_screen_codes = list(screen_by_code.keys())
    handle_screen_search_query_param(valid_screen_codes, screen_search_names)

    if st.session_state.pop("screen_search_reset_requested", False):
        st.session_state["screen_search_query"] = ""
        st.session_state["screen_search_pending_value"] = ""
    force_clear_search_dom = bool(st.session_state.pop("screen_search_force_clear_dom", False))

    pending_search_value = st.session_state.pop("screen_search_pending_value", None)
    if pending_search_value is not None:
        st.session_state["screen_search_query"] = pending_search_value
    elif "screen_search_query" not in st.session_state:
        st.session_state["screen_search_query"] = ""
    elif st.session_state["screen_search_query"] in {screen_search_value(screen) for screen in screens}:
        st.session_state["screen_search_query"] = ""

    base_screen_code = "111" if "111" in screen_by_code else screens[0].screen_code
    selected_code = str(st.session_state.get("selected_terminal_screen_code") or base_screen_code)
    if selected_code not in screen_by_code:
        selected_code = base_screen_code
    st.session_state["selected_terminal_screen_code"] = selected_code
    selected_screen = screen_by_code[selected_code]

    search_cols = st.columns([0.76, 0.24], gap="small")
    with search_cols[0]:
        with st.form("screen_search_form", border=False):
            form_cols = st.columns([0.9, 0.1], gap="small")
            with form_cols[0]:
                st.text_input(
                    "화면번호 검색",
                    key="screen_search_query",
                    label_visibility="collapsed",
                    placeholder="화면번호 또는 화면명을 검색하세요.",
                )
            with form_cols[1]:
                search_submitted = st.form_submit_button("🔍", use_container_width=True)
        if search_submitted:
            handle_screen_search_submit(valid_screen_codes, screen_search_names)
            st.rerun()
        components.html(
            f"""
            <script>
            const clearScreenSearchInput = () => {{
              const doc = window.parent.document;
              const input = doc.querySelector('.st-key-screen_search_query input');
              if (input) {{
                input.value = '';
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
              }}
            }};
            const bindScreenSearchFormEnter = () => {{
              const doc = window.parent.document;
              const input = doc.querySelector('.st-key-screen_search_query input');
              const button = doc.querySelector('.st-key-FormSubmitter-screen_search_form--- button');
              if (!input || !button || input.dataset.screenSearchFormEnterBound === '1') return;
              input.dataset.screenSearchFormEnterBound = '1';
              input.addEventListener('keydown', (event) => {{
                if (event.key !== 'Enter') return;
                event.preventDefault();
                event.stopPropagation();
                window.setTimeout(() => button.click(), 20);
              }});
            }};
            if ({str(force_clear_search_dom).lower()}) {{
              clearScreenSearchInput();
              window.setTimeout(clearScreenSearchInput, 100);
              window.setTimeout(clearScreenSearchInput, 400);
            }}
            bindScreenSearchFormEnter();
            window.setTimeout(bindScreenSearchFormEnter, 250);
            window.setTimeout(bindScreenSearchFormEnter, 750);
            </script>
            """,
            height=0,
        )
    with search_cols[1]:
        if st.button("📢 통합단말 신문고", type="primary", key="open_shinmungo_from_search", use_container_width=True):
            st.session_state["screen_access_denied"] = False
            st.session_state["terminal_area_select_mode"] = False
            st.session_state["current_screen_code"] = selected_screen.screen_code
            st.session_state["current_screen_name"] = selected_screen.screen_name
            st.session_state["current_business_category"] = selected_screen.business_category
            st.session_state["current_error_log"] = (
                f"[자동첨부] screen={selected_screen.screen_code}, "
                f"name={selected_screen.screen_name}, branch={user.branch}, "
                f"employee={user.employee_id}, captured_at={datetime.now().isoformat(timespec='seconds')}"
            )
            st.session_state["show_shinmungo_dialog"] = True
    access_denied_active = bool(st.session_state.get("screen_access_denied"))
    if access_denied_active:
        st.session_state["show_shinmungo_dialog"] = False
        st.session_state["terminal_area_select_mode"] = False
        render_access_denied_layer()
    render_follow_completion_layer()

    render_terminal_header(user.name, user.employee_id, user.branch, selected_screen)

    if not access_denied_active and st.session_state.get("show_shinmungo_dialog"):
        context_code = str(st.session_state.get("current_screen_code") or selected_screen.screen_code)
        dialog_screen = next((screen for screen in screens if screen.screen_code == context_code), selected_screen)
        dialog_error_log = st.session_state.get(
            "current_error_log",
            (
                f"[자동첨부] screen={dialog_screen.screen_code}, "
                f"name={dialog_screen.screen_name}, branch={user.branch}, "
                f"employee={user.employee_id}, captured_at={datetime.now().isoformat(timespec='seconds')}"
            ),
        )
        render_shinmungo_layer(dialog_screen, user, dialog_error_log)

    left, main_area = st.columns([0.22, 0.78], gap="small")
    with left:
        render_left_panel(selected_screen)
    with main_area:
        if selected_screen.screen_code == "111":
            render_screen_111()
        else:
            render_screen_827()
    render_area_selection_bridge(selected_screen)


main()
