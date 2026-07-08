# -*- coding: utf-8 -*-
"""内置 RSS 订阅源预设（来自 rss_manager 项目）。"""

import json
from pathlib import Path
from typing import Dict, List, Optional

PRESETS_FILE = Path(__file__).resolve().parent.parent.parent / "config" / "rss_feed_presets.json"


def load_presets() -> List[Dict]:
    """读取预设订阅源列表。"""
    if not PRESETS_FILE.exists():
        return []
    try:
        data = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
        feeds = data.get("feeds", [])
        if isinstance(feeds, list):
            return feeds
    except (json.JSONDecodeError, OSError):
        pass
    return []


def list_preset_categories() -> List[str]:
    """返回所有预设分类（去重排序）。"""
    cats = sorted({f.get("category") or "默认" for f in load_presets()})
    return cats


def get_presets_by_category(category: Optional[str] = None) -> List[Dict]:
    """按分类筛选预设，category 为空则返回全部。"""
    feeds = load_presets()
    if not category:
        return feeds
    return [f for f in feeds if (f.get("category") or "默认") == category]


def group_presets() -> Dict[str, List[Dict]]:
    """按分类分组返回预设。"""
    grouped: Dict[str, List[Dict]] = {}
    for feed in load_presets():
        cat = feed.get("category") or "默认"
        grouped.setdefault(cat, []).append(feed)
    return grouped
