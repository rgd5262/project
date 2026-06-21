from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from services.clustering import cluster_size_by_ticket_id
from services.models import Ticket

IMPACT_WEIGHTS = {
    "버그": 30,
    "성능": 24,
    "기능개선": 22,
    "업무절차혼선": 18,
    "UI불편": 16,
    "기타": 10,
    "미분류": 8,
}
DONE_STATUSES = {"DONE", "REJECTED"}


def unresolved_age_days(ticket: Ticket, now: datetime | None = None) -> int:
    if ticket.status in DONE_STATUSES:
        return 0
    now = now or datetime.now()
    return max(0, (now - ticket.created_at).days)


def calculate_priority(ticket: Ticket, cluster_size: int = 1, now: datetime | None = None) -> dict:
    follower_count = len(ticket.followers)
    frequency_score = min(40, cluster_size * 7 + follower_count * 3)
    impact_score = IMPACT_WEIGHTS.get(ticket.category or "미분류", 10)
    age_days = unresolved_age_days(ticket, now=now)
    age_score = min(30, age_days * 2)
    score = min(100, frequency_score + impact_score + age_score)
    return {
        "ticket_id": ticket.id,
        "priority_score": score,
        "frequency_score": frequency_score,
        "impact_score": impact_score,
        "age_score": age_score,
        "age_days": age_days,
        "cluster_size": cluster_size,
        "follower_count": follower_count,
    }


def priority_rows(session: Session, limit: int | None = None) -> list[dict]:
    cluster_sizes = cluster_size_by_ticket_id(session)
    rows: list[dict] = []
    for ticket in session.query(Ticket).all():
        priority = calculate_priority(ticket, cluster_sizes.get(ticket.id, 1))
        department = ticket.assigned_department.name if ticket.assigned_department else "미배정"
        rows.append(
            {
                **priority,
                "screen_code": ticket.screen_code,
                "screen_name": ticket.screen_name,
                "status": ticket.status,
                "category": ticket.category or "미분류",
                "title": ticket.title,
                "department": department,
            }
        )
    rows = sorted(rows, key=lambda row: row["priority_score"], reverse=True)
    return rows[:limit] if limit else rows
