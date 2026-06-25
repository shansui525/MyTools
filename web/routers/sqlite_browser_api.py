# -*- coding: utf-8 -*-
"""SQLite 浏览器 API。"""

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from modules.sqlite_browser.history import add_record, clear_history, list_history
from modules.sqlite_browser.repository import delete_database, get_database, list_databases, register_local_path, register_upload
from modules.sqlite_browser.service import execute_query, get_metadata

router = APIRouter(prefix="/api/tools/sqlite-browser", tags=["sqlite-browser"])


class QueryRequest(BaseModel):
    sql: str = Field(min_length=1)
    row_limit: int = Field(default=1000, ge=1, le=10000)


class LinkRequest(BaseModel):
    path: str = Field(min_length=1, description="本地 SQLite 数据库文件绝对或相对路径")


def _require_db(db_id: str) -> dict:
    info = get_database(db_id)
    if not info:
        raise HTTPException(status_code=404, detail="数据库不存在")
    return info


@router.get("/databases")
def get_databases():
    return {"databases": list_databases()}


@router.post("/link")
def link_local_db(body: LinkRequest):
    try:
        info = register_local_path(body.path)
        return info
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="链接失败: {}".format(exc))


@router.post("/upload")
async def upload_db(file: UploadFile = File(...)):
    filename = file.filename or "database.db"
    if not filename.lower().endswith((".db", ".sqlite", ".sqlite3", ".db3")):
        raise HTTPException(status_code=400, detail="请上传 .db / .sqlite / .sqlite3 文件")

    suffix = Path(filename).suffix or ".db"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="文件为空")
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        info = register_upload(tmp_path, filename)
        return info
    except Exception as exc:
        raise HTTPException(status_code=500, detail="上传失败: {}".format(exc))
    finally:
        tmp_path.unlink(missing_ok=True)


@router.delete("/databases/{db_id}")
def remove_db(db_id: str):
    info = get_database(db_id)
    if not info:
        raise HTTPException(status_code=404, detail="数据库不存在")
    if not delete_database(db_id):
        raise HTTPException(status_code=404, detail="数据库不存在")
    if info.get("source_type") == "local":
        return {"message": "已移除本地连接"}
    return {"message": "已删除"}


@router.get("/databases/{db_id}/metadata")
def metadata(db_id: str):
    _require_db(db_id)
    try:
        return get_metadata(db_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/databases/{db_id}/query")
def run_query(db_id: str, body: QueryRequest):
    db_info = _require_db(db_id)
    try:
        result = execute_query(db_id, body.sql, row_limit=body.row_limit)
        record = add_record(
            db_id=db_id,
            sql=body.sql,
            success=True,
            duration_ms=result["duration_ms"],
            row_count=result.get("row_count", 0),
            affected_rows=result.get("affected_rows", 0),
            db_filename=db_info.get("filename", ""),
        )
        result["history_id"] = record["id"]
        return result
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        add_record(
            db_id=db_id,
            sql=body.sql,
            success=False,
            duration_ms=0,
            error=str(exc),
            db_filename=db_info.get("filename", ""),
        )
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/history")
def get_history(db_id: Optional[str] = None, limit: int = 50):
    return {"records": list_history(db_id=db_id, limit=limit)}


@router.delete("/history")
def remove_history(db_id: Optional[str] = None):
    count = clear_history(db_id=db_id)
    return {"message": "已清除 {} 条历史".format(count), "removed": count}
