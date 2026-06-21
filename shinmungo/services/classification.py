from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
CATEGORIES = ["버그", "UI불편", "기능개선", "성능", "업무절차혼선", "기타", "미분류"]
LOW_CONFIDENCE_THRESHOLD = 0.55


@dataclass(frozen=True)
class ClassificationResult:
    category: str
    confidence: float
    provider: str


class ClassifierProvider(ABC):
    @abstractmethod
    def classify(self, title: str, content: str) -> ClassificationResult:
        raise NotImplementedError


def _clip_confidence(value: object) -> float:
    try:
        confidence = float(value)
    except Exception:
        return 0.0
    return max(0.0, min(1.0, confidence))


def classify_with_rules(title: str, content: str) -> ClassificationResult:
    text = f"{title} {content}".lower()
    rules = [
        ("버그", 0.82, ["오류", "에러", "버그", "안됨", "불가", "조회되지", "미인자", "누락", "정정"]),
        ("성능", 0.78, ["느림", "지연", "멈춤", "속도", "로딩", "타임아웃"]),
        ("기능개선", 0.80, ["추가", "개선", "기능", "가능하게", "제한", "늘려", "해제", "반영", "자동"]),
        ("업무절차혼선", 0.74, ["문의", "방법", "절차", "기준", "유효기간", "선행", "조건", "재거래", "통합인자"]),
        ("UI불편", 0.70, ["화면", "버튼", "항목", "표시", "세팅", "기본값", "입력", "선택"]),
    ]
    for category, confidence, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return ClassificationResult(category, confidence, "rules")
    return ClassificationResult("미분류", 0.40, "rules")


class RuleBasedClassifier(ClassifierProvider):
    def classify(self, title: str, content: str) -> ClassificationResult:
        return classify_with_rules(title, content)


class OpenAIClassifier(ClassifierProvider):
    def __init__(self) -> None:
        load_dotenv(ROOT_DIR / ".env")
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "통합단말 신문고 접수 내용을 분류한다. 반드시 JSON만 출력한다. "
                    "category는 버그, UI불편, 기능개선, 성능, 업무절차혼선, 기타 중 하나다. "
                    "confidence는 0부터 1 사이 숫자다.",
                ),
                ("user", "제목: {title}\n내용: {content}"),
            ]
        )
        llm = ChatOpenAI(model="gpt-5.5", temperature=0)
        self.chain = prompt | llm | StrOutputParser()

    def classify(self, title: str, content: str) -> ClassificationResult:
        raw = self.chain.invoke({"title": title, "content": content})
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        data = json.loads(match.group(0) if match else raw)
        category = str(data.get("category", "기타")).strip()
        if category not in CATEGORIES:
            category = "기타"
        confidence = _clip_confidence(data.get("confidence", 0.0))
        if confidence < LOW_CONFIDENCE_THRESHOLD:
            category = "미분류"
        return ClassificationResult(category, confidence, "gpt-5.5")


def get_classifier() -> ClassifierProvider:
    load_dotenv(ROOT_DIR / ".env")
    if os.getenv("OPENAI_API_KEY"):
        try:
            return OpenAIClassifier()
        except Exception:
            return RuleBasedClassifier()
    return RuleBasedClassifier()


def classify_ticket(title: str, content: str, use_llm: bool = True) -> ClassificationResult:
    provider: ClassifierProvider = get_classifier() if use_llm else RuleBasedClassifier()
    try:
        result = provider.classify(title, content)
    except Exception:
        result = classify_with_rules(title, content)
    if result.confidence < LOW_CONFIDENCE_THRESHOLD:
        return ClassificationResult("미분류", result.confidence, result.provider)
    return result
