# -*- coding: utf-8 -*-
"""文本对比 API。"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from modules.text_diff.export import export_html
from modules.text_diff.service import compare_text

router = APIRouter(prefix="/api/tools/text-diff", tags=["text-diff"])


class TextCompareRequest(BaseModel):
    text_a: str = Field(description="文本 A")
    text_b: str = Field(description="文本 B")
    title_a: str = Field(default="文本 A", description="A 侧标题")
    title_b: str = Field(default="文本 B", description="B 侧标题")


@router.post("/compare")
def compare(body: TextCompareRequest):
    if not body.text_a and not body.text_b:
        raise HTTPException(status_code=400, detail="请至少输入一段文本")
    return compare_text(body.text_a, body.text_b)


@router.post("/export")
def export(body: TextCompareRequest):
    if not body.text_a and not body.text_b:
        raise HTTPException(status_code=400, detail="请至少输入一段文本")
    content = export_html(body.text_a, body.text_b, body.title_a, body.title_b)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"text_diff_{ts}.html"
    return Response(
        content=content.encode("utf-8"),
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
