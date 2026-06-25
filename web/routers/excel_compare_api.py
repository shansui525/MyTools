# -*- coding: utf-8 -*-
"""Excel 文件对比 API。"""

import asyncio
import logging
import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from modules.excel_compare.service import CompareMode, compare_excel, get_sheet_names
from modules.excel_io import ExcelIOError, normalize_excel_bytes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tools/excel-compare", tags=["excel-compare"])

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".xlsm"}


def _validate_excel(filename: str) -> None:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="不支持的文件格式: {}，请上传 .xlsx / .xls / .xlsm 文件".format(ext),
        )


def _run_compare(
    path_a: Path,
    path_b: Path,
    result_path: Path,
    compare_mode: CompareMode,
    keys: str,
    sheet_a: str = None,
    sheet_b: str = None,
) -> dict:
    return compare_excel(
        path_a,
        path_b,
        result_path,
        mode=compare_mode,
        keys=keys,
        sheet_a=sheet_a or None,
        sheet_b=sheet_b or None,
    )


@router.post("/sheets")
async def list_sheets(file: UploadFile = File(..., description="Excel 文件")):
    """获取 Excel 文件中的工作表名称列表。"""
    filename = file.filename or "file.xlsx"
    _validate_excel(filename)

    work_dir = Path(tempfile.gettempdir()) / "mytools" / uuid.uuid4().hex
    work_dir.mkdir(parents=True, exist_ok=True)
    path = work_dir / "upload.xlsx"

    try:
        raw = await file.read()
        path.write_bytes(normalize_excel_bytes(raw, filename))
        names = await asyncio.to_thread(get_sheet_names, path)
        logger.info("读取工作表列表: filename=%r count=%d", filename, len(names))
        return {"sheet_names": names}
    except ExcelIOError as e:
        logger.warning("Excel 预处理失败: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("读取工作表列表失败: filename=%r", filename)
        raise HTTPException(status_code=500, detail="读取工作表失败: {}".format(e))
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


@router.post("/compare")
async def compare_files(
    file_a: UploadFile = File(..., description="第一个 Excel 文件"),
    file_b: UploadFile = File(..., description="第二个 Excel 文件"),
    mode: str = Form("direct", description="对比模式: direct 或 key"),
    keys: str = Form("", description="主键列名，多个用逗号分隔"),
    sheet_a: str = Form("", description="文件 A 的工作表名称，空则使用第一个"),
    sheet_b: str = Form("", description="文件 B 的工作表名称，空则使用第一个"),
):
    filename_a = file_a.filename or "file_a.xlsx"
    filename_b = file_b.filename or "file_b.xlsx"
    logger.info(
        "收到对比请求: file_a=%r file_b=%r mode=%r keys=%r sheet_a=%r sheet_b=%r",
        filename_a,
        filename_b,
        mode,
        keys,
        sheet_a,
        sheet_b,
    )

    _validate_excel(filename_a)
    _validate_excel(filename_b)

    try:
        compare_mode = CompareMode(mode)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的对比模式: {}".format(mode))

    if compare_mode == CompareMode.KEY and not keys.strip():
        raise HTTPException(status_code=400, detail="主键对比模式需要指定主键列名")

    work_dir = Path(tempfile.gettempdir()) / "mytools" / uuid.uuid4().hex
    work_dir.mkdir(parents=True, exist_ok=True)

    path_a = work_dir / "a.xlsx"
    path_b = work_dir / "b.xlsx"
    result_path = work_dir / "compare_result.xlsx"

    try:
        raw_a = await file_a.read()
        raw_b = await file_b.read()
        logger.info("文件已读取: a=%d bytes b=%d bytes", len(raw_a), len(raw_b))

        path_a.write_bytes(normalize_excel_bytes(raw_a, filename_a))
        path_b.write_bytes(normalize_excel_bytes(raw_b, filename_b))

        result = await asyncio.to_thread(
            _run_compare,
            path_a,
            path_b,
            result_path,
            compare_mode,
            keys,
            sheet_a.strip() or None,
            sheet_b.strip() or None,
        )
        result_bytes = result_path.read_bytes()
        logger.info(
            "对比完成: mode=%s diff_count=%d result_bytes=%d",
            result.get("mode"),
            result.get("diff_count", 0),
            len(result_bytes),
        )

        return Response(
            content=result_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": 'attachment; filename="compare_result.xlsx"',
                "X-Diff-Count": str(result["diff_count"]),
                "X-Compare-Mode": result["mode"],
            },
        )
    except ExcelIOError as e:
        logger.warning("Excel 预处理失败: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        logger.warning("对比参数/数据错误: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("对比未预期异常: mode=%r keys=%r", mode, keys)
        raise HTTPException(status_code=500, detail="对比过程中发生错误: {}".format(e))
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
