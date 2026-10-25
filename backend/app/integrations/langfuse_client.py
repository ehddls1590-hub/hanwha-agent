from __future__ import annotations

from contextlib import contextmanager
from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)

_client = None
_tried = False

# langfuse 클라이언트 하나 만들어 주는 함수. 못 만들면 None 리턴.
def get_client():
    global _client, _tried
    if _tried:
        return _client
    _tried = True

    # 테스트가 설정을 갈아끼울 수 있게 함수안에서 설정정보 읽어오기
    settings = get_settings()
    # 랭퓨즈가 사용여부가 False면 -> None 리턴
    if not settings.langfuse_enabled:
        return None

    if not settings.langfuse_public_key or settings.langfuse_secret_key is None:
        log.warning("LANGFUSE_ENABLED=true인데 키가 비어있습니다. 관측을 건너뜁니다.")
        return None
    
    try:
        from langfuse import Langfuse
        _client = Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key.get_secret_value(),
        host=settings.langfuse_host,

        )
    except Exception as e:
        log.warning("Langfuse 클라이언트를 만들지 못하였습니다(무시하고 계속) : %s" ,e)
        _client = None

    return _client

# 첫 실패만 크게 알리고, 그 다음부터는 조용히 남기기 위한 표시(변수)
_warned = False

# 관측 실패를 남기는 함수: 처음 한번만 경고, 그 다음부터는 디버그.
def _quiet(message: str, e:Exception) -> None:
    global _warned
    if not _warned:
        _warned = True
        log.warning("%s(무시하고 계속): %s", message, e)
    else:
        log.debug("%s: %s", message, e)

# 실행 하나를 트레이스 하나로 감싸는 함수
@contextmanager 
def trace(name: str,*,run_id: str, user_id: str, metadata: dict | None = None):
    # name: 트레이스 이름
    # run_id: 이 실행의 고유 번호
    # user_id: 누가 물었나, 문자열
    # metadata : 화면에서 함께 보고 싶은 값들 
    client = get_client()
    handle = None
    if client is not None:
        try:
            handle = client.trace(
                id=run_id,
                name=name,
                user_id=user_id,
                metadata=metadata or {}
            )
        except Exception as e:
            _quiet("Langfuse 트레이스를 시작하지 못하였습니다.", e)

    try:
        yield handle
    finally:
        pass # 일부러 비워두기

# 트레이스 하나에 점수를 붙이는 함수
def score(run_id: str, name: str, value: float) -> None:
    # run_id : 점수를 붙일 트레이스 고유id
    # name: 점수 이름
    # vlaue: 점수 값. 0.0 = 폴백, 1.0 = 정상
    client = get_client()
    if client is None:
        return
    try:
        client.score(
            trace_id=run_id,
            name=name,
            value=value
        )
    except Exception as e:
         _quiet("Langfuse 점수를 남기지 못했습니다.", e)
        