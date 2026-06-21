from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.db import get_session, init_db
from services.models import Notification, Ticket, TicketFollower
from services.rag import summarize_similar_cases
from services.seed import seed_if_empty
from services.selected_area import selected_area_detail, selected_area_label
from services.ui import apply_page_config, apply_styles, current_user, html_escape, status_badge, status_label


def ensure_data() -> None:
    init_db()
    session = get_session()
    try:
        seed_if_empty(session)
    finally:
        session.close()


def main() -> None:
    apply_page_config("내 접수내역")
    apply_styles()
    ensure_data()
    user = current_user()
    st.title("내 접수내역")

    session = get_session()
    try:
        tickets = (
            session.query(Ticket)
            .filter(Ticket.reporter_employee_id == user.employee_id)
            .order_by(Ticket.updated_at.desc())
            .all()
        )
        if not tickets:
            st.info("현재 직원ID로 접수된 내역이 없습니다.")
        else:
            rows = [
                {
                    "접수번호": ticket.id,
                    "상태": status_label(ticket.status),
                    "화면번호": ticket.screen_code,
                    "화면명": ticket.screen_name,
                    "유형": ticket.ticket_type,
                    "AI분류": ticket.category,
                    "원문분류": ticket.source_category,
                    "신뢰도": f"{ticket.classification_confidence:.2f}" if ticket.classification_confidence else "-",
                    "제목": ticket.title,
                    "배정 부서": ticket.assigned_department.name if ticket.assigned_department else "미배정",
                    "수정일시": ticket.updated_at.strftime("%Y-%m-%d %H:%M"),
                }
                for ticket in tickets
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            labels = [f"#{ticket.id} · {ticket.screen_code} · {ticket.title[:48]}" for ticket in tickets]
            selected = st.selectbox("상세 조회", labels)
            ticket = tickets[labels.index(selected)]

            st.markdown(
                f"""
                <div class="section-box">
                  <div class="section-title">접수 상세</div>
                  <div class="section-content">
                    <div style="margin-bottom:8px">{status_badge(ticket.status)}</div>
                    <div class="kv-grid">
                      <div class="kv-label">화면</div><div>{html_escape(ticket.screen_code)} {html_escape(ticket.screen_name)}</div>
                      <div class="kv-label">업무영역</div><div>{html_escape(ticket.business_category)}</div>
                      <div class="kv-label">배정 부서</div><div>{html_escape(ticket.assigned_department.name if ticket.assigned_department else '미배정')}</div>
                      <div class="kv-label">담당자</div><div>{html_escape(ticket.assigned_manager.name if ticket.assigned_manager else '미배정')}</div>
                      <div class="kv-label">AI분류</div><div>{html_escape(ticket.category or '-')} ({ticket.classification_confidence or 0:.2f})</div>
                      <div class="kv-label">원문분류</div><div>{html_escape(ticket.source_category or '-')}</div>
                      <div class="kv-label">선택 영역</div><div>{html_escape(selected_area_label(ticket.selected_area_json))}</div>
                      <div class="kv-label">제목</div><div>{html_escape(ticket.title)}</div>
                      <div class="kv-label">첨부</div><div>{html_escape(ticket.attachment_name or '-')}</div>
                    </div>
                    <div style="margin-top:10px"><b>내용</b><br>{html_escape(ticket.content)}</div>
                    <div style="margin-top:10px"><b>선택 영역 상세</b><br>{html_escape(selected_area_detail(ticket.selected_area_json))}</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            summary_key = f"similar_summary_{ticket.id}"
            if summary_key not in st.session_state:
                with st.spinner("유사 사례 처리 결과를 요약하는 중입니다."):
                    st.session_state[summary_key] = summarize_similar_cases(session, ticket.id, use_llm=True)
            st.markdown(
                f"""
                <div class="context-card">
                  <b>유사 사례 처리 결과 요약</b><br>
                  {html_escape(st.session_state[summary_key])}
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.subheader("진행상황")
            for history in ticket.histories:
                st.markdown(
                    f"""
                    <div class="section-box">
                      <div class="section-content">
                        <b>{history.created_at.strftime('%Y-%m-%d %H:%M')}</b>
                        &nbsp; {status_badge(history.to_status)}
                        <div style="margin-top:6px">처리자: {html_escape(history.changed_by)}</div>
                        <div>{html_escape(history.comment or '')}</div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.divider()
        st.subheader("팔로우 중인 요청")
        followed_tickets = (
            session.query(Ticket)
            .join(TicketFollower, TicketFollower.ticket_id == Ticket.id)
            .filter(TicketFollower.employee_id == user.employee_id, Ticket.reporter_employee_id != user.employee_id)
            .order_by(Ticket.updated_at.desc())
            .all()
        )
        if followed_tickets:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "접수번호": ticket.id,
                            "상태": status_label(ticket.status),
                            "화면번호": ticket.screen_code,
                            "AI분류": ticket.category,
                            "제목": ticket.title,
                            "배정 부서": ticket.assigned_department.name if ticket.assigned_department else "미배정",
                            "수정일시": ticket.updated_at.strftime("%Y-%m-%d %H:%M"),
                        }
                        for ticket in followed_tickets
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.caption("공감하거나 팔로우 중인 기존 요청이 없습니다.")

        st.subheader("알림")
        notifications = (
            session.query(Notification)
            .filter(Notification.employee_id == user.employee_id)
            .order_by(Notification.created_at.desc())
            .limit(10)
            .all()
        )
        if notifications:
            for notification in notifications:
                st.markdown(
                    f"""
                    <div class="section-box">
                      <div class="section-content">
                        <b>{notification.created_at.strftime('%Y-%m-%d %H:%M')}</b><br>
                        {html_escape(notification.message)}
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.caption("표시할 알림이 없습니다.")
    finally:
        session.close()


main()
