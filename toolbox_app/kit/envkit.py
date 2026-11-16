"""用户环境变量：Windows 注册表与 POSIX shell 文件的读写。

Windows 写 HKCU\\Environment 并广播 WM_SETTINGCHANGE；POSIX 写
~/.personal_toolbox/env.sh 并确保 rc 文件 source 过它。只做数据读写，不含界面。
"""
import os
import re
import shlex

from toolbox_app.natives import _win_broadcast_setting

POSIX_ENV_FILE = os.path.join(os.path.expanduser("~"), ".personal_toolbox", "env.sh")
POSIX_RC_MARKER = "# personal_toolbox env"
SHELL_RC_FILES = (".zshrc", ".bashrc")
WIN_ENV_SUBKEY = "Environment"
ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def user_env_location():
    return r"HKCU\Environment" if os.name == "nt" else POSIX_ENV_FILE


def load_user_env():
    return _win_load_env() if os.name == "nt" else _posix_load_env()


def save_user_env(name, value):
    if os.name == "nt":
        _win_save_env(name, value)
        _win_broadcast_env()
    else:
        items = _posix_load_env()
        items[name] = value
        _posix_write_env(items)
    os.environ[name] = value


def remove_user_env(name):
    if os.name == "nt":
        _win_remove_env(name)
        _win_broadcast_env()
    else:
        items = _posix_load_env()
        items.pop(name, None)
        _posix_write_env(items)
    os.environ.pop(name, None)


def _win_load_env():
    import winreg
    items = {}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WIN_ENV_SUBKEY) as key:
            for i in range(winreg.QueryInfoKey(key)[1]):
                name, value, _type = winreg.EnumValue(key, i)
                items[name] = value
    except OSError:
        pass
    return items


def _win_save_env(name, value):
    import winreg
    # %VAR% references only survive as REG_EXPAND_SZ; REG_SZ would freeze them literally.
    vtype = winreg.REG_EXPAND_SZ if "%" in value else winreg.REG_SZ
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, WIN_ENV_SUBKEY) as key:
        winreg.SetValueEx(key, name, 0, vtype, value)


def _win_remove_env(name):
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WIN_ENV_SUBKEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.DeleteValue(key, name)


def _win_broadcast_env():
    """Tell running shells/Explorer to reload the environment; best effort."""
    _win_broadcast_setting("Environment")


def _posix_load_env():
    items = {}
    try:
        with open(POSIX_ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line.startswith("export "):
                    continue
                name, sep, raw = line[len("export "):].partition("=")
                if not sep or not ENV_NAME_RE.match(name):
                    continue
                try:
                    # shlex does not treat "=" as a separator, so unquote the value alone.
                    parts = shlex.split(raw)
                except ValueError:
                    continue
                items[name] = parts[0] if parts else ""
    except OSError:
        pass
    return items


def _posix_write_env(items):
    try:
        os.makedirs(os.path.dirname(POSIX_ENV_FILE), exist_ok=True)
        with open(POSIX_ENV_FILE, "w", encoding="utf-8") as f:
            for name in sorted(items):
                f.write("export %s=%s\n" % (name, shlex.quote(items[name])))
    except OSError as e:
        raise RuntimeError("无法写入 %s: %s" % (POSIX_ENV_FILE, e))
    _posix_ensure_rc()


def _posix_ensure_rc():
    """Source the env file from interactive shells, once per rc file."""
    for rc in SHELL_RC_FILES:
        path = os.path.join(os.path.expanduser("~"), rc)
        try:
            existing = ""
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    existing = f.read()
            if POSIX_RC_MARKER in existing:
                continue
            with open(path, "a", encoding="utf-8") as f:
                f.write("\n%s\n. %s\n" % (POSIX_RC_MARKER, shlex.quote(POSIX_ENV_FILE)))
        except OSError:
            continue
