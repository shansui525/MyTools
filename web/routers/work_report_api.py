# -*- coding: utf-8 -*-
"""工作记录与 AI 报告 API。"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from modules.work_report.repository import (
    delete_entry,
    delete_report,
    get_entry,
    get_report,
    get_settings_public,
    list_entries,
    list_entry_dates,
    list_reports,
    update_settings,
    upsert_entry,
    upsert_report,
)
from modules.work_report.service import generate_report, get_period_range, test_llm_connection

router = APIRouter(prefix="/api/tools/work-report", tags=["work-report"])


class EntryForm(BaseModel):
    content: str = Field(min_length=1, description="工作内容")


class SettingsForm(BaseModel):
    llm_api_base: str = Field(default="https://api.openai.com/v1")
    llm_model: str = Field(default="gpt-4o-mini")
    llm_api_key: Optional[str] = Field(default=None, description="留空或不改则保留原密钥")


class ReportForm(BaseModel):
    period: str = Field(description="week / month / quarter / year")
    reference_date: str = Field(description="参考日期 YYYY-MM-DD")


class ReportSaveForm(BaseModel):
    period: str = Field(description="week / month / quarter / year")
    reference_date: str = Field(description="参考日期 YYYY-MM-DD")
    title: str = Field(min_length=1, description="报告标题")
    start_date: str = Field(description="起始日期 YYYY-MM-DD")
    end_date: str = Field(description="结束日期 YYYY-MM-DD")
    content: str = Field(min_length=1, description="报告正文（Markdown）")
    entry_count: int = Field(default=0, ge=0, description="关联工作记录天数")
    report_id: Optional[str] = Field(default=None, description="已有报告 ID，留空则按周期匹配或新建")


class ReportUpdateForm(BaseModel):
    content: str = Field(min_length=1, description="报告正文（Markdown）")
    title: Optional[str] = Field(default=None, description="可选更新标题")


@router.get("/entries")
def get_entries(
    start: Optional[str] = Query(default=None, description="起始日期"),
    end: Optional[str] = Query(default=None, description="结束日期"),
):
    return {"entries": list_entries(start, end)}


@router.get("/entries/dates")
def get_entry_dates():
    return {"dates": list_entry_dates()}


@router.get("/entries/{entry_date}")
def get_entry_by_date(entry_date: str):
    entry = get_entry(entry_date)
    if not entry:
        return {"entry": None}
    return {"entry": entry}


@router.put("/entries/{entry_date}")
def save_entry(entry_date: str, body: EntryForm):
    try:
        entry = upsert_entry(entry_date, body.content)
        return {"entry": entry}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/entries/{entry_date}")
def remove_entry(entry_date: str):
    if not delete_entry(entry_date):
        raise HTTPException(status_code=404, detail="该日期无工作记录")
    return {"message": "已删除"}


@router.get("/settings")
def read_settings():
    return get_settings_public()


@router.put("/settings")
def save_settings(body: SettingsForm):
    return update_settings(body.llm_api_base, body.llm_model, body.llm_api_key)


@router.post("/settings/test")
def test_settings():
    try:
        reply = test_llm_connection()
        return {"ok": True, "message": reply}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/period-range")
def period_range(
    period: str = Query(description="week / month / quarter / year"),
    reference_date: str = Query(description="参考日期 YYYY-MM-DD"),
):
    try:
        ref = date.fromisoformat(reference_date)
        start, end, title = get_period_range(period, ref)
        entries = list_entries(start.isoformat(), end.isoformat())
        return {
            "period": period,
            "title": title,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "entry_count": len(entries),
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/reports/generate")
def create_report(body: ReportForm):
    try:
        ref = date.fromisoformat(body.reference_date)
        return generate_report(body.period, ref)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/reports")
def get_reports():
    return {"reports": list_reports()}


@router.get("/reports/{report_id}")
def read_report(report_id: str):
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    return {"report": report}


@router.post("/reports")
def save_report(body: ReportSaveForm):
    try:
        report = upsert_report(
            period=body.period,
            reference_date=body.reference_date,
            title=body.title.strip(),
            start_date=body.start_date,
            end_date=body.end_date,
            content=body.content,
            entry_count=body.entry_count,
            report_id=body.report_id,
        )
        return {"report": report}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/reports/{report_id}")
def update_report(report_id: str, body: ReportUpdateForm):
    existing = get_report(report_id)
    if not existing:
        raise HTTPException(status_code=404, detail="报告不存在")
    try:
        report = upsert_report(
            period=existing["period"],
            reference_date=existing["reference_date"],
            title=(body.title or existing["title"]).strip(),
            start_date=existing["start_date"],
            end_date=existing["end_date"],
            content=body.content,
            entry_count=existing.get("entry_count", 0),
            report_id=report_id,
        )
        return {"report": report}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/reports/{report_id}")
def remove_report(report_id: str):
    if not delete_report(report_id):
        raise HTTPException(status_code=404, detail="报告不存在")
    return {"message": "已删除"}
