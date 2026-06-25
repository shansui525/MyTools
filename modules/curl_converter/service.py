# -*- coding: utf-8 -*-
"""将 curl 命令转换为 Python requests 代码。"""

import json
import shlex
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


class CurlParseError(Exception):
    pass


def _normalize_curl(text: str) -> str:
    text = text.strip()
    if not text:
        raise CurlParseError("请输入 curl 命令")
    lines = text.splitlines()
    merged: List[str] = []
    buf = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.endswith("\\"):
            buf += line[:-1].strip() + " "
        else:
            buf += line
            merged.append(buf.strip())
            buf = ""
    if buf:
        merged.append(buf.strip())
    return " ".join(merged)


def _is_url(token: str) -> bool:
    return token.startswith("http://") or token.startswith("https://") or "://" in token


def _parse_header(value: str) -> Tuple[str, str]:
    if ":" in value:
        key, val = value.split(":", 1)
        return key.strip(), val.strip()
    return value.strip(), ""


def _parse_cookie_string(cookie_str: str) -> Dict[str, str]:
    cookies: Dict[str, str] = {}
    for part in cookie_str.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, v = part.split("=", 1)
        cookies[k.strip()] = v.strip()
    return cookies


def _merge_query(url: str, data: str) -> str:
    parsed = urlparse(url)
    existing = parse_qsl(parsed.query, keep_blank_values=True)
    extra = parse_qsl(data.lstrip("?"), keep_blank_values=True)
    query = urlencode(existing + extra)
    return urlunparse(parsed._replace(query=query))


def _try_parse_json(text: str) -> Optional[Any]:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def parse_curl(curl_command: str) -> Dict[str, Any]:
    normalized = _normalize_curl(curl_command)
    try:
        tokens = shlex.split(normalized)
    except ValueError as exc:
        raise CurlParseError(f"命令解析失败: {exc}") from exc

    if not tokens or tokens[0].lower() != "curl":
        raise CurlParseError("命令需以 curl 开头")

    method = "GET"
    url: Optional[str] = None
    headers: Dict[str, str] = {}
    cookies: Dict[str, str] = {}
    data: Optional[str] = None
    json_body: Optional[Any] = None
    form_data: Dict[str, str] = {}
    auth: Optional[Tuple[str, str]] = None
    verify = True
    allow_redirects = True
    timeout: Optional[float] = None
    proxy: Optional[str] = None
    use_get_query = False

    skip_next = False
    ignored_with_value = {
        "--compressed", "-s", "--silent", "-v", "--verbose", "-i", "--include",
        "--output", "-o", "--dump-header", "-D",
    }

    i = 1
    while i < len(tokens):
        tok = tokens[i]
        if skip_next:
            skip_next = False
            i += 1
            continue

        if tok in ("-X", "--request"):
            i += 1
            if i >= len(tokens):
                raise CurlParseError("缺少请求方法")
            method = tokens[i].upper()
        elif tok in ("-H", "--header"):
            i += 1
            if i >= len(tokens):
                raise CurlParseError("缺少 Header 值")
            key, val = _parse_header(tokens[i])
            headers[key] = val
        elif tok in ("-d", "--data", "--data-raw", "--data-binary", "--data-urlencode"):
            i += 1
            if i >= len(tokens):
                raise CurlParseError("缺少请求体数据")
            data = tokens[i] if data is None else data + "&" + tokens[i]
            if method == "GET":
                method = "POST"
        elif tok == "--json":
            i += 1
            if i >= len(tokens):
                raise CurlParseError("缺少 JSON 数据")
            json_body = _try_parse_json(tokens[i])
            if json_body is None:
                data = tokens[i]
            if method == "GET":
                method = "POST"
        elif tok in ("-u", "--user"):
            i += 1
            if i >= len(tokens):
                raise CurlParseError("缺少认证信息")
            cred = tokens[i]
            if ":" in cred:
                user, pwd = cred.split(":", 1)
            else:
                user, pwd = cred, ""
            auth = (user, pwd)
        elif tok in ("-b", "--cookie"):
            i += 1
            if i >= len(tokens):
                raise CurlParseError("缺少 Cookie 值")
            cookies.update(_parse_cookie_string(tokens[i]))
        elif tok in ("-F", "--form"):
            i += 1
            if i >= len(tokens):
                raise CurlParseError("缺少表单字段")
            if "=" in tokens[i]:
                k, v = tokens[i].split("=", 1)
                form_data[k] = v
            if method == "GET":
                method = "POST"
        elif tok in ("-G", "--get"):
            use_get_query = True
        elif tok in ("-k", "--insecure"):
            verify = False
        elif tok in ("-L", "--location"):
            allow_redirects = True
        elif tok in ("-I", "--head"):
            method = "HEAD"
        elif tok in ("-A", "--user-agent"):
            i += 1
            headers["User-Agent"] = tokens[i]
        elif tok in ("-e", "--referer"):
            i += 1
            headers["Referer"] = tokens[i]
        elif tok in ("-x", "--proxy"):
            i += 1
            proxy = tokens[i]
        elif tok == "--connect-timeout":
            i += 1
            timeout = float(tokens[i])
        elif tok.startswith("-"):
            if tok in ignored_with_value and i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                skip_next = True
        elif url is None and _is_url(tok):
            url = tok
        i += 1

    if url is None:
        raise CurlParseError("未找到请求 URL")

    content_type = headers.get("Content-Type", headers.get("content-type", ""))
    if json_body is None and data and "application/json" in content_type.lower():
        json_body = _try_parse_json(data)

    if use_get_query and data:
        url = _merge_query(url, data)
        data = None
        method = "GET"

    if json_body is None and data and method in ("POST", "PUT", "PATCH") and not form_data:
        maybe_json = _try_parse_json(data)
        if maybe_json is not None and not content_type:
            json_body = maybe_json
            data = None

    return {
        "method": method.lower(),
        "url": url,
        "headers": headers,
        "cookies": cookies,
        "data": data,
        "json_body": json_body,
        "form_data": form_data,
        "auth": auth,
        "verify": verify,
        "allow_redirects": allow_redirects,
        "timeout": timeout,
        "proxy": proxy,
    }


def _format_dict(name: str, data: Dict[str, Any]) -> str:
    return f"{name} = {json.dumps(data, ensure_ascii=False, indent=4)}"


def curl_to_requests(curl_command: str, include_response: bool = True) -> str:
    spec = parse_curl(curl_command)
    lines: List[str] = ["import requests", ""]

    if spec["headers"]:
        lines.append(_format_dict("headers", spec["headers"]))
    if spec["cookies"]:
        lines.append(_format_dict("cookies", spec["cookies"]))
    if spec["form_data"]:
        lines.append(_format_dict("data", spec["form_data"]))
    if spec["json_body"] is not None and isinstance(spec["json_body"], dict):
        lines.append(_format_dict("json_data", spec["json_body"]))
    if spec["auth"]:
        user, pwd = spec["auth"]
        lines.append(f"auth = ({user!r}, {pwd!r})")
    if spec["proxy"]:
        lines.append(f"proxies = {{'http': {spec['proxy']!r}, 'https': {spec['proxy']!r}}}")

    if len(lines) > 2:
        lines.append("")

    args: List[str] = [f"    {spec['url']!r}"]
    if spec["headers"]:
        args.append("    headers=headers")
    if spec["cookies"]:
        args.append("    cookies=cookies")
    if spec["json_body"] is not None:
        if isinstance(spec["json_body"], dict):
            args.append("    json=json_data")
        else:
            args.append(f"    json={spec['json_body']!r}")
    elif spec["data"] is not None:
        args.append(f"    data={spec['data']!r}")
    elif spec["form_data"]:
        args.append("    data=data")
    if spec["auth"]:
        args.append("    auth=auth")
    if spec["proxy"]:
        args.append("    proxies=proxies")
    if not spec["verify"]:
        args.append("    verify=False")
    if not spec["allow_redirects"]:
        args.append("    allow_redirects=False")
    if spec["timeout"] is not None:
        args.append(f"    timeout={spec['timeout']!r}")

    lines.append(f"response = requests.{spec['method']}(\n" + ",\n".join(args) + ",\n)")

    if include_response:
        lines.extend(["", "print(response.status_code)", "print(response.text)"])

    return "\n".join(lines)
