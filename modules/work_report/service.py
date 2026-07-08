# -*- coding: utf-8 -*-
"""工作记录汇总与报告生成。"""

import calendar
from datetime import date, timedelta
from typing import Dict, List, Tuple

from modules.work_report.llm import chat_completion
from modules.work_report.repository import get_settings_runtime, list_entries

PERIOD_LABELS = {
    "week": "周报",
    "month": "月报",
    "quarter": "季报",
    "year": "年报",
}


def get_period_range(period: str, reference: date) -> Tuple[date, date, str]:
    """计算报告周期的起止日期与标题。"""
    if period == "week":
        start = reference - timedelta(days=reference.weekday())
        end = start + timedelta(days=6)
        iso_year, iso_week, _ = reference.isocalendar()
        title = f"{iso_year} 年第 {iso_week} 周周报"
    elif period == "month":
        start = reference.replace(day=1)
        last_day = calendar.monthrange(reference.year, reference.month)[1]
        end = reference.replace(day=last_day)
        title = f"{reference.year} 年 {reference.month} 月月报"
    elif period == "quarter":
        q = (reference.month - 1) // 3 + 1
        start_month = (q - 1) * 3 + 1
        end_month = start_month + 2
        start = date(reference.year, start_month, 1)
        last_day = calendar.monthrange(reference.year, end_month)[1]
        end = date(reference.year, end_month, last_day)
        title = f"{reference.year} 年第 {q} 季度季报"
    elif period == "year":
        start = date(reference.year, 1, 1)
        end = date(reference.year, 12, 31)
        title = f"{reference.year} 年年度总结"
    else:
        raise ValueError("不支持的报告类型，可选：week / month / quarter / year")

    return start, end, title


def _format_entries_text(entries: List[Dict]) -> str:
    if not entries:
        return "（该时段暂无工作记录）"
    lines = []
    for item in sorted(entries, key=lambda x: x["date"]):
        lines.append(f"### {item['date']}\n{item['content']}")
    return "\n\n".join(lines)


def _build_prompt(period: str, title: str, start: date, end: date, entries_text: str) -> str:
    label = PERIOD_LABELS.get(period, "报告")
    return f"""你是一位专业的工作总结助手。请根据以下每日工作记录，生成一份结构化的{label}。

报告标题：{title}
时间范围：{start.isoformat()} 至 {end.isoformat()}

要求：
1. 使用 Markdown 格式输出
2. 结构清晰，包含：工作概述、主要成果、遇到的问题、改进方向、下阶段计划（如适用）
3. 语言简洁专业，突出可量化的成果与价值
4. 若某日无记录可忽略；若整体记录较少，请基于已有内容合理归纳，不要编造未提及的工作

每日工作记录：
{entries_text}
"""


def generate_report(period: str, reference: date) -> Dict:
    """汇总指定周期内的工作记录并调用大模型生成报告。"""
    start, end, title = get_period_range(period, reference)
    entries = list_entries(start.isoformat(), end.isoformat())
    entries_text = _format_entries_text(entries)

    settings = get_settings_runtime()
    prompt = _build_prompt(period, title, start, end, entries_text)
    messages = [
        {"role": "system", "content": "你是专业的工作总结写作助手，擅长从日常记录中提炼高质量的工作报告。"},
        {"role": "user", "content": prompt},
    ]
    report = chat_completion(
        messages=messages,
        api_base=settings["llm_api_base"],
        api_key=settings["llm_api_key"],
        model=settings["llm_model"],
    )

    return {
        "period": period,
        "title": title,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "entry_count": len(entries),
        "report": report,
    }


def test_llm_connection() -> str:
    """测试大模型连接是否正常。"""
    settings = get_settings_runtime()
    reply = chat_completion(
        messages=[{"role": "user", "content": "请回复：连接成功"}],
        api_base=settings["llm_api_base"],
        api_key=settings["llm_api_key"],
        model=settings["llm_model"],
        temperature=0,
    )
    return reply[:200]
