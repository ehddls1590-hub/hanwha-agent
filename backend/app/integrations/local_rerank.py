from __future__ import annotations

import math
import os
from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger

log = get_logger(__name__)

# 원래 점수를 0~1 사이로 변경
def _sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    z = math.exp(x)
    return z / (1.0 + z)


class LocalCrossEncoder:
    name = "cross_encoder"

    def __init__(self) -> None:
        settings = get_settings()
        folder = Path(settings.rerank_model_dir)
        if not folder.is_dir():
            raise ExternalServiceError(
                f"리랭커 모델 폴더를 찾을 수 없습니다: {folder}",
                detail="모델을 해당 위치에 다운 받거나, .env의 RERANK_MODEL_DIR 을 실제 폴더로 "
                "변경 하세요. 모델 없이 사용하려면 RERANKER=simple로 지정하세요."
            )
        os.environ["HF_HUB_OFFLINE"] = "1" 

        import torch
        from sentence_transformers import CrossEncoder

        try:
            self._model = CrossEncoder(str(folder), max_length=settings.rerank_max_length, 
            activation_fn=torch.nn.Identity())
        except Exception as e:
            raise ExternalServiceError(f"리랭커 모델을 열지 못했습니다: {folder}") from e
        
        log.info("로컬 리랭커 준비 : %s, 최대 %d토큰", folder, settings.rerank_max_length)        

    def score_pairs(self, query: str, texts: list[str]) -> list[float]:
        if not texts:
            return []
        raw = self._model.predict([[query, t] for t in texts], show_progress_bar=False)
        return [round(_sigmoid(float(x)), 4) for x in raw]



