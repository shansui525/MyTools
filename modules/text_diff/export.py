# -*- coding: utf-8
"""文本对比结果 HTML 导出。"""

import html
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from modules.text_diff.service import compare_text

EXPORT_CSS = """
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 1.5rem; background: #f4f6f9; color: #1a1a2e; }
h1 { font-size: 1.35rem; margin: 0 0 0.5rem; }
.meta { color: #6b7280; font-size: 0.9rem; margin-bottom: 1rem; }
.legend { margin-bottom: 1rem; font-size: 0.85rem; }
.legend span { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 4px; margin-right: 0.5rem; }
.legend-delete { background: #fecaca; color: #991b1b; }
.legend-insert { background: #bbf7d0; color: #166534; }
.legend-replace { background: #fde68a; color: #92400e; }
.panels { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.panel { border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; background: #fff; }
.panel-hd { padding: 0.5rem 0.75rem; background: #f3f4f6; font-weight: 600; border-bottom: 1px solid #e5e7eb; }
.panel-bd { font-family: "SF Mono", Menlo, Consolas, monospace; font-size: 0.85rem; line-height: 1.65; }
.line { display: flex; white-space: pre-wrap; word-break: break-all; min-height: 1.65em; }
.lineno { flex-shrink: 0; width: 3rem; padding: 0 0.5rem; text-align: right; color: #6b7280; background: #f3f4f6; border-right: 1px solid #e5e7eb; }
.content { flex: 1; padding: 0 0.5rem; }
.line-equal .content { background: #fff; }
.line-delete .content { background: #fecaca; }
.line-insert .content { background: #bbf7d0; }
.line-replace .content { background: #fef3c7; }
.line-empty .content { background: #f9fafb; }
.char-delete { background: #f87171; border-radius: 2px; }
.char-insert { background: #4ade80; border-radius: 2px; }
.char-replace { background: #fbbf24; border-radius: 2px; }
footer { margin-top: 1.5rem; color: #9ca3af; font-size: 0.8rem; }
@media (max-width: 768px) { .panels { grid-template-columns: 1fr; } }
"""


def _escape(text: str) -> str:
    return html.escape(text, quote=False)


def _render_segments(segments: Optional[List[Dict]], fallback: str) -> str:
    if segments:
        parts = []
        for seg in segments:
            text = _escape(seg.get("text", ""))
            seg_type = seg.get("type", "equal")
            if seg_type == "equal":
                parts.append(text)
            else:
                parts.append(f'<span class="char-{seg_type}">{text}</span>')
        return "".join(parts)
    return _escape(fallback)


def _render_line(line: Dict, index: int, side: str = "a") -> str:
    src_key = "line_a" if side == "a" else "line_b"
    line_no = line.get(src_key) or "·"
    line_type = line.get("type", "equal")
    type_class = "line-empty" if line_type == "empty" else f"line-{line_type}"
    if line_type == "empty":
        content = "&nbsp;"
    else:
        content = _render_segments(line.get("segments"), line.get("text", "")) or "&nbsp;"
    return (
        f'<div class="line {type_class}">'
        f'<span class="lineno">{line_no}</span>'
        f'<span class="content">{content}</span>'
        f"</div>"
    )


def _render_panel(title: str, lines: List[Dict], side: str) -> str:
    body = "".join(_render_line(line, i, side) for i, line in enumerate(lines))
    return f'<div class="panel"><div class="panel-hd">{_escape(title)}</div><div class="panel-bd">{body}</div></div>'


def export_html(text_a: str, text_b: str, title_a: str = "文本 A", title_b: str = "文本 B") -> str:
    result = compare_text(text_a, text_b)
    stats = result["stats"]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    summary = (
        f"共 {result['total_lines']} 行 · 相同 {stats['equal']} · "
        f"差异 {result.get('change_count', 0)} 处（删除 {stats['deleted']} · 新增 {stats['inserted']} · 修改 {stats['replaced']}）"
    )

    left_panel = _render_panel(title_a, result["left"], "a")
    right_panel = _render_panel(title_b, result["right"], "b")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>文本对比结果 - MyTools</title>
  <style>{EXPORT_CSS}</style>
</head>
<body>
  <h1>文本对比结果</h1>
  <p class="meta">{_escape(summary)} · 导出时间 {now}</p>
  <div class="legend">
    <span class="legend-delete">删除</span>
    <span class="legend-insert">新增</span>
    <span class="legend-replace">修改</span>
  </div>
  <div class="panels">
    {left_panel}
    {right_panel}
  </div>
  <footer>由 MyTools 文本对比工具导出</footer>
</body>
</html>"""
