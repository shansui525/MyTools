# -*- coding: utf-8
"""加解密运算实现。"""

import base64
import hashlib
import hmac as hmac_lib
import re
import urllib.parse
from typing import Optional, Tuple

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, padding, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

try:
    from gmssl import sm2, sm3
    from gmssl.sm4 import SM4_DECRYPT, SM4_ENCRYPT, CryptSM4

    _HAS_GMSSL = True
except ImportError:
    _HAS_GMSSL = False


class CryptoLabError(Exception):
    pass


def _require_gmssl() -> None:
    if not _HAS_GMSSL:
        raise CryptoLabError("未安装 gmssl，请执行 pip install gmssl")


def to_bytes(text: str, length: int) -> bytes:
    raw = (text or "").strip()
    if re.fullmatch(r"[0-9a-fA-F]+", raw) and len(raw) == length * 2:
        return bytes.fromhex(raw)
    data = raw.encode("utf-8")
    if len(data) >= length:
        return data[:length]
    return data + b"\0" * (length - len(data))


def _input_bytes(text: str, input_format: str) -> bytes:
    fmt = (input_format or "text").lower()
    if fmt == "hex":
        return bytes.fromhex(text.strip())
    if fmt == "base64":
        return base64.b64decode(text.strip())
    return text.encode("utf-8")


def _format_output(data: bytes, output_format: str) -> str:
    fmt = (output_format or "hex").lower()
    if fmt == "text":
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CryptoLabError("结果无法解码为 UTF-8 文本") from exc
    if fmt == "base64":
        return base64.b64encode(data).decode("ascii")
    return data.hex()


def _parse_input_for_decode(text: str, input_format: str) -> bytes:
    fmt = (input_format or "text").lower()
    if fmt == "hex":
        return bytes.fromhex(text.strip())
    if fmt == "base64":
        return base64.b64decode(text.strip())
    if fmt == "text":
        try:
            return bytes.fromhex(text.strip())
        except ValueError:
            pass
        try:
            return base64.b64decode(text.strip())
        except Exception:
            pass
        return text.encode("utf-8")
    return _input_bytes(text, fmt)


# ---------- 编码 ----------

def op_base64(action: str, text: str, **_kwargs) -> str:
    if action == "encode":
        return base64.b64encode(text.encode("utf-8")).decode("ascii")
    return base64.b64decode(text.strip()).decode("utf-8", errors="replace")


def op_base64url(action: str, text: str, **_kwargs) -> str:
    if action == "encode":
        return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text.strip() + pad).decode("utf-8", errors="replace")


def op_hex(action: str, text: str, **_kwargs) -> str:
    if action == "encode":
        return text.encode("utf-8").hex()
    return bytes.fromhex(text.strip()).decode("utf-8", errors="replace")


def op_url(action: str, text: str, **_kwargs) -> str:
    if action == "encode":
        return urllib.parse.quote(text, safe="")
    return urllib.parse.unquote(text)


# ---------- 哈希 ----------

def op_md5(text: str, **_kwargs) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def op_sha1(text: str, **_kwargs) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def op_sha256(text: str, **_kwargs) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def op_sha512(text: str, **_kwargs) -> str:
    return hashlib.sha512(text.encode("utf-8")).hexdigest()


def op_sm3(text: str, **_kwargs) -> str:
    _require_gmssl()
    return sm3.sm3_hash(list(text.encode("utf-8")))


def op_hmac_md5(text: str, key: str = "", **_kwargs) -> str:
    if not key:
        raise CryptoLabError("HMAC 需要密钥 key")
    return hmac_lib.new(key.encode("utf-8"), text.encode("utf-8"), hashlib.md5).hexdigest()


def op_hmac_sha256(text: str, key: str = "", **_kwargs) -> str:
    if not key:
        raise CryptoLabError("HMAC 需要密钥 key")
    return hmac_lib.new(key.encode("utf-8"), text.encode("utf-8"), hashlib.sha256).hexdigest()


# ---------- AES / DES ----------

def _cipher_cbc(data: bytes, key: bytes, iv: bytes, algorithm, encrypt: bool) -> bytes:
    cipher = Cipher(algorithm(key), modes.CBC(iv), default_backend())
    if encrypt:
        padder = padding.PKCS7(algorithm.block_size).padder()
        padded = padder.update(data) + padder.finalize()
        enc = cipher.encryptor()
        return enc.update(padded) + enc.finalize()
    dec = cipher.decryptor()
    plain = dec.update(data) + dec.finalize()
    unpadder = padding.PKCS7(algorithm.block_size).unpadder()
    return unpadder.update(plain) + unpadder.finalize()


def _cipher_ecb(data: bytes, key: bytes, algorithm, encrypt: bool) -> bytes:
    cipher = Cipher(algorithm(key), modes.ECB(), default_backend())
    if encrypt:
        padder = padding.PKCS7(algorithm.block_size).padder()
        padded = padder.update(data) + padder.finalize()
        enc = cipher.encryptor()
        return enc.update(padded) + enc.finalize()
    dec = cipher.decryptor()
    plain = dec.update(data) + dec.finalize()
    unpadder = padding.PKCS7(algorithm.block_size).unpadder()
    return unpadder.update(plain) + unpadder.finalize()


def op_aes_cbc(action: str, text: str, key: str, iv: str, key_len: int, input_format: str, output_format: str, **_kw) -> str:
    if not key:
        raise CryptoLabError("需要密钥 key")
    if not iv:
        raise CryptoLabError("CBC 模式需要 IV")
    key_b = to_bytes(key, key_len)
    iv_b = to_bytes(iv, 16)
    data = _input_bytes(text, input_format) if action == "encrypt" else _parse_input_for_decode(text, input_format)
    out = _cipher_cbc(data, key_b, iv_b, algorithms.AES, action == "encrypt")
    return _format_output(out, output_format)


def op_aes_ecb(action: str, text: str, key: str, key_len: int, input_format: str, output_format: str, **_kw) -> str:
    if not key:
        raise CryptoLabError("需要密钥 key")
    key_b = to_bytes(key, key_len)
    data = _input_bytes(text, input_format) if action == "encrypt" else _parse_input_for_decode(text, input_format)
    out = _cipher_ecb(data, key_b, algorithms.AES, action == "encrypt")
    return _format_output(out, output_format)


def op_aes_gcm(action: str, text: str, key: str, iv: str, aad: str = "", input_format: str = "text", output_format: str = "base64", **_kw) -> str:
    if not key or not iv:
        raise CryptoLabError("GCM 需要 key 和 iv（12 字节）")
    key_b = to_bytes(key, 32)
    iv_b = to_bytes(iv, 12)
    aad_b = (aad or "").encode("utf-8")
    if action == "encrypt":
        data = _input_bytes(text, input_format)
        cipher = Cipher(algorithms.AES(key_b), modes.GCM(iv_b), default_backend())
        enc = cipher.encryptor()
        if aad_b:
            enc.authenticate_additional_data(aad_b)
        ct = enc.update(data) + enc.finalize()
        out = ct + enc.tag
    else:
        raw = _parse_input_for_decode(text, input_format)
        if len(raw) < 16:
            raise CryptoLabError("GCM 密文长度不足（需含 16 字节 tag）")
        ct, tag = raw[:-16], raw[-16:]
        cipher = Cipher(algorithms.AES(key_b), modes.GCM(iv_b, tag), default_backend())
        dec = cipher.decryptor()
        if aad_b:
            dec.authenticate_additional_data(aad_b)
        out = dec.update(ct) + dec.finalize()
    return _format_output(out, output_format)


def op_des_cbc(action: str, text: str, key: str, iv: str, input_format: str, output_format: str, **_kw) -> str:
    if not key or not iv:
        raise CryptoLabError("需要 key 和 iv")
    key_b = to_bytes(key, 8) * 3
    iv_b = to_bytes(iv, 8)
    data = _input_bytes(text, input_format) if action == "encrypt" else _parse_input_for_decode(text, input_format)
    out = _cipher_cbc(data, key_b, iv_b, algorithms.TripleDES, action == "encrypt")
    return _format_output(out, output_format)


def op_3des_cbc(action: str, text: str, key: str, iv: str, input_format: str, output_format: str, **_kw) -> str:
    if not key or not iv:
        raise CryptoLabError("需要 key 和 iv")
    key_b = to_bytes(key, 24)
    iv_b = to_bytes(iv, 8)
    data = _input_bytes(text, input_format) if action == "encrypt" else _parse_input_for_decode(text, input_format)
    out = _cipher_cbc(data, key_b, iv_b, algorithms.TripleDES, action == "encrypt")
    return _format_output(out, output_format)


# ---------- SM4 ----------

def _sm4_pad(data: bytes) -> bytes:
    pad_len = 16 - (len(data) % 16)
    return data + bytes([pad_len] * pad_len)


def _sm4_unpad(data: bytes) -> bytes:
    if not data:
        raise CryptoLabError("SM4 解密数据为空")
    pad_len = data[-1]
    if pad_len < 1 or pad_len > 16:
        raise CryptoLabError("SM4 填充无效")
    return data[:-pad_len]


def op_sm4_ecb(action: str, text: str, key: str, input_format: str, output_format: str, **_kw) -> str:
    _require_gmssl()
    if not key:
        raise CryptoLabError("需要 16 字节 SM4 密钥")
    key_b = to_bytes(key, 16)
    crypt = CryptSM4()
    if action == "encrypt":
        data = _sm4_pad(_input_bytes(text, input_format))
        crypt.set_key(key_b, SM4_ENCRYPT)
    else:
        data = _parse_input_for_decode(text, input_format)
        crypt.set_key(key_b, SM4_DECRYPT)
    out = crypt.crypt_ecb(data)
    if action == "decrypt":
        out = _sm4_unpad(out)
    return _format_output(out, output_format)


def op_sm4_cbc(action: str, text: str, key: str, iv: str, input_format: str, output_format: str, **_kw) -> str:
    _require_gmssl()
    if not key or not iv:
        raise CryptoLabError("SM4-CBC 需要 key 和 iv")
    key_b = to_bytes(key, 16)
    iv_b = to_bytes(iv, 16)
    crypt = CryptSM4()
    if action == "encrypt":
        data = _sm4_pad(_input_bytes(text, input_format))
        crypt.set_key(key_b, SM4_ENCRYPT)
    else:
        data = _parse_input_for_decode(text, input_format)
        crypt.set_key(key_b, SM4_DECRYPT)
    out = crypt.crypt_cbc(iv_b, data)
    if action == "decrypt":
        out = _sm4_unpad(out)
    return _format_output(out, output_format)


# ---------- RSA / SM2 ----------

def _load_rsa_public(pem: str):
    return serialization.load_pem_public_key(pem.encode("utf-8"), backend=default_backend())


def _load_rsa_private(pem: str):
    return serialization.load_pem_private_key(pem.encode("utf-8"), password=None, backend=default_backend())


def op_rsa_oaep(action: str, text: str, public_key: str = "", private_key: str = "", input_format: str = "text", output_format: str = "base64", **_kw) -> str:
    if action == "encrypt":
        if not public_key:
            raise CryptoLabError("RSA 加密需要公钥 PEM")
        key = _load_rsa_public(public_key.strip())
        data = _input_bytes(text, input_format)
        out = key.encrypt(
            data,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
    else:
        if not private_key:
            raise CryptoLabError("RSA 解密需要私钥 PEM")
        key = _load_rsa_private(private_key.strip())
        data = _parse_input_for_decode(text, input_format)
        out = key.decrypt(
            data,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
    return _format_output(out, output_format)


def op_sm2(action: str, text: str, public_key: str = "", private_key: str = "", input_format: str = "text", output_format: str = "hex", **_kw) -> str:
    _require_gmssl()
    if action == "encrypt":
        if not public_key:
            raise CryptoLabError("SM2 加密需要公钥 hex")
        crypt = sm2.CryptSM2("", public_key.strip())
        data = _input_bytes(text, input_format)
        out = crypt.encrypt(data)
        if isinstance(out, str):
            out = bytes.fromhex(out)
    else:
        if not private_key:
            raise CryptoLabError("SM2 解密需要私钥 hex")
        pub = public_key.strip()
        if not pub and private_key:
            temp = sm2.CryptSM2(private_key.strip(), "")
            pub = temp._kg(int(private_key.strip(), 16), sm2.default_ecc_table["g"])
        crypt = sm2.CryptSM2(private_key.strip(), pub)
        data = _parse_input_for_decode(text, input_format)
        out = crypt.decrypt(data)
        if isinstance(out, str):
            out = out.encode("utf-8")
    return _format_output(out, output_format)


def generate_rsa_keypair() -> Tuple[str, str]:
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")
    return public_pem, private_pem


def generate_sm2_keypair() -> Tuple[str, str]:
    _require_gmssl()
    import secrets

    private_hex = secrets.token_hex(32)
    temp = sm2.CryptSM2(private_hex, "")
    public_hex = temp._kg(int(private_hex, 16), sm2.default_ecc_table["g"])
    return public_hex, private_hex


HANDLERS = {
    "base64": op_base64,
    "base64url": op_base64url,
    "hex": op_hex,
    "url": op_url,
    "md5": op_md5,
    "sha1": op_sha1,
    "sha256": op_sha256,
    "sha512": op_sha512,
    "sm3": op_sm3,
    "hmac-md5": op_hmac_md5,
    "hmac-sha256": op_hmac_sha256,
    "aes-128-cbc": lambda **kw: op_aes_cbc(key_len=16, **kw),
    "aes-256-cbc": lambda **kw: op_aes_cbc(key_len=32, **kw),
    "aes-256-ecb": lambda **kw: op_aes_ecb(key_len=32, **kw),
    "aes-256-gcm": op_aes_gcm,
    "des-cbc": op_des_cbc,
    "3des-cbc": op_3des_cbc,
    "sm4-ecb": op_sm4_ecb,
    "sm4-cbc": op_sm4_cbc,
    "rsa-oaep": op_rsa_oaep,
    "sm2": op_sm2,
}
