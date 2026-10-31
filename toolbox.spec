# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the single-file PyQt5 toolbox.
# Build:  pyinstaller --noconfirm toolbox.spec
# Output: dist/Toolbox/  (a "one-dir" bundle; on macOS it contains Toolbox.app)

import os
import sys

APP_NAME = "Toolbox"

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

a = Analysis(
    ["toolbox.py"],
    pathex=[],
    binaries=[],
    datas=ICON_ASSETS,
    # qrcode picks its PIL image backend lazily; make sure it is bundled.
    # cryptography's Rust binding is an extension module the 加解密 pages need at runtime.
    hiddenimports=["qrcode.pil", "qrcode.image.pil", "cryptography.hazmat.bindings._rust"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "PyQt5.QtWebEngine", "PyQt5.QtQml"],
    win_no_prefer_redirects=False,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # windowed app: no terminal window
    icon=icon,
)

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
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
            "NSHighResolutionCapable": True,
            "NSPrincipalClass": "NSApplication",
        },
    )
