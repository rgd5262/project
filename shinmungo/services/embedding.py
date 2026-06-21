from __future__ import annotations

from abc import ABC, abstractmethod
import hashlib
import math
import re

import numpy as np
import streamlit as st

from services.chunking import compact_for_embedding, split_text

DEFAULT_MODEL_NAME = "jhgan/ko-sroberta-multitask"

KEYWORDS = [
    "통합인자",
    "미인자",
    "베이직팩",
    "재거래",
    "초기화",
    "오류",
    "버그",
    "체크카드",
    "외화예금",
    "쏠트래블",
    "디지털창구",
    "빠른신청",
    "태블릿뱅킹",
    "STAB",
    "비밀번호",
    "미성년자",
    "대리인",
    "유동성",
    "전자금융",
    "OTP",
    "나라사랑카드",
    "ETF",
    "퇴직연금",
    "IRP",
    "DB",
    "DC",
    "원리금보장",
    "원리금비보장",
    "투자자성향",
    "ELB",
    "만기",
    "일괄",
    "지정일",
    "분할매수",
    "매수비율",
    "금액",
    "상품조회",
    "5개",
    "제한",
    "성능",
    "느림",
]


class EmbeddingProvider(ABC):
    name: str

    @abstractmethod
    def embed_text(self, text: str) -> np.ndarray:
        raise NotImplementedError


@st.cache_resource(show_spinner="로컬 임베딩 모델을 불러오는 중입니다.")
def _load_sentence_model(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    name = DEFAULT_MODEL_NAME

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME) -> None:
        self.model_name = model_name
        self.model = _load_sentence_model(model_name)

    def embed_text(self, text: str) -> np.ndarray:
        chunks = split_text(text)
        if not chunks:
            return np.zeros(1, dtype=np.float32)
        vectors = self.model.encode(chunks, normalize_embeddings=True)
        vector = np.asarray(vectors, dtype=np.float32).mean(axis=0)
        norm = np.linalg.norm(vector)
        return vector if norm == 0 else vector / norm


class DeterministicEmbeddingProvider(EmbeddingProvider):
    name = "간이 로컬 벡터"

    def __init__(self, dimensions: int = 128) -> None:
        self.dimensions = dimensions

    def embed_text(self, text: str) -> np.ndarray:
        normalized = text.lower()
        vector = np.zeros(self.dimensions, dtype=np.float32)
        for index, keyword in enumerate(KEYWORDS):
            if keyword.lower() in normalized:
                vector[index % self.dimensions] += 4.0
        for token in re.findall(r"[0-9a-zA-Z가-힣#]+", normalized):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimensions
            vector[bucket] += 1.0 + min(len(token), 10) / 20.0
        norm = math.sqrt(float(np.dot(vector, vector)))
        return vector if norm == 0 else vector / norm


@st.cache_resource(show_spinner=False)
def get_embedding_provider() -> EmbeddingProvider:
    try:
        return SentenceTransformerEmbeddingProvider()
    except Exception:
        return DeterministicEmbeddingProvider()


def embed_ticket_text(screen_code: str, title: str, content: str) -> np.ndarray:
    provider = get_embedding_provider()
    return provider.embed_text(compact_for_embedding(screen_code, title, content))


def embed_plain_text(text: str) -> np.ndarray:
    provider = get_embedding_provider()
    return provider.embed_text((text or "").strip())


def embedding_provider_name() -> str:
    return get_embedding_provider().name
