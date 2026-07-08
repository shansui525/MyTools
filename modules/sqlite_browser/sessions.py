# -*- coding: utf-8 -*-
"""SQLite 会话连接（保持打开以支持 TEMP 临时表）。"""

import sqlite3
from typing import Dict, Optional

from modules.sqlite_browser.repository import get_database, get_db_path

_sessions: Dict[str, sqlite3.Connection] = {}


def is_session_db(db_id: str) -> bool:
    info = get_database(db_id)
    return bool(info and info.get("source_type") == "session")


def get_session(db_id: str) -> sqlite3.Connection:
    if db_id in _sessions:
        return _sessions[db_id]

    info = get_database(db_id)
    if not info:
        raise ValueError("数据库不存在")

    if info.get("source_type") == "session":
        conn = sqlite3.connect(":memory:")
    else:
        path = get_db_path(db_id)
        if not path.exists():
            raise FileNotFoundError("数据库文件不存在")
        conn = sqlite3.connect(str(path))

    conn.row_factory = sqlite3.Row
    _sessions[db_id] = conn
    return conn


def close_session(db_id: str) -> None:
    conn = _sessions.pop(db_id, None)
    if conn is not None:
        conn.close()


def has_session(db_id: str) -> bool:
    return db_id in _sessions
