"""사내 업무 에이전트 UI 킷.

사용법:
    from ui.theme import inject_css
    inject_css()

    from ui import table, badge_html, metrics, note
"""
from ui.badge import badge, badge_html, badges, tone_for
from ui.card import (
    bordered,
    inline_md,
    card,
    card_html,
    log_block,
    message_block,
    meta_footer,
    note,
    page_header,
)
from ui.chart import bars, line, timeline
from ui.metric import metrics
from ui.source import source_html, sources
from ui.status import progress, steps, steps_html
from ui.table import kv, kv_html, table, table_html
from ui.theme import inject_css

__all__ = [
    "inject_css",
    "badge", "badge_html", "badges", "tone_for",
    "table", "table_html", "kv", "kv_html",
    "card", "card_html", "bordered", "note", "message_block", "inline_md",
    "log_block", "meta_footer", "page_header",
    "sources", "source_html",
    "metrics",
    "steps", "steps_html", "progress",
    "bars", "line", "timeline",
]
