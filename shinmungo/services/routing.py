from __future__ import annotations

from sqlalchemy.orm import Session

from services.models import Department, Manager, Screen, ScreenMapping

FALLBACK_DEPARTMENT = "미배정(시스템 관리자 큐)"


def resolve_assignment(session: Session, screen_code: str) -> tuple[Manager | None, Department | None]:
    mapping = (
        session.query(ScreenMapping)
        .join(Screen)
        .filter(Screen.screen_code == str(screen_code))
        .first()
    )
    if mapping:
        return mapping.manager, mapping.department

    fallback_dept = session.query(Department).filter(Department.name == FALLBACK_DEPARTMENT).first()
    fallback_manager = None
    if fallback_dept:
        fallback_manager = session.query(Manager).filter(Manager.department_id == fallback_dept.id).first()
    return fallback_manager, fallback_dept
