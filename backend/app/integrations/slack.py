from __future__ import annotations

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger
from app.integrations.ports import SlackResult

log = get_logger(__name__)

# SlackPort 규약에 맞는 슬랙 어댑터 
class SlackClient:
    name = "slack"

    def __init__(self) -> None:
        try:
            from slack_sdk import WebClient
        except ImportError as e: 
            raise ExternalServiceError("slack_sdk가 설치되어 있지 않습니다.") from e 

        settings = get_settings() 
        token = settings.slack_bot_token 
        if not token or not token.get_secret_value(): 
            raise ExternalServiceError(
                "SLACK_BOT_TOKEN이 비어있습니다. 슬랙 워크스페이스의 Bot token을 .env에 넣어주세요.")
        self._client = WebClient(token=token.get_secret_value())
        self._default = settings.slack_default_channel 

    # 메세지 한줄 전송 
    def post(self, *, channel: str, text: str) -> SlackResult:
        from slack_sdk.errors import SlackClientError

        target = channel or self._default

        try:
            resp = self._client.chat_postMessage(channel=target, text=text)
        except (SlackClientError, OSError) as e:
            log.warning("Slack 전송 실패 (%s) : %s", target, type(e).__name__)
            return SlackResult(ok=False, channel=target, error=str(e))

        log.info("Slack 전송 완료: %s", target)

        return SlackResult(ok=True, channel=resp.get("channel", target), ts=resp.get("ts", ""))

