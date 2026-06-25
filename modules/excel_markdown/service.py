# -*- coding: utf-8 -*-
"""Excel 转 Markdown（极致压缩）。"""

import logging
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Union

import pandas as pd

from modules.excel_io import ExcelIOError, open_excel_file

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".xlsm", ".xls"}


class ExcelMarkdownError(Exception):
    pass


def _cell_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    text = str(value).strip()
    if not text:
        return ""
    text = " ".join(text.split())
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def _sep_cell() -> str:
    return "--"


def _row(cells: List[str]) -> str:
    return "|" + "|".join(cells) + "|"


def _trim_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    while len(df.index) > 0:
        row = df.iloc[-1]
        if all(_cell_str(v) == "" for v in row):
            df = df.iloc[:-1]
        else:
            break
    return df


def _sheet_to_markdown(df: pd.DataFrame, with_header: bool = True) -> str:
    df = _trim_dataframe(df)
    if df.empty:
        return ""

    lines: List[str] = []
    col_count = len(df.columns)
    if col_count == 0:
        return ""

    if with_header:
        headers = [_cell_str(c) for c in df.columns]
        if any(headers):
            lines.append(_row(headers))
            lines.append(_row([_sep_cell()] * col_count))
            data_df = df
        else:
            data_df = df
    else:
        data_df = df

    for _, row in data_df.iterrows():
        cells = [_cell_str(v) for v in row.tolist()]
        if len(cells) < col_count:
            cells.extend([""] * (col_count - len(cells)))
        elif len(cells) > col_count:
            cells = cells[:col_count]
        if any(cells):
            lines.append(_row(cells))

    return "\n".join(lines)


def _open_excel_file(content: bytes, filename: str) -> pd.ExcelFile:
    try:
        return open_excel_file(content, filename)
    except ExcelIOError as exc:
        raise ExcelMarkdownError(str(exc)) from exc


def excel_to_markdown(
    source: Union[str, Path, bytes],
    sheet: str = "all",
    with_header: bool = True,
    include_sheet_title: bool = True,
    filename: str = "",
) -> Dict[str, Any]:
    if isinstance(source, bytes):
        excel = _open_excel_file(source, filename)
    else:
        path = Path(source)
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise ExcelMarkdownError(f"不支持的格式: {path.suffix}")
        logger.info("从路径读取: %s", path)
        excel = pd.ExcelFile(path, engine="openpyxl" if path.suffix.lower() != ".xls" else "xlrd")

    sheet_names = excel.sheet_names
    if not sheet_names:
        raise ExcelMarkdownError("Excel 中没有工作表")

    if sheet == "all":
        targets = sheet_names
    elif sheet in sheet_names:
        targets = [sheet]
    else:
        try:
            idx = int(sheet)
            targets = [sheet_names[idx]]
        except (ValueError, IndexError):
            raise ExcelMarkdownError(f"工作表不存在: {sheet}")

    logger.info("转换目标 sheet=%r -> %s", sheet, targets)

    parts: List[str] = []
    stats = {"sheets": [], "rows": 0, "chars": 0}

    for name in targets:
        logger.info("读取工作表: %s", name)
        try:
            df = pd.read_excel(excel, sheet_name=name, header=0 if with_header else None, dtype=object)
        except Exception as exc:
            logger.exception("读取 sheet 失败: %s", name)
            raise ExcelMarkdownError(f"读取工作表「{name}」失败: {exc}") from exc

        logger.info("sheet=%s shape=%s columns=%s", name, df.shape, list(df.columns)[:10])

        if not with_header and len(df.columns) and isinstance(df.columns[0], int):
            df.columns = ["c{}".format(i + 1) for i in range(len(df.columns))]

        body = _sheet_to_markdown(df, with_header=with_header)
        if not body:
            logger.info("sheet=%s 无有效数据，跳过", name)
            continue

        if include_sheet_title and len(targets) > 1:
            title = _cell_str(name).replace("#", "").strip()
            block = "## {}\n\n{}".format(title, body)
        else:
            block = body

        row_count = body.count("\n") + 1
        stats["sheets"].append({"name": name, "rows": row_count, "chars": len(block)})
        stats["rows"] += row_count
        parts.append(block)
        logger.info("sheet=%s 输出行数=%d 字符=%d", name, row_count, len(block))

    if not parts:
        raise ExcelMarkdownError("未读取到有效数据（所有工作表为空）")

    markdown = "\n\n".join(parts)
    stats["chars"] = len(markdown)
    logger.info("转换完成: sheets=%d total_chars=%d", len(parts), len(markdown))
    return {
        "markdown": markdown,
        "sheet_names": sheet_names,
        "stats": stats,
    }
