# -*- coding: utf-8 -*-
"""任务执行器：子进程运行 Python 脚本，防重复调度。"""

import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from modules.task_scheduler.repository import (
    SchedulerError,
    append_log,
    get_script_path_for_task,
    get_task,
    log_path,
    update_task_runtime,
)

_running: Dict[str, subprocess.Popen] = {}
_lock = threading.Lock()
_watcher_started: Dict[str, bool] = {}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_running(task_id: str) -> bool:
    with _lock:
        proc = _running.get(task_id)
        if proc is None:
            return False
        if proc.poll() is None:
            return True
        _running.pop(task_id, None)
        return False


def get_running_pids() -> Dict[str, int]:
    result = {}
    with _lock:
        for task_id, proc in list(_running.items()):
            if proc.poll() is None:
                result[task_id] = proc.pid
            else:
                _running.pop(task_id, None)
    return result


def _watch_process(task_id: str, proc: subprocess.Popen) -> None:
    proc.wait()
    code = proc.returncode
    status = "success" if code == 0 else "failed"
    append_log(task_id, f"[{_now()}] 执行结束，退出码 {code}\n")
    update_task_runtime(task_id, last_run_at=_now(), last_status=status)
    with _lock:
        if _running.get(task_id) is proc:
            _running.pop(task_id, None)
        _watcher_started.pop(task_id, None)


def run_task(task_id: str, manual: bool = False) -> Dict[str, Any]:
    task = get_task(task_id)
    if not task:
        raise SchedulerError("任务不存在")

    if is_running(task_id):
        msg = f"[{_now()}] 跳过：上次执行尚未结束（{'手动' if manual else '定时'}触发）\n"
        append_log(task_id, msg)
        update_task_runtime(task_id, last_status="skipped")
        return {"status": "skipped", "message": "上次执行尚未结束"}

    python_path = task.get("python_path") or sys.executable
    script_file = get_script_path_for_task(task)

    if not Path(python_path).exists():
        raise SchedulerError(f"Python 路径不存在: {python_path}")

    trigger_label = "手动执行" if manual else "定时调度"
    header = (
        f"\n{'=' * 60}\n"
        f"[{_now()}] {trigger_label} 开始\n"
        f"Python: {python_path}\n"
        f"Script: {script_file}\n"
        f"{'=' * 60}\n"
    )
    append_log(task_id, header)
    update_task_runtime(task_id, last_run_at=_now(), last_status="running")

    log_file = log_path(task_id)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_handle = open(log_file, "a", encoding="utf-8")

    try:
        proc = subprocess.Popen(
            [python_path, str(script_file)],
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            cwd=str(script_file.parent),
        )
        log_handle.close()
    except OSError as exc:
        log_handle.close()
        append_log(task_id, f"[{_now()}] 启动失败: {exc}\n")
        update_task_runtime(task_id, last_status="failed")
        raise SchedulerError(f"启动失败: {exc}") from exc

    with _lock:
        _running[task_id] = proc
        if not _watcher_started.get(task_id):
            _watcher_started[task_id] = True
            thread = threading.Thread(
                target=_watch_process,
                args=(task_id, proc),
                daemon=True,
            )
            thread.start()

    return {"status": "running", "pid": proc.pid, "message": "任务已启动"}
