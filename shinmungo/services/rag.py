from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import os
from pathlib import Path
import re

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from services.models import Answer, Ticket
from services.selected_area import selected_area_detail
from services.similarity import find_similar, latest_answer
from services.ui import status_label

ROOT_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class SimilarCase:
    ticket_id: int
    title: str
    status: str
    category: str
    answer: str
    similarity: float


def latest_answer_body(ticket: Ticket) -> str:
    if ticket.answers:
        for answer in reversed(ticket.answers):
            if answer.body:
                return answer.body
    return latest_answer(ticket)


def _normalize_case_text(value: str | None) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    return text[:180]


def similar_cases_for_ticket(session: Session, ticket_id: int, top_k: int = 5) -> list[SimilarCase]:
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        return []
    rows = find_similar(
        session,
        ticket.screen_code,
        ticket.title,
        ticket.content,
        selected_area_json=ticket.selected_area_json,
        top_k=max(top_k * 6, top_k + 10),
        threshold=0.75,
    )
    cases: list[SimilarCase] = []
    seen_case_keys: set[tuple[str, str, str]] = set()
    for row in rows:
        if int(row["id"]) == ticket_id:
            continue
        similar_ticket = session.get(Ticket, int(row["id"]))
        if not similar_ticket:
            continue
        answer_body = latest_answer_body(similar_ticket)
        case_key = (
            similar_ticket.screen_code,
            _normalize_case_text(similar_ticket.title),
            _normalize_case_text(answer_body),
        )
        if case_key in seen_case_keys:
            continue
        seen_case_keys.add(case_key)
        cases.append(
            SimilarCase(
                ticket_id=similar_ticket.id,
                title=similar_ticket.title,
                status=similar_ticket.status,
                category=similar_ticket.category or "미분류",
                answer=answer_body,
                similarity=float(row["similarity"]),
            )
        )
        if len(cases) >= top_k:
            break
    return cases


def _context_from_cases(cases: list[SimilarCase]) -> str:
    lines: list[str] = []
    for case in cases:
        lines.append(
            f"- 문의번호={case.ticket_id}, 상태={status_label(case.status)}, "
            f"분류={case.category}, 유사도={case.similarity:.2f}\n"
            f"  제목: {case.title}\n"
            f"  답변: {case.answer or '등록된 답변 없음'}"
        )
    return "\n".join(lines)


def _offline_summary(cases: list[SimilarCase]) -> str:
    if not cases:
        return "유사 사례 0건, 대표 답변 요약: 아직 참고할 유사 처리 사례가 없습니다."
    counts = Counter(case.status for case in cases)
    done_count = counts.get("DONE", 0)
    active_count = sum(counts.get(status, 0) for status in ["RECEIVED", "REVIEWING", "IN_PROGRESS", "ON_HOLD"])
    representative = next((case.answer for case in cases if case.answer), "")
    if not representative:
        representative = "유사 요청의 처리 상태를 확인한 뒤 담당 부서 답변을 기다려야 합니다."
    return (
        f"유사 사례 {len(cases)}건(완료 {done_count}·처리중 {active_count}), "
        f"대표 답변 요약: {representative[:180]}"
    )


def _offline_draft(ticket: Ticket, cases: list[SimilarCase]) -> str:
    references = ", ".join(f"#{case.ticket_id}" for case in cases) or "참조 사례 없음"
    answer = next((case.answer for case in cases if case.answer), "")
    if not answer:
        answer = "유사 사례의 처리 이력과 현재 화면 담당부서 기준으로 검토가 필요합니다."
    selected_area = selected_area_detail(ticket.selected_area_json)
    area_sentence = "" if selected_area == "-" else f"요청자가 지정한 화면 영역은 {selected_area}입니다. "
    return (
        f"안녕하세요. {ticket.screen_code} {ticket.screen_name} 화면 관련 문의에 대해 안내드립니다.\n\n"
        f"현재 접수 내용은 '{ticket.title}'이며, 기존 유사 사례({references})를 기준으로 검토했습니다. "
        f"{area_sentence}{answer}\n\n"
        "추가 확인이 필요한 경우 화면번호, 발생 단계, 오류 문구를 함께 전달해 주시면 후속 검토하겠습니다.\n"
        f"참조 문의번호: {references}"
    )


def _openai_generate(system_prompt: str, user_prompt: str) -> str | None:
    load_dotenv(ROOT_DIR / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        return None
    try:
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI

        prompt = ChatPromptTemplate.from_messages([("system", system_prompt), ("user", "{input}")])
        chain = prompt | ChatOpenAI(model="gpt-5.5", temperature=0) | StrOutputParser()
        return chain.invoke({"input": user_prompt}).strip()
    except Exception:
        return None


def summarize_similar_cases(session: Session, ticket_id: int, use_llm: bool = True) -> str:
    cases = similar_cases_for_ticket(session, ticket_id)
    fallback = _offline_summary(cases)
    if not use_llm or not cases:
        return fallback
    context = _context_from_cases(cases)
    online = _openai_generate(
        "통합단말 신문고 유사 처리 사례를 한국어로 짧게 요약한다. 컨텍스트에 없는 내용은 추측하지 않는다.",
        f"다음 유사 사례를 한 문장으로 요약해줘. 반드시 '유사 사례 N건(완료 M·처리중 K), 대표 답변 요약: ...' 형식을 유지해.\n\n{context}",
    )
    return online or fallback


def generate_answer_draft(session: Session, ticket_id: int, use_llm: bool = True) -> str:
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        return "선택한 문의를 찾을 수 없습니다."
    cases = similar_cases_for_ticket(session, ticket_id)
    fallback = _offline_draft(ticket, cases)
    if not use_llm:
        return fallback
    context = _context_from_cases(cases)
    online = _openai_generate(
        "통합단말 신문고 관리자 답변 초안을 작성한다. 컨텍스트에 없는 내용을 추측하지 말고, 참조 문의번호를 반드시 명시한다.",
        f"현재 문의:\n"
        f"- 문의번호={ticket.id}\n- 화면={ticket.screen_code} {ticket.screen_name}\n"
        f"- 분류={ticket.category}\n- 제목={ticket.title}\n- 내용={ticket.content}\n\n"
        f"- 선택 영역={selected_area_detail(ticket.selected_area_json)}\n\n"
        f"유사 사례:\n{context}\n\n"
        "관리자가 편집 가능한 답변 초안을 5문장 이내로 작성해줘.",
    )
    return online or fallback
