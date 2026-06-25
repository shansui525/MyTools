# -*- coding: utf-8 -*-
"""定时调度器 API。"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from modules.task_scheduler.repository import SchedulerError
from modules.task_scheduler import service

router = APIRouter(prefix="/api/tools/task-scheduler", tags=["task-scheduler"])


class TaskCreateRequest(BaseModel):
    name: str
    python_path: str = ""
    cron: str
    script_path: str
    enabled: bool = True


class TaskUpdateRequest(BaseModel):
    name: Optional[str] = None
    python_path: Optional[str] = None
    cron: Optional[str] = None
    script_path: Optional[str] = None
    enabled: Optional[bool] = None


def _task_payload(body: TaskUpdateRequest) -> dict:
    return body.dict(exclude_unset=True)


class ToggleRequest(BaseModel):
    enabled: bool


@router.get("/tasks")
def list_tasks():
    return {"tasks": service.list_tasks_with_status()}


@router.post("/tasks")
def create_task(body: TaskCreateRequest):
    try:
        task = service.create_task(body.dict())
        return task
    except SchedulerError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/tasks/{task_id}")
def get_task(task_id: str):
    task = service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.put("/tasks/{task_id}")
def update_task(task_id: str, body: TaskUpdateRequest):
    try:
        return service.update_task(task_id, _task_payload(body))
    except SchedulerError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/tasks/{task_id}")
def delete_task(task_id: str):
    try:
        service.delete_task(task_id)
        return {"ok": True}
    except SchedulerError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/tasks/{task_id}/toggle")
def toggle_task(task_id: str, body: ToggleRequest):
    try:
        return service.toggle_task(task_id, body.enabled)
    except SchedulerError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/tasks/{task_id}/run")
def run_task_now(task_id: str):
    try:
        return service.run_now(task_id)
    except SchedulerError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/tasks/{task_id}/logs")
def get_logs(task_id: str, tail: int = Query(500, ge=1, le=5000)):
    try:
        return service.get_logs(task_id, tail=tail)
    except SchedulerError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/cron/validate")
def validate_cron(cron: str = Query(...)):
    try:
        return service.validate_cron(cron)
    except SchedulerError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
