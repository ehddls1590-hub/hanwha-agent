"""차트 — 색·라벨을 정확히 제어하기 위해 HTML/SVG 로 직접 그린다.

st.bar_chart / st.line_chart 는 색과 라벨을 우리가 못 잡는다.
막대 길이는 축 눈금과 반드시 일치해야 한다.
"""
from __future__ import annotations

import html

import streamlit as st


def bars(
    items: list[tuple[str, float]],
    *,
    max_value: float = 100,
    unit: str = "%",
    strong_last: bool = True,
    ticks: list[float] | None = None,
) -> None:
    """가로 막대. 단일 색상, 마지막 막대만 진하게.

    items      : [(라벨, 값)]
    max_value  : 축 최대값. 막대 폭 = 값 / max_value
    ticks      : 눈금 값. 기본 0 · 25 · 50 · 75 · 100 (max_value 기준 4등분)
    """
    ticks = ticks or [max_value * i / 4 for i in range(5)]
    out = ['<div class="ag-bars">']

    last = len(items) - 1
    for i, (label, value) in enumerate(items):
        pct = 0 if max_value == 0 else max(0.0, min(100.0, value / max_value * 100))
        fill_cls = "ag-bar-fill ag-bar-fill--strong" if (strong_last and i == last) else "ag-bar-fill"
        weight = "600" if (strong_last and i == last) else "400"
        num = f"{value:g}{unit}"
        out.append(
            f'<div class="ag-bar-row">'
            f'<div class="ag-bar-label" style="font-weight:{weight}">{html.escape(label)}</div>'
            f'<div class="ag-bar-track"><div class="{fill_cls}" style="width:{pct:.4f}%"></div></div>'
            f'<div class="ag-bar-value" style="font-weight:{weight}">{html.escape(num)}</div>'
            f"</div>"
        )

    # 축 — 막대와 같은 flex 레이아웃 위에 올린다
    tick_html = []
    for i, t in enumerate(ticks):
        pos = 0 if max_value == 0 else t / max_value * 100
        cls = "ag-bar-tick"
        if i == 0:
            cls += " ag-bar-tick--first"
        elif i == len(ticks) - 1:
            cls += " ag-bar-tick--last"
        tick_html.append(f'<div class="{cls}" style="left:{pos:.4f}%">{t:g}{unit}</div>')
    out.append(
        '<div class="ag-bar-row" style="margin-top:2px">'
        '<div class="ag-bar-label"></div>'
        f'<div class="ag-bar-axis-track">{"".join(tick_html)}</div>'
        '<div class="ag-bar-value"></div>'
        "</div>"
    )
    out.append("</div>")
    st.markdown("".join(out), unsafe_allow_html=True)


def line(
    values: list[float],
    labels: list[str],
    *,
    y_ticks: list[float],
    last_label: str | None = None,
    height: int = 190,
) -> None:
    """단일 계열 라인 + 옅은 면. 마지막 점에 마커와 라벨."""
    if not values:
        return
    W, H = 720, height
    pad_l, pad_r, pad_t, pad_b = 52, 60, 14, 26
    y_max = max(y_ticks) or 1
    inner_w = W - pad_l - pad_r
    inner_h = H - pad_t - pad_b

    def x_at(i: int) -> float:
        return pad_l + (inner_w * i / max(1, len(values) - 1))

    def y_at(v: float) -> float:
        return pad_t + inner_h - (inner_h * min(v, y_max) / y_max)

    pts = [(x_at(i), y_at(v)) for i, v in enumerate(values)]
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{pad_l},{pad_t + inner_h} {poly} {pts[-1][0]:.1f},{pad_t + inner_h}"

    grid, ylab = [], []
    for t in y_ticks:
        y = y_at(t)
        grid.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{pad_l + inner_w}" y2="{y:.1f}" '
            f'stroke="#DCE4E1" stroke-width="1"/>'
        )
        ylab.append(
            f'<text x="{pad_l - 8}" y="{y + 4:.1f}" text-anchor="end" '
            f'font-size="11" fill="#66766F">{t:g}</text>'
        )

    xlab = []
    step = max(1, len(labels) // 7)
    for i, lb in enumerate(labels):
        if i % step == 0 or i == len(labels) - 1:
            xlab.append(
                f'<text x="{x_at(i):.1f}" y="{H - 6}" text-anchor="middle" '
                f'font-size="11" fill="#66766F">{html.escape(lb)}</text>'
            )

    lx, ly = pts[-1]
    marker = (
        f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="4" fill="#0E6E62"/>'
        f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="7" fill="#0E6E62" opacity="0.18"/>'
    )
    if last_label:
        marker += (
            f'<text x="{lx + 10:.1f}" y="{ly + 4:.1f}" font-size="12" '
            f'font-weight="700" fill="#0A544A">{html.escape(last_label)}</text>'
        )

    svg = f"""<svg viewBox="0 0 {W} {H}" style="width:100%;height:auto" role="img">
  {''.join(grid)}
  <polygon points="{area}" fill="#0E6E62" opacity="0.10"/>
  <polyline points="{poly}" fill="none" stroke="#0E6E62" stroke-width="2"
            stroke-linejoin="round" stroke-linecap="round"/>
  {marker}{''.join(ylab)}{''.join(xlab)}
</svg>"""
    st.markdown(svg, unsafe_allow_html=True)


def timeline(items: list[str]) -> None:
    """버전 타임라인. items 는 이미 만들어진 HTML 조각. 첫 항목이 '현행'."""
    out = ['<div class="ag-tl">']
    for i, body in enumerate(items):
        cls = "ag-tl-item ag-tl-item--now" if i == 0 else "ag-tl-item"
        out.append(f'<div class="{cls}">{body}</div>')
    out.append("</div>")
    st.markdown("".join(out), unsafe_allow_html=True)
