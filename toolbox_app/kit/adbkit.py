"""ADB（Android Debug Bridge）支持：定位 / 下载官方 platform-tools，封装常用命令。

adb 本体不随 Toolbox 打包（约 8–15 MB 的 platform-tools 压缩包），首次使用时
从 Google 官方站点下载并解压，之后一直复用本地这份：

    https://dl.google.com/android/repository/platform-tools-latest-darwin.zip
    https://dl.google.com/android/repository/platform-tools-latest-windows.zip
    https://dl.google.com/android/repository/platform-tools-latest-linux.zip

如果机器上已经装了 Android SDK 的 platform-tools，直接用它，不重复下载。
"""
import os
import platform
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request
import zipfile

from toolbox_app.kit.netkit import https_context

ADB_FOLDER = "adb"
PLATFORM_TOOLS = "platform-tools"
BASE_URL = "https://dl.google.com/android/repository/"

_ARCHIVES = {
    "Darwin": "platform-tools-latest-darwin.zip",
    "Windows": "platform-tools-latest-windows.zip",
    "Linux": "platform-tools-latest-linux.zip",
}


def platform_key():
    return platform.system()


def download_url():
    """当前系统的官方 platform-tools 压缩包地址。"""
    return BASE_URL + _ARCHIVES.get(platform_key(), _ARCHIVES["Linux"])


def adb_binary_name():
    return "adb.exe" if platform_key() == "Windows" else "adb"


def cache_root():
    return os.path.join(os.path.expanduser("~"), ".personal_toolbox")


def install_root():
    """下载后的 adb 存放目录：~/.personal_toolbox/adb/platform-tools。"""
    return os.path.join(cache_root(), ADB_FOLDER, PLATFORM_TOOLS)


def installed_adb():
    path = os.path.join(install_root(), adb_binary_name())
    if os.path.exists(path):
        return path
    return ""


def android_sdk_adb():
    """本机已有的 Android SDK / Homebrew 里的 adb（优先复用，不重复下载）。"""
    candidates = []
    for key in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        value = os.environ.get(key)
        if value:
            candidates.append(os.path.join(value, PLATFORM_TOOLS, adb_binary_name()))
    candidates.extend((
        os.path.join(cache_root(), ADB_FOLDER, PLATFORM_TOOLS, adb_binary_name()),
        os.path.join(os.path.expanduser("~"), "Library", "Android", "sdk",
                     PLATFORM_TOOLS, adb_binary_name()),
        os.path.join(os.path.expanduser("~"), "Android", "Sdk",
                     PLATFORM_TOOLS, adb_binary_name()),
        os.path.join(os.environ.get("LOCALAPPDATA") or "", "Android", "Sdk",
                     PLATFORM_TOOLS, adb_binary_name()),
    ))
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return shutil.which("adb") or ""


def adb_path():
    """按优先级找一个可用的 adb：环境变量 → 已下载 → SDK → PATH。"""
    explicit = os.environ.get("TOOLBOX_ADB")
    if explicit and os.path.exists(explicit):
        return explicit
    return installed_adb() or android_sdk_adb()


def download_adb(progress=None, cancelled=None):
    """下载并解压 platform-tools，返回可执行的 adb 路径。

    progress(done, total) 用于界面进度条；cancelled 是 threading.Event，
    置位后在下一个分块处中止（抛 InterruptedError）。
    """
    url = download_url()
    os.makedirs(os.path.join(cache_root(), ADB_FOLDER), exist_ok=True)
    staging = tempfile.mkdtemp(prefix=".download-", dir=os.path.join(cache_root(), ADB_FOLDER))
    try:
        archive = os.path.join(staging, "platform-tools.zip")
        request = urllib.request.Request(url, headers={
            "User-Agent": "Toolbox/adb-download",
            "Accept": "application/zip, application/octet-stream"})
        with urllib.request.urlopen(request, timeout=25, context=https_context()) as response, \
                open(archive, "wb") as output:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            while True:
                if cancelled is not None and cancelled.is_set():
                    raise InterruptedError
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                done += len(chunk)
                if progress is not None:
                    progress(done, total)
        if cancelled is not None and cancelled.is_set():
            raise InterruptedError
        unpacked = os.path.join(staging, "unpacked")
        os.makedirs(unpacked, exist_ok=True)
        _extract_platform_tools(archive, unpacked)
        binary = os.path.join(unpacked, PLATFORM_TOOLS, adb_binary_name())
        if not os.path.exists(binary):
            raise ValueError("压缩包里没有 adb，请重试或改用 Android SDK 里的 platform-tools。")
        if platform_key() != "Windows":
            os.chmod(binary, 0o755)
        target = os.path.join(cache_root(), ADB_FOLDER)
        for name in os.listdir(target):
            if not name.startswith("."):
                shutil.rmtree(os.path.join(target, name), ignore_errors=True)
        os.replace(os.path.join(unpacked, PLATFORM_TOOLS), install_root())
        return os.path.join(install_root(), adb_binary_name())
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _extract_platform_tools(archive, destination):
    """只取 platform-tools 下的 adb 及其 Windows 依赖 DLL，避免解出整套 SDK 工具。"""
    wanted = (adb_binary_name(), "AdbWinApi.dll", "AdbWinUsbApi.dll")
    with zipfile.ZipFile(archive) as bundle:
        for info in bundle.infolist():
            name = info.filename.replace("\\", "/")
            if not name.startswith(PLATFORM_TOOLS + "/"):
                continue
            leaf = name.rsplit("/", 1)[-1]
            if leaf not in wanted:
                continue
            info.filename = os.path.join(PLATFORM_TOOLS, leaf)
            bundle.extract(info, destination)


def run_adb(args, adb=None, serial=None, timeout=60):
    """执行一条 adb 命令，返回 (returncode, stdout, stderr)。"""
    binary = adb or adb_path()
    if not binary:
        raise RuntimeError("还没有 adb，请先下载平台工具。")
    command = [binary]
    if serial:
        command.extend(["-s", serial])
    command.extend(args)
    creation = 0
    if platform_key() == "Windows":
        creation = 0x08000000  # CREATE_NO_WINDOW
    env = dict(os.environ)
    env.setdefault("ADB_MDNS", "0")
    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             timeout=timeout, creationflags=creation, env=env)
    return (process.returncode,
            process.stdout.decode("utf-8", errors="replace"),
            process.stderr.decode("utf-8", errors="replace"))


def version_text(adb=None):
    """adb 版本那一行，取不到就返回空字符串。"""
    code, out, err = run_adb(["version"], adb=adb, timeout=15)
    text = (out or err).strip()
    return text.splitlines()[0].strip() if text else ""


def parse_devices(text):
    """解析 `adb devices -l` 的输出，返回 [{serial, state, model, product, transport}]。"""
    devices = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("List of devices") or line.startswith("*"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        serial, state = parts[0], parts[1]
        info = {}
        for token in parts[2:]:
            if ":" in token:
                key, _, value = token.partition(":")
                info[key] = value
        devices.append({
            "serial": serial,
            "state": state,
            "model": info.get("model", "") or info.get("device", ""),
            "product": info.get("product", ""),
            "transport": "network" if ":" in serial else "usb",
        })
    return devices


_STATE_LABELS = {
    "device": "已连接",
    "unauthorized": "未授权 · 手机上点“允许调试”",
    "offline": "离线 · 拔插数据线或重启 adb 服务",
    "authorizing": "授权中…",
    "bootloader": "bootloader / fastboot",
    "recovery": "recovery",
    "sideload": "sideload",
}


def state_label(state):
    return _STATE_LABELS.get(state, state or "未知")


def parse_packages(text):
    """解析 `pm list packages` 的输出：去掉 package: 前缀、去重并排序。"""
    names = set()
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line.startswith("package:"):
            continue
        name = line[len("package:"):].strip()
        if name:
            names.add(name)
    return sorted(names)


def list_devices(adb=None):
    """返回 (devices, 原始输出)。顺带把 adb 服务拉起来。"""
    code, out, err = run_adb(["devices", "-l"], adb=adb, timeout=20)
    return parse_devices(out + "\n" + err), (out or err)


def trigger_auth_dialog(adb=None):
    """重启 adb 服务，迫使手机重新弹出「允许 USB 调试吗？」授权弹窗。

    返回值：("ok", 说明文本) / ("fail", 错误文本)。
    """
    try:
        run_adb(["kill-server"], adb=adb, timeout=15)
        code, out, err = run_adb(["start-server"], adb=adb, timeout=20)
        if code != 0 and "daemon" not in (out + err).lower():
            return ("fail", (err or out).strip()[:300] or "adb 服务启动失败")
        devices, raw = list_devices(adb=adb)
        if not devices:
            return ("ok", "adb 服务已重启，但没有发现设备。请用数据线连上手机并选择「文件传输 / MTP」后再点一次。")
        pending = [item for item in devices if item["state"] in ("unauthorized", "authorizing")]
        if pending:
            return ("ok", "已向 %s 发起调试授权请求，请解锁手机并在弹窗里点「允许」（建议勾选“一律允许”）。"
                    % "、".join(item["serial"] for item in pending))
        if all(item["state"] == "device" for item in devices):
            return ("ok", "设备已授权，无需再弹窗。若手机上还看不到弹窗，说明此前已授权过。")
        return ("ok", "adb 服务已重启。当前设备状态：%s" %
                "；".join("%s %s" % (item["serial"], state_label(item["state"])) for item in devices))
    except Exception as exc:
        return ("fail", str(exc)[:300])


def connect(adb, address):
    code, out, err = run_adb(["connect", address], adb=adb, timeout=20)
    text = (out + err).strip()
    ok = code == 0 and "connected" in text.lower() and "cannot" not in text.lower()
    return ("ok" if ok else "fail", text[:300] or "连接失败")


def disconnect(adb, address=""):
    args = ["disconnect"] + ([address] if address else [])
    code, out, err = run_adb(args, adb=adb, timeout=20)
    return ("ok" if code == 0 else "fail", (out + err).strip()[:300])


def pair(adb, address, code_text):
    code, out, err = run_adb(["pair", address, code_text], adb=adb, timeout=25)
    text = (out + err).strip()
    ok = "successfully paired" in text.lower()
    return ("ok" if ok else "fail", text[:300] or "配对失败")


def install(adb, apk, serial=None, reinstall=True, grant=True):
    args = ["install"]
    if reinstall:
        args.append("-r")
    if grant:
        args.append("-g")
    args.append(apk)
    code, out, err = run_adb(args, adb=adb, serial=serial, timeout=300)
    text = (out + err).strip()
    ok = code == 0 and "success" in text.lower() and "failure" not in text.lower()
    return ("ok" if ok else "fail", text[:400] or "安装失败")


def uninstall(adb, package, serial=None, keep_data=False):
    args = ["uninstall"] + (["-k"] if keep_data else []) + [package]
    code, out, err = run_adb(args, adb=adb, serial=serial, timeout=120)
    text = (out + err).strip()
    ok = code == 0 and "success" in text.lower()
    return ("ok" if ok else "fail", text[:400] or "卸载失败")


def packages(adb, serial=None, third_party=True):
    args = ["shell", "pm", "list", "packages"] + (["-3"] if third_party else [])
    code, out, err = run_adb(args, adb=adb, serial=serial, timeout=60)
    if code != 0:
        return []
    return parse_packages(out)


def is_network_address(address):
    return bool(re.match(r"^\d{1,3}(\.\d{1,3}){3}(:\d+)?$", (address or "").strip()))


# ---------- 录屏 / 截图 ----------
def default_record_dir():
    """录屏和截图默认落在桌面，用户看得见、删得掉。"""
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    if os.path.isdir(desktop):
        return desktop
    return cache_root()


def record_filename(kind, serial=""):
    """adb-<序列号>-<时间戳>.mp4 / .png"""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", serial or "device")[:24]
    return "adb-%s-%s.%s" % (safe, stamp, kind)


class ScreenRecorder:
    """用手机自带的 screenrecord 录制，应用侧不打包任何编码器。

    安卓设备侧上限 180 秒；这里把 adb 进程挂在 Popen 上，停止时给手机端的
    screenrecord 发 SIGINT（pkill -2），让它把 mp4 正常收尾。
    """

    MAX_SECONDS = 180

    def __init__(self, adb=None, serial=None, remote="", size="", bitrate="", time_limit=180):
        self.adb = adb or adb_path()
        self.serial = serial or ""
        self.remote = remote
        self.size = size
        self.bitrate = bitrate
        try:
            self.time_limit = max(1, min(int(time_limit or self.MAX_SECONDS), self.MAX_SECONDS))
        except (TypeError, ValueError):
            self.time_limit = self.MAX_SECONDS
        self._process = None
        self._started_at = 0.0

    def build_args(self):
        args = [self.adb]
        if self.serial:
            args.extend(["-s", self.serial])
        args.extend(["shell", "screenrecord"])
        if self.time_limit:
            args.extend(["--time-limit", str(self.time_limit)])
        if self.size:
            args.extend(["--size", self.size])
        if self.bitrate:
            args.extend(["--bit-rate", self.bitrate])
        args.append(self.remote)
        return args

    def start(self):
        if not self.adb:
            raise RuntimeError("还没有 adb，请先下载平台工具。")
        self._process = subprocess.Popen(self.build_args(), stdout=subprocess.PIPE,
                                         stderr=subprocess.STDOUT)
        self._started_at = time.time()
        return self

    @property
    def elapsed(self):
        return int(time.time() - self._started_at) if self._started_at else 0

    def running(self):
        return self._process is not None and self._process.poll() is None

    def wait(self, timeout=10):
        if self._process is None:
            return 0
        try:
            code = self._process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return None
        finally:
            self._close_pipes()
        return code

    def output(self):
        if self._process is None or self._process.stdout is None:
            return ""
        try:
            text = self._process.stdout.read().decode("utf-8", errors="replace")
        except (AttributeError, ValueError):
            return ""
        return text.strip()

    def stop(self, timeout=8):
        """先让手机端收尾（SIGINT），等不到再掐本地 adb 进程。"""
        remote = self.remote
        if self.adb and remote:
            try:
                run_adb(["shell", "pkill", "-2", "screenrecord"], adb=self.adb,
                        serial=self.serial, timeout=timeout)
            except Exception:
                pass
        code = self.wait(timeout=timeout)
        if code is None and self._process is not None:
            try:
                self._process.terminate()
            except Exception:
                pass
            code = self.wait(timeout=3)
        return code

    def _close_pipes(self):
        if self._process is not None and self._process.stdout is not None:
            try:
                self._process.stdout.close()
            except Exception:
                pass


def screencap(adb=None, serial=None, dest=""):
    """exec-out screencap -p 直接把 PNG 二进制写到本地文件。"""
    binary = adb or adb_path()
    if not binary:
        raise RuntimeError("还没有 adb，请先下载平台工具。")
    command = [binary]
    if serial:
        command.extend(["-s", serial])
    command.extend(["exec-out", "screencap", "-p"])
    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             timeout=60)
    data = process.stdout or b""
    if not data.startswith(b"\x89PNG"):
        message = (process.stderr or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(message or "手机没有返回图像数据，确认设备已连接并授权。")
    if not dest:
        dest = os.path.join(default_record_dir(), record_filename("png", serial))
    with open(dest, "wb") as output:
        output.write(data)
    return dest


def pull(adb=None, serial=None, remote="", local="", timeout=240):
    """抓屏/录屏文件拉回本地，返回 (状态, 文案)。"""
    if not remote or not local:
        return ("fail", "缺少远端或本地路径。")
    code, out, err = run_adb(["pull", remote, local], adb=adb, serial=serial, timeout=timeout)
    if code == 0 and os.path.exists(local):
        size = os.path.getsize(local)
        return ("ok", "%s（%.1f MB）" % (local, size / 1024.0 / 1024.0))
    return ("fail", (out + err).strip()[:300] or "adb pull 失败。")


def remove_remote(adb=None, serial=None, remote=""):
    if not remote:
        return
    try:
        run_adb(["shell", "rm", "-f", remote], adb=adb, serial=serial, timeout=20)
    except Exception:
        pass
