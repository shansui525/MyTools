# -*- coding: utf-8 -*-
"""保险库会话管理：主密码解锁后，派生密钥保存在内存中。"""

import secrets
import time
from dataclasses import dataclass
from typing import Optional

from modules.password_manager.crypto import KDF_ITERATIONS, derive_key, verify_password

SESSION_TIMEOUT_SECONDS = 30 * 60


@dataclass
class VaultSession:
    session_id: str
    derived_key: bytes
    expires_at: float


_sessions: dict[str, VaultSession] = {}


def _cleanup_expired() -> None:
    now = time.time()
    expired = [sid for sid, s in _sessions.items() if s.expires_at <= now]
    for sid in expired:
        del _sessions[sid]


def create_session(password: str, vault_salt: bytes, password_hash: bytes, iterations: int) -> Optional[str]:
    if not verify_password(password, vault_salt, password_hash, iterations):
        return None
    _cleanup_expired()
    session_id = secrets.token_urlsafe(32)
    derived_key = derive_key(password, vault_salt, iterations)
    _sessions[session_id] = VaultSession(
        session_id=session_id,
        derived_key=derived_key,
        expires_at=time.time() + SESSION_TIMEOUT_SECONDS,
    )
    return session_id


def get_session_key(session_id: Optional[str]) -> Optional[bytes]:
    if not session_id:
        return None
    _cleanup_expired()
    session = _sessions.get(session_id)
    if not session:
        return None
    if session.expires_at <= time.time():
        del _sessions[session_id]
        return None
    session.expires_at = time.time() + SESSION_TIMEOUT_SECONDS
    return session.derived_key


def destroy_session(session_id: Optional[str]) -> None:
    if session_id and session_id in _sessions:
        del _sessions[session_id]


def is_session_valid(session_id: Optional[str]) -> bool:
    return get_session_key(session_id) is not None
