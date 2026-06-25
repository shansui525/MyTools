# -*- coding: utf-8 -*-
"""APScheduler 调度引擎。"""

import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from modules.task_scheduler.cron_util import next_fire_time
from modules.task_scheduler.executor import run_task
from modules.task_scheduler.repository import list_tasks, update_task_runtime

logger = logging.getLogger(__name__)

_scheduler: Optional[BackgroundScheduler] = None


def _job_runner(task_id: str) -> None:
    try:
        run_task(task_id, manual=False)
    except Exception as exc:
        logger.exception("任务 %s 调度失败: %s", task_id, exc)


def _register_task(scheduler: BackgroundScheduler, task: dict) -> None:
    task_id = task["id"]
    cron = task.get("cron", "")
    job_id = f"task_{task_id}"

    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    if not task.get("enabled", True):
        update_task_runtime(task_id, next_run_at=None)
        return

    try:
        trigger = CronTrigger.from_crontab(cron)
        scheduler.add_job(
            _job_runner,
            trigger=trigger,
            id=job_id,
            args=[task_id],
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=30,
        )
        update_task_runtime(task_id, next_run_at=next_fire_time(cron))
    except Exception as exc:
        logger.error("注册任务 %s 失败: %s", task_id, exc)
        update_task_runtime(task_id, next_run_at=None)


def reload_all() -> None:
    if _scheduler is None:
        return
    for task in list_tasks():
        _register_task(_scheduler, task)


def register_task(task: dict) -> None:
    if _scheduler is None:
        return
    _register_task(_scheduler, task)


def unregister_task(task_id: str) -> None:
    if _scheduler is None:
        return
    job_id = f"task_{task_id}"
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    _scheduler.start()
    reload_all()
    logger.info("定时调度器已启动")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
    logger.info("定时调度器已停止")
