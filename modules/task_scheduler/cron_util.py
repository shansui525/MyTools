# -*- coding: utf-8 -*-
"""Cron 表达式校验与说明。"""

from typing import Any, Dict, Optional

from apscheduler.triggers.cron import CronTrigger

from modules.task_scheduler.repository import SchedulerError


def validate_cron(expr: str) -> Dict[str, Any]:
    expr = (expr or "").strip()
    if not expr:
        raise SchedulerError("Cron 表达式不能为空")

    parts = expr.split()
    if len(parts) != 5:
        raise SchedulerError("Cron 需 5 段：分 时 日 月 周，例如 0 9 * * *")

    try:
        trigger = CronTrigger.from_crontab(expr)
    except Exception as exc:
        raise SchedulerError(f"Cron 表达式无效: {exc}") from exc

    next_run = trigger.get_next_fire_time(None, __import__("datetime").datetime.now())
    return {
        "cron": expr,
        "valid": True,
        "description": describe_cron(expr),
        "next_run_at": next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else None,
    }


def describe_cron(expr: str) -> str:
    minute, hour, day, month, dow = expr.split()
    hints = []

    if minute.startswith("*/"):
        hints.append(f"每 {minute[2:]} 分钟")
    elif minute == "*":
        hints.append("每分钟")
    else:
        hints.append(f"第 {minute} 分")

    if hour.startswith("*/"):
        hints.append(f"每 {hour[2:]} 小时")
    elif hour != "*":
        hints.append(f"{hour} 点")

    if day != "*":
        hints.append(f"每月 {day} 日")
    if month != "*":
        hints.append(f"{month} 月")
    if dow != "*":
        hints.append(f"周 {dow}")

    return "，".join(hints) if hints else expr


def next_fire_time(expr: str) -> Optional[str]:
    try:
        result = validate_cron(expr)
        return result.get("next_run_at")
    except SchedulerError:
        return None
