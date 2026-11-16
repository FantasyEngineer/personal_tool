"""HTTPS 证书上下文：保证打包后的程序能找到可用的 CA 证书库。

用 python.org 版解释器打包时，PyInstaller 只带走 libssl/libcrypto，不会带上
解释器自身的 ``etc/openssl/cert.pem``。而 OpenSSL 的默认证书路径是编译期写死
的（例如 ``/Library/Frameworks/Python.framework/Versions/3.11/etc/openssl/cert.pem``），
在用户机器上这个目录并不存在，于是所有 HTTPS 请求都会报：

    [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
    unable to get local issuer certificate (_ssl.c:1006)

这里显式构造 SSLContext，按优先级找一个确实存在的 CA 库：
环境变量 → 随包分发的 cacert.pem → certifi → 系统 / Homebrew 证书库。
"""
import os
import ssl
import sys

# 显式指定证书库的环境变量（OpenSSL / requests / curl 三套命名都认）。
_ENV_KEYS = ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE")

_BUNDLED_NAMES = ("cacert.pem", "cert.pem", "ca-bundle.crt")

# 常见系统证书库位置（越靠前越优先）。
_SYSTEM_CANDIDATES = (
    "/opt/homebrew/etc/ca-certificates/cert.pem",
    "/opt/homebrew/etc/openssl@3/cert.pem",
    "/usr/local/etc/ca-certificates/cert.pem",
    "/usr/local/etc/openssl@3/cert.pem",
    "/etc/ssl/cert.pem",
    "/private/etc/ssl/cert.pem",
    "/etc/pki/tls/certs/ca-bundle.crt",
)

_cached_context = None
_cached_path = ""


def _project_root():
    """源码运行时的仓库根目录（toolbox_app/kit/netkit.py 往上三层）。"""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _search_roots():
    roots = []
    if getattr(sys, "_MEIPASS", ""):          # PyInstaller 解包目录
        roots.append(sys._MEIPASS)
    roots.append(_project_root())
    return [root for root in roots if root]


def candidate_files():
    """按优先级列出候选 CA 文件路径。"""
    files = []
    for key in _ENV_KEYS:
        value = os.environ.get(key)
        if value:
            files.append(value)
    for root in _search_roots():
        for name in _BUNDLED_NAMES:
            files.append(os.path.join(root, "assets", name))
    try:
        import certifi  # 构建/开发环境通常有
        files.append(certifi.where())
    except Exception:
        pass
    files.extend(_SYSTEM_CANDIDATES)
    return files


def ca_file():
    """第一个真实可用的 CA 文件；找不到返回空串。"""
    for path in candidate_files():
        try:
            if path and os.path.isfile(path) and os.path.getsize(path) > 0:
                return path
        except OSError:
            continue
    return ""


def https_context():
    """给 urllib 用的 SSLContext，缺证书库时退回系统默认行为。"""
    global _cached_context, _cached_path
    path = ca_file()
    if _cached_context is not None and path == _cached_path:
        return _cached_context
    if path:
        context = ssl.create_default_context(cafile=path)
    else:
        context = ssl.create_default_context()
    _cached_context, _cached_path = context, path
    return context
