# -*- coding: utf-8 -*-
"""SQL 格式化 API。"""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from modules.sql_formatter.service import SqlFormatError, process_sql

router = APIRouter(prefix="/api/tools/sql-formatter", tags=["sql-formatter"])


class SqlFormatRequest(BaseModel):
    text: str = Field(description="待格式化的 SQL 文本")
    indent: int = Field(default=2, ge=2, le=4)
    keyword_case: Literal["upper", "lower", "preserve"] = "upper"
    dialect: Literal["standard", "hive", "spark"] = "standard"


class SqlLintRequest(BaseModel):
    text: str = Field(description="待检查的 SQL 文本")
    dialect: Literal["standard", "hive", "spark"] = "standard"


@router.post("/lint")
def lint_sql_api(body: SqlLintRequest):
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="请输入 SQL 内容")
    try:
        from modules.sql_formatter.linter import lint_sql

        issues = lint_sql(text, body.dialect)
        return {
            "issues": issues,
            "issue_summary": {
                "errors": sum(1 for item in issues if item["level"] == "error"),
                "warnings": sum(1 for item in issues if item["level"] == "warning"),
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/process")
def format_sql_api(body: SqlFormatRequest):
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="请输入 SQL 内容")

    try:
        return process_sql(
            text,
            indent=body.indent,
            keyword_case=body.keyword_case,
            dialect=body.dialect,
        )
    except SqlFormatError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
