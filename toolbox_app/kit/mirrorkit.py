"""包管理器镜像源：npm/pip/Go/Maven/Docker 配置文件的读取与写入。

只操作各工具自己的配置文件，写入的 mirror 块都带可识别的 id，绝不覆盖
用户手写的配置；界面（下拉框与备份逻辑）在配置文件工具里。
"""
import json
import platform
import re

from toolbox_app.storage import (
    user_path, _app_config_dir, _read_text, _write_text, _ini_get, _ini_set,
)


def npm_config_path():
    return user_path(".npmrc")


def pip_config_path():
    return _app_config_dir("pip", "pip.ini" if platform.system() == "Windows" else "pip.conf")


def go_env_path():
    return _app_config_dir("go", "env")


def docker_daemon_path():
    return user_path(".docker", "daemon.json")


def maven_settings_path():
    return user_path(".m2", "settings.xml")


MAVEN_NOTE = "<!-- 这一段由 系统工具箱 的「镜像源」标签维护 -->"
MAVEN_OUR_ID = "toolbox-mirror"
MAVEN_MIRROR_RE = re.compile(r"<mirror\b[^>]*>.*?</mirror>", re.S | re.I)
MAVEN_OURS_RE = re.compile(
    r"<mirror\b[^>]*>(?:(?!</mirror>).)*?<id>\s*" + MAVEN_OUR_ID + r"\s*</id>(?:(?!</mirror>).)*?</mirror>",
    re.S | re.I)
MAVEN_MIRROR_OF_RE = re.compile(r"<mirrorOf\b[^>]*>([^<]*)</mirrorOf>", re.I)
MAVEN_URL_RE = re.compile(r"<url\b[^>]*>([^<]*)</url>", re.I)


def _xml_escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def maven_central_url():
    text = _read_text(maven_settings_path())
    if not text:
        return None
    for block in MAVEN_MIRROR_RE.finditer(text):
        of = MAVEN_MIRROR_OF_RE.search(block.group(0))
        if of and "central" in [p.strip().lower() for p in of.group(1).split(",")]:
            url = MAVEN_URL_RE.search(block.group(0))
            if url:
                return url.group(1).strip()
    return None


def _maven_mirror_block(url, label):
    return ('<mirror>\n      <id>%s</id>\n      <mirrorOf>central</mirrorOf>\n'
            '      <name>%s</name>\n      <url>%s</url>\n    </mirror>'
            % (MAVEN_OUR_ID, _xml_escape(label), _xml_escape(url)))


def _maven_document(mirror):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n%s\n<settings>\n  <mirrors>\n    %s\n'
            '  </mirrors>\n</settings>\n' % (MAVEN_NOTE, mirror))


def maven_set_central(url, label):
    """Only ever touch the mirror block we own, so a hand-written settings.xml survives."""
    path = maven_settings_path()
    text = _read_text(path)
    mirror = _maven_mirror_block(url, label) if url else None
    if text is None:
        if url is None:
            return
        _write_text(path, _maven_document(mirror))
        return
    ours = MAVEN_OURS_RE.search(text)
    if ours:
        if url:
            _write_text(path, text[:ours.start()] + mirror + text[ours.end():])
            return
        start = text.rfind("\n", 0, ours.start()) + 1
        end = text.find("\n", ours.end())
        end = len(text) if end < 0 else end + 1
        _write_text(path, text[:start] + text[end:])
        return
    if MAVEN_MIRROR_RE.search(text):
        raise RuntimeError("settings.xml 里已有别人写的 mirrors，工具不覆盖，请手动编辑：\n%s" % path)
    if url is None:
        return
    lowered = text.lower()
    if "<mirrors" in lowered:
        close = lowered.find("</mirrors>", lowered.index("<mirrors"))
        if close < 0:
            raise RuntimeError("settings.xml 的 <mirrors> 没有闭合，请手动修正：%s" % path)
        _write_text(path, text[:close].rstrip() + "\n    " + mirror + "\n  " + text[close:].lstrip())
        return
    if "<settings" not in lowered:
        raise RuntimeError("settings.xml 缺少 <settings> 根节点，请手动修正：%s" % path)
    close = lowered.rindex("</settings>")
    _write_text(path, text[:close] + "  <mirrors>\n    %s\n  </mirrors>\n" % mirror + text[close:])


def docker_read_mirror():
    text = _read_text(docker_daemon_path())
    if not text:
        return None
    data = json.loads(text)
    mirrors = data.get("registry-mirrors") if isinstance(data, dict) else None
    return mirrors[0] if isinstance(mirrors, list) and mirrors else None


def docker_write_mirror(url):
    path = docker_daemon_path()
    text = _read_text(path)
    data = {}
    if text:
        try:
            data = json.loads(text)
        except ValueError:
            raise RuntimeError("daemon.json 不是合法 JSON，请手动修正：\n%s" % path)
        if not isinstance(data, dict):
            raise RuntimeError("daemon.json 顶层应为对象，请手动修正：\n%s" % path)
        if url is None:
            if "registry-mirrors" not in data:
                return
            data.pop("registry-mirrors")
        else:
            data["registry-mirrors"] = [url]
        _write_text(path, json.dumps(data, indent=4, ensure_ascii=False))
        return
    if url is None:
        return
    _write_text(path, json.dumps({"registry-mirrors": [url]}, indent=4, ensure_ascii=False))


class _MirrorTarget:
    def __init__(self, name, read, write, path_of, options, note=""):
        self.name, self.read, self.write, self.path_of = name, read, write, path_of
        self.options, self.note = options, note


CUSTOM_MIRROR = "__custom__"


def mirror_targets():
    npm = [
        ("官方", "https://registry.npmjs.org/"),
        ("淘宝 npmmirror", "https://registry.npmmirror.com"),
        ("腾讯云", "https://mirrors.cloud.tencent.com/npm/"),
    ]
    pip = [
        ("官方默认", None),
        ("清华", "https://pypi.tuna.tsinghua.edu.cn/simple"),
        ("阿里云", "https://mirrors.aliyun.com/pypi/simple/"),
        ("腾讯云", "https://mirrors.cloud.tencent.com/pypi/simple"),
    ]
    go = [
        ("官方", "https://proxy.golang.org,direct"),
        ("goproxy.cn", "https://goproxy.cn,direct"),
        ("阿里云", "https://mirrors.aliyun.com/goproxy/,direct"),
    ]
    maven = [
        ("官方（不设镜像）", None),
        ("阿里云", "https://maven.aliyun.com/repository/public"),
        ("华为云", "https://repo.huaweicloud.com/repository/maven/"),
    ]
    docker = [
        ("官方（不设镜像）", None),
        ("DaoCloud 公共加速", "https://docker.m.daocloud.io"),
        ("清华", "https://docker.mirrors.tuna.tsinghua.edu.cn"),
    ]
    return [
        _MirrorTarget("npm / yarn",
                      lambda: _ini_get(npm_config_path(), None, "registry"),
                      lambda url: _ini_set(npm_config_path(), None, "registry", url, tight=True),
                      npm_config_path, npm,
                      "yarn 也读这个 .npmrc"),
        _MirrorTarget("pip",
                      lambda: _ini_get(pip_config_path(), "global", "index-url"),
                      lambda url: _ini_set(pip_config_path(), "global", "index-url", url),
                      pip_config_path, pip,
                      "等价于 pip config set global.index-url"),
        _MirrorTarget("Go modules",
                      lambda: _ini_get(go_env_path(), None, "GOPROXY"),
                      lambda url: _ini_set(go_env_path(), None, "GOPROXY", url, tight=True),
                      go_env_path, go,
                      "等价于 go env -w GOPROXY，新开的终端立刻生效"),
        _MirrorTarget("Maven central",
                      maven_central_url,
                      lambda url: maven_set_central(url, "personal_toolbox mirror"),
                      maven_settings_path, maven,
                      "只改 central 的镜像；已有自定义 mirrors 时不覆盖"),
        _MirrorTarget("Docker Hub",
                      docker_read_mirror,
                      docker_write_mirror,
                      docker_daemon_path, docker,
                      "改完需要重启 Docker 才生效"),
    ]
