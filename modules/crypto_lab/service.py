# -*- coding: utf-8 -*-
"""加解密实验室服务。"""

from typing import Any, Dict, Optional

from modules.crypto_lab.catalog import get_algorithm, list_catalog
from modules.crypto_lab.codegen import generate_code
from modules.crypto_lab.operations import (
    CryptoLabError,
    HANDLERS,
    generate_rsa_keypair,
    generate_sm2_keypair,
    _HAS_GMSSL,
)


def get_catalog() -> dict:
    catalog = list_catalog()
    catalog["gmssl_available"] = _HAS_GMSSL
    return catalog


def process(
    algorithm_id: str,
    action: str,
    text: str,
    key: str = "",
    iv: str = "",
    aad: str = "",
    public_key: str = "",
    private_key: str = "",
    input_format: str = "text",
    output_format: str = "",
) -> Dict[str, Any]:
    meta = get_algorithm(algorithm_id)
    if not meta:
        raise CryptoLabError(f"未知算法: {algorithm_id}")

    actions = meta.get("actions", [])
    if action not in actions:
        raise CryptoLabError(f"算法 {meta['name']} 不支持操作: {action}")

    if not text and action != "hash":
        raise CryptoLabError("请输入内容")

    out_fmt = output_format or meta.get("output_format", "hex")
    handler = HANDLERS.get(algorithm_id)
    if not handler:
        raise CryptoLabError("算法处理器未实现")

    params = {
        "action": action,
        "text": text,
        "key": key,
        "iv": iv,
        "aad": aad,
        "public_key": public_key,
        "private_key": private_key,
        "input_format": input_format,
        "output_format": out_fmt,
    }

    try:
        result = handler(**params)
    except CryptoLabError:
        raise
    except Exception as exc:
        raise CryptoLabError(str(exc)) from exc

    codes = generate_code(algorithm_id, action, params)
    return {
        "algorithm_id": algorithm_id,
        "action": action,
        "result": result,
        "output_format": out_fmt,
        "python_code": codes["python"],
        "javascript_code": codes["javascript"],
        "meta": meta,
    }


def generate_keys(algorithm_id: str) -> Dict[str, str]:
    if algorithm_id == "rsa-oaep":
        public_key, private_key = generate_rsa_keypair()
        return {"public_key": public_key, "private_key": private_key}
    if algorithm_id == "sm2":
        public_key, private_key = generate_sm2_keypair()
        return {"public_key": public_key, "private_key": private_key}
    raise CryptoLabError("该算法不支持在线生成密钥对")
