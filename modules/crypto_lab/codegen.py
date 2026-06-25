# -*- coding: utf-8 -*-
"""生成 Python / JavaScript 示例代码。"""

from typing import Any, Dict


def _py(s: str) -> str:
    return s.strip() + "\n"


def _js(s: str) -> str:
    return s.strip() + "\n"


def generate_code(algorithm_id: str, action: str, params: Dict[str, Any]) -> Dict[str, str]:
    text = params.get("text", "")
    key = params.get("key", "")
    iv = params.get("iv", "")
    aad = params.get("aad", "")
    public_key = params.get("public_key", "")
    private_key = params.get("private_key", "")
    input_format = params.get("input_format", "text")
    output_format = params.get("output_format", "hex")

    gen = _GENERATORS.get(algorithm_id)
    if not gen:
        return {
            "python": f"# 算法 {algorithm_id}\n# 请查阅官方文档",
            "javascript": f"// 算法 {algorithm_id}\n// 请查阅官方文档",
        }
    return gen(action, text, key, iv, aad, public_key, private_key, input_format, output_format)


def _gen_base64(action, text, *_a, **_k):
    if action == "encode":
        py = _py(f'''
import base64
text = {text!r}
result = base64.b64encode(text.encode()).decode()
print(result)
''')
        js = _js(f'''
const text = {text!r};
const result = btoa(unescape(encodeURIComponent(text)));
console.log(result);
''')
    else:
        py = _py(f'''
import base64
cipher = {text!r}
result = base64.b64decode(cipher).decode("utf-8", errors="replace")
print(result)
''')
        js = _js(f'''
const cipher = {text!r};
const result = decodeURIComponent(escape(atob(cipher)));
console.log(result);
''')
    return {"python": py, "javascript": js}


def _gen_base64url(action, text, *_a, **_k):
    if action == "encode":
        py = _py(f'''
import base64
text = {text!r}
result = base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")
print(result)
''')
        js = _js(f'''
// npm install crypto-js
const CryptoJS = require("crypto-js");
const text = {text!r};
const result = CryptoJS.enc.Base64url.stringify(CryptoJS.enc.Utf8.parse(text));
console.log(result);
''')
    else:
        py = _py(f'''
import base64
cipher = {text!r}
pad = "=" * (-len(cipher) % 4)
result = base64.urlsafe_b64decode(cipher + pad).decode()
print(result)
''')
        js = _js(f'''
const CryptoJS = require("crypto-js");
const cipher = {text!r};
const result = CryptoJS.enc.Base64url.parse(cipher).toString(CryptoJS.enc.Utf8);
console.log(result);
''')
    return {"python": py, "javascript": js}


def _gen_hex(action, text, *_a, **_k):
    if action == "encode":
        py = _py(f"text = {text!r}\nprint(text.encode().hex())")
        js = _js(f'''
const text = {text!r};
console.log(Buffer.from(text, "utf8").toString("hex"));
''')
    else:
        py = _py(f"cipher = {text!r}\nprint(bytes.fromhex(cipher).decode())")
        js = _js(f'''
const cipher = {text!r};
console.log(Buffer.from(cipher, "hex").toString("utf8"));
''')
    return {"python": py, "javascript": js}


def _gen_url(action, text, *_a, **_k):
    if action == "encode":
        py = _py(f'''
from urllib.parse import quote
print(quote({text!r}, safe=""))
''')
        js = _js(f"console.log(encodeURIComponent({text!r}));")
    else:
        py = _py(f'''
from urllib.parse import unquote
print(unquote({text!r}))
''')
        js = _js(f"console.log(decodeURIComponent({text!r}));")
    return {"python": py, "javascript": js}


def _gen_md5(_a, text, *_r, **_k):
    py = _py(f'''
import hashlib
print(hashlib.md5({text!r}.encode()).hexdigest())
''')
    js = _js(f'''
const CryptoJS = require("crypto-js");
console.log(CryptoJS.MD5({text!r}).toString());
''')
    return {"python": py, "javascript": js}


def _gen_sha1(_a, text, *_r, **_k):
    py = _py(f"import hashlib\nprint(hashlib.sha1({text!r}.encode()).hexdigest())")
    js = _js(f'const CryptoJS = require("crypto-js");\nconsole.log(CryptoJS.SHA1({text!r}).toString());')
    return {"python": py, "javascript": js}


def _gen_sha256(_a, text, *_r, **_k):
    py = _py(f"import hashlib\nprint(hashlib.sha256({text!r}.encode()).hexdigest())")
    js = _js(f'const CryptoJS = require("crypto-js");\nconsole.log(CryptoJS.SHA256({text!r}).toString());')
    return {"python": py, "javascript": js}


def _gen_sha512(_a, text, *_r, **_k):
    py = _py(f"import hashlib\nprint(hashlib.sha512({text!r}.encode()).hexdigest())")
    js = _js(f'const CryptoJS = require("crypto-js");\nconsole.log(CryptoJS.SHA512({text!r}).toString());')
    return {"python": py, "javascript": js}


def _gen_sm3(_a, text, *_r, **_k):
    py = _py(f'''
from gmssl import sm3
print(sm3.sm3_hash(list({text!r}.encode())))
''')
    js = _js(f'''
const {{ sm3 }} = require("sm-crypto");
console.log(sm3({text!r}));
''')
    return {"python": py, "javascript": js}


def _gen_hmac_md5(_a, text, key, *_r, **_k):
    py = _py(f'''
import hmac, hashlib
print(hmac.new({key!r}.encode(), {text!r}.encode(), hashlib.md5).hexdigest())
''')
    js = _js(f'''
const CryptoJS = require("crypto-js");
console.log(CryptoJS.HmacMD5({text!r}, {key!r}).toString());
''')
    return {"python": py, "javascript": js}


def _gen_hmac_sha256(_a, text, key, *_r, **_k):
    py = _py(f'''
import hmac, hashlib
print(hmac.new({key!r}.encode(), {text!r}.encode(), hashlib.sha256).hexdigest())
''')
    js = _js(f'''
const CryptoJS = require("crypto-js");
console.log(CryptoJS.HmacSHA256({text!r}, {key!r}).toString());
''')
    return {"python": py, "javascript": js}


def _gen_aes_cbc(action, text, key, iv, *_r, mode_bits=256, **_k):
    if action == "encrypt":
        py = _py(f'''
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
import base64

key = {key!r}.encode()[:{mode_bits // 8}].ljust({mode_bits // 8}, b"\\0")
iv = {iv!r}.encode()[:16].ljust(16, b"\\0")
data = {text!r}.encode()
padder = padding.PKCS7(128).padder()
padded = padder.update(data) + padder.finalize()
cipher = Cipher(algorithms.AES(key), modes.CBC(iv), default_backend())
enc = cipher.encryptor()
print(base64.b64encode(enc.update(padded) + enc.finalize()).decode())
''')
        js = _js(f'''
const CryptoJS = require("crypto-js");
const key = CryptoJS.enc.Utf8.parse({key!r}.slice(0, {mode_bits // 8}));
const iv = CryptoJS.enc.Utf8.parse({iv!r}.slice(0, 16));
const encrypted = CryptoJS.AES.encrypt({text!r}, key, {{
  iv, mode: CryptoJS.mode.CBC, padding: CryptoJS.pad.Pkcs7
}});
console.log(encrypted.toString());
''')
    else:
        py = _py(f'''
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
import base64

key = {key!r}.encode()[:{mode_bits // 8}].ljust({mode_bits // 8}, b"\\0")
iv = {iv!r}.encode()[:16].ljust(16, b"\\0")
raw = base64.b64decode({text!r})
cipher = Cipher(algorithms.AES(key), modes.CBC(iv), default_backend())
dec = cipher.decryptor()
plain = dec.update(raw) + dec.finalize()
unpadder = padding.PKCS7(128).unpadder()
print((unpadder.update(plain) + unpadder.finalize()).decode())
''')
        js = _js(f'''
const CryptoJS = require("crypto-js");
const key = CryptoJS.enc.Utf8.parse({key!r}.slice(0, {mode_bits // 8}));
const iv = CryptoJS.enc.Utf8.parse({iv!r}.slice(0, 16));
const decrypted = CryptoJS.AES.decrypt({text!r}, key, {{
  iv, mode: CryptoJS.mode.CBC, padding: CryptoJS.pad.Pkcs7
}});
console.log(decrypted.toString(CryptoJS.enc.Utf8));
''')
    return {"python": py, "javascript": js}


def _gen_aes_ecb(action, text, key, *_r, **_k):
    if action == "encrypt":
        py = _py(f'''
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
import base64

key = {key!r}.encode()[:32].ljust(32, b"\\0")
data = {text!r}.encode()
padder = padding.PKCS7(128).padder()
padded = padder.update(data) + padder.finalize()
cipher = Cipher(algorithms.AES(key), modes.ECB(), default_backend())
enc = cipher.encryptor()
print(base64.b64encode(enc.update(padded) + enc.finalize()).decode())
''')
        js = _js(f'''
const CryptoJS = require("crypto-js");
const key = CryptoJS.enc.Utf8.parse({key!r}.slice(0, 32));
const encrypted = CryptoJS.AES.encrypt({text!r}, key, {{
  mode: CryptoJS.mode.ECB, padding: CryptoJS.pad.Pkcs7
}});
console.log(encrypted.toString());
''')
    else:
        py = _py("# AES-ECB 解密\n" + _gen_aes_ecb("encrypt", text, key)["python"].replace("encryptor", "decryptor"))
        js = _js(f'''
const CryptoJS = require("crypto-js");
const key = CryptoJS.enc.Utf8.parse({key!r}.slice(0, 32));
const decrypted = CryptoJS.AES.decrypt({text!r}, key, {{
  mode: CryptoJS.mode.ECB, padding: CryptoJS.pad.Pkcs7
}});
console.log(decrypted.toString(CryptoJS.enc.Utf8));
''')
    return {"python": py, "javascript": js}


def _gen_aes_gcm(action, text, key, iv, aad, *_r, **_k):
    if action == "encrypt":
        py_body = (
            f"ct = aesgcm.encrypt(iv, {repr(text.encode())}, aad)\n"
            "print(base64.b64encode(ct).decode())"
        )
        js_body = (
            f"const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);\n"
            f"cipher.setAAD(aad);\n"
            f"let enc = cipher.update({repr(text)}, 'utf8');\n"
            "enc = Buffer.concat([enc, cipher.final(), cipher.getAuthTag()]);\n"
            "console.log(enc.toString('base64'));"
        )
    else:
        py_body = (
            f"raw = base64.b64decode({repr(text)})\n"
            "print(aesgcm.decrypt(iv, raw, aad).decode())"
        )
        js_body = "// 解密需分离 tag 与密文"

    py = _py(f'''
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64

key = {key!r}.encode()[:32].ljust(32, b"\\0")
iv = {iv!r}.encode()[:12].ljust(12, b"\\0")
aad = {aad!r}.encode()
aesgcm = AESGCM(key)
{py_body}
''')
    js = _js(f'''
const crypto = require("crypto");
const key = Buffer.from({key!r}.padEnd(32, "\\0").slice(0, 32));
const iv = Buffer.from({iv!r}.padEnd(12, "\\0").slice(0, 12));
const aad = Buffer.from({aad!r});
{js_body}
''')
    return {"python": py, "javascript": js}


def _gen_des_cbc(action, text, key, iv, *_r, **_k):
    py = _py(f'''
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
import base64

key = ({key!r}.encode()[:8].ljust(8, b"\\0")) * 3
iv = {iv!r}.encode()[:8].ljust(8, b"\\0")
# DES-CBC（通过 3DES 模拟单 DES）
''')
    js = _js(f'''
const CryptoJS = require("crypto-js");
const key = CryptoJS.enc.Utf8.parse({key!r}.slice(0, 8));
const iv = CryptoJS.enc.Utf8.parse({iv!r}.slice(0, 8));
const r = CryptoJS.AES.encrypt({text!r}, key, {{ iv, mode: CryptoJS.mode.CBC }});
console.log("请使用 crypto-js TripleDES/DES 模块");
''')
    return {"python": py + "# 参考上方 AES 示例替换为 TripleDES\n", "javascript": js}


def _gen_3des_cbc(action, text, key, iv, *_r, **_k):
    js = _js(f'''
const CryptoJS = require("crypto-js");
const key = CryptoJS.enc.Utf8.parse({key!r}.slice(0, 24));
const iv = CryptoJS.enc.Utf8.parse({iv!r}.slice(0, 8));
const r = CryptoJS.TripleDES.{ "encrypt" if action == "encrypt" else "decrypt" }({text!r}, key, {{ iv, mode: CryptoJS.mode.CBC, padding: CryptoJS.pad.Pkcs7 }});
console.log(r.toString());
''')
    py = _py(f"# 3DES-CBC\n# pip install cryptography\n# 参考 AES-CBC，algorithm 换为 algorithms.TripleDES(key24)\nkey={key!r}\niv={iv!r}\ntext={text!r}")
    return {"python": py, "javascript": js}


def _gen_sm4_ecb(action, text, key, *_r, **_k):
    py = _py(f'''
from gmssl.sm4 import CryptSM4, SM4_ENCRYPT, SM4_DECRYPT

key = {key!r}.encode()[:16].ljust(16, b"\\0")
crypt = CryptSM4()
crypt.set_key(key, {"SM4_ENCRYPT" if action == "encrypt" else "SM4_DECRYPT"})
# 需手动 PKCS7 填充
''')
    js = _js(f'''
const sm4 = require("sm-crypto").sm4;
const key = {key!r}.slice(0, 16);
console.log(sm4.{ "encrypt" if action == "encrypt" else "decrypt" }({text!r}, key));
''')
    return {"python": py, "javascript": js}


def _gen_sm4_cbc(action, text, key, iv, *_r, **_k):
    js = _js(f'''
const sm4 = require("sm-crypto").sm4;
console.log(sm4.{ "encrypt" if action == "encrypt" else "decrypt" }({text!r}, {key!r}.slice(0,16), {{
  mode: "cbc", iv: {iv!r}.slice(0,16)
}}));
''')
    py = _py(f"# SM4-CBC\nfrom gmssl.sm4 import CryptSM4, SM4_ENCRYPT\nkey={key!r}\niv={iv!r}")
    return {"python": py, "javascript": js}


def _gen_rsa(action, text, _k, _i, _a, public_key, private_key, *_r, **_k2):
    if action == "encrypt":
        py = _py(f'''
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
import base64

public_key = serialization.load_pem_public_key({public_key!r}.encode())
ct = public_key.encrypt(
    {text!r}.encode(),
    padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
)
print(base64.b64encode(ct).decode())
''')
        js = _js(f'''
const crypto = require("crypto");
const pub = {public_key!r};
const buf = crypto.publicEncrypt({{ key: pub, padding: crypto.constants.RSA_PKCS1_OAEP_PADDING }}, Buffer.from({text!r}));
console.log(buf.toString("base64"));
''')
    else:
        py = _py(f'''
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
import base64

private_key = serialization.load_pem_private_key({private_key!r}.encode(), password=None)
pt = private_key.decrypt(
    base64.b64decode({text!r}),
    padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
)
print(pt.decode())
''')
        js = _js(f'''
const crypto = require("crypto");
const priv = {private_key!r};
const buf = crypto.privateDecrypt({{ key: priv, padding: crypto.constants.RSA_PKCS1_OAEP_PADDING }}, Buffer.from({text!r}, "base64"));
console.log(buf.toString("utf8"));
''')
    return {"python": py, "javascript": js}


def _gen_sm2(action, text, _k, _i, _a, public_key, private_key, *_r, **_k2):
    if action == "encrypt":
        py = _py(f'''
from gmssl import sm2
crypt = sm2.CryptSM2("", {public_key!r})
print(crypt.encrypt({text!r}.encode()).hex())
''')
        js = _js(f'''
const sm2 = require("sm-crypto").sm2;
console.log(sm2.doEncrypt({text!r}, {public_key!r}, 1));
''')
    else:
        py = _py(f'''
from gmssl import sm2
crypt = sm2.CryptSM2({private_key!r}, {public_key!r})
print(crypt.decrypt(bytes.fromhex({text!r})))
''')
        js = _js(f'''
const sm2 = require("sm-crypto").sm2;
console.log(sm2.doDecrypt({text!r}, {private_key!r}, 1));
''')
    return {"python": py, "javascript": js}


_GENERATORS = {
    "base64": _gen_base64,
    "base64url": _gen_base64url,
    "hex": _gen_hex,
    "url": _gen_url,
    "md5": _gen_md5,
    "sha1": _gen_sha1,
    "sha256": _gen_sha256,
    "sha512": _gen_sha512,
    "sm3": _gen_sm3,
    "hmac-md5": _gen_hmac_md5,
    "hmac-sha256": _gen_hmac_sha256,
    "aes-128-cbc": lambda a, t, k, i, *r, **kw: _gen_aes_cbc(a, t, k, i, *r, mode_bits=128, **kw),
    "aes-256-cbc": lambda a, t, k, i, *r, **kw: _gen_aes_cbc(a, t, k, i, *r, mode_bits=256, **kw),
    "aes-256-ecb": _gen_aes_ecb,
    "aes-256-gcm": _gen_aes_gcm,
    "des-cbc": _gen_des_cbc,
    "3des-cbc": _gen_3des_cbc,
    "sm4-ecb": _gen_sm4_ecb,
    "sm4-cbc": _gen_sm4_cbc,
    "rsa-oaep": _gen_rsa,
    "sm2": _gen_sm2,
}
