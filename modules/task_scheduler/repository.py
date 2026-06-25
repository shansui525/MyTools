# -*- coding: utf-8 -*-
"""定时任务持久化。"""

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_FILE = PROJECT_ROOT / "data" / "scheduler_tasks.json"
LOGS_DIR = PROJECT_ROOT / "data" / "scheduler_logs"
LEGACY_SCRIPTS_DIR = PROJECT_ROOT / "data" / "scheduler_scripts"


class SchedulerError(Exception):
    pass


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _ensure_dirs() -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]", encoding="utf-8")


def _load_raw() -> List[Dict[str, Any]]:
    _ensure_dirs()
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return []


def _save_raw(tasks: List[Dict[str, Any]]) -> None:
    _ensure_dirs()
    DATA_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")


def log_path(task_id: str) -> Path:
    return LOGS_DIR / f"{task_id}.log"


def resolve_script_path(script_path: str) -> Path:
    path = Path(script_path.strip()).expanduser()
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    else:
        path = path.resolve()
    return path


def validate_script_path(script_path: str) -> str:
    if not (script_path or "").strip():
        raise SchedulerError("Python 脚本路径不能为空")

    path = resolve_script_path(script_path)
    if not path.exists():
        raise SchedulerError(f"脚本文件不存在: {path}")
    if not path.is_file():
        raise SchedulerError(f"路径不是文件: {path}")
    if path.suffix.lower() != ".py":
        raise SchedulerError("仅支持 .py 文件")

    return str(path)


def get_script_path_for_task(task: Dict[str, Any]) -> Path:
    script_path = (task.get("script_path") or "").strip()
    if script_path:
        path = resolve_script_path(script_path)
        if not path.exists():
            raise SchedulerError(f"脚本文件不存在: {path}")
        return path

    legacy = LEGACY_SCRIPTS_DIR / f"{task['id']}.py"
    if legacy.exists():
        return legacy

    raise SchedulerError("未配置脚本路径")


def list_tasks() -> List[Dict[str, Any]]:
    return _load_raw()


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    for task in _load_raw():
        if task.get("id") == task_id:
            return task
    return None


def create_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    name = (payload.get("name") or "").strip()
    if not name:
        raise SchedulerError("任务名称不能为空")

    cron = (payload.get("cron") or "").strip()
    if not cron:
        raise SchedulerError("Cron 表达式不能为空")

    script_path = validate_script_path(payload.get("script_path") or "")
    python_path = (payload.get("python_path") or sys.executable).strip()
    task_id = uuid.uuid4().hex
    now = _now_iso()
    task = {
        "id": task_id,
        "name": name,
        "python_path": python_path,
        "cron": cron,
        "script_path": script_path,
        "enabled": bool(payload.get("enabled", True)),
        "created_at": now,
        "updated_at": now,
        "last_run_at": None,
        "last_status": None,
        "next_run_at": None,
    }
    tasks = _load_raw()
    tasks.append(task)
    _save_raw(tasks)
    return task


def set_task_enabled(task_id: str, enabled: bool) -> Dict[str, Any]:
    tasks = _load_raw()
    for idx, task in enumerate(tasks):
        if task.get("id") != task_id:
            continue
        task["enabled"] = bool(enabled)
        task["updated_at"] = _now_iso()
        if not enabled:
            task["next_run_at"] = None
        tasks[idx] = task
        _save_raw(tasks)
        return task
    raise SchedulerError("任务不存在")


def update_task(task_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    tasks = _load_raw()
    for idx, task in enumerate(tasks):
        if task.get("id") != task_id:
            continue

        name = (payload.get("name") or task.get("name") or "").strip()
        cron = (payload.get("cron") if "cron" in payload else task.get("cron") or "").strip()
        python_path = (
            payload.get("python_path") if "python_path" in payload else task.get("python_path") or sys.executable
        ).strip()

        if "script_path" in payload:
            script_path = validate_script_path(payload.get("script_path") or "")
        else:
            script_path = task.get("script_path") or ""

        if not name:
            raise SchedulerError("任务名称不能为空")
        if not cron:
            raise SchedulerError("Cron 表达式不能为空")
        if not script_path:
            raise SchedulerError("Python 脚本路径不能为空")

        if "enabled" in payload:
            enabled = bool(payload["enabled"])
        else:
            enabled = bool(task.get("enabled", True))

        task.update(
            {
                "name": name,
                "cron": cron,
                "script_path": script_path,
                "python_path": python_path,
                "enabled": enabled,
                "updated_at": _now_iso(),
            }
        )
        task.pop("code", None)
        tasks[idx] = task
        _save_raw(tasks)
        return task

    raise SchedulerError("任务不存在")


def delete_task(task_id: str) -> None:
    tasks = _load_raw()
    new_tasks = [t for t in tasks if t.get("id") != task_id]
    if len(new_tasks) == len(tasks):
        raise SchedulerError("任务不存在")
    _save_raw(new_tasks)

    log_file = log_path(task_id)
    if log_file.exists():
        log_file.unlink()


def update_task_runtime(task_id: str, **fields: Any) -> None:
    tasks = _load_raw()
    for idx, task in enumerate(tasks):
        if task.get("id") == task_id:
            task.update(fields)
            tasks[idx] = task
            _save_raw(tasks)
            return


def append_log(task_id: str, text: str) -> None:
    _ensure_dirs()
    path = log_path(task_id)
    with open(path, "a", encoding="utf-8") as f:
        f.write(text)
        if text and not text.endswith("\n"):
            f.write("\n")


def read_log(task_id: str, tail: int = 500) -> str:
    path = log_path(task_id)
    if not path.exists():
        return ""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    if tail <= 0:
        return "\n".join(lines)
    return "\n".join(lines[-tail:])
