# -*- coding: utf-8 -*-
"""Excel 文件读取预处理（ZIP 内嵌 xlsx、引擎选择等）。"""

import logging
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class ExcelIOError(Exception):
    pass


def peek_magic(content: bytes) -> str:
    if len(content) < 4:
        return "empty"
    if content[:2] == b"PK":
        return "PK(zip/xlsx)"
    if content[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return "OLE2(xls)"
    return content[:4].hex()


def is_xlsx_zip(content: bytes) -> bool:
    if content[:2] != b"PK":
        return False
    try:
        with zipfile.ZipFile(BytesIO(content)) as zf:
            for name in zf.namelist():
                norm = name.replace("\\", "/").lstrip("./")
                lower = norm.lower()
                if lower == "[content_types].xml" or lower.endswith("/xl/workbook.xml") or lower == "xl/workbook.xml":
                    return True
            return False
    except zipfile.BadZipFile:
        return False


def log_zip_contents(content: bytes) -> None:
    try:
        with zipfile.ZipFile(BytesIO(content)) as zf:
            names = zf.namelist()
            preview = names[:30]
            logger.info("ZIP 条目 (%d): %s", len(names), preview)
            if len(names) > 30:
                logger.info("ZIP 条目 ... 还有 %d 项未列出", len(names) - 30)
    except Exception as exc:
        logger.warning("无法列出 ZIP 内容: %s", exc)


def extract_xlsx_from_zip(content: bytes) -> Optional[bytes]:
    try:
        zf = zipfile.ZipFile(BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise ExcelIOError("ZIP 文件已损坏或不是有效的压缩包") from exc
    with zf:
        candidates = [
            n
            for n in zf.namelist()
            if n.lower().endswith((".xlsx", ".xlsm"))
            and not n.startswith("__MACOSX/")
            and not n.startswith(".")
        ]
        if candidates:
            inner_name = candidates[0]
            logger.info("从 ZIP 中按后缀提取 Excel: %s", inner_name)
            return zf.read(inner_name)

        for name in zf.namelist():
            if name.startswith("__MACOSX/") or name.endswith("/"):
                continue
            try:
                inner = zf.read(name)
            except Exception:
                continue
            if len(inner) >= 2 and inner[:2] == b"PK" and is_xlsx_zip(inner):
                logger.info("从 ZIP 内嵌二进制识别 xlsx: %s size=%d", name, len(inner))
                return inner

        return None


def normalize_excel_bytes(content: bytes, filename: str = "") -> bytes:
    """将上传内容规范化为可直接用 openpyxl/pandas 打开的 Excel 二进制。"""
    ext = Path(filename or "").suffix.lower()
    logger.info(
        "规范化 Excel: filename=%r ext=%s size=%d magic=%s",
        filename,
        ext or "(无后缀)",
        len(content),
        peek_magic(content),
    )

    if len(content) < 4:
        raise ExcelIOError("文件过小或为空")

    if content[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" or ext == ".xls":
        return content

    data = content
    if content[:2] == b"PK":
        if is_xlsx_zip(content):
            logger.info("识别为标准 xlsx/xlsm (OOXML ZIP)")
            return content

        logger.warning("PK 头但非标准 OOXML（可能为 ZIP 包或损坏的 xlsx）")
        log_zip_contents(content)
        inner = extract_xlsx_from_zip(content)
        if inner:
            logger.info("已提取内嵌 Excel: outer=%d inner=%d", len(content), len(inner))
            return inner
        if ext == ".zip":
            raise ExcelIOError("ZIP 压缩包中未找到 .xlsx/.xlsm，请先解压或上传 Excel 本体")

    return data


def open_excel_file(content: bytes, filename: str = "") -> pd.ExcelFile:
    ext = Path(filename or "").suffix.lower()
    data = normalize_excel_bytes(content, filename)
    engine = "xlrd" if ext == ".xls" else "openpyxl"

    logger.info("使用引擎: %s", engine)
    try:
        excel = pd.ExcelFile(BytesIO(data), engine=engine)
    except zipfile.BadZipFile as exc:
        logger.exception("ZIP 结构损坏")
        raise ExcelIOError("Excel 文件已损坏（ZIP 结构无效），请用 Excel 重新保存后再试") from exc
    except Exception as exc:
        logger.exception("ExcelFile 打开失败 engine=%s", engine)
        msg = str(exc)
        if "io.excel.zip.reader" in msg or "Content_Types" in msg:
            raise ExcelIOError(
                "无法识别为有效 Excel：文件可能是 ZIP 压缩包、损坏的 xlsx，或后缀与实际格式不符。"
                "请用 Excel/WPS 打开后另存为 .xlsx，或上传解压后的 Excel 本体。"
            ) from exc
        raise ExcelIOError("无法打开 Excel（{}）: {}".format(engine, msg)) from exc

    logger.info("工作表列表: %s", excel.sheet_names)
    return excel
