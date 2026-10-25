from __future__ import annotations
import re
from dataclasses import dataclass
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.integrations.ports import ParsedDoc

# 제1조, 제12조(숙박비), 
_ARTICLE = re.compile('^[ \\t]*(제\\s*\\d+\\s*조(?:의\\s*\\d+)?\\s*\\([^)\\n]{1,30}\\))', re.M)
# 별표1 .. 
_ANNEX = re.compile('(별표\\s*\\d+)')
# 장,절,부칙 제목 줄 
_HEADING = re.compile('^[ \\t]*(?:(제\\s*\\d+\\s*장)|(제\\s*\\d+\\s*절)|(부\\s*칙))(?:[ \\t]+[^\\n]{1,30})?[ \\t]*$')
# 별표,서식 제목 줄 
_ANNEX_HEAD = re.compile('^[ \\t]*\\[(별표\\s*\\d+|별지[^\\]]{0,20})\\]')

MAX_CHARS = 1200
MIN_CHARS = 30
TOC_BODY_MIN = 10

@dataclass
class ChunkDraft:
    kind: str
    locator: str
    text: str

# 조 단위로 자르기 
def _split_articles(text: str) -> list[tuple[str, str]]:
    parts = _ARTICLE.split(text)
    if len(parts) <= 1:
        return [('', text.strip())] if text.strip() else []
    out: list[tuple[str, str]] = []
    head = parts[0].strip()
    if len(head) >= MIN_CHARS:
        out.append(('', head))
    for i in range(1, len(parts), 2):
        title = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ''
        out.append((title, f'{title} {body}'.strip()))
    return out

# 장,절 제목 줄에서 끊고, 그 줄은 본문에서 제외 
def _split_headings(text: str, where: dict) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    lines: list[str] = []
    for line in text.split('\n'):
        m = _HEADING.match(line)
        annex = _ANNEX_HEAD.match(line)
        if not m and (not annex):
            lines.append(line)
            continue
        if lines:
            out.append((where['at'], '\n'.join(lines)))
            lines = []
        if annex:
            where['chapter'], where['section'] = ('', '')
            where['at'] = re.sub('\\s+', ' ', annex.group(1)).strip()
            lines.append(line)
            continue
        chapter, section, _ = m.groups()
        if chapter:
            where['chapter'], where['section'] = (re.sub('\\s+', '', chapter), '')
        elif section:
            where['section'] = re.sub('\\s+', '', section)
        else:
            where['chapter'], where['section'] = ('부칙', '')
        where['at'] = ' '.join((x for x in (where['chapter'], where['section']) if x))
    if lines:
        out.append((where['at'], '\n'.join(lines)))
    return out

# 길이가 아주 긴 조를 limit 이하로 나누기 (폴백)
def _hard_wrap(text: str, limit: int=MAX_CHARS) -> list[str]:
    if len(text) <= limit:
        return [text]
    splitter = RecursiveCharacterTextSplitter(chunk_size=limit, chunk_overlap=0, separators=['\n\n', '\n', '다. ', '. ', ' ', ''], keep_separator='end')
    return splitter.split_text(text)

# ParsedDoc -> 청크 목록으로 변환해서 리턴 
def chunk(doc: ParsedDoc) -> list[ChunkDraft]:
    out: list[ChunkDraft] = []
    buffer: list[str] = []
    buffer_locator = ''
    where = {'chapter': '', 'section': '', 'at': ''}

    def flush() -> None:
        nonlocal buffer, buffer_locator
        if not buffer:
            return
        out.extend(_articles_from('\n'.join(buffer), buffer_locator, where))
        buffer = []
        buffer_locator = ''
    for block in doc.blocks:
        if block.kind == '표':
            flush()
            out.append(ChunkDraft('표', block.locator, block.text))
            continue
        if not buffer_locator:
            buffer_locator = block.locator
        buffer.append(block.text)
    flush()
    return out
    
# 본문 덩어리를 조 단위로 자르는 함수 
def _articles_from(text: str, fallback_locator: str, where: dict) -> list[ChunkDraft]:
    drafts: list[ChunkDraft] = []
    items = [(at, title, body) for at, part in _split_headings(text, where) for title, body in _split_articles(part)]
    for at, title, body in items:
        if not body.strip():
            continue
        remainder = body[len(title):].strip() if title else body
        if not title and '\n' not in body.strip() and _ANNEX_HEAD.match(body):
            remainder = ''
        if len(remainder) < TOC_BODY_MIN:
            if drafts:
                drafts[-1].text += '\n' + body
            else:
                drafts.append(ChunkDraft('조항', at or fallback_locator, body))
            continue
        if not title:
            locator = at or fallback_locator
        else:
            annex = _ANNEX.search(body)
            locator = f'{at} {title}'.strip()
            locator = locator if not annex else f'{locator} · {annex.group(1)}'
        pieces = _hard_wrap(body)
        for i, piece in enumerate(pieces):
            suffix = f' ({i + 1}/{len(pieces)})' if len(pieces) > 1 else ''
            drafts.append(ChunkDraft('조항', f'{locator}{suffix}', piece))
    return drafts

# 요약 문구 생성 
def summarize(chunks: list[ChunkDraft]) -> str:
    articles = sum((1 for c in chunks if c.kind == '조항'))
    tables = sum((1 for c in chunks if c.kind == '표'))
    return f'조항 단위 {articles} + 표 단위 {tables} = {len(chunks)} 청크'
