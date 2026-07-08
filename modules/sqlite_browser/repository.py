# -*- coding: utf-8 -*-
"""SQLite 数据库连接注册表（支持本地路径与历史上传）。"""

import json
import shutil
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.sqlite_browser.import_store import clear_import_db, get_import_db_size, list_imported_tables

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = PROJECT_ROOT / "data" / "sqlite_uploads"
REGISTRY_PATH = PROJECT_ROOT / "data" / "sqlite_registry.json"

ALLOWED_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".db3"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_registry() -> Dict[str, Any]:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if not REGISTRY_PATH.exists():
        return {"databases": {}}
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_registry(data: Dict[str, Any]) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _validate_sqlite_file(path: Path) -> None:
    if not path.exists():
        raise ValueError("文件不存在: {}".format(path))
    if not path.is_file():
        raise ValueError("路径不是文件: {}".format(path))
    if path.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValueError("不支持的文件格式，请使用 .db / .sqlite / .sqlite3 / .db3")

    conn = None
    try:
        conn = sqlite3.connect(str(path))
        conn.execute("SELECT 1 FROM sqlite_master LIMIT 1")
    except sqlite3.Error as exc:
        raise ValueError("不是有效的 SQLite 数据库: {}".format(exc)) from exc
    finally:
        if conn is not None:
            conn.close()


def _resolve_local_path(path_str: str) -> Path:
    if not path_str or not path_str.strip():
        raise ValueError("请提供数据库文件路径")
    path = Path(path_str.strip()).expanduser().resolve()
    _validate_sqlite_file(path)
    return path


def get_db_path(db_id: str) -> Path:
    if not db_id or not all(c in "0123456789abcdef" for c in db_id):
        raise ValueError("无效的数据库 ID")

    info = get_database(db_id)
    if not info:
        raise ValueError("数据库不存在")

    if info.get("source_type") == "temp":
        raise ValueError("临时库无磁盘数据库文件")

    if info.get("source_type") == "local":
        path = Path(info["path"]).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError("数据库文件不存在: {}".format(path))
        return path

    path = (UPLOAD_DIR / "{}.db".format(db_id)).resolve()
    if UPLOAD_DIR.resolve() not in path.parents and path.parent != UPLOAD_DIR.resolve():
        raise ValueError("非法路径")
    return path


def _temp_session_label(dt: Optional[datetime] = None) -> str:
    if dt is None:
        dt = datetime.now(timezone.utc)
    local = dt.astimezone(timezone(timedelta(hours=8)))
    return local.strftime("临时库 %m-%d %H:%M:%S")


def _apply_temp_stats(info: Dict[str, Any]) -> bool:
    db_id = info.get("db_id")
    if not db_id:
        return False

    changed = False
    if info.get("filename") in ("临时库（导入数据）", "临时库"):
        linked_at = info.get("linked_at")
        suffix = f" #{db_id[:4]}" if db_id else ""
        if linked_at:
            try:
                dt = datetime.fromisoformat(linked_at.replace("Z", "+00:00"))
                info["filename"] = _temp_session_label(dt) + suffix
                changed = True
            except ValueError:
                info["filename"] = _temp_session_label() + suffix
                changed = True

    size = get_import_db_size(db_id)
    tables = list_imported_tables(db_id)
    table_count = len(tables)
    summary = ""
    if tables:
        names = [t["name"] for t in tables[:2]]
        summary = ", ".join(names)
        if table_count > 2:
            summary += f" 等{table_count}表"

    changed = (
        changed
        or info.get("size") != size
        or info.get("table_count") != table_count
        or info.get("summary") != summary
    )
    info["size"] = size
    info["table_count"] = table_count
    info["summary"] = summary
    return changed


def refresh_temp_session_info(db_id: str) -> Optional[Dict[str, Any]]:
    reg = _load_registry()
    info = reg["databases"].get(db_id)
    if not info or info.get("source_type") != "temp":
        return info
    if _apply_temp_stats(info):
        reg["databases"][db_id] = info
        _save_registry(reg)
    return info


def register_temp_session() -> Dict[str, Any]:
    db_id = uuid.uuid4().hex
    info = {
        "db_id": db_id,
        "filename": f"{_temp_session_label()} #{db_id[:4]}",
        "source_type": "temp",
        "size": 0,
        "table_count": 0,
        "summary": "",
        "linked_at": _now_iso(),
    }
    reg = _load_registry()
    reg["databases"][db_id] = info
    _save_registry(reg)
    return info


def register_local_path(path_str: str) -> Dict[str, Any]:
    path = _resolve_local_path(path_str)

    reg = _load_registry()
    for item in reg["databases"].values():
        if item.get("source_type") == "local" and Path(item.get("path", "")).expanduser().resolve() == path:
            return item

    db_id = uuid.uuid4().hex
    info = {
        "db_id": db_id,
        "filename": path.name,
        "source_type": "local",
        "path": str(path),
        "size": path.stat().st_size,
        "linked_at": _now_iso(),
    }
    reg["databases"][db_id] = info
    _save_registry(reg)
    return info


def register_upload(source_path: Path, original_name: str) -> Dict[str, Any]:
    db_id = uuid.uuid4().hex
    dest = UPLOAD_DIR / "{}.db".format(db_id)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, dest)

    info = {
        "db_id": db_id,
        "filename": original_name,
        "source_type": "upload",
        "size": dest.stat().st_size,
        "uploaded_at": _now_iso(),
    }
    reg = _load_registry()
    reg["databases"][db_id] = info
    _save_registry(reg)
    return info


def get_database(db_id: str) -> Optional[Dict[str, Any]]:
    reg = _load_registry()
    return reg["databases"].get(db_id)


def list_databases() -> List[Dict[str, Any]]:
    reg = _load_registry()
    changed = False
    for db_id, info in reg["databases"].items():
        if info.get("source_type") == "temp" and _apply_temp_stats(info):
            reg["databases"][db_id] = info
            changed = True
    if changed:
        _save_registry(reg)

    items = list(reg["databases"].values())
    items.sort(key=lambda x: x.get("linked_at") or x.get("uploaded_at", ""), reverse=True)
    return items


def delete_database(db_id: str) -> bool:
    reg = _load_registry()
    info = reg["databases"].get(db_id)
    if not info:
        return False

    if info.get("source_type", "upload") == "upload":
        path = get_db_path(db_id)
        if path.exists():
            path.unlink()

    clear_import_db(db_id)
    del reg["databases"][db_id]
    _save_registry(reg)
    return True
