"""本地持久化：原子读写文本/ini、历史记录与排序记录的存取。

只提供通用能力，不掺业务语义；各工具的配置解析留在各自模块里。
"""
import json
import os
import platform
import shutil

from toolbox_app.constants import (HISTORY_LIMIT, SECTION_ORDER_PATH, SECTION_RENAMES,
                                   TOOL_ORDER_PATH, TOOL_RENAMES)


def cache_root():
    """配置与缓存目录：Windows / macOS / Linux 统一为 ~/.personal_toolbox。"""
    return os.path.join(os.path.expanduser("~"), ".personal_toolbox")


def user_path(*parts):
    return os.path.join(os.path.expanduser("~"), *parts)


def _read_text(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _write_text(path, text, key_file=False):
    if os.path.exists(path):
        shutil.copy2(path, path + ".bak")
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp = path + ".toolbox-tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text if text.endswith("\n") else text + "\n")
    if key_file and os.name != "nt":
        os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def _read_lines(path):
    text = _read_text(path)
    return text.splitlines() if text else []


def _ini_get(path, section, key):
    want = section.lower() if section else None
    current = None
    for line in _read_lines(path):
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            current = s[1:-1].strip().lower()
            continue
        if not s or s[0] in "#;":
            continue
        name, sep, value = s.partition("=")
        if sep and current == want and name.strip().lower() == key.lower():
            return value.strip()
    return None


def _ini_set(path, section, key, value, tight=False):
    """Add, change or (value=None) drop one key; comments and siblings stay put."""
    want = section.lower() if section else None
    out, hit, current = [], False, None
    joined = None
    if value is not None:
        joined = "%s=%s" % (key, value) if tight else "%s = %s" % (key, value)
    for line in _read_lines(path):
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            current = s[1:-1].strip().lower()
            out.append(line)
            continue
        name, sep, _rest = s.partition("=")
        if sep and current == want and name.strip().lower() == key.lower():
            hit = True
            if joined:
                out.append(joined)
            continue
        out.append(line)
    if value is None:
        if hit:
            _write_text(path, "\n".join(out))
        return
    if not hit:
        if want is None:
            out.append(joined)
        else:
            for idx, line in enumerate(out):
                s = line.strip()
                if s.startswith("[") and s.endswith("]") and s[1:-1].strip().lower() == want:
                    out.insert(idx + 1, joined)
                    break
            else:
                out.extend(["[%s]" % section, joined])
    _write_text(path, "\n".join(out))


XDG_BASE = "Library/Application Support"


def _app_config_dir(*parts):
    """Where the tool itself keeps its config, per OS conventions."""
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("APPDATA") or user_path("AppData", "Roaming")
    elif system == "Darwin":
        base = user_path(*XDG_BASE.split("/"))
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or user_path(".config")
    return os.path.join(base, *parts)


def load_history(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    return data if isinstance(data, list) else []


def append_history(path, entry):
    items = load_history(path)
    if items and items[0].get("input") == entry.get("input"):
        return items
    items.insert(0, entry)
    items = items[:HISTORY_LIMIT]
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False)
    except OSError:
        pass
    return items


def load_section_order():
    try:
        with open(SECTION_ORDER_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    if not isinstance(data, list):
        return []
    order = []
    for title in data:
        if not isinstance(title, str):
            continue
        name = SECTION_RENAMES.get(title, title)
        if name not in order:
            order.append(name)
    return order


def save_section_order(order):
    try:
        os.makedirs(os.path.dirname(SECTION_ORDER_PATH), exist_ok=True)
        with open(SECTION_ORDER_PATH, "w", encoding="utf-8") as f:
            json.dump(order, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def load_tool_order():
    try:
        with open(TOOL_ORDER_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    moved = {
        ("开发工具", "Cron 表达式"): "时间与日程",
        ("开发工具", "取色器"): "系统与桌面",
        ("其他", "房贷计算器"): "数值计算",
    }
    order = {}
    for category, names in data.items():
        if not isinstance(category, str) or not isinstance(names, list):
            continue
        for name in names:
            if not isinstance(name, str):
                continue
            name = TOOL_RENAMES.get(name, name)
            target = moved.get((category, name), SECTION_RENAMES.get(category, category))
            tools = order.setdefault(target, [])
            if name not in tools:
                tools.append(name)
    return order


def save_tool_order(order):
    try:
        os.makedirs(os.path.dirname(TOOL_ORDER_PATH), exist_ok=True)
        with open(TOOL_ORDER_PATH, "w", encoding="utf-8") as f:
            json.dump(order, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
