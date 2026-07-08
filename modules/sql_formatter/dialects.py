# -*- coding: utf-8 -*-
"""SQL 方言定义与关键字集合。"""

import re
from typing import Literal

from modules.sql_formatter.keywords import SQL_KEYWORDS

SqlDialect = Literal["standard", "hive", "spark"]

DIALECT_LABELS = {
    "standard": "标准 SQL",
    "hive": "Hive SQL",
    "spark": "Spark SQL",
}

# Hive 扩展关键字（标准集已含大部分，此处补充遗漏项）
HIVE_EXTRA_KEYWORDS = frozenset({
    "MSCK", "REPAIR", "ANALYZE", "COMPUTE", "STATISTICS", "COLUMNS", "EXTENDED",
    "FORMATTED", "DEPENDENCY", "SKEWED", "DIRECTORIES", "INDEXES", "INDEXED",
    "LOCKS", "UNLOCK", "DATABASES", "TABLES", "FUNCTIONS", "PARTITIONS", "ROLES",
    "ROLE", "USERS", "USER", "GRANTS", "PERMISSION", "PERMANENT", "TRANSIENT",
    "DEFINED", "DEFINER", "INVOKER", "SECURITY", "EXECUTE", "OWNER", "RETURNS",
    "DETERMINISTIC", "READS", "MODIFIES", "SQL", "DATA", "LANGUAGE",
})

# Spark 在 Hive 基础上补充
SPARK_EXTRA_KEYWORDS = frozenset({
    "PIVOT", "UNPIVOT", "TABLESAMPLE", "PERCENTLIT", "OPTIMIZE", "ZORDER",
    "VACUUM", "RESTORE", "HISTORY", "DESCRIBE", "DETAIL", "HISTORY",
    "GENERATED", "ALWAYS", "IDENTITY", "START", "INCREMENT", "MINVALUE",
    "MAXVALUE", "CYCLE", "CACHE", "UNCACHE", "LAZY", "FORMATTED", "SERDE",
    "BROADCAST", "SHUFFLE", "REPARTITION", "COALESCE", "hint", "HINT",
    "RESPECT", "IGNORE", "NULLS", "WINDOW", "TIME", "ZONE", "LOCAL",
    "TIMESTAMP_LTZ", "TIMESTAMP_NTZ", "VOID", "TINYINT", "SMALLINT", "BIGINT",
    "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC", "STRING", "BINARY", "BOOLEAN",
    "DATE", "TIMESTAMP", "INTERVAL", "YEAR", "MONTH", "DAY", "HOUR", "MINUTE",
    "SECOND", "TRY_CAST", "TRY_SUM", "TRY_AVG", "COLLECT_LIST", "COLLECT_SET",
    "APPROX_COUNT_DISTINCT", "APPROX_PERCENTILE", "PERCENTILE", "PERCENTILE_APPROX",
    "HISTOGRAM_NUMERIC", "WIDTH_BUCKET", "ELEMENT_AT", "ARRAY_CONTAINS",
    "ARRAY_DISTINCT", "ARRAY_EXCEPT", "ARRAY_INTERSECT", "ARRAY_JOIN",
    "ARRAY_MAX", "ARRAY_MIN", "ARRAY_POSITION", "ARRAY_REMOVE", "ARRAY_REPEAT",
    "ARRAY_SORT", "ARRAY_UNION", "ARRAYS_OVERLAP", "ARRAYS_ZIP", "FLATTEN",
    "SEQUENCE", "SHUFFLE", "SLICE", "SORT_ARRAY", "MAP_CONCAT", "MAP_ENTRIES",
    "MAP_FROM_ARRAYS", "MAP_FROM_ENTRIES", "MAP_KEYS", "MAP_VALUES", "STR_TO_MAP",
    "NAMED_STRUCT", "STRUCT", "FROM_JSON", "TO_JSON", "SCHEMA_OF_JSON",
    "GET_JSON_OBJECT", "JSON_TUPLE", "JSON_ARRAY_LENGTH", "JSON_OBJECT_KEYS",
    "EXPLODE", "POSEXPLODE", "EXPLODE_OUTER", "POSEXPLODE_OUTER", "INLINE",
    "INLINE_OUTER", "STACK", "LATERAL", "VIEW", "OUTER", "TRANSFORM", "REDUCE",
    "AGGREGATE", "FILTER", "ZIP_WITH", "FORALL", "EXISTS", "TRANSFORM_KEYS",
    "TRANSFORM_VALUES", "MAP_FILTER", "MAP_ZIP_WITH",
})

_DIALECT_KEYWORDS = {
    "standard": SQL_KEYWORDS,
    "hive": SQL_KEYWORDS | HIVE_EXTRA_KEYWORDS,
    "spark": SQL_KEYWORDS | HIVE_EXTRA_KEYWORDS | SPARK_EXTRA_KEYWORDS,
}

_PATTERN_CACHE: dict[str, re.Pattern] = {}


def normalize_dialect(dialect: str) -> SqlDialect:
    value = (dialect or "standard").lower()
    if value not in DIALECT_LABELS:
        raise ValueError(f"不支持的方言：{dialect}")
    return value  # type: ignore[return-value]


def get_keywords(dialect: str) -> frozenset:
    return _DIALECT_KEYWORDS[normalize_dialect(dialect)]


def is_dialect_keyword(name: str, dialect: str) -> bool:
    return name.upper() in get_keywords(dialect)


def get_keyword_pattern(dialect: str) -> re.Pattern:
    d = normalize_dialect(dialect)
    if d not in _PATTERN_CACHE:
        ordered = sorted(get_keywords(d), key=len, reverse=True)
        _PATTERN_CACHE[d] = re.compile(
            r"\b(" + "|".join(re.escape(k) for k in ordered) + r")\b",
            re.IGNORECASE,
        )
    return _PATTERN_CACHE[d]
