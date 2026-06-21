from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from services.models import Base

APP_DIR = Path(__file__).resolve().parents[1]
DB_PATH = APP_DIR / "shinmungo.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def _existing_columns(table_name: str) -> set[str]:
    with engine.connect() as connection:
        rows = connection.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return {str(row[1]) for row in rows}


def migrate_schema() -> None:
    if not DB_PATH.exists():
        return
    ticket_columns = _existing_columns("tickets")
    additions = {
        "embedding_json": "ALTER TABLE tickets ADD COLUMN embedding_json TEXT",
        "classification_confidence": "ALTER TABLE tickets ADD COLUMN classification_confidence FLOAT",
        "source_category": "ALTER TABLE tickets ADD COLUMN source_category VARCHAR(80)",
        "selected_area_json": "ALTER TABLE tickets ADD COLUMN selected_area_json TEXT",
        "title_embedding_json": "ALTER TABLE tickets ADD COLUMN title_embedding_json TEXT",
        "content_embedding_json": "ALTER TABLE tickets ADD COLUMN content_embedding_json TEXT",
        "area_embedding_json": "ALTER TABLE tickets ADD COLUMN area_embedding_json TEXT",
        "similarity_context_hash": "ALTER TABLE tickets ADD COLUMN similarity_context_hash VARCHAR(80)",
    }
    with engine.begin() as connection:
        for column_name, ddl in additions.items():
            if column_name not in ticket_columns:
                connection.execute(text(ddl))
        connection.execute(
            text(
                """
                UPDATE tickets
                SET source_category = category
                WHERE source_category IS NULL
                  AND category IS NOT NULL
                """
            )
        )


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    migrate_schema()


def get_session() -> Session:
    return SessionLocal()
