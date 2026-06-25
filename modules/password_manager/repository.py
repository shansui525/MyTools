# -*- coding: utf-8 -*-
"""密码条目 SQLite 持久化。"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from modules.password_manager.crypto import decrypt, encrypt, generate_salt
from modules.password_manager.models import CredentialEntry, CredentialListItem

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "password_vault.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS vault_meta (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    vault_salt BLOB NOT NULL,
    password_hash BLOB NOT NULL,
    kdf_iterations INTEGER NOT NULL DEFAULT 600000,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'other',
    target TEXT NOT NULL DEFAULT '',
    username_enc BLOB NOT NULL,
    password_enc BLOB NOT NULL,
    notes_enc BLOB,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA)


def is_initialized() -> bool:
    init_db()
    with _connect() as conn:
        row = conn.execute("SELECT 1 FROM vault_meta WHERE id = 1").fetchone()
        return row is not None


def reset_vault() -> None:
    """删除密码库及全部条目，恢复为未初始化状态。"""
    if DB_PATH.exists():
        DB_PATH.unlink()


def get_vault_meta() -> Optional[dict]:
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT vault_salt, password_hash, kdf_iterations, created_at FROM vault_meta WHERE id = 1"
        ).fetchone()
        if not row:
            return None
        return {
            "vault_salt": row["vault_salt"],
            "password_hash": row["password_hash"],
            "kdf_iterations": row["kdf_iterations"],
            "created_at": row["created_at"],
        }


def create_vault(vault_salt: bytes, password_hash: bytes, iterations: int) -> None:
    init_db()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO vault_meta (id, vault_salt, password_hash, kdf_iterations, created_at) VALUES (1, ?, ?, ?, ?)",
            (vault_salt, password_hash, iterations, _now_iso()),
        )


def update_vault_hash(password_hash: bytes) -> None:
    with _connect() as conn:
        conn.execute("UPDATE vault_meta SET password_hash = ? WHERE id = 1", (password_hash,))


def _row_to_list_item(row: sqlite3.Row) -> CredentialListItem:
    return CredentialListItem(
        id=row["id"],
        title=row["title"],
        category=row["category"],
        target=row["target"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_entry(row: sqlite3.Row, key: bytes) -> CredentialEntry:
    return CredentialEntry(
        id=row["id"],
        title=row["title"],
        category=row["category"],
        target=row["target"],
        username=decrypt(row["username_enc"], key),
        password=decrypt(row["password_enc"], key),
        notes=decrypt(row["notes_enc"] or b"", key),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def list_entries(key: bytes, query: str = "") -> list[CredentialListItem]:
    init_db()
    with _connect() as conn:
        if query.strip():
            like = f"%{query.strip()}%"
            rows = conn.execute(
                "SELECT * FROM credentials WHERE title LIKE ? OR target LIKE ? ORDER BY updated_at DESC",
                (like, like),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM credentials ORDER BY updated_at DESC").fetchall()
        return [_row_to_list_item(r) for r in rows]


def get_entry(entry_id: int, key: bytes) -> Optional[CredentialEntry]:
    init_db()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM credentials WHERE id = ?", (entry_id,)).fetchone()
        if not row:
            return None
        return _row_to_entry(row, key)


def create_entry(
    key: bytes,
    title: str,
    category: str,
    target: str,
    username: str,
    password: str,
    notes: str = "",
) -> CredentialEntry:
    init_db()
    now = _now_iso()
    salt = generate_salt()
    username_enc = encrypt(username, key, salt)
    password_enc = encrypt(password, key, salt)
    notes_enc = encrypt(notes, key, salt) if notes else b""

    with _connect() as conn:
        cur = conn.execute(
            """INSERT INTO credentials
               (title, category, target, username_enc, password_enc, notes_enc, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, category, target, username_enc, password_enc, notes_enc, now, now),
        )
        entry_id = cur.lastrowid
        row = conn.execute("SELECT * FROM credentials WHERE id = ?", (entry_id,)).fetchone()
        return _row_to_entry(row, key)


def update_entry(
    entry_id: int,
    key: bytes,
    title: str,
    category: str,
    target: str,
    username: str,
    password: str,
    notes: str = "",
) -> Optional[CredentialEntry]:
    init_db()
    now = _now_iso()
    salt = generate_salt()
    username_enc = encrypt(username, key, salt)
    password_enc = encrypt(password, key, salt)
    notes_enc = encrypt(notes, key, salt) if notes else b""

    with _connect() as conn:
        row = conn.execute("SELECT id FROM credentials WHERE id = ?", (entry_id,)).fetchone()
        if not row:
            return None
        conn.execute(
            """UPDATE credentials SET title=?, category=?, target=?,
               username_enc=?, password_enc=?, notes_enc=?, updated_at=? WHERE id=?""",
            (title, category, target, username_enc, password_enc, notes_enc, now, entry_id),
        )
        row = conn.execute("SELECT * FROM credentials WHERE id = ?", (entry_id,)).fetchone()
        return _row_to_entry(row, key)


def delete_entry(entry_id: int) -> bool:
    init_db()
    with _connect() as conn:
        cur = conn.execute("DELETE FROM credentials WHERE id = ?", (entry_id,))
        return cur.rowcount > 0


def get_all_entries_decrypted(key: bytes) -> list[CredentialEntry]:
    init_db()
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM credentials ORDER BY id").fetchall()
        return [_row_to_entry(r, key) for r in rows]


def reencrypt_all_entries(old_key: bytes, new_key: bytes) -> None:
    entries = get_all_entries_decrypted(old_key)
    with _connect() as conn:
        for entry in entries:
            salt = generate_salt()
            username_enc = encrypt(entry.username, new_key, salt)
            password_enc = encrypt(entry.password, new_key, salt)
            notes_enc = encrypt(entry.notes, new_key, salt) if entry.notes else b""
            conn.execute(
                """UPDATE credentials SET username_enc=?, password_enc=?, notes_enc=?, updated_at=?
                   WHERE id=?""",
                (username_enc, password_enc, notes_enc, _now_iso(), entry.id),
            )


def import_entries(key: bytes, entries: list[dict], mode: str = "merge") -> int:
    """导入条目。mode: merge（合并）或 replace（清空后导入）。"""
    init_db()
    if mode == "replace":
        with _connect() as conn:
            conn.execute("DELETE FROM credentials")

    count = 0
    for item in entries:
        create_entry(
            key=key,
            title=item.get("title", ""),
            category=item.get("category", "other"),
            target=item.get("target", ""),
            username=item.get("username", ""),
            password=item.get("password", ""),
            notes=item.get("notes", ""),
        )
        count += 1
    return count
