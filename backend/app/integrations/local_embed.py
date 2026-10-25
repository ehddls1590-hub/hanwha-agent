# 로컬 임베딩 어댑터
from __future__ import annotations

import os
from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger

log = get_logger(__name__)

# 다운받은 로컬 임베딩 모델 하나를 얄어 두고 재사용
class LocalEmbedder:
    name = "local"

    # 생성자: 임베더 초기 설정 하기
    def __init__(self) -> None:
        folder = Path(get_settings().embed_model_dir)
        if not folder.is_dir():
            raise ExternalServiceError(
                f"임베딩 모델 폴더를 찾을 수 없습니다: {folder}",
                detail="다운 받은 모델을 해당 위치에 압축해제 하거나, .env의 "
                       "EMBED_MODEL_DIR 설정값을 실제 위치를 변경해주세요. "
            )
        os.environ["HF_HUB_OFFLINE"] = "1"
        from sentence_transformers import SentenceTransformer

        try:
            self.model = SentenceTransformer(str(folder))
        except Exception as e:
            raise ExternalServiceError(f"임베딩 모델을 열지 못했습니다: {folder}") from e
        
        self.dim: int = int(self.model.get_embedding_dimension())
        log.info("로컬 임베딩 모델 준비: %s / %d차원", folder, self.dim)

    # 청크 텍스트 여러개를 한번에 벡터로 변환
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts, normalize_embeddings=True)
        return [[float(x) for x in v] for v in vectors]

    # 질문 한 문장을 벡터로 변환 
    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
    

