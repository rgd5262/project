from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.db import get_session, init_db
from services.models import Answer, Department, Ticket, TicketStatusHistory
from services.notifications import notify_followers, notify_followers_message
from services.rag import generate_answer_draft, similar_cases_for_ticket, summarize_similar_cases
from services.seed import seed_if_empty
from services.selected_area import selected_area_detail, selected_area_label
from services.ui import (
    STATUS_LABELS,
    apply_page_config,
    apply_styles,
    current_user,
    html_escape,
    status_badge,
    status_label,
)

ALLOWED_STATUSES = ["RECEIVED", "REVIEWING", "IN_PROGRESS", "DONE", "REJECTED", "ON_HOLD"]
STATUS_STATE_KEY = "admin_selected_status_target"
SELECTED_INQUIRY_KEY = "admin_selected_inquiry_id"
PENDING_STATUS_KEYS = [
    "admin_pending_status_inquiry_id",
    "admin_pending_status",
    "admin_status_change_reason",
    "admin_status_change_error",
]


def ensure_data() -> None:
    init_db()
    session = get_session()
    try:
        seed_if_empty(session)
    finally:
        session.close()


def clear_status_popup_state() -> None:
    for key in PENDING_STATUS_KEYS:
        st.session_state.pop(key, None)


def department_scoped_query(session, department_name: str):
    return (
        session.query(Ticket)
        .join(Department, Ticket.assigned_department_id == Department.id)
        .filter(Department.name == department_name)
    )


def ellipsis(value: str | None, limit: int = 140) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text or "-"
    return text[: limit - 3] + "..."


def department_name(ticket: Ticket) -> str:
    return ticket.assigned_department.name if ticket.assigned_department else "미배정"


def render_notice_if_any() -> None:
    notice = st.session_state.pop("admin_notice", None)
    if notice:
        st.success(str(notice))


def generate_answer_draft_for_ticket(ticket_id: int) -> str:
    draft_session = get_session()
    try:
        return generate_answer_draft(draft_session, ticket_id, use_llm=True)
    finally:
        draft_session.close()


def render_inline_status_controls(ticket: Ticket) -> None:
    state_key = f"{STATUS_STATE_KEY}_{ticket.id}"
    selectable_statuses = [status for status in ALLOWED_STATUSES if status != ticket.status]
    if st.session_state.get(state_key) not in selectable_statuses:
        st.session_state[state_key] = None

    with st.container(key=f"admin_status_inline_{ticket.id}"):
        st.markdown(
            f"""
            <div class="admin-status-current">
              <span class="admin-status-current-label">진행상황</span>
              {status_badge(ticket.status)}
            </div>
            """,
            unsafe_allow_html=True,
        )
        status_columns = st.columns([1, 1, 1, 1, 1, 0.9])
        for index, status in enumerate(selectable_statuses):
            with status_columns[index]:
                selected = st.session_state.get(state_key) == status
                button_type = "primary" if selected else "secondary"
                if st.button(
                    status_label(status),
                    type=button_type,
                    use_container_width=True,
                    key=f"admin_status_pick_{ticket.id}_{status}",
                ):
                    st.session_state[state_key] = status
                    st.rerun()

        with status_columns[-1]:
            if st.button("저장", type="primary", use_container_width=True, key=f"admin_status_save_{ticket.id}"):
                selected_status = st.session_state.get(state_key)
                if not selected_status:
                    st.info("변경할 상태를 선택해 주세요.")
                else:
                    st.session_state["admin_pending_status_inquiry_id"] = ticket.id
                    st.session_state["admin_pending_status"] = selected_status
                    st.session_state["admin_status_change_reason"] = ""
                    st.session_state.pop("admin_status_change_error", None)
                    st.rerun()


def render_inquiry_overview(ticket: Ticket) -> None:
    saved_answers_html = ""
    if ticket.answers:
        answer_cards = "\n".join(
            f"""
              <div class="admin-saved-answer-card">
                <div class="admin-saved-answer-date">{answer.created_at.strftime('%Y-%m-%d %H:%M')}</div>
                <div class="admin-saved-answer-body">{html_escape(answer.body)}</div>
              </div>
            """
            for answer in reversed(ticket.answers)
        )
        saved_answers_html = f"""
              <div class="admin-saved-answers">
                <div class="admin-saved-answers-title">저장된 답변</div>
                {answer_cards}
              </div>
        """

    with st.container(key=f"admin_detail_subsection_{ticket.id}"):
        st.markdown('<div class="admin-detail-subtitle">문의 기본정보</div>', unsafe_allow_html=True)
        render_inline_status_controls(ticket)
        st.markdown(
            f"""
            <div class="admin-inquiry-detail">
              <div class="kv-grid">
                <div class="kv-label">화면</div><div>{html_escape(ticket.screen_code)} {html_escape(ticket.screen_name)}</div>
                <div class="kv-label">업무영역</div><div>{html_escape(ticket.business_category)}</div>
                <div class="kv-label">접수자</div><div>{html_escape(ticket.reporter_employee_id)} / {html_escape(ticket.reporter_branch)}</div>
                <div class="kv-label">배정 부서</div><div>{html_escape(department_name(ticket))}</div>
                <div class="kv-label">제목</div><div>{html_escape(ticket.title)}</div>
                <div class="kv-label">접수 유형</div><div>{html_escape(ticket.ticket_type)}</div>
                <div class="kv-label">AI 분류</div><div>{html_escape(ticket.category or '-')} ({ticket.classification_confidence or 0:.2f})</div>
                <div class="kv-label">원문분류</div><div>{html_escape(ticket.source_category or '-')}</div>
                <div class="kv-label">선택 영역</div><div>{html_escape(selected_area_label(ticket.selected_area_json))}</div>
                <div class="kv-label">접수일시</div><div>{ticket.created_at.strftime('%Y-%m-%d %H:%M')}</div>
              </div>
              <div style="margin-top:10px"><b>문의 내용</b><br>{html_escape(ticket.content)}</div>
              <div style="margin-top:10px"><b>선택 영역 상세</b><br>{html_escape(selected_area_detail(ticket.selected_area_json))}</div>
              {saved_answers_html}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_similar_cases(session, ticket: Ticket) -> list:
    similar_cases = similar_cases_for_ticket(session, ticket.id, top_k=5)
    st.markdown("#### 지금 요건과 비슷한 문의")
    if not similar_cases:
        st.info("지금 요건과 비슷한 문의가 없습니다.")
        return []

    for case in similar_cases:
        answer = ellipsis(case.answer or "등록된 답변이 없습니다.", 160)
        st.markdown(
            f"""
            <div class="admin-similar-inquiry-card">
              <div class="admin-similar-inquiry-head">
                <span class="admin-similar-inquiry-title">문의 #{case.ticket_id} · {html_escape(case.title)}</span>
                {status_badge(case.status)}
              </div>
              <div class="admin-similar-inquiry-meta">
                유사도 {case.similarity:.2f} · 접수 유형/분류 {html_escape(case.category or '-')}
              </div>
              <div class="admin-similar-inquiry-answer">{html_escape(answer)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    return similar_cases


def render_ai_answer_panel(session, ticket: Ticket, user) -> None:
    st.markdown('<div class="admin-detail-subtitle">AI 답변 지원</div>', unsafe_allow_html=True)
    summary = summarize_similar_cases(session, ticket.id, use_llm=False)
    st.markdown(
        f"""
        <div class="admin-ai-summary">
          <b>비슷한 문의 처리 요약</b><br>
          {html_escape(summary)}
        </div>
        """,
        unsafe_allow_html=True,
    )

    draft_key = f"answer_draft_{ticket.id}"
    pending_draft_key = f"answer_draft_pending_{ticket.id}"
    if pending_draft_key in st.session_state:
        st.session_state[draft_key] = st.session_state.pop(pending_draft_key)
    if draft_key not in st.session_state:
        st.session_state[draft_key] = ""

    answer_body = st.text_area("답변 내용", key=draft_key, height=190)
    if st.button("AI 답변 초안 생성", use_container_width=True, key=f"generate_answer_draft_{ticket.id}"):
        with st.spinner("AI 답변 초안을 생성하고 있습니다."):
            st.session_state[pending_draft_key] = generate_answer_draft_for_ticket(ticket.id)
        st.rerun()
    if st.button("답변 저장", type="primary", use_container_width=True, key=f"save_answer_{ticket.id}"):
        if not answer_body.strip():
            st.error("저장할 답변 내용을 입력해 주세요.")
        else:
            now = datetime.now()
            session.add(
                Answer(
                    ticket_id=ticket.id,
                    author_manager_id=ticket.assigned_manager_id,
                    body=answer_body.strip(),
                    created_at=now,
                )
            )
            session.add(
                TicketStatusHistory(
                    ticket_id=ticket.id,
                    from_status=ticket.status,
                    to_status=ticket.status,
                    changed_by=f"{user.name}({user.employee_id})",
                    comment="관리자 답변이 등록되었습니다.",
                    created_at=now,
                )
            )
            ticket.updated_at = now
            notify_count = notify_followers_message(
                session,
                ticket,
                f"#{ticket.id} {ticket.title} 문의에 관리자 답변이 등록되었습니다.",
            )
            session.commit()
            st.session_state["admin_notice"] = f"답변이 저장되었습니다. 알림 {notify_count}건이 생성되었습니다."
            st.rerun()


def render_history_panel(ticket: Ticket) -> None:
    st.markdown('<div class="admin-detail-subtitle">처리 이력</div>', unsafe_allow_html=True)
    if not ticket.histories:
        st.info("아직 처리 이력이 없습니다.")
        return

    for history in ticket.histories:
        st.markdown(
            f"""
            <div class="admin-history-card">
              <div class="admin-history-head">
                <b>{history.created_at.strftime('%Y-%m-%d %H:%M')}</b>
                {status_badge(history.to_status)}
              </div>
              <div class="admin-history-meta">처리자: {html_escape(history.changed_by)}</div>
              <div class="admin-history-comment">{html_escape(history.comment or '')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_inquiry_workspace(session, ticket: Ticket, user) -> None:
    with st.container(key="admin_inquiry_workspace"):
        st.markdown('<div class="section-title admin-workspace-title">문의 상세</div>', unsafe_allow_html=True)
        render_inquiry_overview(ticket)
        if not ticket.answers:
            render_ai_answer_panel(session, ticket, user)
        render_history_panel(ticket)


def render_status_confirm_layer(session, user) -> None:
    inquiry_id = st.session_state.get("admin_pending_status_inquiry_id")
    next_status = st.session_state.get("admin_pending_status")
    if not inquiry_id or not next_status:
        return

    ticket = session.get(Ticket, int(inquiry_id))
    if not ticket:
        clear_status_popup_state()
        return

    st.markdown('<div class="admin-status-confirm-backdrop"></div>', unsafe_allow_html=True)
    with st.container(key="admin_status_confirm_layer"):
        st.markdown(
            f"""
            <div class="admin-status-confirm-copy">
              <div class="confirm-eyebrow">상태 변경 사유 입력</div>
              <div class="confirm-title">문의 #{ticket.id}</div>
              <div class="confirm-desc">{status_label(ticket.status)} → {status_label(str(next_status))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        reason = st.text_area(
            "상태 변경 사유",
            key="admin_status_change_reason",
            height=120,
            placeholder="상태를 변경하는 사유와 후속 처리 내용을 입력해 주세요.",
        )
        if st.session_state.get("admin_status_change_error"):
            st.error("상태 변경 사유를 입력해 주세요.")

        col_save, col_cancel = st.columns(2)
        with col_save:
            if st.button("저장", type="primary", use_container_width=True, key="admin_status_confirm_save"):
                if not reason.strip():
                    st.session_state["admin_status_change_error"] = True
                    st.rerun()
                previous_status = ticket.status
                now = datetime.now()
                ticket.status = str(next_status)
                ticket.updated_at = now
                session.add(
                    TicketStatusHistory(
                        ticket_id=ticket.id,
                        from_status=previous_status,
                        to_status=str(next_status),
                        changed_by=f"{user.name}({user.employee_id})",
                        comment=reason.strip(),
                        created_at=now,
                    )
                )
                notify_count = notify_followers(session, ticket, f"{user.name}({user.employee_id})")
                session.commit()
                st.session_state[SELECTED_INQUIRY_KEY] = ticket.id
                st.session_state["admin_notice"] = f"상태 변경과 담당자 이력이 저장되었습니다. 알림 {notify_count}건이 생성되었습니다."
                clear_status_popup_state()
                st.rerun()
        with col_cancel:
            if st.button("취소", use_container_width=True, key="admin_status_confirm_cancel"):
                clear_status_popup_state()
                st.rerun()


def selected_rows_from_event(event) -> list[int]:
    try:
        return list(event.selection.rows)
    except Exception:
        selection = getattr(event, "selection", None)
        if isinstance(selection, dict):
            return list(selection.get("rows", []))
    return []


def main() -> None:
    apply_page_config("관리자")
    apply_styles()
    ensure_data()
    user = current_user()
    st.title("문의 관리")

    if user.role != "관리자":
        st.warning("본부부서로 전환해야 접근할 수 있습니다. 사이드바에서 역할을 본부부서로 선택해 주세요.")
        return

    session = get_session()
    try:
        department_name_value = user.branch
        render_notice_if_any()

        scoped_query = department_scoped_query(session, department_name_value)
        screen_codes = ["전체"] + [
            row[0]
            for row in scoped_query.with_entities(Ticket.screen_code)
            .distinct()
            .order_by(Ticket.screen_code)
            .all()
        ]
        categories = ["전체"] + [
            row[0]
            for row in scoped_query.with_entities(Ticket.category)
            .filter(Ticket.category.isnot(None))
            .distinct()
            .order_by(Ticket.category)
            .all()
        ]

        st.caption(f"현재 본부부서: {department_name_value}")
        filter_cols = st.columns(3)
        with filter_cols[0]:
            status_filter_label = st.selectbox("상태", ["전체"] + [STATUS_LABELS[s] for s in ALLOWED_STATUSES])
        with filter_cols[1]:
            screen_filter = st.selectbox("화면번호", screen_codes)
        with filter_cols[2]:
            category_filter = st.selectbox("분류", categories)

        query = department_scoped_query(session, department_name_value).order_by(Ticket.updated_at.desc())
        if status_filter_label != "전체":
            label_to_status = {value: key for key, value in STATUS_LABELS.items()}
            query = query.filter(Ticket.status == label_to_status[status_filter_label])
        if screen_filter != "전체":
            query = query.filter(Ticket.screen_code == screen_filter)
        if category_filter != "전체":
            query = query.filter(Ticket.category == category_filter)

        tickets = query.all()
        if not tickets:
            st.info("현재 본부부서 조건에 해당하는 문의가 없습니다.")
            render_status_confirm_layer(session, user)
            return

        rows = [
            {
                "문의번호": ticket.id,
                "상태": status_label(ticket.status),
                "화면번호": ticket.screen_code,
                "접수 유형": ticket.ticket_type,
                "AI 분류": ticket.category or "-",
                "신뢰도": f"{ticket.classification_confidence:.2f}" if ticket.classification_confidence else "-",
                "제목": ticket.title,
                "접수자": ticket.reporter_employee_id,
                "점포": ticket.reporter_branch,
                "수정일시": ticket.updated_at.strftime("%Y-%m-%d %H:%M"),
            }
            for ticket in tickets
        ]
        event = st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="admin_inquiry_table",
        )

        selected_rows = selected_rows_from_event(event)
        if selected_rows:
            selected_id = int(rows[selected_rows[0]]["문의번호"])
            st.session_state[SELECTED_INQUIRY_KEY] = selected_id

        visible_ids = {ticket.id for ticket in tickets}
        selected_id = st.session_state.get(SELECTED_INQUIRY_KEY)
        if selected_id not in visible_ids:
            selected_id = tickets[0].id
            st.session_state[SELECTED_INQUIRY_KEY] = selected_id

        ticket = next(ticket for ticket in tickets if ticket.id == selected_id)

        render_inquiry_workspace(session, ticket, user)
        render_similar_cases(session, ticket)

        render_status_confirm_layer(session, user)
    finally:
        session.close()


main()
