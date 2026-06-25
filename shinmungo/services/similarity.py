from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from services.embedding import embed_plain_text, embed_ticket_text
from services.models import Ticket
from services.selected_area import parse_selected_area

WEIGHTS_WITH_AREA = {
    "screen": 0.25,
    "area": 0.25,
    "title": 0.10,
    "content": 0.40,
}
WEIGHTS_WITHOUT_AREA = {
    "screen": 0.40,
    "title": 0.15,
    "content": 0.45,
}
SIMILARITY_CONTEXT_VERSION = "weighted-v1"


def serialize_embedding(vector: np.ndarray) -> str:
    return json.dumps([round(float(value), 8) for value in vector.tolist()], ensure_ascii=False)


def deserialize_embedding(value: str | None) -> np.ndarray | None:
    if not value:
        return None
    try:
        return np.asarray(json.loads(value), dtype=np.float32)
    except Exception:
        return None


def cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    left_norm = float(np.linalg.norm(left))
    right_norm = float(np.linalg.norm(right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return float(np.dot(left, right) / (left_norm * right_norm))


def ensure_ticket_embedding(ticket: Ticket) -> bool:
    if ticket.embedding_json:
        return False
    ticket.embedding_json = serialize_embedding(embed_ticket_text(ticket.screen_code, ticket.title, ticket.content))
    return True


def area_embedding_text(selected_area_json: str | None) -> str:
    area = parse_selected_area(selected_area_json)
    if not area:
        return ""
    parts = [
        f"영역ID {area.get('area_id') or ''}",
        f"영역명 {area.get('area_name') or ''}",
        f"영역유형 {area.get('area_type') or ''}",
        f"선택텍스트 {area.get('text') or ''}",
    ]
    return "\n".join(part for part in parts if part.strip()).strip()


def similarity_context_hash(screen_code: str, title: str, content: str, selected_area_json: str | None) -> str:
    payload = {
        "version": SIMILARITY_CONTEXT_VERSION,
        "screen_code": str(screen_code or "").strip(),
        "title": str(title or "").strip(),
        "content": str(content or "").strip(),
        "selected_area": parse_selected_area(selected_area_json) or {},
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def ensure_ticket_similarity_embeddings(ticket: Ticket) -> bool:
    expected_hash = similarity_context_hash(
        ticket.screen_code,
        ticket.title,
        ticket.content,
        ticket.selected_area_json,
    )
    if (
        ticket.similarity_context_hash == expected_hash
        and ticket.title_embedding_json
        and ticket.content_embedding_json
        and (ticket.area_embedding_json or not area_embedding_text(ticket.selected_area_json))
    ):
        return False

    ticket.title_embedding_json = serialize_embedding(embed_plain_text(ticket.title))
    ticket.content_embedding_json = serialize_embedding(embed_plain_text(ticket.content))
    area_text = area_embedding_text(ticket.selected_area_json)
    ticket.area_embedding_json = serialize_embedding(embed_plain_text(area_text)) if area_text else None
    ticket.similarity_context_hash = expected_hash
    return True


def backfill_ticket_embeddings(session: Session) -> int:
    tickets = session.query(Ticket).all()
    changed = 0
    for ticket in tickets:
        if ensure_ticket_embedding(ticket):
            changed += 1
        if ensure_ticket_similarity_embeddings(ticket):
            changed += 1
    if changed:
        session.commit()
    return changed


def latest_answer(ticket: Ticket) -> str:
    if not ticket.histories:
        return ""
    for history in reversed(ticket.histories):
        if history.comment:
            return history.comment
    return ""


def display_snippet(text: str, limit: int = 120) -> str:
    legacy_label = "기존 요청" + "과 다른 점"
    cleaned = re.sub(rf"\s*\[{re.escape(legacy_label)}\].*", "", text or "", flags=re.DOTALL).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:limit] + ("..." if len(cleaned) > limit else "")


def area_similarity(
    query_area_json: str | None,
    ticket_area_json: str | None,
    query_area_vector: np.ndarray | None,
    ticket_area_vector: np.ndarray | None,
) -> float:
    query_area = parse_selected_area(query_area_json)
    ticket_area = parse_selected_area(ticket_area_json)
    if not query_area or not ticket_area:
        return 0.0

    query_area_id = str(query_area.get("area_id") or "").strip()
    ticket_area_id = str(ticket_area.get("area_id") or "").strip()
    if query_area_id and ticket_area_id and query_area_id == ticket_area_id:
        return 1.0

    query_area_name = str(query_area.get("area_name") or "").strip()
    ticket_area_name = str(ticket_area.get("area_name") or "").strip()
    if query_area_name and ticket_area_name and query_area_name == ticket_area_name:
        return 0.9

    query_area_type = str(query_area.get("area_type") or "").strip()
    ticket_area_type = str(ticket_area.get("area_type") or "").strip()
    if query_area_type and ticket_area_type and query_area_type == ticket_area_type:
        text_score = 0.0
        if query_area_vector is not None and ticket_area_vector is not None:
            text_score = max(0.0, cosine_similarity(query_area_vector, ticket_area_vector))
        return min(0.8, 0.6 + text_score * 0.2)

    return 0.0


def weighted_similarity_score(
    *,
    screen_code: str,
    ticket: Ticket,
    query_title_vector: np.ndarray,
    query_content_vector: np.ndarray,
    query_area_json: str | None,
    query_area_vector: np.ndarray | None,
) -> float | None:
    title_vector = deserialize_embedding(ticket.title_embedding_json)
    content_vector = deserialize_embedding(ticket.content_embedding_json)
    if title_vector is None or content_vector is None:
        return None

    screen_score = 1.0 if ticket.screen_code == str(screen_code) else 0.0
    title_score = max(0.0, cosine_similarity(query_title_vector, title_vector))
    content_score = max(0.0, cosine_similarity(query_content_vector, content_vector))

    if parse_selected_area(query_area_json):
        ticket_area_vector = deserialize_embedding(ticket.area_embedding_json)
        area_score = area_similarity(query_area_json, ticket.selected_area_json, query_area_vector, ticket_area_vector)
        weights = WEIGHTS_WITH_AREA
        score = (
            screen_score * weights["screen"]
            + area_score * weights["area"]
            + title_score * weights["title"]
            + content_score * weights["content"]
        )
        return min(1.0, max(0.0, score))

    weights = WEIGHTS_WITHOUT_AREA
    score = (
        screen_score * weights["screen"]
        + title_score * weights["title"]
        + content_score * weights["content"]
    )
    return min(1.0, max(0.0, score))


def find_similar(
    session: Session,
    screen_code: str,
    title: str,
    content: str,
    selected_area_json: str | None = None,
    top_k: int = 5,
    threshold: float = 0.75,
) -> list[dict[str, Any]]:
    query_title_vector = embed_plain_text(title)
    query_content_vector = embed_plain_text(content)
    query_area_text = area_embedding_text(selected_area_json)
    query_area_vector = embed_plain_text(query_area_text) if query_area_text else None
    candidates = session.query(Ticket).all()
    results: list[dict[str, Any]] = []
    for ticket in candidates:
        ensure_ticket_embedding(ticket)
        ensure_ticket_similarity_embeddings(ticket)
        score = weighted_similarity_score(
            screen_code=screen_code,
            ticket=ticket,
            query_title_vector=query_title_vector,
            query_content_vector=query_content_vector,
            query_area_json=selected_area_json,
            query_area_vector=query_area_vector,
        )
        if score is None:
            continue
        if score < threshold:
            continue
        department = ticket.assigned_department.name if ticket.assigned_department else "미배정"
        snippet = display_snippet(ticket.content)
        answer = latest_answer(ticket)
        results.append(
            {
                "id": ticket.id,
                "title": ticket.title,
                "status": ticket.status,
                "category": ticket.category or ticket.source_category or ticket.ticket_type,
                "similarity": score,
                "assigned_department": department,
                "content_snippet": snippet,
                "latest_answer": answer[:220] + ("..." if len(answer) > 220 else ""),
            }
        )
    session.commit()
    return sorted(results, key=lambda row: row["similarity"], reverse=True)[:top_k]
