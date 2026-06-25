# -*- coding: utf-8 -*-
"""Markdown 转 PDF（fpdf2 + markdown）。"""

import platform
import re
from pathlib import Path
from typing import Optional

import markdown
from fpdf import FPDF
from fpdf.fonts import FontFace


def _find_cjk_font() -> Optional[str]:
    system = platform.system()
    if system == "Darwin":
        candidates = [
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/Library/Fonts/Arial Unicode.ttf",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
        ]
    elif system == "Windows":
        candidates = [
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simsun.ttc",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        ]
    for path in candidates:
        if Path(path).exists():
            return path
    return None


def _markdown_to_html(md_text: str) -> str:
    html = markdown.markdown(
        md_text,
        extensions=["fenced_code", "codehilite", "tables", "nl2br", "sane_lists"],
        extension_configs={
            "codehilite": {"css_class": "highlight", "guess_lang": False, "noclasses": True},
        },
    )
    # fpdf2 write_html 不支持 span，简化 codehilite 输出
    html = re.sub(r"<span[^>]*>(.*?)</span>", r"\1", html, flags=re.DOTALL)
    return html


class _MarkdownPDF(FPDF):
    def __init__(self, title: str, font_path: Optional[str]):
        super().__init__()
        self._font_path = font_path
        self._font_name = "Helvetica"
        self.set_title(title)
        self.set_auto_page_break(auto=True, margin=20)
        self.add_page()
        if font_path:
            try:
                self.add_font("CJKFont", "", font_path)
                self.add_font("CJKFont", "B", font_path)
                self.add_font("CJKFont", "I", font_path)
                self.add_font("CJKFont", "BI", font_path)
                self._font_name = "CJKFont"
            except Exception:
                pass
        self.set_font(self._font_name, size=11)

    def write_html_content(self, html: str) -> None:
        code_font = FontFace(family=self._font_name, size_pt=9)
        self.write_html(
            html,
            font_family=self._font_name,
            tag_styles={
                "code": code_font,
                "pre": code_font,
            },
        )


def markdown_to_pdf(md_text: str, title: str = "Document") -> bytes:
    if not md_text.strip():
        raise ValueError("Markdown 内容不能为空")

    font_path = _find_cjk_font()
    if not font_path:
        raise RuntimeError(
            "未找到可用的中文字体，请确保系统已安装 Arial Unicode 或微软雅黑等字体"
        )

    html_body = _markdown_to_html(md_text)
    pdf = _MarkdownPDF(title=title, font_path=font_path)
    try:
        pdf.write_html_content(html_body)
    except Exception as exc:
        raise RuntimeError(f"PDF 渲染失败: {exc}") from exc

    out = pdf.output()
    if isinstance(out, (bytes, bytearray)):
        return bytes(out)
    return out.encode("latin-1")
