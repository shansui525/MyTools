# -*- coding: utf-8 -*-
"""密码管理器 API。"""

from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import Response as RawResponse
from pydantic import BaseModel, Field

from modules.password_manager.crypto import KDF_ITERATIONS, derive_key, generate_salt, hash_password
from modules.password_manager.export import (
    export_csv_plain,
    export_encrypted_backup,
    export_json_plain,
    import_csv_plain,
    import_encrypted_backup,
    import_json_plain,
)
from modules.password_manager.repository import (
    create_entry,
    create_vault,
    delete_entry,
    get_entry,
    get_vault_meta,
    is_initialized,
    list_entries,
    reencrypt_all_entries,
    reset_vault,
    update_entry,
    update_vault_hash,
)
from modules.password_manager.vault import SESSION_TIMEOUT_SECONDS, create_session, destroy_session, get_session_key

router = APIRouter(prefix="/api/tools/password-manager", tags=["password-manager"])

SESSION_COOKIE = "pm_session"
VALID_CATEGORIES = {"website", "computer", "other"}


class InitVaultRequest(BaseModel):
    password: str = Field(min_length=8, description="主密码，至少 8 位")


class PasswordRequest(BaseModel):
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)


class EntryRequest(BaseModel):
    title: str = Field(min_length=1)
    category: str = "other"
    target: str = ""
    username: str = ""
    password: str = ""
    notes: str = ""


class ExportEncryptedRequest(BaseModel):
    export_password: str = Field(min_length=8)


class ImportRequest(BaseModel):
    mode: str = "merge"  # merge | replace


def _require_key(pm_session: Optional[str] = Cookie(default=None)) -> bytes:
    key = get_session_key(pm_session)
    if not key:
        raise HTTPException(status_code=401, detail="请先解锁密码库")
    return key


def _set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=SESSION_TIMEOUT_SECONDS,
    )


def _validate_category(category: str) -> str:
    if category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"无效分类: {category}")
    return category


@router.get("/status")
def get_status(pm_session: Optional[str] = Cookie(default=None)):
    initialized = is_initialized()
    unlocked = get_session_key(pm_session) is not None
    entry_count = 0
    if initialized and unlocked:
        key = get_session_key(pm_session)
        entry_count = len(list_entries(key))
    return {
        "initialized": initialized,
        "unlocked": unlocked,
        "entry_count": entry_count,
        "session_timeout_seconds": SESSION_TIMEOUT_SECONDS,
    }


@router.post("/vault/init")
def init_vault(body: InitVaultRequest, response: Response):
    if is_initialized():
        raise HTTPException(status_code=400, detail="密码库已初始化")
    vault_salt = generate_salt()
    pwd_hash = hash_password(body.password, vault_salt, KDF_ITERATIONS)
    create_vault(vault_salt, pwd_hash, KDF_ITERATIONS)
    session_id = create_session(body.password, vault_salt, pwd_hash, KDF_ITERATIONS)
    _set_session_cookie(response, session_id)
    return {"message": "密码库创建成功"}


@router.post("/vault/unlock")
def unlock_vault(body: PasswordRequest, response: Response):
    meta = get_vault_meta()
    if not meta:
        raise HTTPException(status_code=400, detail="密码库尚未初始化，请先设置主密码")
    session_id = create_session(
        body.password,
        meta["vault_salt"],
        meta["password_hash"],
        meta["kdf_iterations"],
    )
    if not session_id:
        raise HTTPException(status_code=401, detail="主密码错误")
    _set_session_cookie(response, session_id)
    return {"message": "解锁成功"}


@router.post("/vault/lock")
def lock_vault(response: Response, pm_session: Optional[str] = Cookie(default=None)):
    destroy_session(pm_session)
    response.delete_cookie(SESSION_COOKIE)
    return {"message": "已锁定"}


@router.post("/vault/reset")
def reset_vault_api(response: Response, pm_session: Optional[str] = Cookie(default=None)):
    """重置密码库，删除所有数据，回到首次使用状态。"""
    destroy_session(pm_session)
    reset_vault()
    response.delete_cookie(SESSION_COOKIE)
    return {"message": "密码库已重置，请重新设置主密码"}


@router.post("/vault/change-password")
def change_password(body: ChangePasswordRequest, response: Response, pm_session: Optional[str] = Cookie(default=None)):
    meta = get_vault_meta()
    if not meta:
        raise HTTPException(status_code=400, detail="密码库尚未初始化")
    old_key = get_session_key(pm_session)
    if not old_key:
        raise HTTPException(status_code=401, detail="请先解锁密码库")
    from modules.password_manager.crypto import verify_password

    if not verify_password(body.old_password, meta["vault_salt"], meta["password_hash"], meta["kdf_iterations"]):
        raise HTTPException(status_code=401, detail="原主密码错误")
    new_key = derive_key(body.new_password, meta["vault_salt"], meta["kdf_iterations"])
    reencrypt_all_entries(old_key, new_key)
    new_hash = hash_password(body.new_password, meta["vault_salt"], meta["kdf_iterations"])
    update_vault_hash(new_hash)
    destroy_session(pm_session)
    session_id = create_session(body.new_password, meta["vault_salt"], new_hash, meta["kdf_iterations"])
    _set_session_cookie(response, session_id)
    return {"message": "主密码修改成功"}


@router.get("/entries")
def get_entries(q: str = "", key: bytes = Depends(_require_key)):
    items = list_entries(key, q)
    return {"entries": [asdict(i) for i in items]}


@router.get("/entries/{entry_id}")
def get_entry_detail(entry_id: int, key: bytes = Depends(_require_key)):
    entry = get_entry(entry_id, key)
    if not entry:
        raise HTTPException(status_code=404, detail="条目不存在")
    return asdict(entry)


@router.post("/entries")
def add_entry(body: EntryRequest, key: bytes = Depends(_require_key)):
    category = _validate_category(body.category)
    entry = create_entry(
        key, body.title, category, body.target, body.username, body.password, body.notes
    )
    return asdict(entry)


@router.put("/entries/{entry_id}")
def edit_entry(entry_id: int, body: EntryRequest, key: bytes = Depends(_require_key)):
    category = _validate_category(body.category)
    entry = update_entry(
        entry_id, key, body.title, category, body.target, body.username, body.password, body.notes
    )
    if not entry:
        raise HTTPException(status_code=404, detail="条目不存在")
    return asdict(entry)


@router.delete("/entries/{entry_id}")
def remove_entry(entry_id: int, key: bytes = Depends(_require_key)):
    if not delete_entry(entry_id):
        raise HTTPException(status_code=404, detail="条目不存在")
    return {"message": "已删除"}


# ---------- 数据导出 ----------

@router.get("/export/json")
def export_json(key: bytes = Depends(_require_key)):
    content = export_json_plain(key)
    return RawResponse(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="password_vault_export.json"'},
    )


@router.get("/export/csv")
def export_csv(key: bytes = Depends(_require_key)):
    content = export_csv_plain(key)
    return RawResponse(
        content=content.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="password_vault_export.csv"'},
    )


@router.post("/export/encrypted")
def export_encrypted(body: ExportEncryptedRequest, key: bytes = Depends(_require_key)):
    content = export_encrypted_backup(body.export_password, key)
    return RawResponse(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="password_vault_backup.mytools-vault"'},
    )


# ---------- 数据导入 ----------

@router.post("/import/json")
async def import_json(
    file: UploadFile = File(...),
    mode: str = Form("merge"),
    key: bytes = Depends(_require_key),
):
    if mode not in ("merge", "replace"):
        raise HTTPException(status_code=400, detail="mode 必须是 merge 或 replace")
    content = await file.read()
    try:
        count = import_json_plain(content, key, mode)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": f"成功导入 {count} 条记录", "imported": count}


@router.post("/import/csv")
async def import_csv(
    file: UploadFile = File(...),
    mode: str = Form("merge"),
    key: bytes = Depends(_require_key),
):
    if mode not in ("merge", "replace"):
        raise HTTPException(status_code=400, detail="mode 必须是 merge 或 replace")
    content = await file.read()
    try:
        count = import_csv_plain(content, key, mode)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": f"成功导入 {count} 条记录", "imported": count}


@router.post("/import/encrypted")
async def import_encrypted(
    file: UploadFile = File(...),
    export_password: str = Form(...),
    mode: str = Form("merge"),
    key: bytes = Depends(_require_key),
):
    if mode not in ("merge", "replace"):
        raise HTTPException(status_code=400, detail="mode 必须是 merge 或 replace")
    content = await file.read()
    try:
        count = import_encrypted_backup(content, export_password, key, mode)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": f"成功导入 {count} 条记录", "imported": count}
