# -*- coding: utf-8 -*-
"""A4 横版 3×4 年历 PDF 导出。"""

import platform
from pathlib import Path
from typing import Dict, List, Optional

from fpdf import FPDF

from modules.calendar_tool.lunar import format_lunar_from_parts
from modules.calendar_tool.service import MONTH_NAMES, WEEKDAY_NAMES, build_calendar_data

A4_WIDTH = 297.0
A4_HEIGHT = 210.0
MARGIN = 8.0
COLS = 3
ROWS = 4


def _find_cjk_font() -> Optional[str]:
    system = platform.system()
    if system == "Darwin":
        candidates = [
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/Library/Fonts/Arial Unicode.ttf",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
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


class CalendarPDF(FPDF):
    def __init__(self, year: int, font_path: Optional[str]):
        super().__init__(orientation="L", unit="mm", format="A4")
        self._year = year
        self._font_name = "Helvetica"
        if font_path:
            try:
                self.add_font("CJK", "", font_path)
                self.add_font("CJK", "B", font_path)
                self._font_name = "CJK"
            except Exception:
                pass
        self.set_auto_page_break(auto=False)
        self.add_page()
        self._draw_title()

    def _set_font(self, size: float, style: str = "") -> None:
        self.set_font(self._font_name, style=style, size=size)

    def _draw_title(self) -> None:
        self._set_font(14, "B")
        self.set_xy(MARGIN, 4)
        self.cell(0, 6, f"{self._year}年日历", align="C")

    def draw_calendar(self, data: dict) -> None:
        usable_w = A4_WIDTH - 2 * MARGIN
        usable_h = A4_HEIGHT - MARGIN - 14
        cell_w = usable_w / COLS
        cell_h = usable_h / ROWS
        pad_x = 1.5
        pad_y = 1.0

        holidays: Dict[str, str] = data.get("holidays", {})
        events: Dict[str, List[str]] = data.get("events", {})

        for idx, month in enumerate(data["months"]):
            row = idx // COLS
            col = idx % COLS
            x0 = MARGIN + col * cell_w + pad_x
            y0 = 14 + row * cell_h + pad_y
            inner_w = cell_w - 2 * pad_x
            inner_h = cell_h - 2 * pad_y
            self._draw_month(x0, y0, inner_w, inner_h, data["year"], month, holidays, events)

    def _draw_month(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        year: int,
        month: dict,
        holidays: Dict[str, str],
        events: Dict[str, List[str]],
    ) -> None:
        m = month["month"]
        weeks = month["weeks"]

        self.set_draw_color(200, 200, 200)
        self.rect(x, y, w, h)

        title_h = 5.0
        header_h = 4.0
        grid_top = y + title_h + header_h
        grid_h = h - title_h - header_h - 1
        row_h = grid_h / 6
        col_w = w / 7

        self._set_font(7.5, "B")
        self.set_xy(x, y + 0.5)
        self.cell(w, title_h, MONTH_NAMES[m - 1], align="C")

        self._set_font(5.5, "")
        for i, wd in enumerate(WEEKDAY_NAMES):
            self.set_xy(x + i * col_w, y + title_h)
            color = (220, 38, 38) if i in (0, 6) else (80, 80, 80)
            self.set_text_color(*color)
            self.cell(col_w, header_h, wd, align="C")
        self.set_text_color(0, 0, 0)

        for wi, week in enumerate(weeks):
            for di, day in enumerate(week):
                cx = x + di * col_w
                cy = grid_top + wi * row_h
                if day == 0:
                    continue
                date_key = f"{year}-{m:02d}-{day:02d}"
                holiday = holidays.get(date_key)
                day_events = events.get(date_key, [])

                is_weekend = di in (0, 6)
                if holiday:
                    self.set_text_color(200, 30, 30)
                elif is_weekend:
                    self.set_text_color(200, 30, 30)
                else:
                    self.set_text_color(30, 30, 30)

                self._set_font(6, "B" if holiday else "")
                self.set_xy(cx, cy + 0.3)
                self.cell(col_w, 3, str(day), align="C")

                lunar_text = format_lunar_from_parts(year, m, day)
                if lunar_text:
                    self._set_font(3.8, "")
                    self.set_text_color(120, 120, 120)
                    self.set_xy(cx, cy + 2.8)
                    self.cell(col_w, 2, lunar_text, align="C")
                    self.set_text_color(0, 0, 0)

                label = holiday or ""
                if day_events and not label:
                    label = day_events[0][:4]
                elif day_events and label:
                    label = label[:3]

                if label:
                    self._set_font(4, "")
                    self.set_text_color(100, 100, 100)
                    self.set_xy(cx, cy + 3.2)
                    self.cell(col_w, 2.5, label, align="C")

                if len(day_events) > 1:
                    self.set_fill_color(59, 130, 246)
                    dot_x = cx + col_w / 2 - 0.5
                    self.rect(dot_x, cy + row_h - 2, 1, 1, style="F")

                self.set_text_color(0, 0, 0)


def calendar_to_pdf(year: int) -> bytes:
    font_path = _find_cjk_font()
    if not font_path:
        raise RuntimeError("未找到可用的中文字体，无法生成 PDF")

    data = build_calendar_data(year)
    pdf = CalendarPDF(year, font_path)
    pdf.draw_calendar(data)

    out = pdf.output()
    if isinstance(out, (bytes, bytearray)):
        return bytes(out)
    return out.encode("latin-1")
