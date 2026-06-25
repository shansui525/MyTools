# -*- coding: utf-8 -*-
"""日历事件持久化。"""

import json
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_FILE = PROJECT_ROOT / "data" / "calendar_events.json"


def _ensure_file() -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("{}", encoding="utf-8")


def load_all() -> Dict[str, Dict[str, List[str]]]:
    _ensure_file()
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def load_year(year: int) -> Dict[str, List[str]]:
    all_data = load_all()
    year_key = str(year)
    events = all_data.get(year_key, {})
    if not isinstance(events, dict):
        return {}
    return {k: v if isinstance(v, list) else [] for k, v in events.items()}


def save_date_events(year: int, date_key: str, events: List[str]) -> Dict[str, List[str]]:
    all_data = load_all()
    year_key = str(year)
    if year_key not in all_data or not isinstance(all_data[year_key], dict):
        all_data[year_key] = {}

    cleaned = [e.strip() for e in events if e and e.strip()]
    if cleaned:
        all_data[year_key][date_key] = cleaned
    elif date_key in all_data[year_key]:
        del all_data[year_key][date_key]

    DATA_FILE.write_text(json.dumps(all_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return load_year(year)
