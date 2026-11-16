"""Git 全局配置：读写 ~/.gitconfig 的键值。

只是 git config 命令的封装，命令参数固定不拼接任意输入；界面在配置文件工具里。
"""
import os
import re
import subprocess

from toolbox_app.natives import win_no_console

GIT_KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]*(\.[A-Za-z0-9._-]+)*$")


def git_global_path():
    override = os.environ.get("GIT_CONFIG_GLOBAL")
    if override:
        return override
    return os.path.join(os.path.expanduser("~"), ".gitconfig")


def _refresh_path_from_system():
    """Windows 上从注册表重新读取 PATH，识别新安装的工具（如 git）。"""
    if os.name != "nt":
        return
    try:
        import winreg
        # 系统 PATH
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                           r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as key:
            sys_path, _ = winreg.QueryValueEx(key, "Path")
        # 用户 PATH
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            usr_path, _ = winreg.QueryValueEx(key, "Path")
        # 合并并更新当前进程的环境变量
        os.environ["PATH"] = sys_path + ";" + usr_path
    except Exception:
        pass


def _run_git(args):
    try:
        return subprocess.run(["git", "config"] + args, capture_output=True,
                              encoding="utf-8", errors="replace", **win_no_console())
    except OSError:
        raise RuntimeError("未找到 git 命令，请确认已安装 Git 并在 PATH 中")


def _git_error(result):
    return (result.stderr or "").strip() or "git config 执行失败"


def git_global_list():
    _refresh_path_from_system()
    import shutil
    if shutil.which("git") is None:
        raise RuntimeError("未找到 git 命令，请确认已安装 Git 并在 PATH 中")
    # git exits 128 on a missing file and 1 on an empty one; neither is an error here.
    if not os.path.exists(git_global_path()):
        return []
    result = _run_git(["--global", "--list"])
    if result.returncode not in (0, 1):
        raise RuntimeError(_git_error(result))
    pairs = []
    for line in (result.stdout or "").splitlines():
        key, sep, value = line.partition("=")
        if sep:
            pairs.append((key, value))
    return pairs


def git_global_set(key, value):
    _refresh_path_from_system()
    result = _run_git(["--global", key, value])
    if result.returncode != 0:
        raise RuntimeError(_git_error(result))


def git_global_unset(key):
    _refresh_path_from_system()
    # rc 1 = no entries left in the file, rc 5 = that key was not set. Both are no-ops.
    result = _run_git(["--global", "--unset-all", key])
    if result.returncode not in (0, 1, 5):
        raise RuntimeError(_git_error(result))
