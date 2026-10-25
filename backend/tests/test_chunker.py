from __future__ import annotations
from pathlib import Path
import pytest
from app.integrations.ports import ParsedBlock, ParsedDoc
from app.rag.chunker import chunk, summarize
from app.rag.local_parsers import parse_local

SAMPLES = Path(__file__).resolve().parents[2] / 'sandbox' / 'w5' / 'day01' / 'samples'
HWPX = SAMPLES / 'DOC-HR-014_국내출장_여비_규정_v2.0.hwpx'
DOCX = SAMPLES / 'DOC-HR-014_국내출장_여비_규정_v2.0.docx'

def _require(path: Path) -> None:
    if not path.is_file():
        pytest.skip(f'실습 재료가 없습니다 (sandbox 는 .gitignore 대상입니다): {path}')

# 표 나뉘어졌는지 확인 
def test_table_is_never_split() -> None:
    big_table = '| 직급 | 일비 | 숙박비 |\n|---|---|---|\n' + '\n'.join((f'| {i}급 | {i * 1000}원 | {i * 10000}원 |' for i in range(1, 121)))
    assert len(big_table) > 1200
    chunks = chunk(ParsedDoc(blocks=[ParsedBlock('표', '별표1 · p.4', big_table)]))
    assert len(chunks) == 1
    assert chunks[0].kind == '표'
    assert chunks[0].text == big_table

# 조 단위 하나로 잘 청킹 되었는지 확인 
def test_articles_are_kept_whole() -> None:
    doc = ParsedDoc(blocks=[ParsedBlock('조항', 'p.3', '제12조(숙박비) 숙박비는 다음 각 호에 따라 지급한다.'), ParsedBlock('조항', 'p.3', '① 광역시 지역의 숙박비는 1박당 70,000원을 상한으로 한다.'), ParsedBlock('조항', 'p.3', '② 그 밖의 지역은 1박당 60,000원을 상한으로 한다.')])
    chunks = chunk(doc)
    assert len(chunks) == 1
    assert '제12조' in chunks[0].locator
    assert '70,000원' in chunks[0].text and '60,000원' in chunks[0].text
    assert '조항 단위 1' in summarize(chunks)
    doc = ParsedDoc(blocks=[ParsedBlock('조항', 'p.5', '제4장 특례'), ParsedBlock('조항', 'p.5', '제26조(재해 대응 출장) ① 긴급 출장의 숙박비는'), ParsedBlock('조항', 'p.5', '제14조의 상한을 초과하여 지급할 수 있다.'), ParsedBlock('조항', 'p.6', '제5장 정산과 관리'), ParsedBlock('조항', 'p.6', '제27조(가지급) ① 출장자는 가지급을 신청할 수 있다.')])
    chunks = chunk(doc)
    assert [c.locator for c in chunks] == ['제4장 제26조(재해 대응 출장)', '제5장 제27조(가지급)']
    assert '제14조의 상한' in chunks[0].text
    assert '제5장' not in chunks[0].text

# 목차 줄 별도로 청크로 나뉘었는지 확인 
def test_toc_lines_do_not_become_chunks() -> None:
    toc = ParsedBlock('조항', 'p.1', '제1조(목적) 제2조(정의) 제12조(숙박비)')
    body = ParsedBlock('조항', 'p.3', '제12조(숙박비) 광역시 지역의 숙박비는 1박당 70,000원을 상한으로 한다.')
    chunks = chunk(ParsedDoc(blocks=[toc, body]))
    assert all((len(c.text) >= 10 for c in chunks))
    assert not any((c.text.strip() == '제2조(정의)' for c in chunks))

# 문서 타입에 따른 청크수 비교 
def test_same_document_different_format_gives_same_chunks() -> None:
    _require(HWPX)
    _require(DOCX)
    a = chunk(parse_local(str(HWPX)))
    b = chunk(parse_local(str(DOCX)))
    assert summarize(a) == summarize(b)
    assert summarize(a) == '조항 단위 46 + 표 단위 7 = 53 청크'
