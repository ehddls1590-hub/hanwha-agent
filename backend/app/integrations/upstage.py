from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger
from app.integrations.ports import ParsedBlock, ParsedDoc

log = get_logger(__name__)

TIMEOUT = 180.0  

_HINTS = {
    401: "API 키가 잘못되었거나, 차단된 키 입니다."
    "console.upstage.ai/api-keys 에서 확인하세요.",
    403: "크래딧이 부족합니다. upstage 콘솔에서 Billing 부분을 확인하세요.",
    413: "파일이 너무 큽니다. 동기 요청에는 페이지 수/용량 상한이 있습니다.",
    415: "지원하지 않는 파일 형식입니다.",
    422: "파일이 손상되었거나 열 수 없습니다.",
    429: "요청이 너무 잦습니다. 잠시 후 다시 시도하세요."
}

# 글자로 받을 카테고리. 
_TEXT = {"paragraph", "heading1", "heading2", "heading3",
         "list", "index", "caption", "equation", "code", "footnote"}

_SKIP = {"header", "footer", "figure"}

# 인증 헤더 만들기 
def _headers() -> dict:
    key = get_settings().upstage_api_key
    if key is None:
        raise ExternalServiceError("UPSTAGE_API_KEY 가 비어있습니다.")
    return {"Authorization": f"Bearer {key.get_secret_value()}"}

# 상태 코드 붙일 안내 문장 리턴 
def _explain(status: int | None) -> str:
    return _HINTS.get(status, "")

# 상용 문서 파서 어댑터.
class UpstageParser:
    
    name = "upstage"

    # 파일 하나 상용 파서에 보내 ParsedDoc 으로 리턴 
    def parse(self, path: str) -> ParsedDoc:
        p = Path(path)
        if not p.exists():
            raise ExternalServiceError(f"파일을 찾을 수 없습니다: {path}")
        return _to_doc(p, _post(p))


# 파일을 멀티파트로 보내고 응답을 JSON으로 리턴 
def _post(p: Path) -> dict:
    import httpx  # http 요청 

    settings = get_settings()
    url = f"{settings.upstage_base_url.rstrip('/')}/document-digitization"
    try:
        with httpx.Client(timeout=TIMEOUT) as client, p.open("rb") as fh:
            response = client.post(
                url,
                headers=_headers(), 
                files={"document": (p.name, fh)}, 
                data={
                    "model": settings.upstage_parse_model, 
                    "ocr": settings.upstage_parse_ocr, 
                    "output_formats": "['markdown']", 
                    "coordinates": "false",
                }
            )
            response.raise_for_status() 

    except httpx.HTTPError as e:
        status = getattr(getattr(e, "response", None), "status_code", None)
        raise ExternalServiceError(f"Upstage 문서 파싱 실패: {e}", detail=_explain(status)) from e

    return response.json() 

 
# 응답의 elements를 ParsedBlock 리스트로 변경 -> ParsedDoc으로 리턴 
def _to_doc(p: Path, payload: dict) -> ParsedDoc:
    blocks: list[ParsedBlock] = []
    tables = 0
    pages = 0 

    for el in payload.get("elements", []):
        category = el.get("category", "")
        page = int(el.get("page", 0) or 0)
        pages = max(pages, page)
        text = (el.get("content") or {}).get("markdown", "").strip()
        if not text or category in _SKIP:
            continue
        if category in ("table", "chart"):
            tables += 1
            blocks.append(ParsedBlock("표", f"표{tables} · p.{page}", text))
        elif category in _TEXT:
            blocks.append(ParsedBlock("조항", f"p.{page}", text))

    log.info("상용 파싱 완료: %s, 블록 %d, 표 %d", p.name, len(blocks), tables)
    return ParsedDoc(blocks=blocks, page_count=pages, table_count=tables)

# ----------------- 임베딩 ---------------------

EMBED_TIMEOUT = 60.0
EMBED_BATCH = 50

# 상용 임베딩 어댑터
class UpstageEmbedder:
    name = "upstage"

    def __init__(self) -> None:
        settings = get_settings()
        self.model = settings.upstage_embed_model
        self.dim: int = settings.embed_dim

    # 문장 목록을 사용 API에 보내 벡터 목록으로 받기
    def _embed(self, texts: list[str], kind: str) -> list[list[float]]:
        import httpx
        if not self.model:
            raise ExternalServiceError(
                "UPSTAGE_EMBED_MODEL이 비어 있습니다.",
                detail=".env에 사용할 모델 이름을 작성해야 상용 임베딩을 부를 수 있습니다."
            )
        settings = get_settings()
        url = f"{settings.upstage_base_url.rstrip('/')}/embeddings"
        try:
            with httpx.Client(timeout=EMBED_TIMEOUT) as client:
                resp = client.post(url, headers=_headers(), json={"model": self.model, "input": texts})
                resp.raise_for_status()

        except httpx.HTTPError as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            raise ExternalServiceError(f"Upstage 임베딩 실패({kind}): {e}", detail=_explain(status)) from e
        rows = sorted(resp.json().get("data", []), key=lambda r: r.get("index", 0))
        log.info("상용 임베딩 완료: %s - %s - %d건", self.model, kind, len(rows))
        return [[float(x) for x in row["embedding"]] for row in rows ]

    def embed_document(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), EMBED_BATCH):
            out.extend(self._embed(texts[i:i + EMBED_BATCH], "passage"))
            return out

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "query")[0]

    
