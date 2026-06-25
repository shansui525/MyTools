# -*- coding: utf-8 -*-
"""公历转农历显示。"""

from datetime import date, datetime
from typing import Optional

try:
    from zhdate import ZhDate

    _HAS_ZHDATE = True
except ImportError:
    _HAS_ZHDATE = False

LUNAR_MONTH_NAMES = ["正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "腊"]

LUNAR_DAY_NAMES = [
    "初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
    "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
    "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十",
]


def format_lunar(d: date) -> str:
    """格式化为墙历常用短格式：初一显示月份，其余显示日。"""
    if not _HAS_ZHDATE:
        return ""
    try:
        zd = ZhDate.from_datetime(datetime(d.year, d.month, d.day))
    except (ValueError, OverflowError):
        return ""

    month_name = LUNAR_MONTH_NAMES[zd.lunar_month - 1]
    prefix = "闰" if zd.leap_month else ""

    if zd.lunar_day == 1:
        return f"{prefix}{month_name}月"
    if 1 <= zd.lunar_day <= len(LUNAR_DAY_NAMES):
        return LUNAR_DAY_NAMES[zd.lunar_day - 1]
    return ""


def format_lunar_from_parts(year: int, month: int, day: int) -> str:
    return format_lunar(date(year, month, day))


def lunar_available() -> bool:
    return _HAS_ZHDATE
