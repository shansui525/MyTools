# -*- coding: utf-8 -*-
"""OpenAI 兼容大模型调用。"""

import json
import urllib.error
import urllib.request
from typing import List, Dict

_TIMEOUT = 120


def chat_completion(
    messages: List[Dict[str, str]],
    api_base: str,
    api_key: str,
    model: str,
    temperature: float = 0.7,
) -> str:
    """调用 Chat Completions API，返回 assistant 文本。"""
    if not api_key:
        raise ValueError("未配置大模型 API Key，请在设置中填写或设置环境变量 MYTOOLS_LLM_API_KEY")

    url = f"{api_base.rstrip('/')}/chat/completions"
    payload = json.dumps(
        {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        },
        ensure_ascii=False,
    ).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(detail)
            msg = err_json.get("error", {}).get("message") or detail
        except json.JSONDecodeError:
            msg = detail or f"HTTP {exc.code}"
        raise ValueError(f"大模型请求失败：{msg}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"无法连接大模型服务：{exc.reason}") from exc
    except TimeoutError:
        raise ValueError(f"大模型请求超时（{_TIMEOUT}秒）") from None

    choices = body.get("choices") or []
    if not choices:
        raise ValueError("大模型未返回有效内容")
    content = choices[0].get("message", {}).get("content", "").strip()
    if not content:
        raise ValueError("大模型返回内容为空")
    return content
