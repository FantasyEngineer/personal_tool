"""应用内更新的纯逻辑：版本号解析、下载地址校验与更新包解压。

不依赖 QtWidgets；QStandardPaths 只是取「下载」目录的值类型。QThread/QDialog 与
平台安装脚本仍在界面层。
"""
import base64
import json
import ntpath
import os
import posixpath
import re
import stat
import sys
import urllib.parse
import urllib.request
import zipfile
import plistlib

from PyQt5.QtCore import QStandardPaths

from toolbox_app.constants import APP_VERSION, UPDATE_TARGET_PATH
from toolbox_app.kit.netkit import https_context


def update_version_parts(version):
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]{1,5}(?:\.[0-9]{1,5}){1,3}", version):
        raise ValueError("更新服务器返回了无效的版本号。")
    parts = tuple(int(part) for part in version.split('.'))
    return parts + (0,) * (4 - len(parts))


def validate_update_url(url):
    if not isinstance(url, str) or any(ord(char) < 33 for char in url):
        raise ValueError("更新下载地址无效。")
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password or parts.fragment:
        raise ValueError("更新仅接受不含账号信息的 HTTPS 下载地址。")


UPDATE_ENDPOINTS = (
    ("Gitee 接口",
     "https://gitee.com/api/v5/repos/jimmy_hou/personal_tool/contents/version.json?ref=main"),
    ("GitHub 接口",
     "https://api.github.com/repos/FantasyEngineer/personal_tool/contents/version.json?ref=main"),
    ("GitHub 原文",
     "https://raw.githubusercontent.com/FantasyEngineer/personal_tool/main/version.json"),
    ("Gitee 原文",
     "https://gitee.com/jimmy_hou/personal_tool/raw/main/version.json"),
)


class UpdateFetchError(Exception):
    """所有更新源都连不上时的汇总错误，消息里逐条列出每个源的失败原因。"""


def _read_version_bytes(url, timeout):
    validate_update_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": "Toolbox/" + APP_VERSION})
    opener = urllib.request.build_opener(
        UpdateRedirectHandler(), urllib.request.HTTPSHandler(context=https_context()))
    with opener.open(request, timeout=timeout) as response:
        validate_update_url(response.geturl())
        content = response.read(1024 * 1024 + 1)
    if len(content) > 1024 * 1024:
        raise ValueError("更新信息超出大小限制。")
    return content


def decode_version_envelope(content):
    """Gitee / GitHub 的 contents 接口都返回 base64 信封，这里统一拆开。"""
    envelope = json.loads(content.decode("utf-8"))
    if (not isinstance(envelope, dict) or envelope.get("encoding") != "base64"
            or not isinstance(envelope.get("content"), str)):
        raise ValueError("更新服务器返回的文件信息无效。")
    data = json.loads(base64.b64decode(envelope["content"], validate=True).decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("更新服务器返回的内容不是版本信息。")
    return data


def fetch_version_data(timeout=8):
    """按 UPDATE_ENDPOINTS 顺序挨个试，拿到 version.json 的内容就返回。

    有些网络（尤其国内访问 gitee 的 raw 文件）会在 TLS 握手后直接 RST，
    报 WinError 10054 / 「远程主机强制关闭了一个现有的连接」，所以单源必然不稳。
    """
    failures = []
    for name, url in UPDATE_ENDPOINTS:
        try:
            return decode_version_envelope(_read_version_bytes(url, timeout))
        except Exception as exc:
            failures.append("%s：%s" % (name, exc))
    raise UpdateFetchError(
        "所有更新源都连不上（多半是网络或代理拦了这些地址）：\n"
        + "\n".join("- " + item for item in failures)
        + "\n\n可以稍后重试，或手动从 GitHub Release 下载新版："
          "\nhttps://github.com/FantasyEngineer/personal_tool/releases/latest"
    )


class UpdateRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_update_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def mac_app_bundle(path=None):
    """返回可执行文件所在的 .app 路径，不在 .app 内运行时返回空串。"""
    path = path or sys.executable
    marker = path.find('.app/')
    return path[:marker + 4] if marker > 0 else ""


def mac_app_translocated(path):
    """Gatekeeper 会把「下载」里直接运行的 app 挂到只读虚拟目录，这种路径不能原地更新。"""
    return '/AppTranslocation/' in path


def mac_downloads_dir():
    return os.path.realpath(QStandardPaths.writableLocation(QStandardPaths.DownloadLocation))


def mac_applications_dir():
    """优先系统级「应用程序」目录，不可写时退回用户级 ~/Applications。"""
    if os.access('/Applications', os.W_OK):
        return '/Applications'
    user_applications = os.path.join(os.path.expanduser('~'), 'Applications')
    try:
        os.makedirs(user_applications, exist_ok=True)
    except OSError:
        return ''
    return user_applications if os.access(user_applications, os.W_OK) else ''


def load_update_target():
    try:
        with open(UPDATE_TARGET_PATH, encoding='utf-8') as file:
            value = json.load(file).get('mac_target')
    except (OSError, ValueError, AttributeError):
        return ''
    return value if isinstance(value, str) and value.endswith('.app') else ''


def save_update_target(target):
    try:
        os.makedirs(os.path.dirname(UPDATE_TARGET_PATH), exist_ok=True)
        temp = UPDATE_TARGET_PATH + '.tmp'
        with open(temp, 'w', encoding='utf-8') as file:
            json.dump({'mac_target': target}, file, ensure_ascii=False)
        os.replace(temp, UPDATE_TARGET_PATH)
    except OSError:
        pass


def mac_update_target():
    """macOS 安装位置：原地更新 → 记住的位置 → /Applications → ~/Applications → 下载。

    只在可写、且不是 Gatekeeper 虚拟路径或「下载」目录时选择原地更新，
    避免把更新装回下载文件夹。
    """
    bundle = mac_app_bundle()
    if bundle and not mac_app_translocated(bundle):
        current = os.path.realpath(bundle)
        if os.path.commonpath((current, mac_downloads_dir())) != mac_downloads_dir() \
                and os.access(os.path.dirname(current), os.W_OK):
            return current
    remembered = load_update_target()
    if remembered and os.access(os.path.dirname(remembered), os.W_OK):
        return remembered
    applications = mac_applications_dir()
    if applications:
        return os.path.join(applications, 'Toolbox.app')
    return os.path.join(mac_downloads_dir(), 'Toolbox.app')


def update_install_target(system):
    if system == "Windows":
        if getattr(sys, "frozen", False):
            return os.path.abspath(sys.executable)
        return os.path.join(os.environ['LOCALAPPDATA'], "PersonalToolbox", "Toolbox.exe")
    if system == "Darwin":
        return mac_update_target()
    raise ValueError("应用内更新仅支持 Windows 和 macOS。")


def extract_update_package(archive_path, directory, system, cancelled):
    with zipfile.ZipFile(archive_path) as archive:
        entries = archive.infolist()
        if len(entries) > 30000 or sum(entry.file_size for entry in entries) > 2 * 1024 ** 3:
            raise ValueError("更新包解压后的大小或文件数超出限制。")
        names = {}
        for entry in entries:
            name = entry.filename.rstrip('/')
            parts = name.split('/')
            mode = entry.external_attr >> 16
            if (entry.orig_filename != entry.filename or not name or '\\' in name
                    or ntpath.splitdrive(name)[0] or any(part in ('', '.', '..') for part in parts)
                    or any(ord(char) < 32 for char in name)
                    or stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK)):
                raise ValueError("更新包包含不安全的路径或文件类型。")
            if system == 'Windows' and (stat.S_ISLNK(mode) or any(
                    ':' in part or part.endswith(('.', ' ')) or re.fullmatch(
                        r'(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', part, re.I)
                    for part in parts)):
                raise ValueError("更新包包含不安全的 Windows 文件名。")
            key = name.casefold()
            if key in names:
                raise ValueError("更新包包含重复的文件路径。")
            names[key] = entry
            if entry.flag_bits & 1:
                raise ValueError("无法安装加密的更新包。")

        files = [entry for entry in entries if not entry.is_dir()
                 and not entry.filename.startswith('__MACOSX/')
                 and posixpath.basename(entry.filename) != '.DS_Store']
        if system == 'Windows':
            candidates = [entry for entry in files if posixpath.basename(entry.filename).casefold()
                          in ('toolbox.exe', 'toolbox-windows.exe')]
            if len(candidates) != 1 or len(files) != 1:
                raise ValueError("Windows 更新包应仅包含单文件 Toolbox.exe。")
            selected = [(candidates[0], 'Toolbox.exe')]
            payload = os.path.join(directory, 'Toolbox.exe')
        elif system == 'Darwin':
            candidates = [entry for entry in files
                          if entry.filename.endswith('Toolbox.app/Contents/Info.plist')]
            if len(candidates) != 1:
                raise ValueError("macOS 更新包中未找到唯一的 Toolbox.app。")
            prefix = candidates[0].filename[:-len('Contents/Info.plist')]
            selected = [(entry, 'Toolbox.app/' + entry.filename[len(prefix):]) for entry in entries
                        if entry.filename.startswith(prefix) and entry.filename != prefix]
            payload = os.path.join(directory, 'Toolbox.app')
        else:
            raise ValueError("不支持的更新平台。")

        links, directories = [], []
        link_names = {relative.rstrip('/') for entry, relative in selected
                      if stat.S_ISLNK(entry.external_attr >> 16)}
        for entry, relative in selected:
            if cancelled.is_set():
                raise InterruptedError("已取消更新。")
            components = relative.rstrip('/').split('/')
            if any('/'.join(components[:index]) in link_names for index in range(1, len(components))):
                raise ValueError("更新包不能通过符号链接写入文件。")
            path = os.path.join(directory, *components)
            mode = (entry.external_attr >> 16) & 0o777
            if entry.is_dir():
                os.makedirs(path, exist_ok=True)
                directories.append((path, mode))
                continue
            os.makedirs(os.path.dirname(path), exist_ok=True)
            if stat.S_ISLNK(entry.external_attr >> 16):
                if entry.file_size > 4096:
                    raise ValueError("更新包的符号链接过长。")
                target = archive.read(entry).decode('utf-8')
                resolved = posixpath.normpath(posixpath.join(posixpath.dirname(relative), target))
                if (not target or '\\' in target or ntpath.splitdrive(target)[0]
                        or target.startswith('/') or resolved == '..' or resolved.startswith('../')
                        or not resolved.startswith('Toolbox.app/')):
                    raise ValueError("更新包的符号链接指向应用目录之外。")
                links.append((path, target))
                continue
            with archive.open(entry) as source, open(path, 'xb') as output:
                while True:
                    if cancelled.is_set():
                        raise InterruptedError("已取消更新。")
                    chunk = source.read(256 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
            if system == 'Darwin' and mode:
                os.chmod(path, mode)
        for path, target in links:
            os.symlink(target, path)
        for path, _ in links:
            resolved = os.path.realpath(path)
            if (os.path.commonpath((os.path.realpath(payload), resolved)) != os.path.realpath(payload)
                    or not os.path.exists(path)):
                raise ValueError("更新包包含越界或失效的符号链接。")
        if system == 'Darwin':
            for path, mode in reversed(directories):
                if mode:
                    os.chmod(path, mode)
            with open(os.path.join(payload, 'Contents', 'Info.plist'), 'rb') as file:
                info = plistlib.load(file)
            if not isinstance(info, dict):
                raise ValueError("更新包的应用信息格式无效。")
            executable = info.get('CFBundleExecutable', '')
            if (info.get('CFBundleIdentifier') != 'com.jimmy.personal_tool'
                    or not isinstance(executable, str) or not executable
                    or executable in ('.', '..') or ntpath.splitdrive(executable)[0]
                    or '/' in executable or '\\' in executable):
                raise ValueError("更新包不是系统工具箱应用。")
            executable_path = os.path.join(payload, 'Contents', 'MacOS', executable)
            with open(executable_path, 'rb') as file:
                magic = file.read(4)
            if magic not in (b'\xfe\xed\xfa\xce', b'\xce\xfa\xed\xfe', b'\xfe\xed\xfa\xcf',
                             b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca',
                             b'\xca\xfe\xba\xbf', b'\xbf\xba\xfe\xca'):
                raise ValueError("更新包中缺少有效的 macOS 可执行程序。")
            os.chmod(executable_path, os.stat(executable_path).st_mode | stat.S_IXUSR)
        else:
            with open(payload, 'rb') as file:
                header = file.read(64)
                if len(header) < 64 or header[:2] != b'MZ':
                    raise ValueError("更新包不是有效的 Windows 应用程序。")
                offset = int.from_bytes(header[60:64], 'little')
                if offset < 64 or offset > os.path.getsize(payload) - 24:
                    raise ValueError("更新包的 Windows 可执行文件头损坏。")
                file.seek(offset)
                if file.read(4) != b'PE\x00\x00':
                    raise ValueError("更新包的 Windows 可执行文件头损坏。")
        return payload
