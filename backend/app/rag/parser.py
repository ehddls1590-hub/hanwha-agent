from __future__ import annotations

from pathlib import Path

from app.core.logging import get_logger 
from app.integrations.ports import ParsedBlock, ParsedDoc
from app.rag.local_parsers import parse_local

log = get_logger(__name__) 

_PLAIN = {".txt", ".md"}

_HTML = {".html", ".htm"}

_LOCAL_ONLY = {".hwp", ".hwpx"}

# 파일 한건 읽어서 형식과 무관한 한가지 모양으로 리턴해주는 함수
def parse(path: str | Path, *, use_upstage: bool = False) -> ParsedDoc:
    p = Path(path)
    ext = p.suffix.lower()

    if ext in _PLAIN:
        return _parse_plain(p)
    if ext in _HTML:
        return _parse_html(p)
    if use_upstage and ext not in _LOCAL_ONLY:
        from app.integrations.upstage import UpstageParser

        return UpstageParser().parse(str(p))
    return parse_local(p)


def _parse_plain(p: Path) -> ParsedDoc:
    
    if p.suffix.lower() == ".md": 
        return _parse_markdown(p) 
    text = _read_text(p) 
    blocks = [
        ParsedBlock("조항", f"{p.name} · {i + 1}단락", part.strip())
        for i, part in enumerate(text.split("\n\n"))
        if part.strip()
    ]
    return ParsedDoc(blocks=blocks, page_count=1, table_count=0)


def _read_text(p: Path) -> str:  
    
    raw = p.read_bytes()
    for enc in ("utf-8-sig", "cp949"):
        try:
            text = raw.decode(enc)
        except UnicodeDecodeError:
            continue
        if enc != "utf-8-sig":
            log.info("인코딩을 %s 로 읽었습니다: %s", enc, p.name)
        return text
    log.warning("인코딩을 알 수 없어 글자를 바꿔 읽었습니다: %s", p.name)
    return raw.decode("utf-8", errors="replace")  # ◀ 추가 끝


def _parse_markdown(p: Path) -> ParsedDoc: 
    import re

    text = _read_text(p)
    blocks: list[ParsedBlock] = []
    locator = p.name                       
    buffer: list[str] = []                 

    def flush() -> None:
        body = "\n".join(buffer).strip()
        if body:
            blocks.append(ParsedBlock("조항", locator, body))
        buffer.clear()

    for line in text.split("\n"):
        if re.match(r"#{1,6}\s", line):
            flush()                       
            locator = line.lstrip("#").strip()
        else:
            buffer.append(line)
    flush()                               
    return ParsedDoc(blocks=blocks, page_count=1, table_count=0) 


def _parse_html(p: Path) -> ParsedDoc:
    import re

    raw = _read_text(p)  
    raw = re.sub(r"<head.*?</head>", " ", raw, flags=re.S | re.I) 
    raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)

    tables = re.findall(r"<table.*?</table>", raw, flags=re.S | re.I)
    body = re.sub(r"<table.*?</table>", " ", raw, flags=re.S | re.I)
    body = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body)).strip()

    blocks = [ParsedBlock("조항", p.name, body)] if body else []
    for i, table in enumerate(tables, 1):
        cleaned = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", table)).strip()
        blocks.append(ParsedBlock("표", f"{p.name} · 표{i}", cleaned))
    return ParsedDoc(blocks=blocks, page_count=1, table_count=len(tables))
    