"""SQL 执行历史持久化。"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
HISTORY_PATH = PROJECT_ROOT / "data" / "sql_query_history.json"
MAX_HISTORY = 500


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load() -> Dict[str, Any]:
    if not HISTORY_PATH.exists():
        return {"records": []}
    with open(HISTORY_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save(data: Dict[str, Any]) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_record(
    db_id: str,
    sql: str,
    success: bool,
    duration_ms: float,
    row_count: int = 0,
    affected_rows: int = 0,
    error: str = "",
    db_filename: str = "",
) -> Dict[str, Any]:
    record = {
        "id": uuid.uuid4().hex,
        "db_id": db_id,
        "db_filename": db_filename,
        "sql": sql,
        "success": success,
        "duration_ms": round(duration_ms, 2),
        "row_count": row_count,
        "affected_rows": affected_rows,
        "error": error,
        "executed_at": _now_iso(),
    }
    data = _load()
    records = data.get("records", [])
    records.insert(0, record)
    data["records"] = records[:MAX_HISTORY]
    _save(data)
    return record


def list_history(db_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    data = _load()
    records = data.get("records", [])
    if db_id:
        records = [r for r in records if r.get("db_id") == db_id]
    return records[:limit]


def clear_history(db_id: Optional[str] = None) -> int:
    data = _load()
    records = data.get("records", [])
    if db_id:
        kept = [r for r in records if r.get("db_id") != db_id]
        removed = len(records) - len(kept)
        data["records"] = kept
    else:
        removed = len(records)
        data["records"] = []
    _save(data)
    return removed
