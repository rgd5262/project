from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Screen(Base):
    __tablename__ = "screens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    screen_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    screen_name: Mapped[str] = mapped_column(String(120), nullable=False)
    business_category: Mapped[str] = mapped_column(String(80), nullable=False)

    mappings: Mapped[list["ScreenMapping"]] = relationship(back_populates="screen")


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

    managers: Mapped[list["Manager"]] = relationship(back_populates="department")
    mappings: Mapped[list["ScreenMapping"]] = relationship(back_populates="department")


class Manager(Base):
    __tablename__ = "managers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    employee_id: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False)

    department: Mapped[Department] = relationship(back_populates="managers")
    mappings: Mapped[list["ScreenMapping"]] = relationship(back_populates="manager")


class ScreenMapping(Base):
    __tablename__ = "screen_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    screen_id: Mapped[int] = mapped_column(ForeignKey("screens.id"), nullable=False)
    manager_id: Mapped[int] = mapped_column(ForeignKey("managers.id"), nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False)

    screen: Mapped[Screen] = relationship(back_populates="mappings")
    manager: Mapped[Manager] = relationship(back_populates="mappings")
    department: Mapped[Department] = relationship(back_populates="mappings")


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    screen_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    business_category: Mapped[str] = mapped_column(String(80), nullable=False)
    screen_name: Mapped[str] = mapped_column(String(120), nullable=False)
    reporter_employee_id: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    reporter_branch: Mapped[str] = mapped_column(String(80), nullable=False)
    ticket_type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    attachment_name: Mapped[str | None] = mapped_column(String(240), nullable=True)
    error_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_area_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    embedding_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    title_embedding_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_embedding_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    area_embedding_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    similarity_context_hash: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="RECEIVED", index=True)
    assigned_manager_id: Mapped[int | None] = mapped_column(ForeignKey("managers.id"), nullable=True)
    assigned_department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    assigned_manager: Mapped[Manager | None] = relationship()
    assigned_department: Mapped[Department | None] = relationship()
    histories: Mapped[list["TicketStatusHistory"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketStatusHistory.created_at",
    )
    followers: Mapped[list["TicketFollower"]] = relationship(back_populates="ticket", cascade="all, delete-orphan")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="ticket", cascade="all, delete-orphan")
    answers: Mapped[list["Answer"]] = relationship(
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="Answer.created_at",
    )


class TicketStatusHistory(Base):
    __tablename__ = "ticket_status_histories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), nullable=False, index=True)
    from_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(80), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    ticket: Mapped[Ticket] = relationship(back_populates="histories")


class TicketFollower(Base):
    __tablename__ = "ticket_followers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), nullable=False, index=True)
    employee_id: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    ticket: Mapped[Ticket] = relationship(back_populates="followers")


class ClassificationFeedback(Base):
    __tablename__ = "classification_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), nullable=False, index=True)
    previous_category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    new_category: Mapped[str] = mapped_column(String(80), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(80), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    ticket: Mapped[Ticket] = relationship()


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), nullable=False, index=True)
    employee_id: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    ticket: Mapped[Ticket] = relationship(back_populates="notifications")


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), nullable=False, index=True)
    author_manager_id: Mapped[int | None] = mapped_column(ForeignKey("managers.id"), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    ticket: Mapped[Ticket] = relationship(back_populates="answers")
    author_manager: Mapped[Manager | None] = relationship()
