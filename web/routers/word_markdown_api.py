# -*- coding: utf-8 -*-
"""Word 转 Markdown API。"""

import logging
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from modules.word_markdown.service import ALLOWED_EXTENSIONS, WordMarkdownError, word_to_markdown

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tools/word-markdown", tags=["word-markdown"])


def _validate_word(filename: str) -> None:
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="不支持的文件格式: {}，请上传 .docx 文件".format(ext or "(无后缀)"),
        )


@router.post("/convert")
async def convert_word(
    file: UploadFile = File(..., description="Word 文件"),
    ignore_images: bool = Form(True, description="忽略文档内嵌图片"),
):
    filename = file.filename or ""
    logger.info(
        "收到转换请求: filename=%r ignore_images=%s content_type=%r",
        filename,
        ignore_images,
        file.content_type,
    )
    _validate_word(filename)
    try:
        content = await file.read()
        logger.info("文件已读取: size=%d bytes", len(content))
        result = word_to_markdown(content, ignore_images=ignore_images, filename=filename)
        logger.info(
            "转换成功: filename=%r chars=%d warnings=%d",
            filename,
            result.get("stats", {}).get("chars", 0),
            result.get("stats", {}).get("warnings", 0),
        )
        return result
    except WordMarkdownError as exc:
        logger.warning("转换业务错误: filename=%r error=%s", filename, exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("转换未预期异常: filename=%r", filename)
        raise HTTPException(status_code=500, detail="转换失败: {}".format(exc))
