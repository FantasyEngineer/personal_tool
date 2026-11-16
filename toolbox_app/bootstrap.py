"""进程启动准备：必须在导入 PyQt5 之前完成的工作。

目前只有一件事：Windows 上把系统运行库先加载进来，避免之后导入 onnxruntime 崩溃。
"""
import ctypes
import os
import platform


def preload_windows_runtime():
    """Windows 上 PyQt5 自带的 msvcp140/vcruntime140 与 onnxruntime 冲突：先加载系统运行时，
    否则之后再导入 onnxruntime（本地 OCR）会直接崩溃。优先用 System32 里的版本。"""
    if platform.system() != "Windows":
        return
    system32 = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
    for dll in ("msvcp140.dll", "vcruntime140.dll", "vcruntime140_1.dll"):
        for path in (os.path.join(system32, dll), dll):
            try:
                ctypes.WinDLL(path)
                break
            except (OSError, AttributeError):
                continue
