# -*- coding: utf-8 -*-
"""JSON 格式化、压缩与校验。"""

import json
from typing import Any, Optional


class JsonFormatError(Exception):
    def __init__(self, message: str, line: Optional[int] = None, column: Optional[int] = None):
        super().__init__(message)
        self.line = line
        self.column = column


def _parse(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise JsonFormatError(e.msg, e.lineno, e.colno) from e


def format_json(text: str, indent: int = 2, sort_keys: bool = False) -> str:
    data = _parse(text)
    return json.dumps(data, ensure_ascii=False, indent=indent, sort_keys=sort_keys)


def minify_json(text: str) -> str:
    data = _parse(text)
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def validate_json(text: str) -> dict:
    data = _parse(text)
    if isinstance(data, dict):
        kind = "object"
        size = len(data)
    elif isinstance(data, list):
        kind = "array"
        size = len(data)
    else:
        kind = type(data).__name__
        size = None
    return {"valid": True, "type": kind, "size": size}
