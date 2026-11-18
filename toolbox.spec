# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the single-file PyQt5 toolbox.
# Build:  pyinstaller --noconfirm toolbox.spec
# Output: Windows: dist/Toolbox.exe (single file, double-click to run)
#         macOS:   dist/Toolbox/Toolbox.app (one-dir bundle)

import os
import shutil
import sys

APP_NAME = "Toolbox"

# 版本号由 CI 从 git tag 注入（如 BUILD_VERSION=1.0.11）；本地构建用默认值。
BUILD_VERSION = os.environ.get("BUILD_VERSION", "1.0.0")

# Windows ships a single exe: no _internal folder to lose when copying or
# extracting, which is the most common "double-click does nothing" cause.
ONEFILE = sys.platform == "win32"

ICON_MAC = os.path.join("assets", "icon.icns")
ICON_WIN = os.path.join("assets", "icon.ico")

icon = None
if sys.platform == "darwin" and os.path.exists(ICON_MAC):
    icon = ICON_MAC
elif os.name == "nt" and os.path.exists(ICON_WIN):
    icon = ICON_WIN

# Ship the icon files so the running app can load them for the window/taskbar.
ICON_ASSETS = [(os.path.join("assets", f), "assets")
               for f in ("icon.ico", "icon.icns", "icon.png", "tray_template.png")
               if os.path.exists(os.path.join("assets", f))]


# 打包后的 OpenSSL 找不到默认证书库：python.org 解释器的 etc/openssl/cert.pem
# 不会被 PyInstaller 带走，而 libssl 里写死的默认路径在用户机上不存在，于是所有
# HTTPS 都报 "unable to get local issuer certificate"（离线 OCR 引擎下载、检查
# 更新、大模型识别都受影响）。随包带一份 Mozilla CA 库，运行时由
# toolbox_app/kit/netkit.py 优先使用。
def _ca_bundle_source():
    try:
        import certifi  # 构建机一般不缺
        return certifi.where()
    except Exception:
        pass
    for path in ("/opt/homebrew/etc/ca-certificates/cert.pem",
                 "/usr/local/etc/ca-certificates/cert.pem",
                 "/etc/ssl/cert.pem"):
        if os.path.exists(path):
            return path
    return None


_ca_source = _ca_bundle_source()
BUNDLED_DATAS = list(ICON_ASSETS)
if _ca_source:
    _ca_dir = os.path.join(SPECPATH, "build")
    os.makedirs(_ca_dir, exist_ok=True)
    _ca_dest = os.path.join(_ca_dir, "cacert.pem")
    shutil.copyfile(_ca_source, _ca_dest)
    BUNDLED_DATAS.append((_ca_dest, "assets"))
else:
    print("WARNING: 没找到可用的 CA 证书库，打包后 HTTPS 会校验失败")

# 本地 OCR（RapidOCR + onnxruntime + opencv）不打进安装包：首次识别时按需下载到
# 用户目录（见 toolbox.py 的 ensure_ocr_runtime），安装包因此保持在几十 MB。
# 代码里只用 importlib 探测、不写死 import，这里再排除一次，避免构建机装了这些包
# 之后被顺手打进包里。
OCR_EXCLUDES = ["rapidocr", "onnxruntime", "cv2"]

# numpy 也只在 Windows 上排除：长截图拼接已经改成纯 Pillow（toolbox_app/kit/screenkit.py），
# 应用本身不再 import numpy，Windows 包里的 numpy（含 20 MB 的 OpenBLAS）也就没用了——
# 首次用「本地 RapidOCR」时下载的运行时压缩包里自带配套的那份 numpy。
# macOS 暂时保持原样（numpy 仍打进包里）：mac 的 numpy wheel 分 arm64 / x86_64，
# 而运行时压缩包目前按「平台_主_次」选条目、没有架构维度，Intel 机器上层还要再验证。
HAS_BUNDLED_NUMPY = sys.platform != "win32"
if not HAS_BUNDLED_NUMPY:
    OCR_EXCLUDES = OCR_EXCLUDES + ["numpy"]

# qrcode picks its PIL image backend lazily; make sure it is bundled.
# cryptography's Rust binding is an extension module the 加解密 pages need at runtime.
# numpy.core 是 numpy 2 给旧代码留的兼容层：按需下载的 cv2 里仍有
# import numpy.core.multiarray，构建时没有模块引用它就会被裁掉，导致运行时
# 「No module named 'numpy.core.multiarray'」，这里显式带上（仅限仍带 numpy 的平台）。
# http.cookies / queue 同理：只有运行时下载的 requests / urllib3 才会用到，应用本身
# 不引用，不加就会在本地 OCR 加载时报 No module named 'queue'。
HIDDEN_IMPORTS = ["qrcode.image.pil", "cryptography.hazmat.bindings._rust",
                  "http.cookies", "queue"]
if HAS_BUNDLED_NUMPY:
    HIDDEN_IMPORTS += ["numpy.core", "numpy.core.multiarray"]

a = Analysis(
    ["toolbox.py"],
    pathex=[],
    binaries=[],
    datas=BUNDLED_DATAS,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "PyQt5.QtWebEngine", "PyQt5.QtQml",
              "PyQt5.QtQuick", "PyQt5.QtQuickWidgets",
              # 纯 QWidget 应用，运行时不会用到这些标准库组件
              "unittest", "doctest", "pydoc", "pydoc_data", "lib2to3",
              "ensurepip", "pip", "test"] + OCR_EXCLUDES,
    win_no_prefer_redirects=False,
    noarchive=False,
)

pyz = PYZ(a.pure)

# 瘦身：剔除运行时用不到的二进制（不改动任何功能，只减体积）。
#   opengl32sw / d3dcompiler_47 / libEGL / libGLESv2 —— Qt 的软件 OpenGL 与 ANGLE 兜底，
#   QWidget 程序走 Windows 光栅后端，正常显卡驱动下用不到；
#   Qt5Quick/Qml 栈 —— 界面全部是 QWidget，没有 QML；
#   _avif —— Pillow 的 AVIF 插件，没有加载过 AVIF 图片；
#   qminimal / qoffscreen / qwebgl —— 其它平台插件，实际只用 qwindows（macOS 是 libqcocoa，
#     其 libqminimal/libqwebgl 由下面的 SLIM_PATHS 负责）；
#   _imagingft —— Pillow 的字体渲染扩展，代码里没有用 ImageFont（二维码走 ImageDraw 纯像素绘制）。
SLIM_PREFIXES = (
    "opengl32sw",
    "d3dcompiler_47",
    "qt5quick",
    "qt5qml",
    "libglesv2",
    "libegl",
    "_avif",
    "qminimal",
    "qoffscreen",
    "qwebgl",
    "_imagingft",
)

# Windows 上按 DLL 名命中的 Qt 模块（macOS 是 framework 目录，未在此改动）：
#   Qt5Network —— 网络请求全部走 urllib / http.client，不引 QtNetwork；
#   Qt5DBus —— Linux 的进程间通信，Windows 上没有用途；
#   Qt5Svg + qsvg 图像插件 —— 图标只有 png / ico / icns，没有 SVG 资源。
WIN_SLIM_PREFIXES = (
    "qt5network",
    "qt5dbus",
    "qt5svg",
    "qsvg",
)

# 只按名字匹配挡不住 macOS 上的 framework 目录，这里按收集路径再筛一遍：
#   Qt5/lib/QtQuick.framework、QtQml、QtQmlModels、QtWebSockets —— 界面全是 QWidget；
#   plugins/platforms/libqwebgl、libqminimal —— 平台插件只用 cocoa / qwindows；
#   plugins/generic —— 触摸板输入插件，桌面端不用。
SLIM_PATHS = (
    "qt5/lib/qtquick.framework",
    "qt5/lib/qtqml.framework",
    "qt5/lib/qtqmlmodels.framework",
    "qt5/lib/qtwebsockets.framework",
    "plugins/platforms/libqwebgl",
    "plugins/platforms/libqminimal",
    "plugins/generic/",
)


# Qt 自带的全语言翻译表默认会被整包收进来（约 5 MB），界面只有中英文，
# 只留 zh_CN 和 en 两份，标准对话框的语言不变。
KEEP_TRANSLATIONS = ("zh_cn", "zh_", "_en")


def _keep_binary(entry):
    name = os.path.basename(entry[0]).lower()
    path = entry[0].replace(os.sep, "/").lower()
    prefixes = SLIM_PREFIXES + (WIN_SLIM_PREFIXES if os.name == "nt" else ())
    if any(name.startswith(prefix) for prefix in prefixes):
        return False
    return not any(part in path for part in SLIM_PATHS)


def _keep_data(entry):
    src = str(entry[0]).replace(os.sep, "/").lower()
    if "/translations/" in src:
        return any(token in os.path.basename(src) for token in KEEP_TRANSLATIONS)
    return True


a.binaries = [entry for entry in a.binaries if _keep_binary(entry)]
a.datas = [entry for entry in a.datas if _keep_binary(entry) and _keep_data(entry)]

# 统一 MSVC 运行时版本，避免按需下载的 onnxruntime（用新 MSVC 编译）加载到
# Qt 自带的旧版 MSVCP140.dll（14.26）后在 MSVCP140.dll 里访问违例闪退。
# 做法：把系统里 msvcp140 / vcruntime140 / vcruntime140_1 这一组配套 DLL
# 放到打包根目录，覆盖 PyQt5\Qt5\bin 下的旧副本；根目录在 DLL 搜索顺序里
# 优先于 Qt 的 bin 目录，所以全进程都会用这一套一致的新版本。
if os.name == "nt":
    _RUNTIME_DLLS = ("msvcp140.dll", "vcruntime140.dll", "vcruntime140_1.dll")

    def _find_runtime_dll(name):
        # 优先用仓库里随附的副本（assets/vcrt），其次系统 System32，最后 Python 目录。
        # PyInstaller onefile 在某些环境下会拒绝直接收集 System32 里的 DLL，
        # 所以仓库里放一份兜底，本地和 CI 都能稳定打包。
        for base in (os.path.join(SPECPATH, "assets", "vcrt"),
                     os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32"),
                     os.path.dirname(sys.executable)):
            candidate = os.path.join(base, name)
            if os.path.exists(candidate):
                return candidate
        return None

    _new_runtime = []
    for _name in _RUNTIME_DLLS:
        _src = _find_runtime_dll(_name)
        if _src:
            # TOC 条目顺序是 (dest_name, src_name, typecode)，dest 放根目录
            _new_runtime.append((_name, _src, "BINARY"))

    if _new_runtime:
        _seen = set()
        _deduped = []
        for entry in a.binaries:
            base = os.path.basename(entry[1]).lower()
            if base in _RUNTIME_DLLS:
                continue  # 丢掉 Qt 等自带的旧副本
            if base in _seen:
                continue
            _seen.add(base)
            _deduped.append(entry)
        _deduped.extend(_new_runtime)
        a.binaries = _deduped

EXE_OPTS = dict(
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # windowed app: no terminal window
    icon=icon,
)

if ONEFILE:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], **EXE_OPTS)
    coll = None
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **EXE_OPTS)

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        name=APP_NAME,
    )

# On macOS, wrap the onedir output into a real .app bundle (with Info.plist).
# Without this, onedir only produces a bare Mach-O executable, not an app.
if sys.platform == "darwin":
    app_bundle = BUNDLE(
        coll,
        name=APP_NAME + ".app",
        icon=icon,
        bundle_identifier="com.jimmy.personal_tool",
        info_plist={
            "CFBundleName": APP_NAME,
            "CFBundleDisplayName": "系统工具箱",
            "CFBundleShortVersionString": BUILD_VERSION,
            "CFBundleVersion": BUILD_VERSION,
            "NSHighResolutionCapable": True,
            "NSPrincipalClass": "NSApplication",
        },
    )
