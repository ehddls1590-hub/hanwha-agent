# 임베딩 진입점 
from __future__ import annotations
from collections.abc import Callable
from app.integrations.factory import get_embedder
from app.core.config import get_settings
from pathlib import Path

# 청크 텍스트 목록을 벡터 목록으로 변환해주는 함수
def embed_documents(
        texts: list[str],
        *,
        batch: int = 50,
        on_progress: Callable[[int, int], None] | None = None,
) -> list[list[float]]:
    embedder = get_embedder()
    out: list[list[float]] = []
    total = len(texts)
    for i in range(0, total, batch):
        out.extend(embedder.embed_documents(texts[i : i + batch]))
        if on_progress is not None:
            on_progress(min(i + batch, total), total)
    return out


# 질문 한 문장을 벡터로 변환해주는 함수
def embed_query(text: str) -> list[float]:
    return get_embedder().embed_query(text)

# 현재 사용중인 어댑터가 만들어주는 벡터 길이
def embed_dim() -> int:
    return int(getattr(get_embedder(),"dim",0))

# 임베읻 모델명 리턴 함수
def model_label() -> str:
    s = get_settings()
    if s.embed_provider =="upstage":
        return f"upstage/{s.upstage_embed_model or 'embed'}" # upstage/모델명
    return f"local/{Path(s.embed_model_dir).name}" #local/bge-m3