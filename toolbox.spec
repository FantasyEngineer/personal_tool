# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the single-file PyQt5 toolbox.
# Build:  pyinstaller --noconfirm toolbox.spec
# Output: Windows: dist/Toolbox.exe (single file, double-click to run)
#         macOS:   dist/Toolbox/Toolbox.app (one-dir bundle)

import os
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
               for f in ("icon.ico", "icon.icns", "icon.png")
               if os.path.exists(os.path.join("assets", f))]

# 本地 OCR（RapidOCR + onnxruntime）按需收集：未安装时构建仍可成功，程序会自动跳过本地引擎。
OCR_BINARIES, OCR_DATAS, OCR_HIDDEN = [], [], []
# 这些子包只在训练/模型转换时用，运行时不需要。PyInstaller 分析它们会在隔离子进程里
# 导入 onnxruntime，与 PyQt5 自带的 CRT 冲突而崩溃（exit 3221225477），必须排除。
OCR_SKIP = (
    "onnxruntime.quantization", "onnxruntime.transformers", "onnxruntime.tools",
    "onnxruntime.datasets", "onnxruntime.training",
    "rapidocr.inference_engine.tensorrt", "rapidocr.inference_engine.pytorch",
    "rapidocr.inference_engine.paddle", "rapidocr.inference_engine.mnn",
    "rapidocr.inference_engine.openvino",
)
try:
    from PyInstaller.utils.hooks import collect_all
    for package in ("rapidocr", "onnxruntime"):
        binaries, datas, hiddenimports = collect_all(package)
        OCR_BINARIES += binaries
        OCR_DATAS += datas
        OCR_HIDDEN += [name for name in hiddenimports
                       if not any(name == skip or name.startswith(skip + ".") for skip in OCR_SKIP)]
except Exception as exc:  # noqa: BLE001
    print("skip local OCR collection:", exc)

# PyInstaller 的二进制依赖扫描会把 Qt 绑定放在最前面导入，之后再导入 onnxruntime 就会因
# Qt5/bin 自带的旧版 msvcp140 冲突而崩溃（0xC0000005，导致 Windows 打包失败）。
# onnxruntime 的 DLL 已由 collect_all 完整收集，无需再让扫描步骤导入它，这里直接跳过。
import PyInstaller.building.build_main as _build_main

_original_find_binary_dependencies = _build_main.find_binary_dependencies


def _find_binary_dependencies(binaries, import_packages, symlink_suppression_patterns):
    # onnxruntime 及其上层封装在 PyQt5 之后导入都会崩溃，两者都不参与扫描；
    # 它们的 DLL 由上面的 collect_all 完整收集，运行时直接从包里加载。
    skip = ("onnxruntime", "rapidocr")
    safe_packages = [name for name in import_packages
                     if not any(name == root or name.startswith(root + ".") for root in skip)]
    return _original_find_binary_dependencies(binaries, safe_packages, symlink_suppression_patterns)


_build_main.find_binary_dependencies = _find_binary_dependencies

a = Analysis(
    ["toolbox.py"],
    pathex=[],
    binaries=OCR_BINARIES,
    datas=ICON_ASSETS + OCR_DATAS,
    # qrcode picks its PIL image backend lazily; make sure it is bundled.
    # cryptography's Rust binding is an extension module the 加解密 pages need at runtime.
    hiddenimports=["qrcode.image.pil", "cryptography.hazmat.bindings._rust"] + OCR_HIDDEN,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "PyQt5.QtWebEngine", "PyQt5.QtQml"] + list(OCR_SKIP),
    win_no_prefer_redirects=False,
    noarchive=False,
)

pyz = PYZ(a.pure)

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
