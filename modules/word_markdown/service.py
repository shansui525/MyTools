# -*- coding: utf-8 -*-
"""Word 转 Markdown（极致压缩）。"""

import logging
import re
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Union

import html2text
import mammoth

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".docx"}


class WordMarkdownError(Exception):
    pass


def _normalize_cell(text: str) -> str:
    text = " ".join(text.strip().split())
    return text.replace("\\", "\\\\").replace("|", "\\|")


def _split_table_cells(line: str) -> List[str]:
    stripped = line.strip()
    if stripped.startswith("|") and stripped.endswith("|"):
        stripped = stripped[1:-1]
    return stripped.split("|")


def _is_separator_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    cells = _split_table_cells(stripped)
    if not cells:
        return False
    return all(re.match(r"^[\s\-:]*$", cell) and "-" in cell for cell in cells)


def _looks_like_table_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith("```"):
        return False
    if stripped.startswith("|") and stripped.count("|") >= 2:
        return True
    if "|" in stripped and not stripped.startswith("#"):
        parts = stripped.split("|")
        if len(parts) >= 2 and all(not p.strip().startswith("http") for p in parts[:2]):
            return True
    return False


def _table_row(cells: List[str], separator: bool = False) -> str:
    if separator:
        return "|" + "|".join(["--"] * len(cells)) + "|"
    return "|" + "|".join(_normalize_cell(c) for c in cells) + "|"


def _compress_table_block(block: List[str]) -> List[str]:
    if not block:
        return []

    parsed: List[List[str]] = []
    separators: List[bool] = []
    for line in block:
        cells = _split_table_cells(line)
        is_sep = _is_separator_line(line)
        parsed.append(cells)
        separators.append(is_sep)

    col_count = max(len(row) for row in parsed) if parsed else 0
    if col_count == 0:
        return []

    normalized = [row + [""] * (col_count - len(row)) for row in parsed]

    out: List[str] = []
    has_sep = any(separators)
    for idx, cells in enumerate(normalized):
        if separators[idx]:
            out.append(_table_row(cells, separator=True))
        else:
            out.append(_table_row(cells, separator=False))
            if not has_sep and idx == 0 and len(normalized) > 1:
                out.append(_table_row(cells, separator=True))
                has_sep = True
    return out


def _compress_text_line(line: str) -> str:
    stripped = line.rstrip()
    if not stripped:
        return ""

    heading = re.match(r"^(#+)\s+(.*)$", stripped)
    if heading:
        title = " ".join(heading.group(2).split())
        return "{} {}".format(heading.group(1), title)

    bullet = re.match(r"^(\s*[-*+]\s+)(.*)$", stripped)
    if bullet:
        return bullet.group(1) + " ".join(bullet.group(2).split())

    ordered = re.match(r"^(\s*\d+\.\s+)(.*)$", stripped)
    if ordered:
        return ordered.group(1) + " ".join(ordered.group(2).split())

    return " ".join(stripped.split())


def _compress_markdown(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if _looks_like_table_line(line):
            block: List[str] = []
            while i < len(lines) and _looks_like_table_line(lines[i]):
                block.append(lines[i])
                i += 1
            out.extend(_compress_table_block(block))
            continue

        out.append(_compress_text_line(line))
        i += 1

    merged: List[str] = []
    for line in out:
        if line == "" and merged and merged[-1] == "":
            continue
        merged.append(line)

    result = "\n".join(merged)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip() + "\n"


def _html_to_markdown(html: str, ignore_images: bool) -> str:
    converter = html2text.HTML2Text()
    converter.body_width = 0
    converter.ignore_links = False
    converter.ignore_images = ignore_images
    converter.ignore_emphasis = False
    converter.single_line_break = False
    converter.wrap_links = False
    converter.pad_tables = True
    return converter.handle(html)


def word_to_markdown(
    source: Union[str, Path, bytes],
    ignore_images: bool = True,
    filename: str = "",
) -> Dict[str, Any]:
    if isinstance(source, bytes):
        data = source
        ext = Path(filename or "").suffix.lower()
    else:
        path = Path(source)
        ext = path.suffix.lower()
        filename = path.name
        data = path.read_bytes()

    if ext not in ALLOWED_EXTENSIONS:
        raise WordMarkdownError("不支持的格式: {}，请上传 .docx 文件".format(ext or "(无后缀)"))

    if len(data) < 4:
        raise WordMarkdownError("文件过小或为空")

    logger.info("打开 Word: filename=%r size=%d", filename, len(data))

    try:
        result = mammoth.convert_to_html(BytesIO(data))
    except Exception as exc:
        logger.exception("Word 解析失败")
        msg = str(exc)
        if "zip" in msg.lower() or "not a zip" in msg.lower():
            raise WordMarkdownError("文件已损坏或不是有效的 .docx 文档") from exc
        raise WordMarkdownError("无法打开 Word 文档: {}".format(msg)) from exc

    warnings = [m.message for m in result.messages if getattr(m, "message", "")]
    if warnings:
        logger.info("Word 转换警告 (%d): %s", len(warnings), warnings[:5])

    html = result.value or ""
    if not html.strip():
        raise WordMarkdownError("文档中没有可转换的内容")

    raw_md = _html_to_markdown(html, ignore_images=ignore_images)
    markdown = _compress_markdown(raw_md)
    if not markdown.strip():
        raise WordMarkdownError("转换结果为空")

    stats = {
        "chars": len(markdown),
        "lines": markdown.count("\n") + 1,
        "warnings": len(warnings),
    }
    logger.info("转换完成: chars=%d lines=%d warnings=%d", stats["chars"], stats["lines"], stats["warnings"])

    return {
        "markdown": markdown,
        "stats": stats,
        "warnings": warnings[:20],
    }
