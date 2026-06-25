from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from services.models import TicketFollower


def is_following(session: Session, ticket_id: int, employee_id: str) -> bool:
    return (
        session.query(TicketFollower)
        .filter(TicketFollower.ticket_id == ticket_id, TicketFollower.employee_id == employee_id)
        .first()
        is not None
    )


def follow_ticket(session: Session, ticket_id: int, employee_id: str) -> bool:
    if is_following(session, ticket_id, employee_id):
        return False
    session.add(TicketFollower(ticket_id=ticket_id, employee_id=employee_id, created_at=datetime.now()))
    session.commit()
    return True


def unfollow_ticket(session: Session, ticket_id: int, employee_id: str) -> bool:
    follower = (
        session.query(TicketFollower)
        .filter(TicketFollower.ticket_id == ticket_id, TicketFollower.employee_id == employee_id)
        .first()
    )
    if not follower:
        return False
    session.delete(follower)
    session.commit()
    return True
