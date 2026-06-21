from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from services.models import Notification, Ticket, TicketFollower
from services.ui import status_label


def notify_followers(session: Session, ticket: Ticket, changed_by: str) -> int:
    followers = session.query(TicketFollower).filter(TicketFollower.ticket_id == ticket.id).all()
    count = 0
    for follower in followers:
        message = (
            f"#{ticket.id} {ticket.title} 요청 상태가 "
            f"{status_label(ticket.status)}(으)로 변경되었습니다. 처리자: {changed_by}"
        )
        session.add(
            Notification(
                ticket_id=ticket.id,
                employee_id=follower.employee_id,
                message=message,
                is_read=0,
                created_at=datetime.now(),
            )
        )
        count += 1
    return count


def notify_followers_message(session: Session, ticket: Ticket, message: str) -> int:
    followers = session.query(TicketFollower).filter(TicketFollower.ticket_id == ticket.id).all()
    count = 0
    for follower in followers:
        session.add(
            Notification(
                ticket_id=ticket.id,
                employee_id=follower.employee_id,
                message=message,
                is_read=0,
                created_at=datetime.now(),
            )
        )
        count += 1
    return count
