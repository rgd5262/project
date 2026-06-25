from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from services.models import (
    Answer,
    Department,
    Manager,
    Screen,
    ScreenMapping,
    Ticket,
    TicketFollower,
    TicketStatusHistory,
)
from services.routing import FALLBACK_DEPARTMENT
from services.classification import classify_ticket
from services.similarity import backfill_ticket_embeddings

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data" / "terminal_synthetic_xlsx"

REFERENCE_FILE = DATA_DIR / "01_terminal_reference.xlsx"
POST_FILE = DATA_DIR / "02_oullim_posts.xlsx"
ANSWER_FILE = DATA_DIR / "03_oullim_answers.xlsx"

DEPARTMENT_BY_SCREEN = {
    "111": "금융서비스개발부",
    "827": "퇴직연금사업부",
}

MANAGER_BY_DEPARTMENT = {
    "금융서비스개발부": ("M111", "김동시"),
    "퇴직연금사업부": ("M827", "박연금"),
    FALLBACK_DEPARTMENT: ("MSYS", "시스템관리자"),
}

STATUS_MAP = {
    "접수": "RECEIVED",
    "검토중": "REVIEWING",
    "개선검토": "REVIEWING",
    "처리중": "IN_PROGRESS",
    "처리완료": "DONE",
    "답변완료": "DONE",
    "완료": "DONE",
    "반려": "REJECTED",
    "보류": "ON_HOLD",
}

TYPE_MAP = {
    "업무문의": "불편",
    "기존기능문의": "불편",
    "오류/버그": "버그",
    "개선요청": "개선",
    "상품/기능문의": "개선",
}

REPORTERS = ["355901", "402045", "388210", "790112"]
AI_DEMO_TICKET_LIMIT_PER_SCREEN = 8

AI_DEMO_TICKETS = [
    (
        "111",
        "[AI시연] 베이직팩 통합인자 상태가 누락되어 감사 지적이 반복됩니다",
        "유동성 신규 후 전자금융 단계에서 오류가 났는데 재거래와 통합인자를 바로 인지하지 못해 베이직팩 장표가 미인자 상태로 남았습니다. 화면에서 즉시 안내가 필요합니다.",
        "DONE",
        "통합인자는 초기화 전 재거래 후 수행해야 하며 동일 문의 답변을 기준으로 즉시 확인 안내가 필요합니다.",
    ),
    (
        "111",
        "[AI시연] 베이직팩 미인자 보완 방법을 화면에서 안내해주세요",
        "오류 발생 후 초기화한 뒤에야 미인자를 알게 되는 경우가 있습니다. 재거래 가능 여부와 통합인자 버튼을 더 명확히 보여주세요.",
        "REVIEWING",
        "개별 오류 건은 재거래와 통합인자가 필요하며 초기화 전 가능하므로 안내 문구 개선을 검토합니다.",
    ),
    (
        "111",
        "[AI시연] 외화예금과 쏠트래블체크카드를 111에서 동시신규하고 싶습니다",
        "고객이 외화예금과 쏠트래블체크카드를 같이 요청하는 경우가 많아 계좌 카드 동시신규 화면에서 한 번에 처리되면 좋겠습니다.",
        "DONE",
        "외화예금 전산 담당 영역 협의가 필요하며 장표와 거래 흐름이 상이해 현 화면 단독 반영은 어렵습니다.",
    ),
    (
        "111",
        "[AI시연] 디지털창구 빠른신청 기본값을 직원별로 저장하고 싶습니다",
        "빠른신청으로 넘어온 건에서 매번 같은 값을 다시 선택합니다. 직원별 선호 기본값 저장 기능이 필요합니다.",
        "ON_HOLD",
        "직원별 선호값이 달라 일괄 변경은 어렵고 개인화 설정 방식은 후속 검토 대상입니다.",
    ),
    (
        "111",
        "[AI시연] 태블릿뱅킹 STAB 비밀번호 등록 내역이 조회되지 않습니다",
        "방문판매 후 영업점 동시신규 거래에서 STAB 클릭 시 비밀번호 등록 내역이 조회되지 않는 경우가 있습니다. 유효기간과 정정 방법 안내가 필요합니다.",
        "REVIEWING",
        "태블릿뱅킹 등록 내역 유효기간과 STAB 거래 정정 절차를 기존 답변 기준으로 안내합니다.",
    ),
    (
        "111",
        "[AI시연] 미성년자 대리인 신규 입력 항목을 줄여주세요",
        "미성년자 대리인 신규 시 확인 항목이 많아 시간이 오래 걸립니다. 필수 항목과 선택 항목을 분리해서 보여주세요.",
        "REVIEWING",
        "대리인 거래 필수 확인 항목은 업무 기준을 유지해야 하며 화면 배치 개선은 검토하겠습니다.",
    ),
    (
        "111",
        "[AI시연] 체크카드 신상품이 111 화면에 늦게 반영됩니다",
        "다른 체크카드 신규 화면에는 보이는 신상품이 계좌 카드 동시신규 화면에는 보이지 않습니다. 반영 일정을 맞춰주세요.",
        "DONE",
        "상품별 발급자격조회와 장표 차이로 반영 범위가 다를 수 있으며 담당 부서 검토 후 반영됩니다.",
    ),
    (
        "827",
        "[AI시연] 퇴직연금 보유상품변경에서 ETF 거래가 가능했으면 합니다",
        "고객이 IRP에서 ETF 매수를 요청하는 경우가 많은데 통합단말 827 화면에서 ETF 거래가 되지 않습니다. ETF 거래 기능을 추가해주세요.",
        "REVIEWING",
        "통합단말에서는 ETF 거래가 불가하며 미지원 기능 개선요청으로 접수해 검토합니다.",
    ),
    (
        "827",
        "[AI시연] 매도 매수 상품 5개 제한을 해제해주세요",
        "보유상품변경 시 매도와 매수 상품이 최대 5개로 제한되어 포트폴리오 변경을 여러 번 나눠 처리해야 합니다.",
        "ON_HOLD",
        "현재 매도와 매수 상품은 최대 5개까지 가능하며 제한 해제는 거래 안정성 검토가 필요합니다.",
    ),
    (
        "827",
        "[AI시연] 상품 매수 시 비율 말고 금액으로 지정하고 싶습니다",
        "매수상품을 30% 70% 같은 비율이 아니라 정확한 금액으로 지정해야 하는 고객 요청이 있습니다.",
        "DONE",
        "거래구분을 상세로 선택하면 매수상품 금액 지정이 가능합니다.",
    ),
    (
        "827",
        "[AI시연] 원리금비보장 상품이 조회되지 않습니다",
        "퇴직연금 보유상품변경에서 펀드 같은 원리금비보장 상품이 목록에 나오지 않습니다. 조회 방법이 별도로 있나요?",
        "DONE",
        "원리금비보장 버튼 선택 후 상품조회를 해야 원리금비보장상품이 조회됩니다.",
    ),
    (
        "827",
        "[AI시연] 투자자성향분석을 완료해야 상품 조회가 가능한지 문의",
        "원리금 보장상품 조회 전 투자자성향분석을 먼저 진행해야 하는지 화면 안내가 부족합니다.",
        "DONE",
        "원리금 보장상품의 경우 투자자성향분석을 선행해야 투자상품 조회가 가능합니다.",
    ),
    (
        "827",
        "[AI시연] ELB 거래가 가능한 조건을 화면에 표시해주세요",
        "ELB 거래를 시도하면 제한되는 경우가 있어 현금성 대기자산에서만 가능한 조건을 화면에서 바로 알고 싶습니다.",
        "REVIEWING",
        "ELB 거래는 현금성 대기자산에서만 가능하며 조건 안내 표시 개선을 검토합니다.",
    ),
    (
        "827",
        "[AI시연] 지정일 매수와 분할매수 기능 안내가 부족합니다",
        "상품 매도 후 원하는 날짜에 매수하거나 분할매수하는 기능을 직원들이 자주 놓칩니다. 화면에 안내가 필요합니다.",
        "REVIEWING",
        "지정일 매수와 분할매수 기능은 제공 중이며 업무 안내 문구 보강을 검토합니다.",
    ),
    (
        "111",
        "[AI시연] 통합인자 버튼을 오류 단계에서 강조 표시해주세요",
        "전자금융 오류가 발생한 뒤 직원이 통합인자 필요 여부를 놓치는 경우가 있습니다. 오류 단계에서 통합인자 버튼을 강조해주세요.",
        "IN_PROGRESS",
        "오류 발생 후 초기화 전 재거래와 통합인자 필요 여부를 화면에서 안내하는 방향으로 검토 중입니다.",
    ),
    (
        "111",
        "[AI시연] 베이직팩 감사 대상 여부를 바로 확인하고 싶습니다",
        "베이직팩 장표가 미인자 상태인지 감사 대상 여부를 업무 화면에서 바로 확인할 수 있으면 좋겠습니다.",
        "REVIEWING",
        "통합인자 누락 여부는 거래 직후 확인이 필요하며 감사 대상 안내 문구 개선을 검토합니다.",
    ),
    (
        "111",
        "[AI시연] 외화예금 동시신규 요청이 많은데 별도 안내가 필요합니다",
        "외화예금과 쏠트래블체크카드 동시신규를 요청하는 고객이 많아, 111 화면에서 처리 불가 사유와 담당 영역을 안내해주세요.",
        "DONE",
        "외화예금 전산 담당 영역 협의가 필요하며 유동성·전자금융·체크카드 거래 흐름과 장표가 달라 111 화면 단독 처리는 어렵습니다.",
    ),
    (
        "111",
        "[AI시연] 빠른신청 값이 직원마다 달라 화면 개인화가 필요합니다",
        "디지털창구 빠른신청 값이 직원마다 선호가 달라 매번 수정합니다. 개인별 기본값 저장이 필요합니다.",
        "ON_HOLD",
        "직원별 선호값이 상이해 일괄 기본값 변경은 어렵고 개인화 설정 방식은 후속 검토하겠습니다.",
    ),
    (
        "111",
        "[AI시연] STAB 거래 정정 경로를 화면에 표시해주세요",
        "태블릿뱅킹 비밀번호 등록 후 STAB 거래 정정이 필요한데 화면에서 정정 경로를 찾기 어렵습니다.",
        "IN_PROGRESS",
        "STAB 거래 정정 방법과 등록 내역 유효기간 안내를 업무 화면에 보강하는 방향으로 검토합니다.",
    ),
    (
        "111",
        "[AI시연] 미성년자 대리인 거래 필수 항목 안내가 필요합니다",
        "미성년자 대리인 신규 시 어떤 항목이 필수인지 직원마다 다르게 처리합니다. 필수 항목을 화면에 구분 표시해주세요.",
        "REVIEWING",
        "대리인 거래 필수 확인 항목은 업무 기준을 유지하되 필수/선택 구분 표시를 검토하겠습니다.",
    ),
    (
        "111",
        "[AI시연] 신규 체크카드 상품 반영 현황을 보여주세요",
        "체크카드 신규 화면에는 보이는 상품이 111 동시신규 화면에는 보이지 않아 고객 안내가 어렵습니다.",
        "DONE",
        "상품별 발급자격조회와 장표 차이로 반영 시점이 다를 수 있으며 상품 반영 현황 안내를 검토합니다.",
    ),
    (
        "111",
        "[AI시연] 모바일OTP 오류 후 재거래 안내를 추가해주세요",
        "모바일OTP 신규 중 오류가 나면 전자금융 재거래를 해야 하는데 직원이 바로 알기 어렵습니다.",
        "IN_PROGRESS",
        "모바일OTP 오류 후 전자금융 재거래와 통합인자 안내를 같은 흐름에서 표시하는 방안을 검토 중입니다.",
    ),
    (
        "827",
        "[AI시연] ETF 거래 불가 사유를 고객에게 안내하기 어렵습니다",
        "IRP 고객이 ETF 매수를 요청할 때 통합단말에서 불가한 이유를 설명할 문구가 필요합니다.",
        "DONE",
        "통합단말 827 화면에서는 ETF 거래가 미지원이며 별도 거래 채널 안내와 개선 요청으로 관리합니다.",
    ),
    (
        "827",
        "[AI시연] 상품 5개 제한 때문에 여러 번 처리해야 합니다",
        "매도 매수 상품이 각각 5개로 제한되어 포트폴리오가 복잡한 고객은 거래를 반복해야 합니다.",
        "IN_PROGRESS",
        "현재 최대 5개 제한은 거래 안정성 기준이며 제한 완화는 영향도 검토가 필요합니다.",
    ),
    (
        "827",
        "[AI시연] 매수금액 지정 메뉴를 못 찾겠습니다",
        "매수비율이 아니라 금액으로 입력하려는데 상세 거래구분을 선택해야 하는지 화면에서 잘 보이지 않습니다.",
        "DONE",
        "거래구분을 상세로 선택하면 매수상품 금액 지정이 가능하므로 해당 안내를 보강하겠습니다.",
    ),
    (
        "827",
        "[AI시연] 원리금비보장 버튼 선택 전에도 안내가 필요합니다",
        "원리금비보장 상품이 조회되지 않아 장애로 오해하는 경우가 있습니다. 버튼 선택 후 조회 필요 문구가 필요합니다.",
        "REVIEWING",
        "원리금비보장 버튼 선택 후 상품조회를 해야 조회된다는 안내를 화면에 표시하는 방안을 검토합니다.",
    ),
    (
        "827",
        "[AI시연] 투자자성향분석 미완료 시 안내 팝업이 필요합니다",
        "상품 조회 전 투자자성향분석을 하지 않으면 왜 조회가 안 되는지 직원이 바로 알기 어렵습니다.",
        "IN_PROGRESS",
        "투자자성향분석 선행 조건을 팝업 또는 안내 영역에 표시하는 방향으로 검토 중입니다.",
    ),
    (
        "827",
        "[AI시연] ELB는 현금성 대기자산 조건을 먼저 알려주세요",
        "ELB 거래 시 현금성 대기자산에서만 가능한 조건을 거래 전 단계에서 안내받고 싶습니다.",
        "REVIEWING",
        "ELB 거래 가능 조건을 거래 전 안내 영역에 표시하도록 검토하겠습니다.",
    ),
    (
        "827",
        "[AI시연] 분할매수 지정일 매수 안내 문구가 부족합니다",
        "지정일 매수와 분할매수 기능이 제공되지만 직원들이 잘 몰라 고객 안내가 누락됩니다.",
        "DONE",
        "지정일 매수와 분할매수는 제공 중인 기능이며 화면 안내와 업무 기준 문구를 보강하겠습니다.",
    ),
    (
        "827",
        "[AI시연] 만기 상품 일괄 보유상품변경 안내를 추가해주세요",
        "1개월 이내 만기 상품과 일괄 보유상품변경 차이를 화면에서 바로 알기 어렵습니다.",
        "REVIEWING",
        "만기 대상 거래와 일괄 지정 거래의 차이를 화면 안내 문구로 보강하는 방안을 검토합니다.",
    ),
]


def _clean(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _to_datetime(value: object, fallback: datetime) -> datetime:
    if value is None or pd.isna(value):
        return fallback
    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp):
        return fallback
    return timestamp.to_pydatetime()


def _status(value: object) -> str:
    return STATUS_MAP.get(_clean(value), "RECEIVED")


def _ticket_type(category: str) -> str:
    return TYPE_MAP.get(category, "불편")


def seed_if_empty(session: Session) -> None:
    if session.query(Screen).count() == 0:
        _seed_raw_data(session)
    _prepare_ai_demo_data(session)


def _seed_raw_data(session: Session) -> None:
    if not (REFERENCE_FILE.exists() and POST_FILE.exists() and ANSWER_FILE.exists()):
        raise FileNotFoundError(f"Raw Excel files not found under {DATA_DIR}")

    reference_df = pd.read_excel(REFERENCE_FILE).fillna("")
    posts_df = pd.read_excel(POST_FILE).fillna("")
    answers_df = pd.read_excel(ANSWER_FILE).fillna("")

    departments: dict[str, Department] = {}
    for dept_name in ["금융서비스개발부", "퇴직연금사업부", FALLBACK_DEPARTMENT]:
        department = Department(name=dept_name)
        session.add(department)
        departments[dept_name] = department
    session.flush()

    managers: dict[str, Manager] = {}
    for dept_name, (employee_id, manager_name) in MANAGER_BY_DEPARTMENT.items():
        manager = Manager(name=manager_name, employee_id=employee_id, department_id=departments[dept_name].id)
        session.add(manager)
        managers[dept_name] = manager
    session.flush()

    screens: dict[str, Screen] = {}
    screen_rows = reference_df[reference_df["자료유형"] == "화면"]
    for _, row in screen_rows.iterrows():
        code = _clean(row["화면번호"])
        screen = Screen(
            screen_code=code,
            screen_name=_clean(row["화면명"]),
            business_category=_clean(row["업무영역"]),
        )
        session.add(screen)
        screens[code] = screen
    session.flush()

    for code, screen in screens.items():
        dept_name = DEPARTMENT_BY_SCREEN.get(code, FALLBACK_DEPARTMENT)
        mapping = ScreenMapping(
            screen_id=screen.id,
            manager_id=managers[dept_name].id,
            department_id=departments[dept_name].id,
        )
        session.add(mapping)
    session.flush()

    ticket_by_post_id: dict[str, Ticket] = {}
    for index, row in posts_df.iterrows():
        post_id = _clean(row["post_id"])
        screen_code = _clean(row["화면번호"])
        dept_name = _clean(row["담당부서"]) or DEPARTMENT_BY_SCREEN.get(screen_code, FALLBACK_DEPARTMENT)
        created_at = _to_datetime(row["작성일시"], datetime.now() - timedelta(days=30))
        source_category = _clean(row["원문분류"])
        attachment = "업무화면_캡처.png" if _clean(row["첨부여부"]) == "Y" else None
        ticket = Ticket(
            screen_code=screen_code,
            business_category=screens[screen_code].business_category,
            screen_name=_clean(row["화면명"]),
            reporter_employee_id=REPORTERS[index % len(REPORTERS)],
            reporter_branch=_clean(row["점포유형"]) or "일반영업점",
            ticket_type=_ticket_type(source_category),
            title=_clean(row["요청제목"]),
            content=_clean(row["요청본문"]),
            attachment_name=attachment,
            error_log=f"[자동첨부] screen={screen_code}, source=어울림광장 raw seed, post_id={post_id}",
            category=source_category,
            source_category=source_category,
            status=_status(row["현재상태"]),
            assigned_manager_id=managers[dept_name].id,
            assigned_department_id=departments[dept_name].id,
            created_at=created_at,
            updated_at=created_at,
        )
        session.add(ticket)
        session.flush()
        ticket_by_post_id[post_id] = ticket
        session.add(TicketFollower(ticket_id=ticket.id, employee_id=ticket.reporter_employee_id, created_at=created_at))

    for _, row in answers_df.iterrows():
        post_id = _clean(row["post_id"])
        ticket = ticket_by_post_id.get(post_id)
        if not ticket:
            continue
        created_at = _to_datetime(row["답변일시"], ticket.created_at + timedelta(hours=1))
        from_status = _status(row["이전상태"]) if _clean(row["이전상태"]) else None
        to_status = _status(row["변경상태"] or row["처리결과상태"])
        comment = _clean(row["답변본문"]) or _clean(row["처리이력메모"]) or _clean(row["답변유형"])
        session.add(
            TicketStatusHistory(
                ticket_id=ticket.id,
                from_status=from_status,
                to_status=to_status,
                changed_by=_clean(row["답변자역할"]) or _clean(row["처리부서"]) or "시스템",
                comment=comment,
                created_at=created_at,
            )
        )
        ticket.status = to_status
        ticket.updated_at = max(ticket.updated_at, created_at)

    session.commit()


def _departments_by_name(session: Session) -> dict[str, Department]:
    return {department.name: department for department in session.query(Department).all()}


def _managers_by_department(session: Session) -> dict[str, Manager]:
    managers: dict[str, Manager] = {}
    for manager in session.query(Manager).all():
        managers[manager.department.name] = manager
    return managers


def _screens_by_code(session: Session) -> dict[str, Screen]:
    return {screen.screen_code: screen for screen in session.query(Screen).all()}


def _prepare_ai_demo_data(session: Session) -> None:
    _backfill_source_and_classification(session)
    _seed_ai_demo_tickets(session)
    _backfill_source_and_classification(session)
    _backfill_answers(session)
    backfill_ticket_embeddings(session)


def _backfill_source_and_classification(session: Session) -> int:
    changed = 0
    for ticket in session.query(Ticket).all():
        if not ticket.source_category and ticket.category:
            ticket.source_category = ticket.category
            changed += 1
        if ticket.classification_confidence is None or ticket.category in TYPE_MAP:
            result = classify_ticket(ticket.title, ticket.content, use_llm=False)
            ticket.category = result.category
            ticket.classification_confidence = result.confidence
            changed += 1
    if changed:
        session.commit()
    return changed


def _seed_ai_demo_tickets(session: Session) -> int:
    screens = _screens_by_code(session)
    departments = _departments_by_name(session)
    managers = _managers_by_department(session)
    existing_counts = Counter(
        screen_code
        for (screen_code,) in session.query(Ticket.screen_code)
        .filter(Ticket.source_category == "AI시연")
        .all()
    )
    created = 0
    for index, (screen_code, title, content, status, answer) in enumerate(AI_DEMO_TICKETS):
        if existing_counts[screen_code] >= AI_DEMO_TICKET_LIMIT_PER_SCREEN:
            continue
        if session.query(Ticket).filter(Ticket.title == title).first():
            continue
        screen = screens[screen_code]
        dept_name = DEPARTMENT_BY_SCREEN[screen_code]
        department = departments[dept_name]
        manager = managers[dept_name]
        now = datetime.now() - timedelta(days=7 - min(index, 6), hours=index)
        result = classify_ticket(title, content, use_llm=False)
        ticket = Ticket(
            screen_code=screen_code,
            business_category=screen.business_category,
            screen_name=screen.screen_name,
            reporter_employee_id=REPORTERS[index % len(REPORTERS)],
            reporter_branch="일반영업점",
            ticket_type="개선" if result.category == "기능개선" else "불편",
            title=title,
            content=content,
            attachment_name="AI시연_업무화면.png",
            error_log=f"[자동첨부] screen={screen_code}, source=AI demo seed",
            category=result.category,
            source_category="AI시연",
            classification_confidence=result.confidence,
            status=status,
            assigned_manager_id=manager.id,
            assigned_department_id=department.id,
            created_at=now,
            updated_at=now + timedelta(hours=2),
        )
        session.add(ticket)
        session.flush()
        session.add(
            TicketStatusHistory(
                ticket_id=ticket.id,
                from_status=None,
                to_status="RECEIVED",
                changed_by="AI시연시드",
                comment="유사 검색 시연을 위해 등록된 기존 요청입니다.",
                created_at=now,
            )
        )
        session.add(
            TicketStatusHistory(
                ticket_id=ticket.id,
                from_status="RECEIVED",
                to_status=status,
                changed_by=manager.name,
                comment=answer,
                created_at=now + timedelta(hours=2),
            )
        )
        session.add(
            Answer(
                ticket_id=ticket.id,
                author_manager_id=manager.id,
                body=answer,
                created_at=now + timedelta(hours=2, minutes=5),
            )
        )
        created += 1
        existing_counts[screen_code] += 1
    if created:
        session.commit()
    return created


def _backfill_answers(session: Session) -> int:
    created = 0
    for ticket in session.query(Ticket).all():
        if ticket.answers:
            continue
        history = next((item for item in reversed(ticket.histories) if item.comment and item.to_status != "RECEIVED"), None)
        if not history:
            continue
        session.add(
            Answer(
                ticket_id=ticket.id,
                author_manager_id=ticket.assigned_manager_id,
                body=history.comment,
                created_at=history.created_at,
            )
        )
        created += 1
    if created:
        session.commit()
    return created
