# -*- coding: utf-8 -*-
"""SQL 格式化与高亮分词。"""

import re
from typing import Literal, Optional

import sqlparse
import sqlparse.engine.grouping as sqlparse_grouping
from sqlparse import tokens as T
from sqlparse.sql import Identifier, Statement

from modules.sql_formatter.dialects import SqlDialect, get_keyword_pattern, is_dialect_keyword, normalize_dialect
from modules.sql_formatter.linter import lint_sql

KeywordCase = Literal["upper", "lower", "preserve"]

_TABLE_CONTEXT = frozenset({"FROM", "INTO", "UPDATE", "TABLE"})
_DEFAULT_MAX_GROUPING_TOKENS = sqlparse_grouping.MAX_GROUPING_TOKENS

_FALLBACK_TABLE_CTX = re.compile(
    r"\b(FROM|JOIN|INTO|UPDATE|TABLE|(?:LEFT|RIGHT|INNER|FULL|CROSS|NATURAL)\s+JOIN)\s+",
    re.IGNORECASE,
)
_FALLBACK_STRING = re.compile(r"'([^']|'')*'")
_FALLBACK_LINE_COMMENT = re.compile(r"--[^\n]*")
_FALLBACK_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_FALLBACK_NUMBER = re.compile(r"\b\d+(?:\.\d+)?\b")
_TABLE_IDENT = re.compile(r"[\w$]+(?:\.[\w$]+)*")
_BACKTICK_IDENT = re.compile(r"`[^`]+`")


def _match_at(pattern: re.Pattern, text: str, pos: int):
    """在指定位置匹配，避免 re.match(..., pos) 遇到中文时的编码错误。"""
    chunk = text[pos:]
    if not chunk:
        return None
    return pattern.match(chunk)


class SqlFormatError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


def format_sql(
    text: str,
    indent: int = 2,
    keyword_case: KeywordCase = "upper",
    dialect: SqlDialect = "standard",
) -> str:
    raw = text.strip()
    if not raw:
        raise SqlFormatError("请输入 SQL 内容")

    normalize_dialect(dialect)
    case_opt = None if keyword_case == "preserve" else keyword_case
    formatted = sqlparse.format(
        raw,
        reindent=True,
        indent_width=indent,
        keyword_case=case_opt,
        strip_comments=False,
    )
    if not formatted.strip():
        raise SqlFormatError("SQL 内容无效")
    return formatted


def _grouping_token_limit(text: str) -> Optional[int]:
    """按 SQL 长度动态放宽 sqlparse 分组 token 上限。"""
    if _DEFAULT_MAX_GROUPING_TOKENS is None:
        return None
    return min(max(len(text) * 2, _DEFAULT_MAX_GROUPING_TOKENS), 500_000)


def _parse_statements(text: str):
    old_limit = sqlparse_grouping.MAX_GROUPING_TOKENS
    try:
        sqlparse_grouping.MAX_GROUPING_TOKENS = _grouping_token_limit(text)
        return sqlparse.parse(text)
    finally:
        sqlparse_grouping.MAX_GROUPING_TOKENS = old_limit


def _is_keyword(token) -> bool:
    if not token.ttype:
        return False
    return token.ttype in T.Keyword or token.ttype.parent is T.Keyword


def _keyword_upper(token) -> str:
    return str(token).upper()


def _name_segment_type(name: str, token, *, as_table: bool, dialect: SqlDialect) -> str:
    if as_table and not is_dialect_keyword(name, dialect):
        return "table"
    if is_dialect_keyword(name, dialect):
        return "keyword"
    if token.ttype in T.Name.Builtin:
        return "keyword"
    return "identifier"


def _emit_leaf(token, segments: list[dict], dialect: SqlDialect) -> None:
    value = str(token)
    ttype = token.ttype

    if ttype in T.Comment:
        segments.append({"type": "comment", "value": value})
    elif ttype in T.Text.Whitespace:
        segments.append({"type": "whitespace", "value": value})
    elif ttype in T.String:
        segments.append({"type": "string", "value": value})
    elif ttype in T.Literal.Number:
        segments.append({"type": "number", "value": value})
    elif ttype in T.Operator or ttype and ttype.parent is T.Operator:
        segments.append({"type": "operator", "value": value})
    elif ttype in T.Punctuation:
        segments.append({"type": "punctuation", "value": value})
    elif _is_keyword(token):
        segments.append({"type": "keyword", "value": value})
    elif ttype in T.Name or (ttype and ttype.parent is T.Name):
        seg_type = _name_segment_type(value, token, as_table=False, dialect=dialect)
        segments.append({"type": seg_type, "value": value})
    else:
        segments.append({"type": "text", "value": value})


def _emit_identifier(identifier: Identifier, segments: list[dict], *, as_table: bool, dialect: SqlDialect) -> None:
    alias = identifier.get_alias()

    for token in identifier.tokens:
        if isinstance(token, Identifier):
            if alias and str(token).strip() == alias:
                _emit_identifier(token, segments, as_table=False, dialect=dialect)
            else:
                _emit_identifier(token, segments, as_table=as_table, dialect=dialect)
            continue

        if token.is_whitespace:
            segments.append({"type": "whitespace", "value": str(token)})
            continue

        if token.ttype in T.Name or (token.ttype and token.ttype.parent is T.Name):
            name = str(token)
            if as_table and not is_dialect_keyword(name, dialect):
                segments.append({"type": "table", "value": name})
            elif not as_table and alias and name == alias:
                segments.append({"type": "identifier", "value": name})
            else:
                seg_type = _name_segment_type(name, token, as_table=as_table, dialect=dialect)
                segments.append({"type": seg_type, "value": name})
            continue

        _emit_leaf(token, segments, dialect)


def _emit_table_identifier(identifier: Identifier, segments: list[dict], dialect: SqlDialect) -> None:
    parent = identifier.get_parent_name()
    real = identifier.get_real_name()
    alias = identifier.get_alias()

    for token in identifier.tokens:
        if isinstance(token, Identifier):
            if alias and str(token).strip() == alias:
                _emit_identifier(token, segments, as_table=False, dialect=dialect)
            else:
                _emit_table_identifier(token, segments, dialect)
            continue

        if token.is_whitespace:
            segments.append({"type": "whitespace", "value": str(token)})
            continue

        if token.ttype in T.Name or (token.ttype and token.ttype.parent is T.Name):
            name = str(token)
            if is_dialect_keyword(name, dialect):
                segments.append({"type": "keyword", "value": name})
            elif name in {real, parent} or (parent is None and name == real):
                segments.append({"type": "table", "value": name})
            elif alias and name == alias:
                segments.append({"type": "identifier", "value": name})
            else:
                segments.append({"type": "table", "value": name})
        else:
            _emit_leaf(token, segments, dialect)


def _walk_statement(statement: Statement, segments: list[dict], dialect: SqlDialect) -> None:
    expect_table = False

    for token in statement.tokens:
        if isinstance(token, Identifier):
            if expect_table:
                _emit_table_identifier(token, segments, dialect)
                expect_table = False
            else:
                _emit_identifier(token, segments, as_table=False, dialect=dialect)
            continue

        if token.is_group and not isinstance(token, Identifier):
            _walk_statement(token, segments, dialect)
            continue

        if _is_keyword(token):
            upper = _keyword_upper(token)
            segments.append({"type": "keyword", "value": str(token)})

            if upper in _TABLE_CONTEXT or "JOIN" in upper.split():
                expect_table = True
            else:
                expect_table = False
            continue

        _emit_leaf(token, segments, dialect)
        if token.ttype and token.ttype not in T.Text.Whitespace:
            if not (token.ttype in T.Punctuation and str(token) == "."):
                expect_table = False


def _tokenize_plain_text(text: str, dialect: SqlDialect) -> list[dict]:
    """对纯文本块做关键字/注释/字符串/表名等高亮分词。"""
    segments: list[dict] = []
    pos = 0
    length = len(text)

    while pos < length:
        block = _match_at(_FALLBACK_BLOCK_COMMENT, text, pos)
        if block:
            segments.append({"type": "comment", "value": block.group(0)})
            pos += len(block.group(0))
            continue

        line = _match_at(_FALLBACK_LINE_COMMENT, text, pos)
        if line:
            segments.append({"type": "comment", "value": line.group(0)})
            pos += len(line.group(0))
            continue

        string = _match_at(_FALLBACK_STRING, text, pos)
        if string:
            segments.append({"type": "string", "value": string.group(0)})
            pos += len(string.group(0))
            continue

        backtick = _match_at(_BACKTICK_IDENT, text, pos)
        if backtick:
            segments.append({"type": "identifier", "value": backtick.group(0)})
            pos += len(backtick.group(0))
            continue

        table_ctx = _match_at(_FALLBACK_TABLE_CTX, text, pos)
        if table_ctx:
            keyword = table_ctx.group(1)
            segments.append({"type": "keyword", "value": keyword})
            tail = table_ctx.group(0)[len(keyword):]
            if tail:
                segments.append({"type": "whitespace", "value": tail})
            pos += len(table_ctx.group(0))
            ident = _match_at(_TABLE_IDENT, text, pos)
            if ident:
                parts = ident.group(0).split(".")
                for i, part in enumerate(parts):
                    if i:
                        segments.append({"type": "punctuation", "value": "."})
                    segments.append({"type": "table", "value": part})
                pos += len(ident.group(0))
            continue

        number = _match_at(_FALLBACK_NUMBER, text, pos)
        if number:
            segments.append({"type": "number", "value": number.group(0)})
            pos += len(number.group(0))
            continue

        kw = _match_at(get_keyword_pattern(dialect), text, pos)
        if kw:
            segments.append({"type": "keyword", "value": kw.group(0)})
            pos += len(kw.group(0))
            continue

        segments.append({"type": "text", "value": text[pos]})
        pos += 1

    return segments


def _enhance_segments(segments: list[dict], dialect: SqlDialect) -> list[dict]:
    """对 sqlparse 未细分的 text 块补充关键字高亮。"""
    enhanced: list[dict] = []
    for seg in segments:
        if seg["type"] == "text" and seg["value"]:
            enhanced.extend(_tokenize_plain_text(seg["value"], dialect))
        else:
            enhanced.append(seg)
    return enhanced


def _highlight_fallback(text: str, dialect: SqlDialect) -> list[dict]:
    """sqlparse 解析失败时的正则高亮兜底。"""
    return _tokenize_plain_text(text, dialect)


def highlight_sql(text: str, dialect: SqlDialect = "standard") -> list[dict]:
    d = normalize_dialect(dialect)
    try:
        segments: list[dict] = []
        for statement in _parse_statements(text):
            _walk_statement(statement, segments, d)
        if segments:
            return _enhance_segments(segments, d)
    except Exception:
        pass
    return _highlight_fallback(text, d)


def process_sql(
    text: str,
    indent: int = 2,
    keyword_case: KeywordCase = "preserve",
    dialect: SqlDialect = "standard",
) -> dict:
    d = normalize_dialect(dialect)
    formatted = format_sql(text, indent=indent, keyword_case=keyword_case, dialect=d)
    issues = lint_sql(formatted, d)
    return {
        "result": formatted,
        "segments": highlight_sql(formatted, d),
        "dialect": d,
        "issues": issues,
        "issue_summary": {
            "errors": sum(1 for item in issues if item["level"] == "error"),
            "warnings": sum(1 for item in issues if item["level"] == "warning"),
        },
    }
