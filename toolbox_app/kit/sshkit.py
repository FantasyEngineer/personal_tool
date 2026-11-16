"""SSH config：~/.ssh/config 的解析、序列化与受管选项合并。

解析时保留选项顺序与注释，未改动的块重写后逐字节不变；界面表单在配置文件工具里。
"""
import re

from toolbox_app.storage import user_path

SSH_CONFIG_KEYS = ("HostName", "User", "Port", "IdentityFile", "ProxyJump")
SSH_ALIAS_RE = re.compile(r"^[A-Za-z0-9._*:/\[\]-]+$")


def ssh_config_path():
    return user_path(".ssh", "config")


def _ssh_canonical(key):
    for name in SSH_CONFIG_KEYS:
        if name.lower() == key.lower():
            return name
    return key


def ssh_parse_config(text):
    """Split into Host blocks; option order and comments are kept so untouched blocks
    survive a rewrite byte-for-byte."""
    preamble, blocks, has_match = [], [], False
    current = None
    for line in (text or "").splitlines():
        s = line.strip()
        low = s.lower()
        if low.startswith("host ") and len(s.split()) > 1:
            current = {"host": s.split()[1:], "opts": []}
            blocks.append(current)
            continue
        if low.startswith("match"):
            has_match = True
        if current is None:
            preamble.append(("#", line))
        elif not s or s.startswith("#"):
            current["opts"].append(("#", line))
        else:
            match = re.match(r"^(\S+?)\s*=\s*(.*)$", s) or re.match(r"^(\S+)\s+(.*)$", s)
            if match:
                current["opts"].append((match.group(1), match.group(2).strip()))
            else:
                current["opts"].append(("#", line))
    return preamble, blocks, has_match


def ssh_dump(preamble, blocks):
    lines = [raw for _k, raw in preamble]
    for block in blocks:
        lines.append("Host " + " ".join(block["host"]))
        for key, value in block["opts"]:
            lines.append(value if key == "#" else "    %s %s" % (key, value))
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n" if lines else ""


def ssh_summary(block):
    opts = {k.lower(): v for k, v in block["opts"] if k != "#"}
    target = opts.get("hostname") or (block["host"][0] if block["host"] else "?")
    bits = []
    if opts.get("user"):
        bits.append(opts["user"] + "@")
    bits.append(target)
    if opts.get("port"):
        bits.append(":%s" % opts["port"])
    if opts.get("proxyjump"):
        bits.append(" 经 %s" % opts["proxyjump"])
    return "".join(bits)


def _ssh_merge_opts(old_opts, managed, extras):
    """Replace only the keys the form manages; comments and unknown options stay in place."""
    out, placed = [], set()
    for key, value in old_opts:
        if key == "#":
            out.append((key, value))
            continue
        canonical = _ssh_canonical(key)
        if canonical in managed:
            placed.add(canonical)
            if managed[canonical]:
                out.append((canonical, managed[canonical]))
        else:
            out.append((key, value))
    for key, value in managed.items():
        if value and key not in placed:
            out.append((key, value))
    out.extend(extras)
    return out
