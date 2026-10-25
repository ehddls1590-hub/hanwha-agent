from __future__ import annotations

from pathlib import Path

from app.core.logging import get_logger
from app.integrations.ports import ParsedBlock, ParsedDoc

log = get_logger(__name__)


def pdf_tables_on() -> bool: 
    import os

    raw = os.environ.get("PDF_TABLES")
    if raw is None:
        from dotenv import dotenv_values   

        raw = dotenv_values(".env").get("PDF_TABLES")  
    return str(raw or "").strip().lower() in ("1", "true", "yes", "on")  


def parse_pdf(path: Path) -> ParsedDoc:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    blocks: list[ParsedBlock] = []


    for page_no, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").strip()
        if not text:
            log.info("텍스트 없음 (스캔본으로 보임): %s p.%d", path.name, page_no)
            continue
        blocks.append(ParsedBlock("조항", f"p.{page_no}", text))

    return ParsedDoc(blocks=blocks, page_count=len(reader.pages), table_count=0)


def parse_docx(path: Path) -> ParsedDoc:
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    doc = Document(str(path))
    blocks: list[ParsedBlock] = []
    tables = 0

    body = doc.element.body
    for child in body.iterchildren():
        tag = child.tag.split("}")[-1]
        if tag == "p":
            text = Paragraph(child, doc).text.strip()
            if text:
                blocks.append(ParsedBlock("조항", f"{path.stem}", text))
        elif tag == "tbl":
            table = Table(child, doc)
            rows = [[cell.text.strip() for cell in row.cells] for row in table.rows]
            if not rows:
                continue
            tables += 1
            blocks.append(
                ParsedBlock("표", f"표{tables}", _table_to_markdown(rows[0], rows[1:]))
            )

    return ParsedDoc(blocks=blocks, page_count=1, table_count=tables)



def _table_to_markdown(headers: list[str], rows: list[list[str]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    sep = "|" + "---|" * len(headers)
    body = ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join([head, sep, *body])

# 표 한칸을 마크다운 표에 넣어도 되는 한 줄 글자로 변경
def _cell(value) -> str:
    if value is None:
        return ""
    text = " ".join(str(value).split())
    return text.replace(":", "\\|")   


# 엑셀 시트의 값을 행 목록으로 읽기, 병합 겔은 왼쪽 위 값으로 체운다.
def _fill_merged(ws) -> list[list]:
    grid = [list(row) for row in ws.iter_rows(values_only=True)]
    if not grid:
        return grid
    r0, c0 = ws.min_row, ws.min_column
    for rng in ws.merged_cells.ranges:
        top_left = grid[rng.min_row - r0][rng.min_col - c0]
        for r in range(rng.min_row, rng.max_row + 1):
            for c in range(rng.min_col, rng.max_col + 1):
                grid[r - r0][c - c0] = top_left
    return grid

# 슬라이드의 표 도형하나를 마크다운으로 변경
def _pptx_table(shape) -> str:
    rows = [[_cell(cell.text) for cell in row.cells] for row in shape.table.rows]
    if not any(any(row) for row in rows):
        return ""
    return _table_to_markdown(rows[0], rows[1:])

# 계산값이 없는(None) 칸에 수식이 있으면 '수식 (계산갑 없음)' 글자로 넣어주기
def _fill_formulas(grid: list[list], ws, ws_formula) -> list[list]:
    r0, c0 = ws.min_row, ws.min_column
    for i, row in enumerate(grid):
        for j, value in enumerate(row):
            if value is not None:
                continue
            formula = ws_formula.cell(row=r0 + i, column=c0 + j).value
            if isinstance(formula, str) and formula.startswith("="):
                row[j] = f"{formula} (계산값 없음)"
    return grid

# 시트에 표 여러개 있을때, 시트 한장을 값이 하나도 없는 행에서 잘라서 표 덩어리 목록으로 만들기
def _split_regions(grid: list[list], first_row: int) -> list[tuple[int, list[list]]]:
    regions: list[tuple[int, list[list]]] = []
    for i, row in enumerate(grid):
        if all(c is None for c in row):
            continue
        if regions and regions[-1][0] + len(regions[-1][1]) == first_row + i:
            regions[-1][1].append(row)          # 바로 위 행에 이어지게       
        else:
            regions.append((first_row + i, [row])) # 빈 행 뒤 -> 새 덩어리
    if len(regions) > 1:
        for _, rows in regions:
            width = max(max((j + 1 for j, c in enumerate(r) if c is not None), default=0) for r in rows)
            rows[:] = [r[:width] for r in rows]
    return regions

# 표 덩어리 하나를 마크다운으로 변경
def _xlsx_table(ws, top: int, rows: list[list[str]]) -> str:
    def merged_across(row_no: int) -> bool:
        return any(r.min_row == row_no and r.max_col > r.min_col for r in ws.merged_cells.ranges)

    title = ""
    if len(rows) > 2 and len(set(rows[0])) == 1 and len(rows[0]) > 1 and merged_across(top):
        title, rows, top = rows[0][0], rows[1:], top + 1
    header, body = rows[0], rows[1:]
    if body and merged_across(top):
        second = body[0]
        header = [a if a == b or not b else (b if not a else f"{a} {b}") for a, b in zip(header, second)]
        body = body[1:]
    table = _table_to_markdown(header, body)
    return f"{title}\n\n{table}" if title else table

# 슬라이드의 도형을 하나씩 리턴하는 함수
def _walk_shapes(shapes):
    from pptx.shapes.group import GroupShape

    for shape in shapes:
        if isinstance(shape, GroupShape):
            yield from _walk_shapes(shape.shapes)
        else:
            yield shape

# 슬라이드의 차트 하나를 '항목 x 계열' 마크다운 표로 변경
def _pptx_chart(shape) -> str:
    chart = shape.chart
    try:
        categories = [_cell(c) for c in chart.plots[0].categories]
    except (IndexError, AttributeError, TypeError):
        return ""
    series = list(chart.series)
    if not categories or not series:
        return ""

    def num(v) -> str:
        return _cell(int(v) if isinstance(v, float) and v.is_integer() else v)

    header = ["항목", *(_cell(s.name) for s in series)]
    body = [[cat, *(num(s.values[i]) if i < len(s.values) else "" for s in series)]
            for i, cat in enumerate(categories)]
    table = _table_to_markdown(header, body)
    title = chart.chart_title.text_frame.text.strip() if chart.has_title else ""
    return f"{title}\n\n{table}" if title else table

# PDF를 pdfplumber로 파싱 -> 
def parse_pdf_tables(path: Path) -> ParsedDoc:
    import pdfplumber

    blocks: list[ParsedBlock] = []
    n_tables = 0
    with pdfplumber.open(str(path)) as pdf:
        page_count = len(pdf.pages)
        for page_no, page in enumerate(pdf.pages, 1):
            found = page.find_tables()
            boxes = [t.bbox for t in found]       # (x0, top, x1, bottom) 

            def outside(obj, boxes=boxes) -> bool:
                x0, top = obj.get("x0", 0), obj.get("top", 0)
                x1, bottom = obj.get("x1", 0), obj.get("bottom", 0)
                return not any(b[0] <= x0 and x1 <= b[2] and b[1] <= top and bottom <= b[3]
                               for b in boxes)

            text = ((page.filter(outside) if boxes else page).extract_text() or "").strip()
            if text:
                blocks.append(ParsedBlock("조항", f"p.{page_no}", text))
            for k, table in enumerate(found, 1):
                rows = [[_cell(c) for c in row] for row in table.extract()]
                if not any(any(row) for row in rows):
                    continue                     
                blocks.append(ParsedBlock("표", f"p.{page_no} · 표{k}",
                                          _table_to_markdown(rows[0], rows[1:])))
                n_tables += 1
            if not text and not found:
                log.info("텍스트 없음 (스캔본으로 보임): %s p.%d", path.name, page_no)

    return ParsedDoc(blocks=blocks, page_count=page_count, table_count=n_tables) 

# 한글 파일 파싱
def parse_hwpx(path: Path) -> ParsedDoc:
    import re
    import zipfile
    from xml.etree import ElementTree as ET

    ns_p = "{http://www.hancom.co.kr/hwpml/2011/paragraph}"
    blocks: list[ParsedBlock] = []
    tables = 0

    with zipfile.ZipFile(path) as zf:
        sections = sorted(n for n in zf.namelist()
                          if re.match(r"Contents/section\d+\.xml$", n))
        for name in sections:
            root = ET.fromstring(zf.read(name))

            for para in root.findall(f"{ns_p}p"):
                table_el = para.find(f".//{ns_p}tbl")
                if table_el is not None:
                    tables += 1
                    rows: list[list[str]] = []
                    for tr in table_el.findall(f"{ns_p}tr"):
                        cells = []
                        for tc in tr.findall(f"{ns_p}tc"):
                            cells.append("".join(
                                t.text or "" for t in tc.iter(f"{ns_p}t")
                            ).strip())
                        rows.append(cells)
                    if rows:
                        blocks.append(ParsedBlock(
                            "표", f"표{tables}", _table_to_markdown(rows[0], rows[1:])
                        ))
                    continue
                text = "".join(t.text or "" for t in para.iter(f"{ns_p}t")).strip()
                if text:
                    blocks.append(ParsedBlock("조항", path.stem, text))

    return ParsedDoc(blocks=blocks, page_count=1, table_count=tables)

# 엑셀 파싱
def parse_xlsx(path: Path) -> ParsedDoc:
    from openpyxl import load_workbook

    wb = load_workbook(str(path), data_only=True)
    wb_formula = load_workbook(str(path))  
    blocks: list[ParsedBlock] = []

    for ws in wb.worksheets:
        grid = _fill_formulas(_fill_merged(ws), ws, wb_formula[ws.title]) # 수식 처리
        regions = _split_regions(grid, ws.min_row) # 여러 표
        for k, (top, region) in enumerate(regions, 1):
            rows = [["" if c is None else str(c) for c in row] for row in region]
            locator = ws.title if len(regions) == 1 else f"{ws.title} · 표{k}"
            blocks.append(ParsedBlock("표", locator, _xlsx_table(ws, top, rows)))

    return ParsedDoc(
        blocks=blocks, page_count=len(wb.worksheets), table_count=len(blocks)
    )

# PPTX 파싱
def parse_pptx(path: Path) -> ParsedDoc:
    from pptx import Presentation

    prs = Presentation(str(path))
    blocks: list[ParsedBlock] = []
    n_tables = 0  

    for page_no, slide in enumerate(prs.slides, 1):
        lines = [shape.text.strip() for shape in _walk_shapes(slide.shapes) 
                 if shape.has_text_frame and shape.text.strip()]
        if slide.has_notes_slide:
            note = slide.notes_slide.notes_text_frame.text.strip()
            if note:
                lines.append(f"[발표자 노트] {note}")
        if lines:
            blocks.append(ParsedBlock("조항", f"슬라이드 {page_no}", "\n".join(lines)))
        shapes = list(_walk_shapes(slide.shapes))
        tables = [md for md in (_pptx_table(s) for s in shapes if s.has_table) if md]
        charts = [md for md in (_pptx_chart(s) for s in shapes if s.has_chart) if md]
        for k, md in enumerate(tables, 1):
            blocks.append(ParsedBlock("표", f"슬라이드 {page_no} · 표{k}", md))
        for k, md in enumerate(charts, 1):
            blocks.append(ParsedBlock("표", f"슬라이드 {page_no} · 차트{k}", md))
        n_tables += len(tables) + len(charts)  

    return ParsedDoc(blocks=blocks, page_count=len(prs.slides), table_count=n_tables)


_CONVERT_HINT = {
    ".hwp": "한글에서 열고 [다른 이름으로 저장] → HWPX 또는 PDF 로 내보내세요. "
            "구 .hwp 는 한컴 독자 바이너리라 열지 않고는 읽을 방법이 없습니다",
    ".doc": "Word 에서 열고 .docx 로 저장하세요",
    ".ppt": "PowerPoint 에서 열고 .pptx 로 저장하세요",
    ".xls": "Excel 에서 열고 .xlsx 로 저장하세요",
    ".hwt": "한글 서식 파일입니다. 내용이 든 .hwpx 문서를 넣으세요",
    ".zip": "압축을 풀고 안의 문서를 한 건씩 넣으세요",
}

HANDLERS = {
    ".docx": parse_docx,
    ".pdf": parse_pdf,
    ".hwpx": parse_hwpx,
    ".xlsx": parse_xlsx,
    ".pptx": parse_pptx,
}

# 확장자를 보고 알맞은 파서로 넘겨주는 진입점
def parse_local(path: str | Path) -> ParsedDoc | None:
    from app.core.exceptions import ValidationFailed

    p = Path(path)

    ext = p.suffix.lower()

    handler = HANDLERS.get(ext)
    if handler is parse_pdf and pdf_tables_on():  
        handler = parse_pdf_tables  
    if handler is None:
        if ext in _CONVERT_HINT:
            raise ValidationFailed(
                f"읽을 수 없는 형식입니다: {ext}",
                detail=_CONVERT_HINT[ext],
            )
        raise ValidationFailed(
            f"지원하지 않는 형식입니다: {ext}",
            detail="핸들러를 추가하면 지원할 수 있습니다",
        )

    try:
        doc = handler(p)
    except Exception as exc:
        log.warning("로컬 파싱 실패 (%s): %s", p.name, exc)
        return None

    if not doc.blocks:
        raise ValidationFailed(
            f"문서에서 글자를 찾지 못했습니다: {p.name}",
            detail="스캔본(이미지)일 수 있습니다. .env 의 UPSTAGE_PARSE_OCR 를 force 로 "
                   "두고 실동작 모드로 다시 적재해 보세요",
        )

    return doc








