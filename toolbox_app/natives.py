"""跨平台原生调用：macOS 窗口层级/前台应用、Windows 注册表与设置广播、子进程无控制台。

这里只跟操作系统打交道，不放业务逻辑；Qt 仅用于判断当前是否 cocoa 平台。
"""
import os
import platform
import subprocess

from PyQt5.QtWidgets import QApplication

# Windows 资源管理器“显示/隐藏”开关所在的注册表子键（HKCU 下）
WIN_ADVANCED_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"


def win_no_console():
    """Windows: keep console from flashing when spawning child processes."""
    if platform.system() == "Windows":
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)}
    return {}


def _mac_objc_runtime():
    import ctypes
    import ctypes.util
    objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
    objc.sel_registerName.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]
    objc.objc_getClass.restype = ctypes.c_void_p
    objc.objc_getClass.argtypes = [ctypes.c_char_p]
    return objc


def _mac_is_cocoa():
    return platform.system() == "Darwin" and QApplication.platformName() == "cocoa"


def _mac_cover_menu_bar(widget):
    """把原生 NSWindow 抬到菜单栏之上（屏幕保护程序用的 window level），
    并让它覆盖所有 Space。纯 Qt 无法盖住 macOS 系统菜单栏，必须走 AppKit。"""
    import ctypes
    import ctypes.util
    objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
    objc.sel_registerName.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]
    objc.objc_msgSend.restype = ctypes.c_void_p
    objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

    def sel(name):
        return objc.sel_registerName(name.encode())

    view_ptr = int(widget.winId())
    window = objc.objc_msgSend(view_ptr, sel("window"))
    if not window:
        return False

    cg = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreGraphics"))
    cg.CGShieldingWindowLevel.restype = ctypes.c_int
    level = cg.CGShieldingWindowLevel()

    objc.objc_msgSend.restype = ctypes.c_void_p
    objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_longlong]
    # NSWindowCollectionBehavior: CanJoinAllSpaces(1<<0) | Stationary(1<<2) | FullScreenAuxiliary(1<<7)
    behavior = (1 << 0) | (1 << 2) | (1 << 7)
    objc.objc_msgSend(window, sel("setCollectionBehavior:"), behavior)
    objc.objc_msgSend(window, sel("setLevel:"), level)

    objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
    objc.objc_msgSend(window, sel("setHidesOnDeactivate:"), 0)
    return True


def mac_input_access():
    """返回 (能否合成键鼠, 能否录屏)。长截图靠合成滚轮驱动目标窗口，缺辅助功能权限就会「滚不动」。"""
    try:
        import ctypes
        import ctypes.util
        cg = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreGraphics"))
        cg.CGPreflightPostEventAccess.restype = ctypes.c_bool
        cg.CGPreflightScreenCaptureAccess.restype = ctypes.c_bool
        return bool(cg.CGPreflightPostEventAccess()), bool(cg.CGPreflightScreenCaptureAccess())
    except (OSError, AttributeError):
        return False, False


def mac_request_post_event_access():
    """申请（并弹出系统授权面板）合成输入权限。"""
    try:
        import ctypes
        import ctypes.util
        cg = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreGraphics"))
        cg.CGRequestPostEventAccess.restype = ctypes.c_bool
        return bool(cg.CGRequestPostEventAccess())
    except (OSError, AttributeError):
        return False


def _mac_activate_app():
    """把本应用切到前台（等价于点一下 Dock），覆盖层要用键盘时先激活自己。

    macOS 14 起后台应用激活会被系统压制，activateIgnoringOtherApps 仍然有效；
    探测 selector 再调用，避免旧系统上命中不存在的 selector 直接 abort。
    """
    if not _mac_is_cocoa():
        return False
    import ctypes
    try:
        objc = _mac_objc_runtime()
        send = objc.objc_msgSend
        send.restype = ctypes.c_void_p
        send.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        nsapp = send(objc.objc_getClass(b"NSApplication"),
                     objc.sel_registerName(b"sharedApplication"))
        if not nsapp:
            return False
        send.restype = ctypes.c_bool
        send.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        if not send(nsapp, objc.sel_registerName(b"respondsToSelector:"),
                    objc.sel_registerName(b"activateIgnoringOtherApps:")):
            return False
        send.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
        return bool(send(nsapp, objc.sel_registerName(b"activateIgnoringOtherApps:"), 1))
    except Exception:
        return False


def _mac_picker_nonactivating(widget):
    """把取色罩抬到菜单栏之上并覆盖所有 Space，但只 orderFront、不 makeKey、不 activate：
    被取色的应用保持原样停在最前，不会退到后台。键盘退出靠 HID 键态轮询。"""
    import ctypes
    import ctypes.util
    objc = _mac_objc_runtime()
    send = objc.objc_msgSend
    send.restype = ctypes.c_void_p
    send.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    view = int(widget.winId())
    window = send(view, objc.sel_registerName(b"window"))
    if not window:
        return False
    cg = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreGraphics"))
    cg.CGShieldingWindowLevel.restype = ctypes.c_int
    send.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_longlong]
    send(window, objc.sel_registerName(b"setLevel:"), cg.CGShieldingWindowLevel())
    send(window, objc.sel_registerName(b"setCollectionBehavior:"),
         (1 << 0) | (1 << 2) | (1 << 7))
    send.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
    send(window, objc.sel_registerName(b"setHidesOnDeactivate:"), 0)
    # 关掉原生投影：否则首帧 loupe 的阴影会缓存成糊在初始位置的"影子"
    send(window, objc.sel_registerName(b"setHasShadow:"), 0)
    send.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    send(window, objc.sel_registerName(b"orderFront:"), None)
    return True


def _mac_frontmost_pid():
    """提醒弹出时用户正在用的 app 的 PID；本进程或取不到时返回 None。"""
    if not _mac_is_cocoa():
        return None
    import ctypes
    try:
        objc = _mac_objc_runtime()
        send = objc.objc_msgSend
        send.restype = ctypes.c_void_p
        send.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        workspace = send(objc.objc_getClass(b"NSWorkspace"),
                         objc.sel_registerName(b"sharedWorkspace"))
        app = send(workspace, objc.sel_registerName(b"frontmostApplication"))
        if not app:
            return None
        send.restype = ctypes.c_int
        pid = send(app, objc.sel_registerName(b"processIdentifier"))
    except Exception:
        return None
    return pid if pid > 0 and pid != os.getpid() else None


def _mac_reactivate(pid):
    """把前台交还给指定 PID 的 app：点掉提醒卡片不该顺手把工具箱吊起来。"""
    if not pid or pid <= 0 or not _mac_is_cocoa():
        return False
    import ctypes
    try:
        objc = _mac_objc_runtime()
        send = objc.objc_msgSend
        send.restype = ctypes.c_void_p
        send.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
        app = send(objc.objc_getClass(b"NSRunningApplication"),
                   objc.sel_registerName(b"runningApplicationWithProcessIdentifier:"), int(pid))
        if not app:
            return False

        # macOS 14 起 activateWithOptions: 换成 activate；探测后再调，
        # 命中不存在的 selector 是 doesNotRecognizeSelector，Python 抓不到直接 abort。
        send.restype = ctypes.c_bool
        send.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        probe = objc.sel_registerName(b"respondsToSelector:")
        if send(app, probe, objc.sel_registerName(b"activate")):
            send.restype = ctypes.c_bool
            send.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            return bool(send(app, objc.sel_registerName(b"activate")))
        if send(app, probe, objc.sel_registerName(b"activateWithOptions:")):
            send.restype = ctypes.c_bool
            send.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
            # NSApplicationActivateIgnoringOtherApps
            return bool(send(app, objc.sel_registerName(b"activateWithOptions:"), 1 << 1))
    except Exception:
        return False
    return False


def _win_dword_get(name):
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WIN_ADVANCED_SUBKEY) as key:
            return int(winreg.QueryValueEx(key, name)[0])
    except OSError:
        return None


def _win_dword_set(name, value):
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, WIN_ADVANCED_SUBKEY) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, int(value))


def _win_broadcast_setting(message):
    """WM_SETTINGCHANGE so open Explorer windows and shells can reload."""
    try:
        import ctypes
        HWND_BROADCAST, WM_SETTINGCHANGE, SMTO_ABORTIFHUNG = 0xFFFF, 0x1A, 0x0002
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST, WM_SETTINGCHANGE, 0, message, SMTO_ABORTIFHUNG, 5000, None)
    except Exception:
        pass


def _macos_default_read(domain, key):
    result = subprocess.run(["defaults", "read", domain, key], capture_output=True,
                            encoding="utf-8", errors="replace", **win_no_console())
    if result.returncode != 0:
        return None
    return (result.stdout or "").strip()


def _macos_default_write(domain, key, on):
    subprocess.run(["defaults", "write", domain, key, "-bool", "true" if on else "false"],
                   capture_output=True, **win_no_console())


def _macos_restart_finder():
    subprocess.run(["killall", "Finder"], capture_output=True, **win_no_console())


def visibility_read(row):
    """True/False for the current state, or None when the value was never written."""
    if platform.system() == "Windows":
        name, on, _off = row["win"]
        value = _win_dword_get(name)
        return None if value is None else value == on
    if platform.system() == "Darwin" and row["mac"]:
        raw = _macos_default_read(*row["mac"])
        if raw is None:
            return None
        return raw in ("1", "true", "YES")
    return None


def visibility_write(row, on):
    if platform.system() == "Windows":
        name, win_on, win_off = row["win"]
        _win_dword_set(name, win_on if on else win_off)
        _win_broadcast_setting("Probe")
        return "已写入注册表，资源管理器若没立刻变化，重开一个窗口即可。"
    if platform.system() == "Darwin" and row["mac"]:
        _macos_default_write(row["mac"][0], row["mac"][1], on)
        _macos_restart_finder()
        return "已写入 defaults，访达已重启。"
    raise RuntimeError("当前系统没有对应的开关。")
