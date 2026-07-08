# -*- coding: utf-8 -*-
"""RSS 订阅源本地存储（JSON 文件）。"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional

# 数据文件路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_FILE = PROJECT_ROOT / "data" / "rss_feeds.json"


def _ensure_file() -> None:
    """确保数据目录和文件存在。"""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text('{"feeds": []}', encoding="utf-8")


def _load() -> Dict:
    _ensure_file()
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("feeds"), list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {"feeds": []}


def _save(data: Dict) -> None:
    _ensure_file()
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_feeds() -> List[Dict]:
    """返回所有订阅源。"""
    return _load()["feeds"]


def get_existing_urls() -> set:
    """获取已存在的 URL 集合，用于导入去重。"""
    return {f.get("url", "").strip() for f in list_feeds() if f.get("url")}


def get_feed(feed_id: str) -> Optional[Dict]:
    """按 ID 查找订阅源。"""
    for feed in list_feeds():
        if feed.get("id") == feed_id:
            return feed
    return None


def add_feed(name: str, url: str, category: str = "默认") -> Dict:
    """新增订阅源。"""
    name = name.strip()
    url = url.strip()
    category = (category or "默认").strip()
    if not name or not url:
        raise ValueError("名称和 URL 不能为空")

    # URL 重复则拒绝
    if url in get_existing_urls():
        raise ValueError("该 RSS 地址已存在")

    data = _load()
    feed = {"id": uuid.uuid4().hex, "name": name, "url": url, "category": category}
    data["feeds"].append(feed)
    _save(data)
    return feed


def import_feed(name: str, url: str, category: str = "默认") -> Optional[Dict]:
    """导入订阅源，已存在则跳过并返回 None。"""
    url = url.strip()
    if not url or url in get_existing_urls():
        return None
    return add_feed(name.strip() or url, url, category)


def import_feeds(feeds: List[Dict]) -> Dict:
    """批量导入订阅源，返回统计结果。"""
    added = 0
    skipped = 0
    for item in feeds:
        url = (item.get("url") or "").strip()
        if not url:
            continue
        if import_feed(item.get("name") or url, url, item.get("category") or "默认"):
            added += 1
        else:
            skipped += 1
    return {"added": added, "skipped": skipped, "total": len(feeds)}


def update_feed(feed_id: str, name: str, url: str, category: str = None) -> Dict:
    """修改订阅源。"""
    name = name.strip()
    url = url.strip()
    if not name or not url:
        raise ValueError("名称和 URL 不能为空")

    data = _load()
    for feed in data["feeds"]:
        if feed.get("id") == feed_id:
            # 修改 URL 时检查是否与其他源冲突
            if url != feed.get("url") and url in get_existing_urls():
                raise ValueError("该 RSS 地址已存在")
            feed["name"] = name
            feed["url"] = url
            if category is not None:
                feed["category"] = (category or "默认").strip()
            _save(data)
            return feed
    raise ValueError("订阅源不存在")


def delete_feed(feed_id: str) -> bool:
    """删除订阅源。"""
    data = _load()
    before = len(data["feeds"])
    data["feeds"] = [f for f in data["feeds"] if f.get("id") != feed_id]
    if len(data["feeds"]) == before:
        return False
    _save(data)
    return True
