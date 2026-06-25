# -*- coding: utf-8 -*-
"""Markdown 转 PDF API。"""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from modules.markdown_pdf.service import markdown_to_pdf

router = APIRouter(prefix="/api/tools/markdown-pdf", tags=["markdown-pdf"])


class MarkdownPdfRequest(BaseModel):
    markdown: str = Field(description="Markdown 文本")
    title: str = Field(default="Document", description="PDF 文档标题")
    filename: str = Field(default="document.pdf", description="下载文件名")


@router.post("/convert")
def convert_json(body: MarkdownPdfRequest):
    try:
        pdf_bytes = markdown_to_pdf(body.markdown, title=body.title)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF 生成失败: {exc}")

    filename = body.filename if body.filename.endswith(".pdf") else f"{body.filename}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/convert-file")
async def convert_file(
    file: UploadFile = File(...),
    title: str = Form("Document"),
    filename: str = Form("document.pdf"),
):
    content = (await file.read()).decode("utf-8")
    try:
        pdf_bytes = markdown_to_pdf(content, title=title or "Document")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF 生成失败: {exc}")

    out_name = filename if filename.endswith(".pdf") else f"{filename}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{out_name}"'},
    )
