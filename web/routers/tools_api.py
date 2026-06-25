# -*- coding: utf-8 -*-
"""工具列表 API。"""

from fastapi import APIRouter

from modules.registry import get_app_info, get_enabled_tools, get_tool_by_id, get_tool_groups

router = APIRouter(prefix="/api", tags=["tools"])


@router.get("/app")
def get_app():
    return get_app_info()


@router.get("/tools")
def list_tools():
    return {"groups": get_tool_groups(), "tools": get_enabled_tools()}


@router.get("/tools/{tool_id}")
def get_tool(tool_id: str):
    tool = get_tool_by_id(tool_id)
    if not tool:
        return {"error": "工具不存在", "tool_id": tool_id}
    return tool
