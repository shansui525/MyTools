# -*- coding: utf-8 -*-
"""RSS 抓取与解析。"""

import urllib.error
import urllib.request
from typing import Dict, List, Tuple

import feedparser

_USER_AGENT = "MyTools-RSS/1.0"
_CHECK_TIMEOUT = 8
_FETCH_TIMEOUT = 15


def _parse_feed(url: str, timeout: int = _CHECK_TIMEOUT):
    """带超时的 RSS 抓取与解析。"""
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
    except urllib.error.HTTPError as exc:
        raise ValueError(f"HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        reason = getattr(exc.reason, "args", [exc.reason])[0]
        if isinstance(reason, TimeoutError) or "timed out" in str(exc.reason).lower():
            raise ValueError(f"请求超时（{timeout}秒）") from exc
        raise ValueError(str(exc.reason)) from exc
    except TimeoutError:
        raise ValueError(f"请求超时（{timeout}秒）") from None
    return feedparser.parse(data)


def check_feed(url: str) -> Tuple[bool, str, int]:
    """
    检测订阅源是否可用。

    返回: (是否正常, 错误信息, 文章数量)
    """
    try:
        feed = _parse_feed(url, timeout=_CHECK_TIMEOUT)
        # bozo=1 表示 XML 有瑕疵，但若有条目仍视为可用
        if not feed.entries:
            err = str(feed.bozo_exception) if feed.bozo else "未找到文章"
            return False, err or "订阅源无内容", 0
        return True, "", len(feed.entries)
    except Exception as exc:
        return False, str(exc), 0


def get_feed_items(url: str, limit: int = 50) -> Dict:
    """获取订阅源文章列表。"""
    feed = _parse_feed(url, timeout=_FETCH_TIMEOUT)
    if not feed.entries:
        raise ValueError("无法读取订阅源或暂无文章")

    items: List[Dict] = []
    for entry in feed.entries[:limit]:
        # 摘要过长时截断，避免页面卡顿
        summary = entry.get("summary") or entry.get("description") or ""
        if len(summary) > 300:
            summary = summary[:300] + "..."
        items.append(
            {
                "title": entry.get("title") or "无标题",
                "link": entry.get("link") or "",
                "published": entry.get("published") or entry.get("updated") or "",
                "summary": summary,
            }
        )

    channel_title = ""
    if feed.feed:
        channel_title = feed.feed.get("title") or ""

    return {"channel_title": channel_title, "items": items}
