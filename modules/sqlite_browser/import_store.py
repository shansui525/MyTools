# -*- coding: utf-8 -*-
"""CSV/Excel 导入数据的临时 SQLite 存储（按 db_id 隔离）。"""

import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
IMPORT_DIR = PROJECT_ROOT / "data" / "sqlite_imports"

IMPORT_SCHEMA = "imported"
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _import_db_path(db_id: str) -> Path:
    return IMPORT_DIR / f"{db_id}.import.db"


def has_imports(db_id: str) -> bool:
    path = _import_db_path(db_id)
    if not path.exists() or path.stat().st_size == 0:
        return False
    conn = sqlite3.connect(str(path))
    try:
        cur = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' LIMIT 1"
        )
        return cur.fetchone() is not None
    finally:
        conn.close()


def sanitize_identifier(name: str, fallback: str = "col") -> str:
    text = re.sub(r"[^\w]", "_", str(name).strip())
    if not text:
        text = fallback
    if text[0].isdigit():
        text = f"{fallback}_{text}"
    return text[:64]


def sanitize_table_name(name: str, fallback: str = "import_data") -> str:
    text = sanitize_identifier(name, fallback=fallback)
    if not _IDENTIFIER_RE.match(text):
        text = fallback
    return text


def ensure_import_db(db_id: str) -> Path:
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = _import_db_path(db_id)
    if not path.exists():
        conn = sqlite3.connect(str(path))
        conn.close()
    return path


def clear_import_db(db_id: str) -> None:
    path = _import_db_path(db_id)
    if path.exists():
        path.unlink()


def get_import_db_size(db_id: str) -> int:
    path = _import_db_path(db_id)
    return path.stat().st_size if path.exists() else 0


def attach_import_db(conn: sqlite3.Connection, db_id: str) -> bool:
    path = _import_db_path(db_id)
    if not path.exists():
        return False
    conn.execute("ATTACH DATABASE ? AS imported", (str(path),))
    return True


def list_imported_tables(db_id: str) -> List[Dict[str, Any]]:
    path = _import_db_path(db_id)
    if not path.exists():
        return []

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        tables = []
        for row in cur.fetchall():
            name = row["name"]
            safe = name.replace("'", "''")
            cur.execute(f"PRAGMA table_info('{safe}')")
            columns = [
                {
                    "cid": col[0],
                    "name": col[1],
                    "type": col[2],
                    "notnull": bool(col[3]),
                    "default": col[4],
                    "pk": bool(col[5]),
                }
                for col in cur.fetchall()
            ]
            cur.execute(f"SELECT COUNT(*) FROM '{safe}'")
            row_count = cur.fetchone()[0]
            tables.append({
                "name": name,
                "type": "table",
                "sql": row["sql"] or "",
                "temporary": True,
                "schema": IMPORT_SCHEMA,
                "columns": columns,
                "row_count": row_count,
            })
        return tables
    finally:
        conn.close()


def drop_imported_table(db_id: str, table_name: str) -> bool:
    if not _IDENTIFIER_RE.match(table_name):
        raise ValueError("无效的表名")
    path = _import_db_path(db_id)
    if not path.exists():
        return False

    conn = sqlite3.connect(str(path))
    try:
        safe = table_name.replace('"', '""')
        conn.execute(f'DROP TABLE IF EXISTS "{safe}"')
        conn.commit()
        return True
    finally:
        conn.close()


def import_dataframe(db_id: str, table_name: str, df: pd.DataFrame, *, is_temp: bool = False) -> Dict[str, Any]:
    if df.empty and len(df.columns) == 0:
        raise ValueError("文件无有效数据")

    table_name = sanitize_table_name(table_name)
    df = df.copy()
    df.columns = [sanitize_identifier(col, fallback=f"col_{i}") for i, col in enumerate(df.columns)]

    path = ensure_import_db(db_id)
    conn = sqlite3.connect(str(path))
    try:
        df.to_sql(table_name, conn, index=False, if_exists="replace")
        conn.commit()
    finally:
        conn.close()

    schema = "main" if is_temp else IMPORT_SCHEMA
    qualified_name = table_name if is_temp else f"{IMPORT_SCHEMA}.{table_name}"

    return {
        "table_name": table_name,
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": list(df.columns),
        "schema": schema,
        "qualified_name": qualified_name,
    }


def read_csv_file(path: Path, encoding: Optional[str] = None) -> pd.DataFrame:
    if encoding:
        return pd.read_csv(path, encoding=encoding)
    for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030", "latin1"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("无法识别 CSV 编码，请使用 UTF-8 或 GBK")


def read_excel_file(path: Path, sheet_name: Optional[str] = None) -> pd.DataFrame:
    kwargs: Dict[str, Any] = {"engine": "openpyxl"}
    if sheet_name:
        kwargs["sheet_name"] = sheet_name
    return pd.read_excel(path, **kwargs)


def table_name_from_filename(filename: str) -> str:
    stem = Path(filename).stem
    return sanitize_table_name(stem, fallback="import_data")
