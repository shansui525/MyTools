# -*- coding: utf-8 -*-
"""工具注册表：从配置文件加载可用工具列表。"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOLS_CONFIG_PATH = PROJECT_ROOT / "config" / "tools.json"


def load_tools_config() -> dict[str, Any]:
    with open(TOOLS_CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_app_info() -> dict[str, str]:
    config = load_tools_config()
    return config.get("app", {})


def get_tool_groups() -> list[dict[str, Any]]:
    config = load_tools_config()
    return config.get("groups", [])


def get_enabled_tools() -> list[dict[str, Any]]:
    config = load_tools_config()
    return [t for t in config.get("tools", []) if t.get("enabled", True)]


def get_tool_by_id(tool_id: str) -> Optional[Dict[str, Any]]:
    for tool in get_enabled_tools():
        if tool.get("id") == tool_id:
            return tool
    return None
