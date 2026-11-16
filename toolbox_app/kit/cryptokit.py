"""编码与安全：Base64URL、JWT 解析验签、AES 对称加解密、RSA/HMAC/口令哈希。

纯逻辑，不依赖 Qt；算法表与格式常量一并放这里，界面只负责取值与展示。
"""
import base64
import datetime
import hashlib
import hmac
import json
import os
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.asymmetric import utils as der_utils
from cryptography.hazmat.primitives.asymmetric.ec import ECDSA
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

JWT_HS_ALGS = {"HS256": hashlib.sha256, "HS384": hashlib.sha384, "HS512": hashlib.sha512}
JWT_PUB_ALGS = {"RS256": hashes.SHA256, "RS384": hashes.SHA384, "RS512": hashes.SHA512,
                "PS256": hashes.SHA256, "PS384": hashes.SHA384, "PS512": hashes.SHA512,
                "ES256": hashes.SHA256, "ES384": hashes.SHA384, "ES512": hashes.SHA512}
# ES* 的签名是定长 r||s；ES512 走 P-521，所以每段 66 字节
JWT_EC_PART = {"ES256": 32, "ES384": 48, "ES512": 66}
JWT_TIME_CLAIMS = (("iat", "签发"), ("nbf", "生效"), ("exp", "过期"))


def b64url_encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(text):
    try:
        return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    except ValueError:
        raise ValueError("Base64URL 段解不开：%s" % text[:24])


def jwt_parts(token):
    """拆 JWT，返回 (头部, 载荷, 签名, 待签名内容)。"""
    parts = token.strip().split(".")
    if len(parts) < 2:
        raise ValueError("看不到 . 分隔的段，不像 JWT")
    try:
        header = json.loads(b64url_decode(parts[0]).decode("utf-8", "replace"))
        payload = json.loads(b64url_decode(parts[1]).decode("utf-8", "replace"))
    except ValueError:
        raise ValueError("头部或载荷不是 JSON，检查是否粘全了三段")
    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise ValueError("头部和载荷得是 JSON 对象")
    signature = b64url_decode(parts[2]) if len(parts) > 2 and parts[2] else b""
    return header, payload, signature, ".".join(parts[:2]).encode()


def load_pem_key(text):
    """先当公钥读，读不通再当私钥读；私钥里也带公钥，本地自测方便。"""
    data = text.strip().encode("utf-8")
    try:
        return serialization.load_pem_public_key(data)
    except ValueError:
        return serialization.load_pem_private_key(data, password=None)


def as_public(key):
    """私钥对象顺手取它的公钥；本来就是公钥则原样返回。"""
    return key.public_key() if hasattr(key, "public_key") else key


def jwt_verify(alg, signing_input, signature, key_text):
    """返回 (True/False/None, 说明)；None 表示手头条件验不了。"""
    if alg.lower() == "none":
        return None, "alg=none，这个 token 压根没签名，别信"
    if not signature:
        return None, "缺少签名段，只能看内容"
    if alg in JWT_HS_ALGS:
        if not key_text.strip():
            return None, "要验 %s 还需要填共享密钥" % alg
        mac = hmac.new(key_text.encode("utf-8"), signing_input, JWT_HS_ALGS[alg]).digest()
        if hmac.compare_digest(mac, signature):
            return True, "%s 验签通过（共享密钥）" % alg
        return False, "%s 验签失败：密钥不对，或 token 被改过" % alg
    if alg not in JWT_PUB_ALGS:
        return None, "算法 %s 还不支持验签，只看内容" % alg
    if not key_text.strip():
        return None, "要验 %s 还需要填 PEM 公钥" % alg
    hash_cls = JWT_PUB_ALGS[alg]
    try:
        public = as_public(load_pem_key(key_text))
    except Exception as e:
        return None, "公钥读不出来：%s" % e
    try:
        if alg.startswith("RS"):
            public.verify(signature, signing_input, asym_padding.PKCS1v15(), hash_cls())
        elif alg.startswith("PS"):
            public.verify(signature, signing_input,
                          asym_padding.PSS(mgf=asym_padding.MGF1(hash_cls()),
                                            salt_length=hash_cls().digest_size), hash_cls())
        else:
            half = JWT_EC_PART[alg]
            if len(signature) != half * 2:
                return None, "%s 签名长度应为 %d 字节，实际 %d" % (alg, half * 2, len(signature))
            r = int.from_bytes(signature[:half], "big")
            s = int.from_bytes(signature[half:], "big")
            public.verify(der_utils.encode_dss_signature(r, s), signing_input, ECDSA(hash_cls()))
    except InvalidSignature:
        return False, "%s 验签失败：签名和密钥不匹配" % alg
    except Exception as e:
        return None, "%s 没法验签：%s" % (alg, e)
    return True, "%s 验签通过" % alg


def span_text(seconds):
    seconds = int(abs(seconds))
    for unit, size in (("天", 86400), ("小时", 3600), ("分钟", 60)):
        if seconds >= size:
            return "%d%s" % (seconds // size, unit)
    return "%d秒" % seconds


def jwt_claim_notes(payload):
    notes = []
    now = time.time()
    for name, cn in JWT_TIME_CLAIMS:
        val = payload.get(name)
        if not isinstance(val, (int, float)):
            continue
        local = datetime.datetime.fromtimestamp(val).strftime("%Y-%m-%d %H:%M:%S")
        note = "%s %s：%s" % (cn, name, local)
        if name == "exp":
            note += "（已过期 %s）" % span_text(val - now) if val < now else "（还剩 %s）" % span_text(val - now)
        notes.append(note)
    return notes


AES_MODES = ("AES-256-GCM", "AES-128-GCM", "AES-256-CBC", "AES-256-CTR")
AES_KEY_SOURCES = ("口令派生（推荐）", "Hex 原始密钥")
AES_KEY_BYTES = {"AES-256-GCM": 32, "AES-128-GCM": 16, "AES-256-CBC": 32, "AES-256-CTR": 32}
AES_IV_BYTES = {"AES-256-GCM": 12, "AES-128-GCM": 12, "AES-256-CBC": 16, "AES-256-CTR": 16}
AES_MAGIC = b"TBX1"
AES_PBKDF2_ROUNDS = 210000
AES_SALT_BYTES = 16


def encode_blob(data, encoding):
    return data.hex() if encoding == "Hex" else base64.b64encode(data).decode()


def decode_blob(text, encoding):
    text = text.strip()
    if not text:
        raise ValueError("先输入密文")
    if encoding == "Hex":
        return bytes.fromhex("".join(text.split()))
    return base64.b64decode("".join(text.split()), validate=True)


def pbkdf2_key(passphrase, salt, length, rounds=AES_PBKDF2_ROUNDS):
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=length, salt=salt,
                      iterations=rounds).derive(passphrase.encode("utf-8"))


def aes_run(key, iv, mode_name, data, encrypt, aad):
    if mode_name.endswith("GCM"):
        box = AESGCM(key)
        return box.encrypt(iv, data, aad) if encrypt else box.decrypt(iv, data, aad)
    if mode_name.endswith("CBC"):
        if encrypt:
            padder = sym_padding.PKCS7(128).padder()
            data = padder.update(data) + padder.finalize()
    cipher = Cipher(algorithms.AES(key),
                    modes.CBC(iv) if mode_name.endswith("CBC") else modes.CTR(iv))
    engine = cipher.encryptor() if encrypt else cipher.decryptor()
    out = engine.update(data) + engine.finalize()
    if mode_name.endswith("CBC") and not encrypt:
        unpadder = sym_padding.PKCS7(128).unpadder()
        out = unpadder.update(out) + unpadder.finalize()
    return out


def aes_encrypt(data, mode_name, passphrase=None, raw_key=None):
    """TBX1 | 模式 | 密钥来源 | salt | IV | 密文；头部当作 GCM 的附加认证数据。"""
    idx = AES_MODES.index(mode_name)
    size = AES_KEY_BYTES[mode_name]
    iv = os.urandom(AES_IV_BYTES[mode_name])
    if passphrase is None:
        salt, key, flag = b"", raw_key, 1
    else:
        salt = os.urandom(AES_SALT_BYTES)
        key = pbkdf2_key(passphrase, salt, size)
        flag = 0
    head = AES_MAGIC + bytes([idx, flag]) + salt + iv
    return head + aes_run(key, iv, mode_name, data, True, head)


def aes_decrypt(blob, passphrase=None, raw_key=None):
    if not blob.startswith(AES_MAGIC):
        raise ValueError("密文没有 TBX1 头，不是本工具加密的；确认一下输出编码选对了吗")
    idx, flag = blob[4], blob[5]
    if idx >= len(AES_MODES) or flag > 1:
        raise ValueError("密文头部编号不认识")
    mode_name = AES_MODES[idx]
    size = AES_KEY_BYTES[mode_name]
    pos = len(AES_MAGIC) + 2
    salt = b""
    if flag == 0:
        salt = blob[pos:pos + AES_SALT_BYTES]
        pos += AES_SALT_BYTES
    iv = blob[pos:pos + AES_IV_BYTES[mode_name]]
    pos += AES_IV_BYTES[mode_name]
    key = pbkdf2_key(passphrase, salt, size) if passphrase is not None else raw_key
    return aes_run(key, iv, mode_name, blob[pos:], False, blob[:pos])


def rsa_oaep():
    return asym_padding.OAEP(mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                            algorithm=hashes.SHA256(), label=None)


def rsa_plain_limit(bits):
    """OAEP-SHA256 的明文上限：key_size - 2*digest - 2。"""
    return bits // 8 - 2 * 32 - 2


def decode_maybe_text(data):
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return base64.b64encode(data).decode()


HMAC_ALGS = {"SHA-1": hashlib.sha1, "SHA-256": hashlib.sha256,
             "SHA-384": hashlib.sha384, "SHA-512": hashlib.sha512}


PASS_ALGS = ("PBKDF2-SHA256", "scrypt")
PASS_ROUNDS = 210000
PASS_SCRYPT_N = 16384
PASS_SCRYPT_R = 8
PASS_SCRYPT_P = 1
PASS_HASH_BYTES = 32
PASS_SALT_BYTES = 16


def passhash_derive(tag, passphrase, salt, params=None):
    """不带 params 用默认值；PBKDF2 传次数，scrypt 传 (N, r, p)。"""
    if tag == "pbkdf2-sha256":
        return pbkdf2_key(passphrase, salt, PASS_HASH_BYTES,
                          int(params) if params else PASS_ROUNDS)
    n, r, p = params or (PASS_SCRYPT_N, PASS_SCRYPT_R, PASS_SCRYPT_P)
    n, r, p = int(n), int(r), int(p)
    if n < 2 or n & (n - 1):
        raise ValueError("scrypt 的 N 必须是 2 的整数次幂，串里写的是 %d" % n)
    return hashlib.scrypt(passphrase.encode("utf-8"), salt=salt, n=n, r=r, p=p,
                          dklen=PASS_HASH_BYTES, maxmem=128 * n * r * p + (1 << 20))


def passhash_make(alg, passphrase):
    """自带盐和参数的字符串，回头可以直接校验，不用记参数。"""
    if not passphrase:
        raise ValueError("口令不能为空")
    salt = os.urandom(PASS_SALT_BYTES)
    digest = passhash_derive(alg_tag(alg), passphrase, salt)
    if alg_tag(alg) == "pbkdf2-sha256":
        return "$pbkdf2-sha256$%d$%s$%s" % (PASS_ROUNDS, base64.b64encode(salt).decode(),
                                           base64.b64encode(digest).decode())
    return "$scrypt$%d$%d$%d$%s$%s" % (PASS_SCRYPT_N, PASS_SCRYPT_R, PASS_SCRYPT_P,
                                      base64.b64encode(salt).decode(),
                                      base64.b64encode(digest).decode())


def alg_tag(name):
    return "pbkdf2-sha256" if name == "PBKDF2-SHA256" else "scrypt"


def passhash_parse(text):
    """解析成 (算法, 参数, salt, 哈希)，格式不对就报错。"""
    parts = text.strip().split("$")
    if parts and not parts[0]:
        parts = parts[1:]
    if not parts or not parts[0]:
        raise ValueError("应是 $pbkdf2-sha256$次数$salt$hash 或 $scrypt$N$r$p$salt$hash")
    tag = parts[0]
    if tag == "pbkdf2-sha256":
        if len(parts) != 4:
            raise ValueError("PBKDF2 串应是 $pbkdf2-sha256$次数$salt$hash")
        return tag, int(parts[1]), base64.b64decode(parts[2]), base64.b64decode(parts[3])
    if tag == "scrypt":
        if len(parts) != 6:
            raise ValueError("scrypt 串应是 $scrypt$N$r$p$salt$hash")
        return (tag, (int(parts[1]), int(parts[2]), int(parts[3])),
                base64.b64decode(parts[4]), base64.b64decode(parts[5]))
    raise ValueError("不认识的算法：%s" % tag)


def passhash_verify(stored, passphrase):
    tag, params, salt, digest = passhash_parse(stored)
    if passphrase == "":
        raise ValueError("先输入口令")
    mine = passhash_derive(tag, passphrase, salt, params)
    return hmac.compare_digest(mine, digest)
