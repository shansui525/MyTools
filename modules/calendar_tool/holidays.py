# -*- coding: utf-8 -*-
"""中国常见节日（公历固定 + 农历换算）。"""

from datetime import date, timedelta
from typing import Dict, Optional

try:
    from zhdate import ZhDate

    _HAS_ZHDATE = True
except ImportError:
    _HAS_ZHDATE = False

# 公历固定节日 MM-DD -> 名称
FIXED_HOLIDAYS: Dict[str, str] = {
    "01-01": "元旦",
    "02-14": "情人节",
    "03-08": "妇女节",
    "03-12": "植树节",
    "04-01": "愚人节",
    "05-01": "劳动节",
    "05-04": "青年节",
    "06-01": "儿童节",
    "07-01": "建党节",
    "08-01": "建军节",
    "09-10": "教师节",
    "10-01": "国庆节",
    "12-24": "平安夜",
    "12-25": "圣诞节",
}

# 清明节（节气日，按年近似）
QINGMING_DAY: Dict[int, int] = {
    y: 4 if y % 4 not in (0, 1) else 5 for y in range(2000, 2041)
}

# 农历节日 (月, 日, 名称)
LUNAR_FESTIVALS = [
    (1, 1, "春节"),
    (1, 15, "元宵节"),
    (5, 5, "端午节"),
    (7, 7, "七夕"),
    (8, 15, "中秋节"),
    (9, 9, "重阳节"),
    (12, 8, "腊八节"),
]


def _lunar_to_gregorian(lunar_year: int, lunar_month: int, lunar_day: int) -> Optional[date]:
    if not _HAS_ZHDATE:
        return None
    try:
        return ZhDate(lunar_year, lunar_month, lunar_day).to_datetime().date()
    except (ValueError, OverflowError):
        return None


def _add_lunar_holidays(result: Dict[str, str], gregorian_year: int) -> None:
    if not _HAS_ZHDATE:
        return
    for ly in (gregorian_year - 1, gregorian_year, gregorian_year + 1):
        for lm, ld, name in LUNAR_FESTIVALS:
            d = _lunar_to_gregorian(ly, lm, ld)
            if d and d.year == gregorian_year:
                key = d.isoformat()
                if key not in result:
                    result[key] = name
        # 除夕：春节前一日
        spring = _lunar_to_gregorian(ly, 1, 1)
        if spring and spring.year == gregorian_year:
            eve = spring - timedelta(days=1)
            if eve.year == gregorian_year:
                result.setdefault(eve.isoformat(), "除夕")


def get_holidays(year: int) -> Dict[str, str]:
    """返回 {YYYY-MM-DD: 节日名}。"""
    result: Dict[str, str] = {}

    for md, name in FIXED_HOLIDAYS.items():
        mm, dd = md.split("-")
        result[f"{year}-{mm}-{dd}"] = name

    if year in QINGMING_DAY:
        d = date(year, 4, QINGMING_DAY[year])
        result[d.isoformat()] = "清明节"

    # 国庆长假标注（2-7 日显示为国庆节）
    for day in range(2, 8):
        result.setdefault(f"{year}-10-{day:02d}", "国庆节")

    _add_lunar_holidays(result, year)
    return result
