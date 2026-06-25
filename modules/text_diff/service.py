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


def _line_item(line_type: str, text: str, segments: Optional[List[Dict]] = None) -> dict:
    item: dict[str, Any] = {"type": line_type, "text": text}
    if segments is not None:
        item["segments"] = segments
    return item


def compare_text(text_a: str, text_b: str) -> dict:
    lines_a = text_a.splitlines()
    lines_b = text_b.splitlines()

    matcher = difflib.SequenceMatcher(None, lines_a, lines_b)
    left: List[Dict] = []
    right: List[Dict] = []
    stats = {"equal": 0, "deleted": 0, "inserted": 0, "replaced": 0}

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                line = lines_a[i1 + k]
                left.append(_line_item("equal", line))
                right.append(_line_item("equal", lines_b[j1 + k]))
                stats["equal"] += 1
        elif tag == "delete":
            for k in range(i1, i2):
                left.append(_line_item("delete", lines_a[k]))
                right.append(_line_item("empty", ""))
                stats["deleted"] += 1
        elif tag == "insert":
            for k in range(j1, j2):
                left.append(_line_item("empty", ""))
                right.append(_line_item("insert", lines_b[k]))
                stats["inserted"] += 1
        elif tag == "replace":
            a_part = lines_a[i1:i2]
            b_part = lines_b[j1:j2]
            max_len = max(len(a_part), len(b_part))
            for k in range(max_len):
                la = a_part[k] if k < len(a_part) else ""
                lb = b_part[k] if k < len(b_part) else ""
                if la and lb:
                    segs_a, segs_b = _char_segments(la, lb)
                    left.append(_line_item("replace", la, segs_a))
                    right.append(_line_item("replace", lb, segs_b))
                    stats["replaced"] += 1
                elif la:
                    left.append(_line_item("delete", la))
                    right.append(_line_item("empty", ""))
                    stats["deleted"] += 1
                else:
                    left.append(_line_item("empty", ""))
                    right.append(_line_item("insert", lb))
                    stats["inserted"] += 1

    return {
        "left": left,
        "right": right,
        "stats": stats,
        "total_lines": len(left),
    }
