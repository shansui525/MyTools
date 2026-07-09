# -*- coding: utf-8 -*-
"""工作记录本地存储（JSON 文件）。"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_FILE = PROJECT_ROOT / "data" / "work_report.json"

DEFAULT_SETTINGS = {
    "llm_api_base": "https://api.openai.com/v1",
    "llm_api_key": "",
    "llm_model": "gpt-4o-mini",
}


def _ensure_file() -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text(json.dumps({"entries": {}, "settings": DEFAULT_SETTINGS.copy()}, ensure_ascii=False, indent=2), encoding="utf-8")


def _load() -> Dict:
    _ensure_file()
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("entries", {})
            data.setdefault("settings", DEFAULT_SETTINGS.copy())
            data.setdefault("reports", {})
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {"entries": {}, "settings": DEFAULT_SETTINGS.copy(), "reports": {}}


def _save(data: Dict) -> None:
    _ensure_file()
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _mask_key(key: str) -> str:
    if len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]


def list_entries(start: str = None, end: str = None) -> List[Dict]:
    """按日期范围列出工作记录，按日期倒序。"""
    entries = _load()["entries"]
    result = []
    for date_str, item in entries.items():
        if start and date_str < start:
            continue
        if end and date_str > end:
            continue
        result.append(
            {
                "date": date_str,
                "content": item.get("content", ""),
                "updated_at": item.get("updated_at", ""),
            }
        )
    result.sort(key=lambda x: x["date"], reverse=True)
    return result


def get_entry(date_str: str) -> Optional[Dict]:
    item = _load()["entries"].get(date_str)
    if not item:
        return None
    return {
        "date": date_str,
        "content": item.get("content", ""),
        "updated_at": item.get("updated_at", ""),
    }


def upsert_entry(date_str: str, content: str) -> Dict:
    content = content.strip()
    if not content:
        raise ValueError("工作内容不能为空")

    data = _load()
    entry = data["entries"].get(date_str, {})
    entry.update(
        {
            "id": entry.get("id") or uuid.uuid4().hex,
            "content": content,
            "updated_at": _now_iso(),
        }
    )
    data["entries"][date_str] = entry
    _save(data)
    return {"date": date_str, "content": entry["content"], "updated_at": entry["updated_at"]}


def delete_entry(date_str: str) -> bool:
    data = _load()
    if date_str not in data["entries"]:
        return False
    del data["entries"][date_str]
    _save(data)
    return True


def list_entry_dates() -> List[str]:
    """返回所有有记录的日期列表。"""
    return sorted(_load()["entries"].keys())


def get_settings_public() -> Dict:
    """返回可展示给前端的设置（密钥脱敏）。"""
    settings = _load()["settings"]
    key = settings.get("llm_api_key") or os.getenv("MYTOOLS_LLM_API_KEY", "")
    api_base = settings.get("llm_api_base") or os.getenv("MYTOOLS_LLM_API_BASE", DEFAULT_SETTINGS["llm_api_base"])
    model = settings.get("llm_model") or os.getenv("MYTOOLS_LLM_MODEL", DEFAULT_SETTINGS["llm_model"])
    return {
        "llm_api_base": api_base,
        "llm_model": model,
        "llm_api_key_set": bool(key),
        "llm_api_key_masked": _mask_key(key) if key else "",
    }


def get_settings_runtime() -> Dict:
    """返回运行时完整设置（含密钥），供后端调用大模型。"""
    settings = _load()["settings"]
    return {
        "llm_api_base": settings.get("llm_api_base") or os.getenv("MYTOOLS_LLM_API_BASE", DEFAULT_SETTINGS["llm_api_base"]),
        "llm_api_key": settings.get("llm_api_key") or os.getenv("MYTOOLS_LLM_API_KEY", ""),
        "llm_model": settings.get("llm_model") or os.getenv("MYTOOLS_LLM_MODEL", DEFAULT_SETTINGS["llm_model"]),
    }


def update_settings(api_base: str, model: str, api_key: Optional[str] = None) -> Dict:
    data = _load()
    settings = data.setdefault("settings", DEFAULT_SETTINGS.copy())
    settings["llm_api_base"] = (api_base or DEFAULT_SETTINGS["llm_api_base"]).strip()
    settings["llm_model"] = (model or DEFAULT_SETTINGS["llm_model"]).strip()
    if api_key is not None and api_key.strip() and "****" not in api_key:
        settings["llm_api_key"] = api_key.strip()
    _save(data)
    return get_settings_public()


def _report_summary(report_id: str, item: Dict) -> Dict:
    content = item.get("content", "")
    preview = content.replace("\n", " ").strip()[:80]
    return {
        "id": report_id,
        "period": item.get("period", ""),
        "title": item.get("title", ""),
        "reference_date": item.get("reference_date", ""),
        "start_date": item.get("start_date", ""),
        "end_date": item.get("end_date", ""),
        "entry_count": item.get("entry_count", 0),
        "created_at": item.get("created_at", ""),
        "updated_at": item.get("updated_at", ""),
        "preview": preview,
    }


def list_reports() -> List[Dict]:
    """列出已保存报告，按更新时间倒序。"""
    reports = _load().get("reports", {})
    items = [_report_summary(rid, item) for rid, item in reports.items()]
    items.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return items


def get_report(report_id: str) -> Optional[Dict]:
    item = _load().get("reports", {}).get(report_id)
    if not item:
        return None
    return _report_summary(report_id, item) | {"content": item.get("content", "")}


def get_report_by_period(period: str, reference_date: str) -> Optional[Dict]:
    reports = _load().get("reports", {})
    for rid, item in reports.items():
        if item.get("period") == period and item.get("reference_date") == reference_date:
            return _report_summary(rid, item) | {"content": item.get("content", "")}
    return None


def upsert_report(
    *,
    period: str,
    reference_date: str,
    title: str,
    start_date: str,
    end_date: str,
    content: str,
    entry_count: int = 0,
    report_id: Optional[str] = None,
) -> Dict:
    content = content.strip()
    if not content:
        raise ValueError("报告内容不能为空")

    data = _load()
    reports = data.setdefault("reports", {})
    now = _now_iso()

    target_id = report_id
    if not target_id:
        for rid, item in reports.items():
            if item.get("period") == period and item.get("reference_date") == reference_date:
                target_id = rid
                break

    if target_id and target_id in reports:
        item = reports[target_id]
        item.update(
            {
                "period": period,
                "reference_date": reference_date,
                "title": title,
                "start_date": start_date,
                "end_date": end_date,
                "content": content,
                "entry_count": entry_count,
                "updated_at": now,
            }
        )
    else:
        target_id = uuid.uuid4().hex
        reports[target_id] = {
            "id": target_id,
            "period": period,
            "reference_date": reference_date,
            "title": title,
            "start_date": start_date,
            "end_date": end_date,
            "content": content,
            "entry_count": entry_count,
            "created_at": now,
            "updated_at": now,
        }

    _save(data)
    return get_report(target_id)


def delete_report(report_id: str) -> bool:
    data = _load()
    reports = data.get("reports", {})
    if report_id not in reports:
        return False
    del reports[report_id]
    _save(data)
    return True
