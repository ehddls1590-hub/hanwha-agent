from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr
from functools import lru_cache

from app.models.base import EMBED_DIM

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False  # APP_MODE 든 app_mode든 같은것으로 보게 설정 
    )

    app_mode: str = Field(default="mock", pattern=r"^(mock|live)$")
    # --- LLM ------------------------------------------------------
    anthropic_api_key : SecretStr | None = None
    upstage_api_key: SecretStr | None = None
    llm_model: str = "claude-haiku-4-5"
    max_tokens: int = Field(default=400, ge=1, le=8192)
    top_k: int = Field(default=3, ge=1, le=20)
    temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    # --- 안전장치 -------------------------------------------------------
    daily_call_limit: int = Field(default=200, ge=1)
    max_input_chars: int = Field(default=200, ge=1)
    # --- DB ------------------------------------------------------------
    database_url: str = "sqlite:///./app.db"
    # --- 기본 설정 -----------------------------------------------------
    # Windows 등의 공용 DEBUG 환경 변수와 충돌하지 않도록 앱 전용 이름을 쓴다.
    debug: bool = Field(default=False, validation_alias="APP_DEBUG")
    allow_external_send: bool = False

    # --- 관측 Langfuse ------------------------------------------------
    langfuse_enabled: bool = False 
    langfuse_host: str = "http://localhost:3000"
    langfuse_public_key: str | None = None
    langfuse_secret_key: SecretStr | None = None
    # --- Upstage ------------------------------------------------------
    upstage_api_key: SecretStr | None = None
    upstage_base_url: str = "https://api.upstage.ai/v1"
    upstage_parse_model: str = "document-parse"
    upstage_parse_ocr: str = "auto"
    #  --- embedding ---------------------------------------------------
    embed_provider: str = Field(default="local", pattern=r"^(local|upstage)")
    embed_model_dir: str = "../models/bge-m3"
    embed_dim: int = EMBED_DIM
    upstage_embed_model: str | None = None

    # --- 검색 ---------------------------------------------------------
    retrieval_threshold: float = Field(default=0.55, ge=0.0, le=1.0) # 임계값. 점수를 넘지 못하면 근거 부족 
    retrieval_top_k: int = Field(default=12, ge=1, le=100)  # 벡터 검색이 받아올 후보 갯수 
    # 아래 두 줄 추가 
    multi_query_n: int = Field(default=3, ge=1, le=10) # 질문을 몇 갈래까지 늘리는가   
    rerank_top_n: int = Field(default=3, ge=1, le=20) # 다시 줄 세운 뒤 몇 건을 남길 것인가 

    # --- 리랭커 -------------------------------------------------------
    # simple : 간이리랭커, cross_encoder : 모델이 질문과 조각을 한번에 읽어 점수 매김
    reranker: str = Field(default="simple", pattern=r"^(simple|cross_encoder)$")
    rerank_model_dir: str = "../models/bge-reranker-v2-m3"
    rerank_candidates: int = Field(default=12, ge=1, le=100)
    # 질문 + 조각을 합쳐 이 토큰 수에서 자른다. (문서에 따라 수정 요함)
    rerank_max_length: int = Field(default=512, ge=64, le=8192)
    # 크로스 인코더 점수가 (0~1)가 이 값에 못미치면 근거부족.
    rerank_threshold: float = Field(default=0.2, ge=0.0, le=1.0)

    # 모델 미리 로딩
    warn_up_models: bool = True
    

    # live 모드인지 확인 -> settings.is_live => True/Fase 
    @property
    def is_live(self) -> bool:
        return self.app_mode == "live"


@lru_cache
def get_settings() -> Settings:
    return Settings()

def mask(secret: str | None, keep: int = 8) -> str:
    if not secret:
        return "(없음)"
    return f"{secret[:keep]}...({len(secret)}자)"
