# -*- coding: utf-8 -*-
"""加解密实验室 API。"""

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from modules.crypto_lab.operations import CryptoLabError
from modules.crypto_lab.service import generate_keys, get_catalog, process

router = APIRouter(prefix="/api/tools/crypto-lab", tags=["crypto-lab"])


class CryptoProcessRequest(BaseModel):
    algorithm_id: str
    action: str
    text: str = ""
    key: str = ""
    iv: str = ""
    aad: str = ""
    public_key: str = ""
    private_key: str = ""
    input_format: Literal["text", "hex", "base64"] = "text"
    output_format: Optional[str] = None


@router.get("/catalog")
def catalog():
    return get_catalog()


@router.post("/process")
def process_crypto(body: CryptoProcessRequest):
    try:
        return process(
            algorithm_id=body.algorithm_id,
            action=body.action,
            text=body.text,
            key=body.key,
            iv=body.iv,
            aad=body.aad,
            public_key=body.public_key,
            private_key=body.private_key,
            input_format=body.input_format,
            output_format=body.output_format or "",
        )
    except CryptoLabError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/generate-keys")
def gen_keys(algorithm_id: str = Query(...)):
    try:
        return generate_keys(algorithm_id)
    except CryptoLabError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
