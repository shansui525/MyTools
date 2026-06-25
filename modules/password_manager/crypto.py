# -*- coding: utf-8 -*-
"""PBKDF2 密钥派生 + AES-256-GCM 加解密。"""

import hashlib
import os
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KDF_ITERATIONS = 600_000
SALT_BYTES = 16
NONCE_BYTES = 12
KEY_BYTES = 32


def generate_salt() -> bytes:
    return os.urandom(SALT_BYTES)


def derive_key(password: str, salt: bytes, iterations: int = KDF_ITERATIONS) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=KEY_BYTES)


def hash_password(password: str, salt: bytes, iterations: int = KDF_ITERATIONS) -> bytes:
    return derive_key(password, salt, iterations)


def verify_password(password: str, salt: bytes, expected_hash: bytes, iterations: int = KDF_ITERATIONS) -> bool:
    return secrets.compare_digest(hash_password(password, salt, iterations), expected_hash)


def encrypt(plaintext: str, key: bytes, record_salt: bytes) -> bytes:
    """返回 record_salt + nonce + ciphertext（含 GCM tag）。"""
    if not plaintext:
        return b""
    nonce = os.urandom(NONCE_BYTES)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), record_salt)
    return record_salt + nonce + ciphertext


def decrypt(blob: bytes, key: bytes) -> str:
    if not blob:
        return ""
    record_salt = blob[:SALT_BYTES]
    nonce = blob[SALT_BYTES : SALT_BYTES + NONCE_BYTES]
    ciphertext = blob[SALT_BYTES + NONCE_BYTES :]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, record_salt).decode("utf-8")
