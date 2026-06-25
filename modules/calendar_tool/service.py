# -*- coding: utf-8 -*-
"""日历数据与 PDF 导出。"""

import calendar
from datetime import date
from typing import Any, Dict, List

from modules.calendar_tool.holidays import get_holidays
from modules.calendar_tool.lunar import format_lunar, lunar_available
from modules.calendar_tool.repository import load_year, save_date_events

MONTH_NAMES = [
    "一月", "二月", "三月", "四月", "五月", "六月",
    "七月", "八月", "九月", "十月", "十一月", "十二月",
]
WEEKDAY_NAMES = ["日", "一", "二", "三", "四", "五", "六"]


def _build_month_grid(year: int, month: int) -> List[List[int]]:
    cal = calendar.Calendar(firstweekday=calendar.SUNDAY)
    weeks = cal.monthdayscalendar(year, month)
    return weeks


def build_calendar_data(year: int) -> Dict[str, Any]:
    holidays = get_holidays(year)
    events = load_year(year)
    lunar_dates: Dict[str, str] = {}

    months = []
    for m in range(1, 13):
        weeks = _build_month_grid(year, m)
        month_days = []
        for week in weeks:
            for day in week:
                if day == 0:
                    month_days.append(None)
                else:
                    date_key = f"{year}-{m:02d}-{day:02d}"
                    lunar_text = format_lunar(date(year, m, day))
                    lunar_dates[date_key] = lunar_text
                    month_days.append({
                        "day": day,
                        "date": date_key,
                        "lunar": lunar_text,
                        "holiday": holidays.get(date_key),
                        "events": events.get(date_key, []),
                    })
        months.append({
            "month": m,
            "name": MONTH_NAMES[m - 1],
            "weeks": weeks,
            "days": month_days,
        })

    return {
        "year": year,
        "months": months,
        "holidays": holidays,
        "events": events,
        "lunar": lunar_dates,
        "lunar_enabled": lunar_available() and any(lunar_dates.values()),
        "weekday_names": WEEKDAY_NAMES,
        "layout": {"cols": 3, "rows": 4},
    }


def update_events(year: int, date_key: str, events: List[str]) -> Dict[str, Any]:
    save_date_events(year, date_key, events)
    return build_calendar_data(year)
