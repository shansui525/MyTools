# -*- coding: utf-8 -*-
"""Excel 转 Markdown API。"""

import logging
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from modules.excel_markdown.service import ALLOWED_EXTENSIONS, ExcelMarkdownError, excel_to_markdown

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tools/excel-markdown", tags=["excel-markdown"])


def _validate_excel(filename: str) -> None:
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS and ext != ".zip":
        raise HTTPException(
            status_code=400,
            detail="不支持的文件格式: {}，请上传 .xlsx / .xls / .xlsm / .xls".format(ext),
        )


@router.post("/convert")
async def convert_excel(
    file: UploadFile = File(..., description="Excel 文件"),
    sheet: str = Form("all", description="工作表：all 或名称/索引"),
    with_header: bool = Form(True, description="首行作为表头"),
    include_sheet_title: bool = Form(True, description="多 sheet 时添加标题"),
):
    filename = file.filename or ""
    logger.info(
        "收到转换请求: filename=%r sheet=%r with_header=%s include_sheet_title=%s content_type=%r",
        filename,
        sheet,
        with_header,
        include_sheet_title,
        file.content_type,
    )
    _validate_excel(filename)
    try:
        content = await file.read()
        logger.info("文件已读取: size=%d bytes", len(content))
        result = excel_to_markdown(
            content,
            sheet=sheet,
            with_header=with_header,
            include_sheet_title=include_sheet_title,
            filename=filename,
        )
        logger.info(
            "转换成功: filename=%r sheets=%d chars=%d",
            filename,
            len(result.get("sheet_names") or []),
            result.get("stats", {}).get("chars", 0),
        )
        return result
    except ExcelMarkdownError as exc:
        logger.warning("转换业务错误: filename=%r error=%s", filename, exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("转换未预期异常: filename=%r", filename)
        raise HTTPException(status_code=500, detail="转换失败: {}".format(exc))
