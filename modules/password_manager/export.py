# -*- coding: utf-8 -*-
"""密码库数据导出与导入。"""

import base64
import csv
import io
import json
from datetime import datetime, timezone

from modules.password_manager.crypto import (
    KDF_ITERATIONS,
    decrypt,
    derive_key,
    encrypt,
    generate_salt,
)
from modules.password_manager.repository import get_all_entries_decrypted, get_vault_meta, import_entries

EXPORT_VERSION = 1


def _entry_to_dict(entry) -> dict:
    return {
        "title": entry.title,
        "category": entry.category,
        "target": entry.target,
        "username": entry.username,
        "password": entry.password,
        "notes": entry.notes,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }


def export_json_plain(key: bytes) -> str:
    """导出明文 JSON（需已解锁，用户自行保管）。"""
    entries = get_all_entries_decrypted(key)
    payload = {
        "format": "mytools-password-vault-plain",
        "version": EXPORT_VERSION,
        "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "entries": [_entry_to_dict(e) for e in entries],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def export_csv_plain(key: bytes) -> str:
    """导出明文 CSV。"""
    entries = get_all_entries_decrypted(key)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["title", "category", "target", "username", "password", "notes", "created_at", "updated_at"])
    for e in entries:
        writer.writerow([e.title, e.category, e.target, e.username, e.password, e.notes, e.created_at, e.updated_at])
    return output.getvalue()


def export_encrypted_backup(export_password: str, key: bytes) -> bytes:
    """
    导出加密备份文件（.mytools-vault）。
    使用独立的导出密码加密，便于迁移；导入时需导出密码。
    """
    entries = get_all_entries_decrypted(key)
    meta = get_vault_meta()
    export_salt = generate_salt()
    export_key = derive_key(export_password, export_salt, KDF_ITERATIONS)
    payload_json = json.dumps([_entry_to_dict(e) for e in entries], ensure_ascii=False)
    encrypted_data = encrypt(payload_json, export_key, export_salt)

    backup = {
        "format": "mytools-password-vault-encrypted",
        "version": EXPORT_VERSION,
        "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "kdf_iterations": KDF_ITERATIONS,
        "export_salt": base64.b64encode(export_salt).decode("ascii"),
        "encrypted_data": base64.b64encode(encrypted_data).decode("ascii"),
        "entry_count": len(entries),
        "vault_created_at": meta["created_at"] if meta else None,
    }
    return json.dumps(backup, ensure_ascii=False, indent=2).encode("utf-8")


def import_encrypted_backup(file_content: bytes, export_password: str, key: bytes, mode: str = "merge") -> int:
    """从加密备份导入。"""
    data = json.loads(file_content.decode("utf-8"))
    if data.get("format") != "mytools-password-vault-encrypted":
        raise ValueError("不是有效的 MyTools 加密备份文件")

    export_salt = base64.b64decode(data["export_salt"])
    encrypted_data = base64.b64decode(data["encrypted_data"])
    export_key = derive_key(export_password, export_salt, data.get("kdf_iterations", KDF_ITERATIONS))

    try:
        plaintext = decrypt(encrypted_data, export_key)
    except Exception as exc:
        raise ValueError("导出密码错误或备份文件已损坏") from exc

    entries = json.loads(plaintext)
    if not isinstance(entries, list):
        raise ValueError("备份数据格式无效")
    return import_entries(key, entries, mode=mode)


def import_json_plain(file_content: bytes, key: bytes, mode: str = "merge") -> int:
    """从明文 JSON 导入。"""
    data = json.loads(file_content.decode("utf-8"))
    fmt = data.get("format", "")
    if fmt == "mytools-password-vault-plain":
        entries = data.get("entries", [])
    elif isinstance(data, list):
        entries = data
    else:
        raise ValueError("不是有效的 JSON 导入文件")
    return import_entries(key, entries, mode=mode)


def import_csv_plain(file_content: bytes, key: bytes, mode: str = "merge") -> int:
    """从 CSV 导入。"""
    text = file_content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    entries = []
    for row in reader:
        entries.append(
            {
                "title": row.get("title", ""),
                "category": row.get("category", "other"),
                "target": row.get("target", ""),
                "username": row.get("username", ""),
                "password": row.get("password", ""),
                "notes": row.get("notes", ""),
            }
        )
    return import_entries(key, entries, mode=mode)
