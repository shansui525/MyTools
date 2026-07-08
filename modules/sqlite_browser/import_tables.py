# -*- coding: utf-8 -*-
"""CSV / Excel 导入为 SQLite 临时表。"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from modules.sqlite_browser.sessions import get_session, is_session_db

IMPORT_SUFFIXES = {".csv", ".xlsx", ".xls"}
TABLE_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def sanitize_table_name(name: str) -> str:
    raw = (name or "").strip()
    if not raw:
        raise ValueError("表名不能为空")
    cleaned = re.sub(r"[^\w]", "_", raw)
    if cleaned and cleaned[0].isdigit():
        cleaned = f"t_{cleaned}"
    if not cleaned or not TABLE_NAME_RE.match(cleaned):
        raise ValueError("表名仅允许字母、数字、下划线，且不能以数字开头")
    return cleaned


def default_table_name(filename: str) -> str:
    stem = Path(filename).stem or "imported"
    return sanitize_table_name(stem)


def _sanitize_column(name: str) -> str:
    col = re.sub(r"[^\w]", "_", str(name).strip()) or "col"
    if col[0].isdigit():
        col = f"c_{col}"
    return col


def _read_file(path: Path, filename: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        for encoding in ("utf-8", "utf-8-sig", "gbk", "gb18030", "latin-1"):
            try:
                return pd.read_csv(path, encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError("无法识别 CSV 编码，请使用 UTF-8 或 GBK")
    if suffix == ".xlsx":
        return pd.read_excel(path, sheet_name=sheet_name or 0, engine="openpyxl")
    if suffix == ".xls":
        return pd.read_excel(path, sheet_name=sheet_name or 0, engine="xlrd")
    raise ValueError("不支持的文件格式，请上传 .csv / .xlsx / .xls")


def _write_dataframe(conn, table_name: str, df: pd.DataFrame, memory_primary: bool) -> None:
    df = df.copy()
    df.columns = [_sanitize_column(c) for c in df.columns]
    # 重复列名加后缀
    seen: Dict[str, int] = {}
    unique_cols: List[str] = []
    for col in df.columns:
        if col not in seen:
            seen[col] = 0
            unique_cols.append(col)
        else:
            seen[col] += 1
            unique_cols.append(f"{col}_{seen[col]}")
    df.columns = unique_cols

    if memory_primary:
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        return

    conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
    cols_sql = ", ".join(f'"{c}" TEXT' for c in df.columns)
    conn.execute(f'CREATE TEMP TABLE "{table_name}" ({cols_sql})')
    if df.empty:
        return

    col_list = ", ".join(f'"{c}"' for c in df.columns)
    placeholders = ", ".join("?" * len(df.columns))
    rows = df.astype(object).where(pd.notnull(df), None).values.tolist()
    conn.executemany(
        f'INSERT INTO "{table_name}" ({col_list}) VALUES ({placeholders})',
        rows,
    )


def import_file(
    db_id: str,
    file_path: Path,
    filename: str,
    table_name: Optional[str] = None,
    sheet_name: Optional[str] = None,
) -> Dict[str, Any]:
    suffix = Path(filename).suffix.lower()
    if suffix not in IMPORT_SUFFIXES:
        raise ValueError("不支持的文件格式，请上传 .csv / .xlsx / .xls")

    df = _read_file(file_path, filename, sheet_name=sheet_name)
    if df.empty and len(df.columns) == 0:
        raise ValueError("文件无有效数据")

    safe_name = sanitize_table_name(table_name) if table_name else default_table_name(filename)
    conn = get_session(db_id)
    _write_dataframe(conn, safe_name, df, memory_primary=is_session_db(db_id))

    return {
        "table_name": safe_name,
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": list(df.columns),
        "temporary": not is_session_db(db_id),
        "message": f"已导入 {len(df)} 行到{'临时' if not is_session_db(db_id) else ''}表「{safe_name}」",
    }


def list_imported_tables(db_id: str) -> List[Dict[str, Any]]:
    conn = get_session(db_id)
    memory_primary = is_session_db(db_id)
    if memory_primary:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    else:
        cur = conn.execute(
            "SELECT name FROM sqlite_temp_master WHERE type='table' ORDER BY name"
        )
    return [{"name": row[0], "temporary": True, "source": "import"} for row in cur.fetchall()]


def drop_imported_table(db_id: str, table_name: str) -> None:
    safe = sanitize_table_name(table_name)
    conn = get_session(db_id)
    conn.execute(f'DROP TABLE IF EXISTS "{safe}"')
