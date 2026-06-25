# -*- coding: utf-8 -*-
"""日历 API。"""

from typing import List

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from modules.calendar_tool.pdf_export import calendar_to_pdf
from modules.calendar_tool.service import build_calendar_data, update_events

router = APIRouter(prefix="/api/tools/calendar", tags=["calendar"])


class SaveEventsRequest(BaseModel):
    year: int = Field(ge=1970, le=2100)
    date: str = Field(description="YYYY-MM-DD")
    events: List[str] = Field(default_factory=list)


@router.get("/data")
def get_calendar_data(year: int = Query(default=2026, ge=1970, le=2100)):
    return build_calendar_data(year)


@router.post("/events")
def save_events(body: SaveEventsRequest):
    parts = body.date.split("-")
    if len(parts) != 3:
        raise HTTPException(status_code=400, detail="日期格式应为 YYYY-MM-DD")
    try:
        y = int(parts[0])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="无效日期") from exc
    if y != body.year:
        raise HTTPException(status_code=400, detail="日期与年份不一致")
    return update_events(body.year, body.date, body.events)


@router.get("/pdf")
def export_pdf(year: int = Query(default=2026, ge=1970, le=2100)):
    try:
        pdf_bytes = calendar_to_pdf(year)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF 生成失败: {exc}")

    filename = f"calendar_{year}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
