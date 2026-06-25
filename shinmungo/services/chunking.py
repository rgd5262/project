from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChunkingConfig:
    model_name: str = "text-embedding-3-large"
    chunk_size: int = 500
    chunk_overlap: int = 30


def split_text(text: str, config: ChunkingConfig | None = None) -> list[str]:
    value = (text or "").strip()
    if not value:
        return []
    config = config or ChunkingConfig()
    if len(value) <= config.chunk_size:
        return [value]
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            model_name=config.model_name,
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
        )
        chunks = splitter.split_text(value)
        return [chunk.strip() for chunk in chunks if chunk.strip()]
    except Exception:
        step = max(1, config.chunk_size - config.chunk_overlap)
        return [value[index : index + config.chunk_size].strip() for index in range(0, len(value), step)]


def compact_for_embedding(screen_code: str, title: str, content: str) -> str:
    return f"화면번호 {screen_code}\n제목 {title.strip()}\n내용 {content.strip()}".strip()
