# -*- coding: utf-8 -*-
"""文本差异对比（基于 difflib）。"""

import difflib
from typing import Any, Dict, List, Optional, Tuple


def _char_segments(text_a: str, text_b: str) -> Tuple[List[Dict], List[Dict]]:
    matcher = difflib.SequenceMatcher(None, text_a, text_b)
    segs_a: List[Dict] = []
    segs_b: List[Dict] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            segs_a.append({"type": "equal", "text": text_a[i1:i2]})
            segs_b.append({"type": "equal", "text": text_b[j1:j2]})
        elif tag == "delete":
            segs_a.append({"type": "delete", "text": text_a[i1:i2]})
        elif tag == "insert":
            segs_b.append({"type": "insert", "text": text_b[j1:j2]})
        elif tag == "replace":
            segs_a.append({"type": "replace", "text": text_a[i1:i2]})
            segs_b.append({"type": "replace", "text": text_b[j1:j2]})
    return segs_a, segs_b


def _line_item(
    line_type: str,
    text: str,
    segments: Optional[List[Dict]] = None,
    line_a: Optional[int] = None,
    line_b: Optional[int] = None,
) -> dict:
    item: dict[str, Any] = {"type": line_type, "text": text}
    if segments is not None:
        item["segments"] = segments
    if line_a is not None:
        item["line_a"] = line_a
    if line_b is not None:
        item["line_b"] = line_b
    return item


def _preview(text: str, limit: int = 48) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"


def _build_changes(left: List[Dict], right: List[Dict]) -> List[Dict]:
    changes: List[Dict] = []
    for idx, (la, lb) in enumerate(zip(left, right)):
        if la["type"] == "equal":
            continue
        change_type = la["type"] if la["type"] != "empty" else lb["type"]
        changes.append(
            {
                "result_row": idx,
                "type": change_type,
                "line_a": la.get("line_a"),
                "line_b": lb.get("line_b"),
                "text_a": la.get("text", ""),
                "text_b": lb.get("text", ""),
                "preview_a": _preview(la.get("text", "")),
                "preview_b": _preview(lb.get("text", "")),
            }
        )
    return changes


def compare_text(text_a: str, text_b: str) -> dict:
    lines_a = text_a.splitlines()
    lines_b = text_b.splitlines()

    matcher = difflib.SequenceMatcher(None, lines_a, lines_b)
    left: List[Dict] = []
    right: List[Dict] = []
    stats = {"equal": 0, "deleted": 0, "inserted": 0, "replaced": 0}
    line_num_a = 0
    line_num_b = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                line_num_a += 1
                line_num_b += 1
                line = lines_a[i1 + k]
                left.append(_line_item("equal", line, line_a=line_num_a, line_b=line_num_b))
                right.append(_line_item("equal", lines_b[j1 + k], line_a=line_num_a, line_b=line_num_b))
                stats["equal"] += 1
        elif tag == "delete":
            for k in range(i1, i2):
                line_num_a += 1
                left.append(_line_item("delete", lines_a[k], line_a=line_num_a))
                right.append(_line_item("empty", ""))
                stats["deleted"] += 1
        elif tag == "insert":
            for k in range(j1, j2):
                line_num_b += 1
                left.append(_line_item("empty", ""))
                right.append(_line_item("insert", lines_b[k], line_b=line_num_b))
                stats["inserted"] += 1
        elif tag == "replace":
            a_part = lines_a[i1:i2]
            b_part = lines_b[j1:j2]
            max_len = max(len(a_part), len(b_part))
            for k in range(max_len):
                la = a_part[k] if k < len(a_part) else ""
                lb = b_part[k] if k < len(b_part) else ""
                line_a_num = None
                line_b_num = None
                if la:
                    line_num_a += 1
                    line_a_num = line_num_a
                if lb:
                    line_num_b += 1
                    line_b_num = line_num_b
                if la and lb:
                    segs_a, segs_b = _char_segments(la, lb)
                    left.append(_line_item("replace", la, segs_a, line_a=line_a_num, line_b=line_b_num))
                    right.append(_line_item("replace", lb, segs_b, line_a=line_a_num, line_b=line_b_num))
                    stats["replaced"] += 1
                elif la:
                    left.append(_line_item("delete", la, line_a=line_a_num))
                    right.append(_line_item("empty", ""))
                    stats["deleted"] += 1
                else:
                    left.append(_line_item("empty", ""))
                    right.append(_line_item("insert", lb, line_b=line_b_num))
                    stats["inserted"] += 1

    changes = _build_changes(left, right)

    return {
        "left": left,
        "right": right,
        "stats": stats,
        "total_lines": len(left),
        "changes": changes,
        "change_count": len(changes),
        "has_diff": bool(changes),
    }
