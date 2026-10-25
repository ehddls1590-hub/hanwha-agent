"""표 — st.dataframe 은 스타일 제어가 안 되므로 HTML 로 직접 그린다."""
from __future__ import annotations

import html
from typing import Iterable, Sequence

import streamlit as st

Cell = str | int | float | None


def _cell(value: Cell, *, raw: bool) -> str:
    if value is None:
        return ""
    return str(value) if raw else html.escape(str(value))


def table_html(
    headers: Sequence[str],
    rows: Iterable[Sequence[Cell]],
    *,
    row_classes: Sequence[str] | None = None,
    align: Sequence[str] | None = None,
    raw_html: bool = True,
) -> str:
    """
    headers    : 헤더 문자열
    rows       : 행. 셀 값에 badge_html() 결과를 그대로 넣을 수 있다 (raw_html=True)
    row_classes: 행마다 "ag-row-sel" / "ag-row-muted" / "ag-row-total" / ""
    align      : 열마다 "" 또는 "ag-num"(우측 정렬)
    """
    rows = list(rows)
    align = list(align) if align else [""] * len(headers)
    row_classes = list(row_classes) if row_classes else [""] * len(rows)

    out = ['<div class="ag-tbl-wrap"><table class="ag-tbl"><thead><tr>']
    for i, h in enumerate(headers):
        cls = f' class="{align[i]}"' if i < len(align) and align[i] else ""
        out.append(f"<th{cls}>{html.escape(str(h))}</th>")
    out.append("</tr></thead><tbody>")

    for r_i, row in enumerate(rows):
        rc = row_classes[r_i] if r_i < len(row_classes) else ""
        out.append(f'<tr class="{rc}">' if rc else "<tr>")
        for c_i, cell in enumerate(row):
            cls = f' class="{align[c_i]}"' if c_i < len(align) and align[c_i] else ""
            out.append(f"<td{cls}>{_cell(cell, raw=raw_html)}</td>")
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def table(headers, rows, **kwargs) -> None:
    st.markdown(table_html(headers, rows, **kwargs), unsafe_allow_html=True)


def kv_html(pairs: Iterable[tuple[str, Cell]], *, raw_html: bool = True) -> str:
    """키-값 2열 표. 문서 초안 카드·상세 패널에 쓴다."""
    out = ['<table class="ag-kv"><tbody>']
    for k, v in pairs:
        val = "" if v is None else (str(v) if raw_html else html.escape(str(v)))
        out.append(
            f'<tr><td class="ag-kv-k">{html.escape(str(k))}</td>'
            f'<td class="ag-kv-v">{val}</td></tr>'
        )
    out.append("</tbody></table>")
    return "".join(out)


def kv(pairs, **kwargs) -> None:
    st.markdown(kv_html(pairs, **kwargs), unsafe_allow_html=True)
