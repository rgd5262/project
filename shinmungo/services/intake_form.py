from __future__ import annotations

from datetime import datetime
import json
from typing import Literal

import streamlit as st

from services.classification import classify_ticket
from services.db import get_session
from services.embedding import embed_ticket_text
from services.following import follow_ticket
from services.masking import detect_sensitive_text
from services.models import Screen, Ticket, TicketFollower, TicketStatusHistory
from services.routing import resolve_assignment
from services.selected_area import parse_selected_area, selected_area_label
from services.similarity import ensure_ticket_similarity_embeddings, find_similar, serialize_embedding
from services.ui import CurrentUser, html_escape, status_badge

CompletionMode = Literal["page", "dialog"]
COMPLETED_HELPFUL_STATUSES = {"DONE", "REJECTED"}
ACTIVE_SHARE_STATUSES = {"RECEIVED", "REVIEWING", "IN_PROGRESS", "ON_HOLD"}


def state_key(namespace: str, name: str) -> str:
    return f"{namespace}_{name}"


def query_signature(
    screen: Screen,
    ticket_type: str,
    title: str,
    content: str,
    selected_area_json: str | None = None,
) -> str:
    return (
        f"{screen.screen_code}|{ticket_type.strip()}|{title.strip()}|"
        f"{content.strip()}|{selected_area_json or ''}"
    )


def clear_intake_state(namespace: str, *, clear_inputs: bool = False) -> None:
    names = [
        "submission_result",
        "helpful_result",
        "similar_review_results",
        "similar_review_signature",
        "selected_helpful_ticket_id",
        "helpful_confirm_ticket_id",
        "helpful_confirm_title",
        "helpful_confirm_status",
        "helpful_confirm_signature",
        "pending_submission",
    ]
    if clear_inputs:
        names.extend(["ticket_type", "ticket_title", "ticket_content"])
    for name in names:
        st.session_state.pop(state_key(namespace, name), None)


def selected_area_for_screen(screen: Screen) -> dict | None:
    area = st.session_state.get("current_selected_area")
    if isinstance(area, dict) and str(area.get("screen_code") or "") == screen.screen_code:
        return area
    area = parse_selected_area(st.session_state.get("current_selected_area_json"))
    if area and str(area.get("screen_code") or "") == screen.screen_code:
        return area
    return None


def selected_area_json_for_screen(screen: Screen) -> str | None:
    area = selected_area_for_screen(screen)
    if not area:
        return None
    return json.dumps(area, ensure_ascii=False)


def begin_area_selection(screen: Screen) -> None:
    st.session_state["show_shinmungo_dialog"] = False
    st.session_state["terminal_area_select_mode"] = True
    st.session_state["terminal_area_select_screen_code"] = screen.screen_code
    st.session_state["current_screen_code"] = screen.screen_code
    st.session_state["current_screen_name"] = screen.screen_name
    st.session_state["current_business_category"] = screen.business_category


def clear_selected_area() -> None:
    st.session_state.pop("current_selected_area", None)
    st.session_state.pop("current_selected_area_json", None)


def store_submission_result(
    namespace: str,
    *,
    signature: str,
    ticket_id: int,
    dept_name: str,
    category: str,
    confidence: float,
    provider: str,
) -> None:
    st.session_state[state_key(namespace, "submission_result")] = {
        "signature": signature,
        "ticket_id": ticket_id,
        "dept_name": dept_name,
        "category": category,
        "confidence": confidence,
        "provider": provider,
    }
    for name in [
        "helpful_result",
        "similar_review_results",
        "similar_review_signature",
        "selected_helpful_ticket_id",
        "helpful_confirm_ticket_id",
        "helpful_confirm_title",
        "helpful_confirm_status",
        "helpful_confirm_signature",
        "pending_submission",
    ]:
        st.session_state.pop(state_key(namespace, name), None)


def finish_submission(
    namespace: str,
    *,
    completion_mode: CompletionMode,
    signature: str,
    ticket_id: int,
    dept_name: str,
    category: str,
    confidence: float,
    provider: str,
) -> None:
    if completion_mode == "dialog":
        st.session_state["shinmungo_completion_alert"] = {
            "message": "접수가 완료되었습니다. 진행 상황은 '내 접수내역'에서 확인 가능합니다.",
        }
        st.session_state["show_shinmungo_dialog"] = False
        clear_intake_state(namespace, clear_inputs=True)
        clear_selected_area()
        return

    store_submission_result(
        namespace,
        signature=signature,
        ticket_id=ticket_id,
        dept_name=dept_name,
        category=category,
        confidence=confidence,
        provider=provider,
    )


def store_helpful_result(
    namespace: str,
    *,
    signature: str,
    ticket_id: int,
    title: str,
    created: bool,
) -> None:
    st.session_state[state_key(namespace, "helpful_result")] = {
        "signature": signature,
        "ticket_id": ticket_id,
        "title": title,
        "created": created,
    }
    for name in [
        "submission_result",
        "similar_review_results",
        "similar_review_signature",
        "selected_helpful_ticket_id",
        "helpful_confirm_ticket_id",
        "helpful_confirm_title",
        "helpful_confirm_status",
        "helpful_confirm_signature",
        "pending_submission",
    ]:
        st.session_state.pop(state_key(namespace, name), None)


def render_submission_result(namespace: str, signature: str, completion_mode: CompletionMode) -> None:
    result = st.session_state.get(state_key(namespace, "submission_result"))
    if not result or result.get("signature") != signature:
        return
    st.success("접수가 완료되었습니다. 진행 상황은 '내 접수내역'에서 확인 가능합니다.")
    if completion_mode == "dialog":
        if st.button("닫기", key=state_key(namespace, "close_dialog"), use_container_width=True):
            st.session_state["show_shinmungo_dialog"] = False
            clear_intake_state(namespace, clear_inputs=True)
            clear_selected_area()
            st.rerun()
        return
    st.markdown(
        '<a class="internal-nav-button" href="/내_접수내역" target="_self">'
        '내 접수내역에서 진행상황 확인'
        '</a>',
        unsafe_allow_html=True,
    )


def render_helpful_result(namespace: str, signature: str, completion_mode: CompletionMode) -> None:
    result = st.session_state.get(state_key(namespace, "helpful_result"))
    if not result or result.get("signature") != signature:
        return
    message = (
        "선택하신 요청사항의 진행 상황을 공유받도록 등록했습니다. "
        "진행 상황은 '내 접수내역'에서 확인하실 수 있습니다."
    )
    if not result.get("created"):
        message = (
            "이미 선택하신 요청사항의 진행 상황을 공유받고 있습니다. "
            "진행 상황은 '내 접수내역'에서 확인하실 수 있습니다."
        )
    st.success(message)
    if completion_mode == "dialog":
        if st.button("닫기", key=state_key(namespace, "close_helpful_dialog"), use_container_width=True):
            st.session_state["show_shinmungo_dialog"] = False
            clear_intake_state(namespace, clear_inputs=True)
            clear_selected_area()
            st.rerun()
        return
    st.markdown(
        '<a class="internal-nav-button" href="/내_접수내역" target="_self">'
        '내 접수내역에서 진행상황 확인'
        '</a>',
        unsafe_allow_html=True,
    )


def render_intake_loading_overlay() -> None:
    st.html(
        """
        <div class="shinmungo-intake-loading-layer">
          <div class="shinmungo-intake-loading-box">
            <div class="shinmungo-intake-loading-spinner" aria-hidden="true"></div>
            <div class="shinmungo-intake-loading-text">접수 진행 중</div>
          </div>
        </div>
        """,
    )


def similar_review_heading(ticket_type: str) -> str:
    noun = {
        "불편": "불편사항",
        "버그": "에러",
        "개선": "개선사항",
    }.get(ticket_type, "요청")
    return f"접수해주신 {noun}과 비슷한 요청이 있어요."


def similar_action_label(status: str) -> str:
    if status in COMPLETED_HELPFUL_STATUSES:
        return "이 내용이 도움이 되었어요"
    return "해당 요건의 진행상황을 공유받기"


def render_similar_review_intro(ticket_type: str) -> None:
    st.markdown(
        f"""
        <div class="shinmungo-similar-review-panel">
          <div class="shinmungo-similar-review-eyebrow">기존 요청 확인</div>
          <div class="shinmungo-similar-review-title">{html_escape(similar_review_heading(ticket_type))}</div>
          <div class="shinmungo-similar-review-desc">
            대표 유사 요청 3개를 확인한 뒤 기존 요청 확인 또는 신규 접수를 선택해 주세요.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_similar_review_cards(
    namespace: str,
    *,
    results: list[dict],
    signature: str,
) -> None:
    for result in results[:3]:
        result_id = int(result["id"])
        result_status = str(result.get("status") or "")
        with st.container(border=True):
            st.markdown(
                f"""
                <div class="shinmungo-similar-card-marker"></div>
                <div class="shinmungo-similar-card-head">
                  <div class="shinmungo-similar-card-title">
                    <span class="ticket-no">#{html_escape(str(result['id']))}</span>
                    {html_escape(str(result['title']))}
                  </div>
                  <div class="shinmungo-similar-card-status">{status_badge(result["status"])}</div>
                </div>
                <div class="shinmungo-similar-card-meta">
                  <span>유사도 {result['similarity'] * 100:.1f}%</span>
                  <span>담당부서 : {html_escape(str(result['assigned_department']))}</span>
                  <span>접수 유형 : {html_escape(str(result['category']))}</span>
                </div>
                <div class="shinmungo-similar-card-snippet">
                  {html_escape(str(result["content_snippet"]))}
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.expander("내용 보기"):
                if result["latest_answer"]:
                    answer_html = html_escape(str(result["latest_answer"])).replace("\n", "<br>")
                    st.markdown(
                        f'<div class="shinmungo-similar-answer">{answer_html}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption("등록된 답변이 없습니다.")

            if st.button(
                similar_action_label(result_status),
                key=state_key(namespace, f"helpful_{result_id}"),
                use_container_width=True,
            ):
                st.session_state[state_key(namespace, "helpful_confirm_ticket_id")] = result_id
                st.session_state[state_key(namespace, "helpful_confirm_title")] = str(result["title"])
                st.session_state[state_key(namespace, "helpful_confirm_status")] = result_status
                st.session_state[state_key(namespace, "helpful_confirm_signature")] = signature
                st.rerun()

def render_helpful_confirm_layer(namespace: str, *, employee_id: str) -> None:
    ticket_id = st.session_state.get(state_key(namespace, "helpful_confirm_ticket_id"))
    confirm_signature = st.session_state.get(state_key(namespace, "helpful_confirm_signature"))
    if not ticket_id or not confirm_signature:
        return
    title = str(st.session_state.get(state_key(namespace, "helpful_confirm_title")) or "")
    status = str(st.session_state.get(state_key(namespace, "helpful_confirm_status")) or "")
    is_completed_case = status in COMPLETED_HELPFUL_STATUSES
    confirm_desc = (
        "선택하신 요청사항의 답변 또는 처리 결과를 확인하고 신규 접수를 중단합니다."
        if is_completed_case
        else "선택하신 요청사항의 진행 상황은 '내 접수내역'에서 확인하실 수 있습니다."
    )
    st.html('<div class="shinmungo-helpful-confirm-backdrop"></div>')
    with st.container(key=state_key(namespace, "helpful_confirm_layer")):
        st.markdown(
            f"""
            <div class="shinmungo-helpful-confirm-copy">
              <div class="confirm-eyebrow">접수 중단 알림</div>
              <div class="confirm-title">신규 접수를 중단하시겠습니까?</div>
              <div class="confirm-desc">{html_escape(confirm_desc)}</div>
              <div class="confirm-ticket">#{html_escape(str(ticket_id))} · {html_escape(title)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        action_cols = st.columns(2)
        with action_cols[0]:
            if st.button(
                "예, 중단합니다",
                key=state_key(namespace, "helpful_confirm_yes"),
                type="primary",
                use_container_width=True,
            ):
                if is_completed_case:
                    created = True
                    st.session_state["shinmungo_follow_alert"] = {
                        "ticket_id": int(ticket_id),
                        "title": title,
                        "created": created,
                        "mode": "completed",
                    }
                else:
                    session = get_session()
                    try:
                        created = follow_ticket(session, int(ticket_id), employee_id)
                        st.session_state["shinmungo_follow_alert"] = {
                            "ticket_id": int(ticket_id),
                            "title": title,
                            "created": created,
                            "mode": "share",
                        }
                    finally:
                        session.close()
                st.session_state["show_shinmungo_dialog"] = False
                clear_intake_state(namespace, clear_inputs=True)
                clear_selected_area()
                st.rerun()
        with action_cols[1]:
            if st.button(
                "취소",
                key=state_key(namespace, "helpful_confirm_cancel"),
                use_container_width=True,
            ):
                for name in [
                    "helpful_confirm_ticket_id",
                    "helpful_confirm_title",
                    "helpful_confirm_status",
                    "helpful_confirm_signature",
                ]:
                    st.session_state.pop(state_key(namespace, name), None)
                st.rerun()


def create_ticket(
    screen: Screen,
    user: CurrentUser,
    ticket_type: str,
    title: str,
    content: str,
    error_log: str,
    selected_area_json: str | None = None,
) -> tuple[int, str, str, float, str]:
    full_content = content.strip()
    classification = classify_ticket(title, full_content, use_llm=True)
    embedding_json = serialize_embedding(embed_ticket_text(screen.screen_code, title, full_content))
    session = get_session()
    try:
        manager, department = resolve_assignment(session, screen.screen_code)
        now = datetime.now()
        ticket = Ticket(
            screen_code=screen.screen_code,
            business_category=screen.business_category,
            screen_name=screen.screen_name,
            reporter_employee_id=user.employee_id,
            reporter_branch=user.branch,
            ticket_type=ticket_type,
            title=title.strip(),
            content=full_content,
            attachment_name=None,
            error_log=error_log,
            selected_area_json=selected_area_json,
            category=classification.category,
            source_category="신규접수",
            classification_confidence=classification.confidence,
            embedding_json=embedding_json,
            status="RECEIVED",
            assigned_manager_id=manager.id if manager else None,
            assigned_department_id=department.id if department else None,
            created_at=now,
            updated_at=now,
        )
        ensure_ticket_similarity_embeddings(ticket)
        session.add(ticket)
        session.flush()
        session.add(
            TicketStatusHistory(
                ticket_id=ticket.id,
                from_status=None,
                to_status="RECEIVED",
                changed_by=f"{user.name}({user.employee_id})",
                comment="통합단말 화면 컨텍스트 기반으로 접수되었습니다.",
                created_at=now,
            )
        )
        session.add(TicketFollower(ticket_id=ticket.id, employee_id=user.employee_id, created_at=now))
        session.commit()
        return (
            ticket.id,
            department.name if department else "미배정",
            classification.category,
            classification.confidence,
            classification.provider,
        )
    finally:
        session.close()


def search_similar(screen: Screen, title: str, content: str, selected_area_json: str | None = None) -> list[dict]:
    session = get_session()
    try:
        return find_similar(
            session,
            screen.screen_code,
            title,
            content,
            selected_area_json=selected_area_json,
            top_k=3,
            threshold=0.75,
        )
    finally:
        session.close()


def render_context_card(screen: Screen, completion_mode: CompletionMode) -> None:
    if completion_mode == "dialog":
        st.markdown(
            f"""
            <div class="shinmungo-layer-context">
              <b>{html_escape(screen.screen_name)} 화면에서 접수합니다.</b>
              <span class="meta">화면번호 {html_escape(screen.screen_code)} · 업무영역 {html_escape(screen.business_category)}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        f"""
        <div class="context-card">
          <b>{html_escape(screen.screen_name)} 화면에서 접수합니다.</b><br>
          화면번호 {html_escape(screen.screen_code)} · 업무영역 {html_escape(screen.business_category)}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_area_selection_controls(
    screen: Screen,
    namespace: str,
    completion_mode: CompletionMode,
    *,
    readonly: bool = False,
) -> None:
    if completion_mode != "dialog":
        return
    selected_area = selected_area_for_screen(screen)
    if readonly:
        if selected_area:
            st.markdown(
                f"""
                <div class="selected-area-chip readonly">
                  <span class="selected-area-label">선택 영역</span>
                  <b>{html_escape(selected_area_label(json.dumps(selected_area, ensure_ascii=False)))}</b>
                  <span>{html_escape(str(selected_area.get("text") or ""))[:80]}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="selected-area-chip readonly empty">
                  <span class="selected-area-label">기능 지정</span>
                  <b>미지정</b>
                  <span>접수 검토 중에는 기능 지정 내용을 변경할 수 없습니다.</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        return
    if selected_area:
        st.markdown(
            f"""
            <div class="selected-area-chip">
              <span class="selected-area-label">선택 영역</span>
              <b>{html_escape(selected_area_label(json.dumps(selected_area, ensure_ascii=False)))}</b>
              <span>{html_escape(str(selected_area.get("text") or ""))[:80]}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        action_cols = st.columns(2)
        with action_cols[0]:
            if st.button("다시 지정", key=state_key(namespace, "select_area_again"), use_container_width=True):
                begin_area_selection(screen)
                st.rerun()
        with action_cols[1]:
            if st.button("선택 해제", key=state_key(namespace, "clear_area"), use_container_width=True):
                clear_selected_area()
                st.rerun()
        return

    if st.button("기능 지정하기", key=state_key(namespace, "select_area"), use_container_width=True):
        begin_area_selection(screen)
        st.rerun()


def render_intake_form(
    *,
    screen: Screen,
    user: CurrentUser,
    error_log: str,
    namespace: str,
    completion_mode: CompletionMode,
) -> None:
    render_context_card(screen, completion_mode)

    stored_review_signature = st.session_state.get(state_key(namespace, "similar_review_signature"))
    stored_review_results = st.session_state.get(state_key(namespace, "similar_review_results"), [])
    current_ticket_type = str(st.session_state.get(state_key(namespace, "ticket_type")) or "불편")
    current_title = str(st.session_state.get(state_key(namespace, "ticket_title")) or "")
    current_content = str(st.session_state.get(state_key(namespace, "ticket_content")) or "")
    current_selected_area_json = selected_area_json_for_screen(screen)
    draft_signature = query_signature(
        screen,
        current_ticket_type,
        current_title,
        current_content,
        current_selected_area_json,
    )
    review_locked = (
        bool(stored_review_signature)
        and stored_review_signature == draft_signature
        and bool(stored_review_results)
        and bool(current_title.strip() and current_content.strip())
    )

    render_area_selection_controls(screen, namespace, completion_mode, readonly=review_locked)

    ticket_type = st.radio(
        "유형",
        ["불편", "버그", "개선"],
        horizontal=True,
        key=state_key(namespace, "ticket_type"),
        disabled=review_locked,
    )
    title = st.text_input(
        "제목",
        placeholder="예: 베이직팩 통합인자 처리상태를 더 명확히 보여주세요",
        key=state_key(namespace, "ticket_title"),
        disabled=review_locked,
    )
    content = st.text_area(
        "상세 내용",
        height=180,
        placeholder="불편한 상황, 재현 조건, 원하는 개선 방향을 입력해 주세요.",
        key=state_key(namespace, "ticket_content"),
        disabled=review_locked,
    )

    sensitive_warnings = detect_sensitive_text(title, content)
    if sensitive_warnings:
        st.warning("민감정보로 보이는 값이 포함되어 있습니다: " + ", ".join(sensitive_warnings))

    selected_area_json = selected_area_json_for_screen(screen)
    signature = query_signature(screen, ticket_type, title, content, selected_area_json)
    submission_result = st.session_state.get(state_key(namespace, "submission_result"))
    if submission_result and submission_result.get("signature") != signature:
        clear_intake_state(namespace)
    helpful_result = st.session_state.get(state_key(namespace, "helpful_result"))
    if helpful_result and helpful_result.get("signature") != signature:
        clear_intake_state(namespace)

    if st.session_state.get(state_key(namespace, "submission_result")):
        render_submission_result(namespace, signature, completion_mode)
        return
    if st.session_state.get(state_key(namespace, "helpful_result")):
        render_helpful_result(namespace, signature, completion_mode)
        return

    review_results = st.session_state.get(state_key(namespace, "similar_review_results"), [])
    review_active = (
        st.session_state.get(state_key(namespace, "similar_review_signature")) == signature
        and bool(title.strip() and content.strip())
    )
    if st.session_state.get(state_key(namespace, "similar_review_signature")) and not review_active:
        for name in [
            "similar_review_results",
            "similar_review_signature",
            "selected_helpful_ticket_id",
            "helpful_confirm_ticket_id",
            "helpful_confirm_title",
            "helpful_confirm_status",
            "helpful_confirm_signature",
            "pending_submission",
        ]:
            st.session_state.pop(state_key(namespace, name), None)
        review_results = []

    if review_active and review_results:
        render_similar_review_intro(ticket_type)
        render_similar_review_cards(
            namespace,
            results=review_results,
            signature=signature,
        )
        st.markdown('<div class="shinmungo-review-action-spacer"></div>', unsafe_allow_html=True)
        if st.button(
            "새로운 요청으로 접수해주세요",
            type="primary",
            key=state_key(namespace, "submit_new_after_review"),
            use_container_width=True,
        ):
            render_intake_loading_overlay()
            ticket_id, dept_name, category, confidence, provider = create_ticket(
                screen,
                user,
                ticket_type,
                title,
                content,
                error_log,
                selected_area_json=selected_area_json,
            )
            finish_submission(
                namespace,
                completion_mode=completion_mode,
                signature=signature,
                ticket_id=ticket_id,
                dept_name=dept_name,
                category=category,
                confidence=confidence,
                provider=provider,
            )
            st.rerun()
        return

    if st.button(
        "접수하기",
        type="primary",
        use_container_width=True,
        key=state_key(namespace, "submit"),
    ):
        clear_intake_state(namespace)
        if not title.strip() or not content.strip():
            st.error("제목과 상세 내용을 입력해 주세요.")
        else:
            render_intake_loading_overlay()
            results = search_similar(screen, title, content, selected_area_json)
            if results:
                st.session_state[state_key(namespace, "similar_review_results")] = results[:3]
                st.session_state[state_key(namespace, "similar_review_signature")] = signature
                st.session_state[state_key(namespace, "pending_submission")] = {
                    "signature": signature,
                    "ticket_type": ticket_type,
                }
                st.rerun()
            else:
                ticket_id, dept_name, category, confidence, provider = create_ticket(
                    screen,
                    user,
                    ticket_type,
                    title,
                    content,
                    error_log,
                    selected_area_json=selected_area_json,
                )
                finish_submission(
                    namespace,
                    completion_mode=completion_mode,
                    signature=signature,
                    ticket_id=ticket_id,
                    dept_name=dept_name,
                    category=category,
                    confidence=confidence,
                    provider=provider,
                )
                st.rerun()
