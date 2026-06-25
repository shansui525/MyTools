# -*- coding: utf-8 -*-
"""curl 转 Python requests API。"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from modules.curl_converter.service import CurlParseError, curl_to_requests

router = APIRouter(prefix="/api/tools/curl-converter", tags=["curl-converter"])


class CurlConvertRequest(BaseModel):
    curl: str = Field(description="curl 命令")
    include_response: bool = Field(default=True, description="是否包含响应打印代码")


@router.post("/convert")
def convert(body: CurlConvertRequest):
    if not body.curl.strip():
        raise HTTPException(status_code=400, detail="请输入 curl 命令")
    try:
        code = curl_to_requests(body.curl, include_response=body.include_response)
    except CurlParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"code": code}
