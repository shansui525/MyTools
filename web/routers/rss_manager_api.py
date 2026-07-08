# -*- coding: utf-8 -*-
"""RSS 订阅源管理 API。"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from modules.rss_manager.presets import get_presets_by_category, group_presets, list_preset_categories, load_presets
from modules.rss_manager.repository import add_feed, delete_feed, get_feed, import_feeds, list_feeds, update_feed
from modules.rss_manager.service import check_feed, get_feed_items

router = APIRouter(prefix="/api/tools/rss-manager", tags=["rss-manager"])

# 并行检测订阅源状态，避免源多时加载过慢
_STATUS_WORKERS = 10


class FeedForm(BaseModel):
    name: str = Field(min_length=1, description="订阅源名称")
    url: str = Field(min_length=1, description="RSS 地址")
    category: str = Field(default="默认", description="分类")


class ImportPresetsForm(BaseModel):
    category: Optional[str] = Field(default=None, description="仅导入指定分类，空则导入全部")


def _feed_with_status(feed: dict) -> dict:
    """检测单个订阅源状态。"""
    ok, err, count = check_feed(feed["url"])
    return {
        **feed,
        "category": feed.get("category") or "默认",
        "status": "ok" if ok else "error",
        "status_message": err,
        "item_count": count,
    }


@router.get("/presets")
def get_presets():
    """获取内置预设订阅源（按分类分组）。"""
    grouped = group_presets()
    return {
        "categories": list_preset_categories(),
        "total": len(load_presets()),
        "groups": grouped,
    }


@router.post("/presets/import")
def import_presets(body: ImportPresetsForm):
    """从预设批量导入订阅源（自动跳过已存在的 URL）。"""
    feeds = get_presets_by_category(body.category)
    if not feeds:
        raise HTTPException(status_code=400, detail="没有可导入的预设订阅源")
    result = import_feeds(feeds)
    result["category"] = body.category or "全部"
    return result


@router.get("/feeds/status-stream")
def feed_status_stream():
    """并发检测所有订阅源，通过 SSE 逐个推送结果。"""

    def generate():
        feeds = list_feeds()
        total = len(feeds)
        if not total:
            yield f"data: {json.dumps({'complete': True, 'total': 0}, ensure_ascii=False)}\n\n"
            return

        done = 0
        with ThreadPoolExecutor(max_workers=_STATUS_WORKERS) as pool:
            futures = {pool.submit(_feed_with_status, f): f for f in feeds}
            for future in as_completed(futures):
                result = future.result()
                done += 1
                payload = json.dumps(
                    {"feed": result, "done": done, "total": total},
                    ensure_ascii=False,
                )
                yield f"data: {payload}\n\n"

        yield f"data: {json.dumps({'complete': True, 'done': total, 'total': total}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/feeds/{feed_id}/status")
def feed_status(feed_id: str):
    """检测单个订阅源状态（供前端逐个刷新）。"""
    feed = get_feed(feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="订阅源不存在")
    return _feed_with_status(feed)


@router.get("/feeds")
def get_feeds(with_status: bool = Query(default=False, description="是否检测每个源的状态")):
    """列出所有订阅源。"""
    feeds = list_feeds()
    if not with_status:
        return {
            "feeds": [
                {
                    **f,
                    "category": f.get("category") or "默认",
                    "status": "unknown",
                    "status_message": "",
                }
                for f in feeds
            ]
        }
    # 多线程并行检测，加快大量订阅源时的响应速度
    with ThreadPoolExecutor(max_workers=_STATUS_WORKERS) as pool:
        result = list(pool.map(_feed_with_status, feeds))
    return {"feeds": result}


@router.post("/feeds")
def create_feed(body: FeedForm):
    """新增订阅源。"""
    try:
        feed = add_feed(body.name, body.url, body.category)
        return _feed_with_status(feed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/feeds/{feed_id}")
def edit_feed(feed_id: str, body: FeedForm):
    """修改订阅源。"""
    try:
        feed = update_feed(feed_id, body.name, body.url, body.category)
        return _feed_with_status(feed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/feeds/{feed_id}")
def remove_feed(feed_id: str):
    """删除订阅源。"""
    if not delete_feed(feed_id):
        raise HTTPException(status_code=404, detail="订阅源不存在")
    return {"message": "已删除"}


@router.get("/feeds/{feed_id}/items")
def feed_items(feed_id: str):
    """获取某个订阅源的文章列表。"""
    feed = get_feed(feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="订阅源不存在")
    try:
        return get_feed_items(feed["url"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
