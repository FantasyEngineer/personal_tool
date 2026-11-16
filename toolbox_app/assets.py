"""图标资源定位：源码目录与 PyInstaller 资源目录两种运行方式都要能找到 assets/。"""
import os
import platform
import sys

from PyQt5.QtGui import QIcon


def asset_root():
    """assets 目录的根：冻结后是 _MEIPASS，源码运行时是仓库根目录。

    本文件位于 toolbox_app/ 下，未打包时要往上退一层才是仓库根，
    否则会去 toolbox_app/assets 找图。
    """
    return getattr(sys, "_MEIPASS",
                   os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def app_asset_path(name):
    """从源码目录或 PyInstaller 资源目录解析图标资源。"""
    return os.path.join(asset_root(), "assets", name)


def app_icon():
    """读取应用主图标。"""
    names = ("icon.icns", "icon.png", "icon.ico") if platform.system() == "Darwin" else (
        "icon.ico", "icon.png", "icon.icns"
    )
    for name in names:
        path = app_asset_path(name)
        if os.path.exists(path):
            icon = QIcon(path)
            if not icon.isNull():
                return icon
    return QIcon()
