# -*- coding: utf-8 -*-
"""SQLite 元数据读取与 SQL 执行。"""

import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple

from modules.sqlite_browser.repository import get_db_path

DEFAULT_ROW_LIMIT = 1000


def _connect(db_id: str) -> sqlite3.Connection:
    path = get_db_path(db_id)
    if not path.exists():
        raise FileNotFoundError("数据库文件不存在")
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def get_metadata(db_id: str) -> Dict[str, Any]:
    conn = _connect(db_id)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT name, type, sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
        )
        objects = cur.fetchall()

        tables: List[Dict] = []
        views: List[Dict] = []
        indexes: List[Dict] = []
        triggers: List[Dict] = []

        for row in objects:
            item = {"name": row["name"], "type": row["type"], "sql": row["sql"] or ""}
            if row["type"] == "table":
                tables.append(item)
            elif row["type"] == "view":
                views.append(item)
            elif row["type"] == "index":
                indexes.append(item)
            elif row["type"] == "trigger":
                triggers.append(item)

        table_schemas: Dict[str, Any] = {}
        for t in tables:
            name = t["name"]
            safe = name.replace("'", "''")
            cur.execute(f"PRAGMA table_info('{safe}')")
            columns = []
            for col in cur.fetchall():
                columns.append({
                    "cid": col[0],
                    "name": col[1],
                    "type": col[2],
                    "notnull": bool(col[3]),
                    "default": col[4],
                    "pk": bool(col[5]),
                })
            try:
                cur.execute(f"SELECT COUNT(*) FROM '{safe}'")
                row_count = cur.fetchone()[0]
            except sqlite3.Error:
                row_count = None
            table_schemas[name] = {"columns": columns, "row_count": row_count}

        return {
            "tables": tables,
            "views": views,
            "indexes": indexes,
            "triggers": triggers,
            "table_schemas": table_schemas,
        }
    finally:
        conn.close()


def _apply_limit(sql: str, limit: int) -> str:
    stripped = sql.strip().rstrip(";")
    upper = stripped.upper()
    if upper.startswith("SELECT") and " LIMIT " not in upper:
        return f"{stripped} LIMIT {limit}"
    return stripped


def execute_query(db_id: str, sql: str, row_limit: int = DEFAULT_ROW_LIMIT) -> Dict[str, Any]:
    sql = sql.strip()
    if not sql:
        raise ValueError("SQL 不能为空")

    conn = _connect(db_id)
    start = time.perf_counter()
    try:
        cur = conn.cursor()
        is_select = sql.lstrip().upper().startswith("SELECT") or sql.lstrip().upper().startswith("WITH")
        exec_sql = _apply_limit(sql, row_limit) if is_select else sql

        cur.execute(exec_sql)
        duration_ms = (time.perf_counter() - start) * 1000

        if cur.description:
            columns = [d[0] for d in cur.description]
            rows_raw = cur.fetchmany(row_limit + 1)
            truncated = len(rows_raw) > row_limit
            if truncated:
                rows_raw = rows_raw[:row_limit]
            rows = [[_serialize_cell(c) for c in row] for row in rows_raw]
            return {
                "query_type": "select",
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "truncated": truncated,
                "affected_rows": 0,
                "duration_ms": round(duration_ms, 2),
                "message": f"返回 {len(rows)} 行" + ("（已截断）" if truncated else ""),
            }

        conn.commit()
        return {
            "query_type": "execute",
            "columns": [],
            "rows": [],
            "row_count": 0,
            "truncated": False,
            "affected_rows": cur.rowcount,
            "duration_ms": round(duration_ms, 2),
            "message": f"执行成功，影响 {cur.rowcount} 行",
        }
    except sqlite3.Error as exc:
        duration_ms = (time.perf_counter() - start) * 1000
        raise RuntimeError(str(exc)) from exc
    finally:
        conn.close()


def _serialize_cell(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (int, float, str, bool)):
        return value
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return f"<BLOB {len(value)} bytes>"
    return str(value)
