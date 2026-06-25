# -*- coding: utf-8 -*-
"""JSON 格式化 API。"""

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from modules.json_formatter.service import JsonFormatError, format_json, minify_json, validate_json

router = APIRouter(prefix="/api/tools/json-formatter", tags=["json-formatter"])


class JsonProcessRequest(BaseModel):
    text: str = Field(description="待处理的 JSON 文本")
    action: Literal["format", "minify", "validate"] = "format"
    indent: int = Field(default=2, ge=0, le=8)
    sort_keys: bool = False


@router.post("/process")
def process_json(body: JsonProcessRequest):
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="请输入 JSON 内容")

    try:
        if body.action == "format":
            result = format_json(text, indent=body.indent, sort_keys=body.sort_keys)
            return {"action": "format", "result": result, "valid": True}
        if body.action == "minify":
            result = minify_json(text)
            return {"action": "minify", "result": result, "valid": True}
        info = validate_json(text)
        return {"action": "validate", "valid": True, **info}
    except JsonFormatError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "message": str(e),
                "line": e.line,
                "column": e.column,
            },
        )
