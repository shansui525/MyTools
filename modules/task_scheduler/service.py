# -*- coding: utf-8 -*-
"""定时调度器服务层。"""

import sys
from typing import Any, Dict, List, Optional

from modules.task_scheduler import cron_util, engine, executor, repository
from modules.task_scheduler.repository import SchedulerError


def list_tasks_with_status() -> List[Dict[str, Any]]:
    running = executor.get_running_pids()
    tasks = []
    for task in repository.list_tasks():
        item = dict(task)
        tid = item["id"]
        item["is_running"] = tid in running
        item["pid"] = running.get(tid)
        item["enabled"] = bool(item.get("enabled", True))
        if not item["enabled"]:
            item["next_run_at"] = None
        elif not item.get("next_run_at"):
            item["next_run_at"] = cron_util.next_fire_time(item.get("cron", ""))
        tasks.append(item)
    return tasks


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    task = repository.get_task(task_id)
    if not task:
        return None
    item = dict(task)
    item["enabled"] = bool(item.get("enabled", True))
    item["is_running"] = executor.is_running(task_id)
    if not item["enabled"]:
        item["next_run_at"] = None
    if item["is_running"]:
        pids = executor.get_running_pids()
        item["pid"] = pids.get(task_id)
    return item


def create_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    cron_util.validate_cron(payload.get("cron", ""))
    if not payload.get("python_path"):
        payload = dict(payload)
        payload["python_path"] = sys.executable
    task = repository.create_task(payload)
    task["next_run_at"] = cron_util.next_fire_time(task["cron"])
    repository.update_task_runtime(task["id"], next_run_at=task["next_run_at"])
    engine.register_task(task)
    return get_task(task["id"])


def update_task(task_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if "cron" in payload:
        cron_util.validate_cron(payload["cron"])
    task = repository.update_task(task_id, payload)
    task["next_run_at"] = cron_util.next_fire_time(task["cron"])
    repository.update_task_runtime(task_id, next_run_at=task["next_run_at"])
    engine.register_task(task)
    return get_task(task_id)


def delete_task(task_id: str) -> None:
    if executor.is_running(task_id):
        raise SchedulerError("任务正在运行，无法删除")
    engine.unregister_task(task_id)
    repository.delete_task(task_id)


def toggle_task(task_id: str, enabled: bool) -> Dict[str, Any]:
    task = repository.set_task_enabled(task_id, enabled)
    engine.register_task(task)
    return get_task(task_id)


def run_now(task_id: str) -> Dict[str, Any]:
    return executor.run_task(task_id, manual=True)


def get_logs(task_id: str, tail: int = 500) -> Dict[str, Any]:
    if not repository.get_task(task_id):
        raise SchedulerError("任务不存在")
    return {
        "task_id": task_id,
        "log": repository.read_log(task_id, tail=tail),
        "is_running": executor.is_running(task_id),
    }


def validate_cron(expr: str) -> Dict[str, Any]:
    return cron_util.validate_cron(expr)
