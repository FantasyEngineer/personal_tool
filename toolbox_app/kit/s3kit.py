"""S3 / MinIO 接入：配置读写与最小的 SigV4 签名请求。

刻意不引入 boto3/botocore：装箱后那套会给安装包再加十几 MB，
而这里只需要「列桶 / 上传 / 预签名下载」这几个动作，标准库足够。
"""
import datetime
import hashlib
import hmac
import json
import mimetypes
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ElementTree

from toolbox_app.constants import S3_SETTINGS_PATH
from toolbox_app.kit.netkit import https_context

DEFAULT_S3_SETTINGS = {
    "endpoint": "",        # 如 http://192.168.1.12:9000 或 https://域名:9444
    "region": "us-east-1",
    "access_key": "",
    "secret_key": "",
    "bucket": "",          # 可留空，测试连接时只列桶
    "path_style": True,    # MinIO 默认 path-style；虚拟主机风格才关掉
    "verify_ssl": True,    # 自签证书的局域网 HTTPS 可关掉
}

_EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
_ALGORITHM = "AWS4-HMAC-SHA256"


# ---- 配置读写 -------------------------------------------------------------

def load_s3_settings():
    settings = dict(DEFAULT_S3_SETTINGS)
    try:
        with open(S3_SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return settings
    if not isinstance(data, dict):
        return settings
    for key in ("endpoint", "region", "access_key", "secret_key", "bucket"):
        value = data.get(key)
        if isinstance(value, str):
            settings[key] = value.strip()
    for key in ("path_style", "verify_ssl"):
        if isinstance(data.get(key), bool):
            settings[key] = data[key]
    return settings


def save_s3_settings(settings):
    merged = dict(DEFAULT_S3_SETTINGS)
    for key in merged:
        if key in settings:
            merged[key] = settings[key]
    os.makedirs(os.path.dirname(S3_SETTINGS_PATH), exist_ok=True)
    temporary = S3_SETTINGS_PATH + ".tmp"
    try:
        with open(temporary, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        os.replace(temporary, S3_SETTINGS_PATH)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)
    return merged


# ---- SigV4 -------------------------------------------------------------

def _quote(value, safe="-_.~"):
    return urllib.parse.quote(str(value), safe=safe)


def _canonical_query(params):
    pairs = sorted((_quote(k), _quote(v)) for k, v in (params or {}).items())
    return "&".join("%s=%s" % (k, v) for k, v in pairs)


def _sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _signing_key(secret, date, region):
    # 第一层的密钥是「AWS4 + SecretKey」，漏掉前缀会导致 SignatureDoesNotMatch
    k_date = _sign(("AWS4" + secret).encode("utf-8"), date)
    k_region = _sign(k_date, region)
    k_service = _sign(k_region, "s3")
    return _sign(k_service, "aws4_request")


def _sign_request(method, url, params, payload_hash, settings):
    """返回带 SigV4 签名头的 urllib Request，签名算法见 AWS S3 文档。"""
    parsed = urllib.parse.urlsplit(url)
    host = parsed.netloc
    path = parsed.path or "/"
    now = datetime.datetime.now(datetime.timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    region = settings.get("region") or "us-east-1"

    canonical_headers = ("host:%s\n" % host
                         + "x-amz-content-sha256:%s\n" % payload_hash
                         + "x-amz-date:%s\n" % amz_date)
    signed_headers = "host;x-amz-content-sha256;x-amz-date"
    canonical_request = "\n".join([
        method, path, _canonical_query(params), canonical_headers, signed_headers, payload_hash
    ])
    scope = "%s/%s/s3/aws4_request" % (date_stamp, region)
    string_to_sign = "\n".join([
        _ALGORITHM, amz_date, scope,
        hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
    ])
    signature = hmac.new(
        _signing_key(settings["secret_key"], date_stamp, region),
        string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    query = _canonical_query(params)
    final_url = url + ("?" + query if query else "")
    headers = {
        "Host": host,
        "x-amz-date": amz_date,
        "x-amz-content-sha256": payload_hash,
        "Authorization": "%s Credential=%s/%s, SignedHeaders=%s, Signature=%s"
                         % (_ALGORITHM, settings["access_key"], scope, signed_headers, signature),
    }
    return urllib.request.Request(final_url, headers=headers, method=method)


def _open(request, settings, timeout=10):
    if settings.get("verify_ssl", True):
        context = https_context()
    else:
        # 局域网自签证书的 HTTPS 入口：用户明确关掉校验时才这样连
        context = ssl._create_unverified_context()
    return urllib.request.urlopen(request, timeout=timeout, context=context)


def _object_path(settings, bucket, key=None):
    """拼出对象/桶的 URL 路径；path-style 时桶名进路径，否则进主机名。"""
    endpoint = settings["endpoint"].rstrip("/")
    if settings.get("path_style", True) or not bucket:
        path = "/" + _quote(bucket, safe="") if bucket else "/"
        if key:
            path += "/" + "/".join(_quote(part, safe="") for part in key.split("/"))
        return endpoint + path
    # 虚拟主机风格：bucket 作为子域名
    scheme, rest = endpoint.split("://", 1)
    return "%s://%s.%s" % (scheme, bucket, rest)


def _bucket_url(settings, bucket):
    return _object_path(settings, bucket)


def _check_settings(settings):
    missing = [label for key, label in (("endpoint", "服务地址"), ("access_key", "Access Key"),
                                        ("secret_key", "Secret Key"))
               if not (settings.get(key) or "").strip()]
    if missing:
        raise ValueError("请先填写：" + "、".join(missing))
    if not settings["endpoint"].startswith(("http://", "https://")):
        raise ValueError("服务地址要以 http:// 或 https:// 开头")


# ---- 对外动作 -------------------------------------------------------------

def s3_list_buckets(settings, timeout=10):
    """列桶（GET /），返回桶名列表；同时用来验证密钥是否有效。"""
    _check_settings(settings)
    request = _sign_request("GET", _object_path(settings, ""), {}, _EMPTY_SHA256, settings)
    with _open(request, settings, timeout) as response:
        body = response.read().decode("utf-8", "replace")
    names = []
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError:
        root = None
    if root is not None:
        for node in root.iter():
            if node.tag.rsplit("}", 1)[-1] == "Bucket":
                for child in node:
                    if child.tag.rsplit("}", 1)[-1] == "Name":
                        names.append((child.text or "").strip())
    return [name for name in names if name]


def s3_bucket_exists(settings, bucket=None, timeout=10):
    """HEAD 桶判断是否存在；不存在时 MinIO 返回 404。"""
    _check_settings(settings)
    bucket = (bucket or settings.get("bucket") or "").strip()
    if not bucket:
        raise ValueError("请先填写 Bucket")
    request = _sign_request("HEAD", _bucket_url(settings, bucket), {}, _EMPTY_SHA256, settings)
    try:
        with _open(request, settings, timeout) as response:
            response.read()
        return True
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        raise


def s3_make_bucket(settings, bucket=None, timeout=10):
    """建桶；已存在时按幂等处理（MinIO 对同区域重复建桶返回 409/200）。"""
    _check_settings(settings)
    bucket = (bucket or settings.get("bucket") or "").strip()
    if not bucket:
        raise ValueError("请先填写 Bucket")
    request = _sign_request("PUT", _bucket_url(settings, bucket), {}, _EMPTY_SHA256, settings)
    try:
        with _open(request, settings, timeout) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        if exc.code not in (409, 200):
            raise
        return bucket
    return bucket


def s3_test(settings, timeout=10):
    """连通性自检：能否列出桶、指定桶是否存在。返回 (是否通过, 说明)。"""
    try:
        buckets = s3_list_buckets(settings, timeout=timeout)
    except ValueError as exc:
        return False, str(exc)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:200]
        message = "鉴权失败（HTTP %d）" % exc.code if exc.code in (401, 403) else \
                  "请求失败（HTTP %d）" % exc.code
        return False, message + ("：" + detail if detail else "")
    except Exception as exc:      # URLError / 超时 / SSL
        return False, "连不上：%s" % exc

    message = "连接成功，共 %d 个桶" % len(buckets)
    bucket = (settings.get("bucket") or "").strip()
    if bucket:
        if bucket in buckets:
            message += "；桶 %s 已存在" % bucket
        else:
            message += "；桶 %s 不存在（可先建桶或换个名字）" % bucket
    elif buckets:
        message += "（%s）" % "、".join(buckets[:5])
    return True, message


def s3_put_object(settings, data, key, content_type=None, timeout=60):
    """上传一段字节到 bucket/key，返回对象的完整地址（不含签名）。"""
    _check_settings(settings)
    bucket = (settings.get("bucket") or "").strip()
    if not bucket:
        raise ValueError("请先在设置里填 Bucket")
    if not key:
        raise ValueError("对象名不能为空")
    if not s3_bucket_exists(settings, bucket, timeout):
        s3_make_bucket(settings, bucket, timeout)
    payload_hash = hashlib.sha256(data).hexdigest()
    url = _object_path(settings, bucket, key)
    request = _sign_request("PUT", url, {}, payload_hash, settings)
    request.data = data
    request.add_header("Content-Type", content_type or "application/octet-stream")
    request.add_header("Content-Length", str(len(data)))
    with _open(request, settings, timeout) as response:
        response.read()
    return url


def s3_upload_file(settings, local_path, key=None, timeout=60):
    """上传本地文件；key 缺省用 文件名，返回 (key, url)。"""
    name = os.path.basename(local_path)
    key = key or name
    with open(local_path, "rb") as f:
        data = f.read()
    content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
    return key, s3_put_object(settings, data, key, content_type, timeout)
