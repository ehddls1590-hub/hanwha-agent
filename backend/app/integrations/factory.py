# mock / live 분기의 유일한 지점
from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.core.exceptions import ModeNotAvailable
from app.integrations.ports import LLMPort, EmbedderPort, RerankerPort

# Claude 어댑터를 하나 만들어 두고, 재사용하기
@lru_cache
def _live_llm() -> LLMPort:
    # live 모드일때만 import해서 ClaudeLLM 생성해주기
    from app.integrations.llm_claude import ClaudeLLM
    return ClaudeLLM()

# 지금 설정에 맞는 LLM 어댑터를 돌려주는 함수
def get_llm() -> LLMPort:
    settings = get_settings() # 환경 설정 정보 가져오기
    if not settings.is_live: # live가 아니다
        raise ModeNotAvailable(
            "테스트용 mock 어댑터는 만들지 않았습니다."
            ".env의 APP_MODE 를 live로 두고 터미널에서 부르세요."
        )
    return _live_llm()

# 로컬 임베딩 어댑터를 하나 만들어두고, 재사용
@lru_cache
def _local_embedder() -> EmbedderPort:
    from app.integrations.local_embed import LocalEmbedder

    return LocalEmbedder()

# 상용 임베딩 어댑터를 하나 만들어두고, 재사용
@lru_cache
def _upstage_embedder() -> EmbedderPort:
    from app.integrations.upstage import UpstageEmbedder

    return UpstageEmbedder()

# 현재 설정에 맞는 임베딩 어댑터 돌려주는 함수
def get_embedder()-> EmbedderPort:
    provider = get_settings().embed_provider
    if provider == "upstage":
        return _upstage_embedder()
    return _local_embedder()

# 크로스 인코더 어댑터 하나 만들어 돌려주는 함수 (재사용)
@lru_cache
def get_cross_encoder() -> RerankerPort:
    from app.integrations.local_rerank import LocalCrossEncoder
    return LocalCrossEncoder()

# 슬랙 어댑터 하나 만들어 주는 함수 (재사용)
@lru_cache
def _live_slack() -> SlackPort: 
    from app.integrations.slack import SlackClient
    return SlackClient() 

# 슬랙 어댑터 빌려주는 함수 
def get_slack() -> SlackPort:
    if not get_settings().allow_external_send:
        raise ModeNotAvailable(
            "외부 전송이 꺼져 있습니다(ALLOW_EXTERNAL_SEND=false). "
            "외부 전송이 필요하면 설정을 키고 다시 시도해 주세요."
        )
    return _live_slack() 




