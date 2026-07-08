# -*- coding: utf-8 -*-
"""基于 sqlglot 解析器的 SQL 语法检查。"""

import re
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

from sqlglot import exp, parse, tokenize
from sqlglot.errors import ErrorLevel, ParseError
from sqlglot.optimizer.scope import traverse_scope

from modules.sql_formatter.dialects import SqlDialect, normalize_dialect

IssueLevel = Literal["error", "warning"]
Issue = Dict[str, Any]

# 标准 SQL 使用 sqlglot 默认方言；Hive / Spark 走对应 read 方言
_READ_DIALECT: Dict[SqlDialect, Optional[str]] = {
    "standard": None,
    "hive": "hive",
    "spark": "spark",
}

# 字符串/注释外常见误输入的全角或中文标点
_INVALID_PUNCT = frozenset("，。；：！？、（）【】《》""''…")

# sqlglot 英文报错 -> 中文提示
_ERROR_LOCALE = (
    (re.compile(r"Expecting \)", re.I), "缺少右括号 )"),
    (re.compile(r"Expecting \(", re.I), "缺少左括号 ("),
    (re.compile(r"Invalid expression / Unexpected token", re.I), "无效表达式或无法识别的符号"),
    (re.compile(r"Required keyword: .+ missing for", re.I), "语法不完整，此处缺少有效表达式"),
    (re.compile(r"No expression was parsed", re.I), "无法解析为有效 SQL 语句"),
    (re.compile(r"Expecting .+", re.I), lambda m: f"语法错误：{m.group(0)}"),
)


def _add_issue(
    issues: List[Issue],
    level: IssueLevel,
    line: int,
    column: int,
    message: str,
) -> None:
    issues.append({"level": level, "line": line, "column": column, "message": message})


def _localize_error(description: str) -> str:
    text = (description or "SQL 语法错误").strip()
    for pattern, replacement in _ERROR_LOCALE:
        if pattern.search(text):
            if callable(replacement):
                return replacement(pattern.search(text))
            return replacement
    return text


def _meta_line_col(node: exp.Expression) -> Tuple[int, int]:
    if (node.meta or {}).get("line"):
        meta = node.meta
        return int(meta["line"]), int(meta.get("col") or 1)
    for child in node.walk():
        if child is node:
            continue
        if (child.meta or {}).get("line"):
            meta = child.meta
            return int(meta["line"]), int(meta.get("col") or 1)
    return 1, 1


def _dedupe_issues(issues: List[Issue]) -> List[Issue]:
    seen_full: Set[Tuple[str, int, int, str]] = set()
    seen_pos: Set[Tuple[str, int, int]] = set()
    result: List[Issue] = []
    for item in issues:
        pos_key = (item["level"], item["line"], item["column"])
        full_key = (*pos_key, item["message"])
        if full_key in seen_full or pos_key in seen_pos:
            continue
        seen_full.add(full_key)
        seen_pos.add(pos_key)
        result.append(item)
    result.sort(key=lambda x: (x["line"], x["column"], x["level"]))
    return result


def _issues_from_parse_errors(errors: List[dict]) -> List[Issue]:
    issues: List[Issue] = []
    for err in errors:
        description = err.get("description") or "SQL 语法错误"
        highlight = err.get("highlight") or ""
        message = _localize_error(description)
        if highlight and highlight not in message:
            message = f"{message}（附近符号：{highlight!r}）"
        _add_issue(
            issues,
            "error",
            int(err.get("line") or 1),
            int(err.get("col") or 1),
            message,
        )
    return issues


def _read_dialect(dialect: SqlDialect) -> Optional[str]:
    return _READ_DIALECT[normalize_dialect(dialect)]


def _check_invalid_characters(text: str) -> List[Issue]:
    """词法层：字符串/注释外不允许出现全角标点等非法字符。"""
    issues: List[Issue] = []
    state = "code"
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""

        if state == "code":
            if ch == "-" and nxt == "-":
                state = "line_comment"
                i += 2
                continue
            if ch == "/" and nxt == "*":
                state = "block_comment"
                i += 2
                continue
            if ch == "'":
                state = "single_quote"
                i += 1
                continue
            if ch == '"':
                state = "double_quote"
                i += 1
                continue
            if ch == "`":
                state = "backtick"
                i += 1
                continue
            if ch in _INVALID_PUNCT:
                line = text.count("\n", 0, i) + 1
                last_nl = text.rfind("\n", 0, i)
                col = i - last_nl if last_nl >= 0 else i + 1
                _add_issue(
                    issues,
                    "error",
                    line,
                    col,
                    f"非法字符「{ch}」，请检查是否误用了中文标点（应使用半角符号）",
                )
            i += 1
            continue

        if state == "line_comment":
            if ch == "\n":
                state = "code"
            i += 1
            continue

        if state == "block_comment":
            if ch == "*" and nxt == "/":
                state = "code"
                i += 2
                continue
            i += 1
            continue

        if state == "single_quote":
            if ch == "'" and nxt == "'":
                i += 2
                continue
            if ch == "'":
                state = "code"
            i += 1
            continue

        if state == "double_quote":
            if ch == '"' and nxt == '"':
                i += 2
                continue
            if ch == '"':
                state = "code"
            i += 1
            continue

        if state == "backtick":
            if ch == "`":
                state = "code"
            i += 1
            continue

        i += 1

    return issues


def _check_token_stream(text: str, read_dialect: Optional[str]) -> List[Issue]:
    """词法层：基于 tokenizer 发现连续逗号、标识符内非法字符等。"""
    issues: List[Issue] = []
    try:
        tokens = tokenize(text, read=read_dialect)
    except ParseError as e:
        return _issues_from_parse_errors(e.errors)

    prev = None
    for tok in tokens:
        if tok.token_type.name == "VAR" and any(c in _INVALID_PUNCT for c in tok.text):
            _add_issue(
                issues,
                "error",
                tok.line,
                tok.col,
                f"标识符「{tok.text}」含非法字符，请检查是否误用了中文标点或漏写逗号",
            )
        if (
            prev
            and prev.token_type.name == "COMMA"
            and tok.token_type.name == "COMMA"
        ):
            _add_issue(
                issues,
                "error",
                tok.line,
                tok.col,
                "出现连续逗号 ,,，语法非法",
            )
        prev = tok
    return issues


def _parse_sql(text: str, read_dialect: Optional[str]) -> tuple[List[Issue], List[exp.Expression]]:
    issues: List[Issue] = []
    try:
        statements = parse(
            text,
            read=read_dialect,
            error_level=ErrorLevel.RAISE,
        )
    except ParseError as e:
        issues.extend(_issues_from_parse_errors(e.errors))
        return issues, []

    valid = [stmt for stmt in statements if stmt is not None]
    if text.strip() and not valid:
        _add_issue(issues, "error", 1, 1, "无法解析为有效 SQL 语句")
    return issues, valid


def _func_total_args(node: exp.Func) -> int:
    total = len(node.expressions or [])
    if node.this is not None:
        total += 1
    expression = node.args.get("expression")
    if expression is not None:
        total += 1
    return total


def _check_function_arity(statements: List[exp.Expression]) -> List[Issue]:
    """语义层：基于 AST 校验常见函数参数个数。"""
    issues: List[Issue] = []
    min_args = {
        exp.Coalesce: 2,
        exp.Nullif: 2,
    }

    for stmt in statements:
        for node in stmt.find_all(exp.Func):
            expected = min_args.get(type(node))
            if expected is None:
                continue
            count = _func_total_args(node)
            if count >= expected:
                continue
            line, col = _meta_line_col(node)
            sql_head = node.sql().split("(", 1)[0].strip().upper()
            label = "NVL/COALESCE" if sql_head == "COALESCE" else sql_head
            _add_issue(
                issues,
                "error",
                line,
                col,
                f"函数 {label} 至少需要 {expected} 个参数，当前仅 {count} 个",
            )
    return issues


def _check_unresolved_references(statements: List[exp.Expression]) -> List[Issue]:
    """语义层：基于 scope 分析检查无法解析的表别名/限定符。"""
    issues: List[Issue] = []

    for stmt in statements:
        for scope in traverse_scope(stmt):
            sources = set(scope.sources.keys())
            for column in scope.columns:
                table = column.table
                if not table or table in sources:
                    continue
                line, col = _meta_line_col(column)
                member = column.name or column.sql()
                _add_issue(
                    issues,
                    "error",
                    line,
                    col,
                    f"无法解析限定符「{table}.{member}」：当前作用域中不存在表/别名「{table}」",
                )
    return issues


def lint_sql(text: str, dialect: str = "standard") -> List[Issue]:
    """对 SQL 做语法检查，返回问题列表。"""
    raw = text.strip()
    if not raw:
        return []

    d = normalize_dialect(dialect)
    read_dialect = _read_dialect(d)
    issues: List[Issue] = []

    # 1. 词法检查（非法字符、连续逗号等）
    issues.extend(_check_invalid_characters(raw))
    issues.extend(_check_token_stream(raw, read_dialect))

    # 2. 语法解析（sqlglot parser）
    parse_issues, statements = _parse_sql(raw, read_dialect)
    issues.extend(parse_issues)

    if not statements:
        return _dedupe_issues(issues)

    # 3. 语义检查（基于 AST，仅在解析成功后执行）
    issues.extend(_check_function_arity(statements))
    issues.extend(_check_unresolved_references(statements))

    return _dedupe_issues(issues)
