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


# ---- 浏览与传输（列表 / 下载 / 删除 / 预签名） --------------------------------

_LIST_LIMIT = 1000          # ListObjectsV2 单页上限
_STREAM_THRESHOLD = 32 * 1024 * 1024   # 超过 32 MB 走流式上传，避免整份读进内存


def _localname(node, name):
    return node.tag.rsplit("}", 1)[-1] == name


def _parse_list_objects(body):
    """解析 ListObjectsV2 的 XML；MinIO 与 AWS 返回结构一致。"""
    root = ElementTree.fromstring(body)
    items, prefixes = [], []
    truncated, token = False, ""
    for child in root:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "Contents":
            item = {"key": "", "size": 0, "last_modified": "", "etag": ""}
            for field in child:
                field_tag = field.tag.rsplit("}", 1)[-1]
                if field_tag == "Key":
                    item["key"] = (field.text or "")
                elif field_tag == "Size":
                    try:
                        item["size"] = int(field.text or 0)
                    except ValueError:
                        item["size"] = 0
                elif field_tag == "LastModified":
                    item["last_modified"] = (field.text or "")
                elif field_tag == "ETag":
                    item["etag"] = (field.text or "").strip('"')
            if item["key"]:
                items.append(item)
        elif tag == "CommonPrefixes":
            for field in child:
                if _localname(field, "Prefix"):
                    prefixes.append(field.text or "")
        elif tag == "IsTruncated":
            truncated = (child.text or "").strip().lower() == "true"
        elif tag == "NextContinuationToken":
            token = (child.text or "").strip()
    return {"files": items, "folders": prefixes, "truncated": truncated, "token": token}


def s3_list_objects(settings, prefix="", delimiter="/", max_keys=_LIST_LIMIT, token=None, timeout=15):
    """列对象。delimiter 给 "/" 时按目录分层，返回 folders(公共前缀) 与 files。

    返回 {"prefix": 当前前缀, "folders": [...], "files": [...], "truncated": bool, "token": str}
    """
    _check_settings(settings)
    bucket = (settings.get("bucket") or "").strip()
    if not bucket:
        raise ValueError("请先在设置里填 Bucket")
    params = {"list-type": "2", "prefix": prefix or "", "max-keys": str(max(1, int(max_keys)))}
    if delimiter:
        params["delimiter"] = delimiter
    if token:
        params["continuation-token"] = token
    request = _sign_request("GET", _bucket_url(settings, bucket), params, _EMPTY_SHA256, settings)
    with _open(request, settings, timeout) as response:
        body = response.read().decode("utf-8", "replace")
    try:
        parsed = _parse_list_objects(body)
    except ElementTree.ParseError:
        raise RuntimeError("对象列表解析失败，返回内容不是合法的 XML")
    parsed["prefix"] = prefix or ""
    parsed["bucket"] = bucket
    return parsed


def s3_get_object_bytes(settings, key, limit=None, timeout=30):
    """取对象内容；给 limit 时用 Range 只取前 N 字节（预览文本用）。"""
    _check_settings(settings)
    bucket = (settings.get("bucket") or "").strip()
    if not bucket:
        raise ValueError("请先在设置里填 Bucket")
    url = _object_path(settings, bucket, key)
    request = _sign_request("GET", url, {}, _EMPTY_SHA256, settings)
    if limit:
        request.add_header("Range", "bytes=0-%d" % max(0, int(limit) - 1))
    with _open(request, settings, timeout) as response:
        return response.read(limit if limit else None)


def s3_download_file(settings, key, local_path, timeout=120, report=None):
    """流式下载到本地文件，边读边写，不在内存里堆整份数据。"""
    _check_settings(settings)
    bucket = (settings.get("bucket") or "").strip()
    if not bucket:
        raise ValueError("请先在设置里填 Bucket")
    url = _object_path(settings, bucket, key)
    request = _sign_request("GET", url, {}, _EMPTY_SHA256, settings)
    total = 0
    os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
    with _open(request, settings, timeout) as response, open(local_path, "wb") as output:
        length = int(response.headers.get("Content-Length") or 0)
        while True:
            chunk = response.read(262144)
            if not chunk:
                break
            output.write(chunk)
            total += len(chunk)
            if report and length:
                report(total, length)
    return total


def s3_delete_object(settings, key, timeout=15):
    _check_settings(settings)
    bucket = (settings.get("bucket") or "").strip()
    if not bucket:
        raise ValueError("请先在设置里填 Bucket")
    url = _object_path(settings, bucket, key)
    request = _sign_request("DELETE", url, {}, _EMPTY_SHA256, settings)
    try:
        with _open(request, settings, timeout) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
    return True


def s3_delete_prefix(settings, prefix, report=None, timeout=15):
    """删除目录：S3 没有目录概念，只能把该前缀下的对象逐个删掉。"""
    removed = 0
    token = None
    while True:
        page = s3_list_objects(settings, prefix=prefix, delimiter="", token=token, timeout=timeout)
        for item in page["files"]:
            s3_delete_object(settings, item["key"], timeout=timeout)
            removed += 1
            if report:
                report(removed, item["key"])
        if not page["truncated"] or not page["token"]:
            break
        token = page["token"]
    return removed


def _stream_put(settings, local_path, key, content_type, payload_hash, size, timeout=None, report=None):
    """大文件流式 PUT：先算好 payload hash，再用 http.client 分块发送。"""
    parsed = urllib.parse.urlsplit(_object_path(settings, settings["bucket"], key))
    host = parsed.netloc
    path = urllib.parse.quote(parsed.path or "/", safe="/-_.~")
    now = datetime.datetime.now(datetime.timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    region = settings.get("region") or "us-east-1"
    canonical_headers = ("host:%s\n" % host
                         + "x-amz-content-sha256:%s\n" % payload_hash
                         + "x-amz-date:%s\n" % amz_date)
    signed_headers = "host;x-amz-content-sha256;x-amz-date"
    canonical_request = "\n".join(["PUT", path, "", canonical_headers, signed_headers, payload_hash])
    scope = "%s/%s/s3/aws4_request" % (date_stamp, region)
    string_to_sign = "\n".join([_ALGORITHM, amz_date, scope,
                                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()])
    signature = hmac.new(_signing_key(settings["secret_key"], date_stamp, region),
                         string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    headers = {
        "Host": host,
        "x-amz-date": amz_date,
        "x-amz-content-sha256": payload_hash,
        "Authorization": "%s Credential=%s/%s, SignedHeaders=%s, Signature=%s"
                         % (_ALGORITHM, settings["access_key"], scope, signed_headers, signature),
        "Content-Type": content_type,
        "Content-Length": str(size),
    }
    if parsed.scheme == "https":
        context = https_context() if settings.get("verify_ssl", True) else ssl._create_unverified_context()
        import http.client as _http
        conn = _http.HTTPSConnection(host, timeout=timeout or 120, context=context)
    else:
        import http.client as _http
        conn = _http.HTTPConnection(host, timeout=timeout or 120)
    try:
        conn.putrequest("PUT", path, skip_host=True, skip_accept_encoding=True)
        for name, value in headers.items():
            conn.putheader(name, value)
        conn.endheaders()
        sent = 0
        with open(local_path, "rb") as source:
            while True:
                chunk = source.read(262144)
                if not chunk:
                    break
                conn.send(chunk)
                sent += len(chunk)
                if report:
                    report(sent, size)
        response = conn.getresponse()
        response.read()
        if response.status not in (200, 201):
            raise RuntimeError("上传失败：HTTP %d %s" % (response.status, response.reason))
    finally:
        conn.close()


def s3_upload_path(settings, local_path, key=None, timeout=None, report=None):
    """上传文件：小文件走内存 PUT，大文件走流式 PUT，都支持进度回调。"""
    _check_settings(settings)
    if not (settings.get("bucket") or "").strip():
        raise ValueError("请先在设置里填 Bucket")
    name = os.path.basename(local_path)
    key = key or name
    size = os.path.getsize(local_path)
    content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
    if size <= _STREAM_THRESHOLD:
        with open(local_path, "rb") as f:
            data = f.read()
        s3_put_object(settings, data, key, content_type, timeout or 120)
        if report:
            report(size, size)
        return key
    digest = hashlib.sha256()
    with open(local_path, "rb") as f:
        while True:
            chunk = f.read(1048576)
            if not chunk:
                break
            digest.update(chunk)
    _stream_put(settings, local_path, key, content_type, digest.hexdigest(), size,
                timeout=timeout, report=report)
    return key


def s3_presigned_url(settings, key, expires=3600, bucket=None, method="GET"):
    """生成预签名直链（默认 1 小时），拿出去就能在浏览器/下载器里直接开。"""
    _check_settings(settings)
    bucket = (bucket or settings.get("bucket") or "").strip()
    if not bucket:
        raise ValueError("请先在设置里填 Bucket")
    url = _object_path(settings, bucket, key)
    parsed = urllib.parse.urlsplit(url)
    host, path = parsed.netloc, urllib.parse.quote(parsed.path or "/", safe="/-_.~")
    now = datetime.datetime.now(datetime.timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = now.strftime("%Y%m%d")
    region = settings.get("region") or "us-east-1"
    scope = "%s/%s/s3/aws4_request" % (date_stamp, region)
    params = {
        "X-Amz-Algorithm": _ALGORITHM,
        "X-Amz-Credential": "%s/%s" % (settings["access_key"], scope),
        "X-Amz-Date": amz_date,
        "X-Amz-Expires": str(max(1, int(expires))),
        "X-Amz-SignedHeaders": "host",
    }
    query = _canonical_query(params)
    canonical_request = "\n".join([method, path, query, "host:%s\n" % host, "host", "UNSIGNED-PAYLOAD"])
    string_to_sign = "\n".join([_ALGORITHM, amz_date, scope,
                                hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()])
    signature = hmac.new(_signing_key(settings["secret_key"], date_stamp, region),
                         string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    return "%s://%s%s?%s&X-Amz-Signature=%s" % (parsed.scheme, host, path, query, signature)
