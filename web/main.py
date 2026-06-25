# -*- coding: utf-8 -*-
"""
MyTools 应用入口。

挂载静态前端、注册 API 路由，可独立运行。
"""

import sys
from contextlib import asynccontextmanager
from logging.config import dictConfig
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from web.log_config import LOGGING_CONFIG

dictConfig(LOGGING_CONFIG)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from modules.registry import get_app_info, get_tool_by_id
from modules.task_scheduler.engine import start_scheduler, stop_scheduler
from web.config import HOST, PORT
from web.routers import excel_compare_api, excel_markdown_api, json_formatter_api, password_manager_api, text_diff_api, curl_converter_api, markdown_pdf_api, sqlite_browser_api, sql_formatter_api, calendar_api, crypto_lab_api, task_scheduler_api, tools_api, word_markdown_api


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="MyTools",
    version="1.0.0",
    description="我的工具箱 - 多功能在线工具集合",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Diff-Count", "X-Compare-Mode"],
)

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(tools_api.router)
app.include_router(excel_compare_api.router)
app.include_router(excel_markdown_api.router)
app.include_router(word_markdown_api.router)
app.include_router(password_manager_api.router)
app.include_router(json_formatter_api.router)
app.include_router(text_diff_api.router)
app.include_router(curl_converter_api.router)
app.include_router(markdown_pdf_api.router)
app.include_router(sqlite_browser_api.router)
app.include_router(sql_formatter_api.router)
app.include_router(calendar_api.router)
app.include_router(crypto_lab_api.router)
app.include_router(task_scheduler_api.router)


@app.get("/")
async def index():
    return FileResponse(static_dir / "index.html")


@app.get("/tools/{tool_id}")
async def tool_page(tool_id: str):
    tool = get_tool_by_id(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")

    page = static_dir / "tools" / f"{tool_id}.html"
    if not page.exists():
        raise HTTPException(status_code=404, detail="工具页面不存在")
    return FileResponse(page)


@app.get("/health")
async def health():
    app_info = get_app_info()
    return {
        "status": "ok",
        "app": app_info.get("title_en", "MyTools"),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "web.main:app",
        host=HOST,
        port=PORT,
        reload=True,
        log_config=LOGGING_CONFIG,
    )
