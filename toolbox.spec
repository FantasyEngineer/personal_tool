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

a = Analysis(
    ["toolbox.py"],
    pathex=[],
    binaries=[],
    datas=[],
    # qrcode picks its PIL image backend lazily; make sure it is bundled.
    hiddenimports=["qrcode.pil", "qrcode.image.pil"],
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
