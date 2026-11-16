"""日期时间纯工具：时间戳解析、格式化、时区转换与日期计算。

除 QDate / QFont 两个值类型外不依赖界面；QDate 用于日历差值的月份对齐。
"""
import datetime
import decimal
import email.utils
import platform
import re
import time
import zoneinfo

from PyQt5.QtCore import QDate
from PyQt5.QtGui import QFont


# 名称, IANA 时区, tzdata 不可用时退回的固定 UTC 偏移（小时）
DT_ZONES = [
    ("本地", None, None),
    ("UTC", "UTC", 0),
    ("北京", "Asia/Shanghai", 8),
    ("香港", "Asia/Hong_Kong", 8),
    ("新加坡", "Asia/Singapore", 8),
    ("东京", "Asia/Tokyo", 9),
    ("首尔", "Asia/Seoul", 9),
    ("新德里", "Asia/Kolkata", 5.5),
    ("迪拜", "Asia/Dubai", 4),
    ("莫斯科", "Europe/Moscow", 3),
    ("柏林", "Europe/Berlin", 1),
    ("巴黎", "Europe/Paris", 1),
    ("伦敦", "Europe/London", 0),
    ("纽约", "America/New_York", -5),
    ("芝加哥", "America/Chicago", -6),
    ("丹佛", "America/Denver", -7),
    ("洛杉矶", "America/Los_Angeles", -8),
    ("悉尼", "Australia/Sydney", 10),
]
DT_UNITS = [("自动识别", None), ("秒", 10 ** 9), ("毫秒", 10 ** 6), ("微秒", 10 ** 3), ("纳秒", 1)]
DT_EPOCH = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
DT_WEEKDAYS = "一二三四五六日"
DT_PRESET_PATTERNS = [
    "yyyy-MM-dd HH:mm:ss",
    "yyyy-MM-dd HH:mm:ss.SSS",
    "yyyy/MM/dd HH:mm:ss",
    "yyyyMMddHHmmss",
    "yyyyMMdd",
    "yyyy年MM月dd日 HH:mm:ss",
    "yyyy-MM-dd'T'HH:mm:ssZ",
    "EEE MMM dd HH:mm:ss yyyy",
    "dd/MMM/yyyy:HH:mm:ss Z",
]
DT_TEXT_FORMATS = [
    ("%Y/%m/%d %H:%M:%S.%f", "yyyy/MM/dd HH:mm:ss.SSS"),
    ("%Y/%m/%d %H:%M:%S", "yyyy/MM/dd HH:mm:ss"),
    ("%Y/%m/%d %H:%M", "yyyy/MM/dd HH:mm"),
    ("%Y/%m/%d", "yyyy/MM/dd"),
    ("%Y年%m月%d日 %H:%M:%S", "yyyy年MM月dd日 HH:mm:ss"),
    ("%Y年%m月%d日 %H时%M分%S秒", "yyyy年MM月dd日 HH时mm分ss秒"),
    ("%Y年%m月%d日", "yyyy年MM月dd日"),
    ("%m/%d/%Y %H:%M:%S", "MM/dd/yyyy HH:mm:ss"),
    ("%m/%d/%Y", "MM/dd/yyyy"),
    ("%d/%b/%Y:%H:%M:%S %z", "Nginx/Apache 日志"),
    ("%a %b %d %H:%M:%S %Y", "ctime"),
]
_DT_MONTHS = ["January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"]
_DT_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_DT_TOKEN_RE = re.compile(r"'[^']*'|y+|M+|d+|H+|h+|m+|s+|S+|E+|a|Z+|X+")


def dt_zone(index):
    """None 表示系统本地时区。"""
    _, key, fallback = DT_ZONES[index]
    if key is None:
        return None
    try:
        return zoneinfo.ZoneInfo(key)
    except Exception:
        return datetime.timezone(datetime.timedelta(hours=fallback), key)


def _dt_local_fixed():
    return datetime.datetime.now().astimezone().tzinfo


def dt_in_zone(dt, tz):
    if tz is not None:
        return dt.astimezone(tz)
    try:
        return dt.astimezone()
    except (OSError, OverflowError, ValueError):
        # Windows 的 localtime 不支持 1970 年之前，退回当前本地偏移
        return dt.astimezone(_dt_local_fixed())


def dt_localize(naive, tz):
    if tz is not None:
        return naive.replace(tzinfo=tz)
    try:
        return naive.astimezone()
    except (OSError, OverflowError, ValueError):
        return naive.replace(tzinfo=_dt_local_fixed())


def dt_to_ns(aware):
    delta = aware - DT_EPOCH
    return (delta.days * 86400 + delta.seconds) * 10 ** 9 + delta.microseconds * 1000


def dt_from_ns(ns):
    try:
        return DT_EPOCH + datetime.timedelta(microseconds=ns // 1000)
    except OverflowError:
        raise ValueError("超出可表示的时间范围（公元 1–9999 年）")


def dt_parse(text, tz, unit_ns=None):
    """解析时间戳或日期字符串，返回 (纳秒时间戳, 识别说明)。"""
    s = text.strip()
    if s.lower() in ("now", "现在", "当前"):
        return time.time_ns(), "当前时间"
    if re.fullmatch(r"[+-]?\d+(\.\d+)?", s):
        if unit_ns is None and len(s) in (8, 14) and s[0] in "12":
            fmt = "%Y%m%d" if len(s) == 8 else "%Y%m%d%H%M%S"
            try:
                naive = datetime.datetime.strptime(s, fmt)
            except ValueError:
                naive = None
            if naive is not None and 1900 <= naive.year < 2200:
                label = "yyyyMMdd" if len(s) == 8 else "yyyyMMddHHmmss"
                return dt_to_ns(dt_localize(naive, tz)), f"日期 {label}（按时间戳解析请指定单位）"
        value = decimal.Decimal(s)
        name = None
        if unit_ns is None:
            mag = abs(value)
            for limit, ns, unit_name in ((10 ** 11, 10 ** 9, "秒"), (10 ** 14, 10 ** 6, "毫秒"),
                                         (10 ** 17, 10 ** 3, "微秒")):
                if mag < limit:
                    unit_ns, name = ns, unit_name
                    break
            else:
                unit_ns, name = 1, "纳秒"
        else:
            name = next(n for n, u in DT_UNITS if u == unit_ns)
        ns = int(value * unit_ns)
        dt_from_ns(ns)
        return ns, f"Unix 时间戳（{name}）"

    dt, label = None, ""
    iso = s[:-1] + "+00:00" if s[-1:] in ("Z", "z") else s
    try:
        dt = datetime.datetime.fromisoformat(iso)
        label = "ISO 8601" if "T" in s.upper() else "日期时间"
    except ValueError:
        pass
    if dt is None and re.search(r"[A-Za-z]{3}", s):
        try:
            dt = email.utils.parsedate_to_datetime(s)
            label = "RFC 2822 / HTTP Date"
        except (TypeError, ValueError, IndexError):
            dt = None
    if dt is None:
        for fmt, fmt_label in DT_TEXT_FORMATS:
            try:
                dt = datetime.datetime.strptime(s, fmt)
                label = fmt_label
                break
            except ValueError:
                continue
    if dt is None:
        raise ValueError("无法识别，支持时间戳、ISO 8601、RFC 2822 及常见日期格式")
    if dt.tzinfo is None:
        dt = dt_localize(dt, tz)
    else:
        label += "（含时区）"
    return dt_to_ns(dt), label


def _dt_offset(dt, colon=True):
    off = dt.utcoffset() or datetime.timedelta(0)
    total = int(off.total_seconds())
    sign = "+" if total >= 0 else "-"
    h, m = divmod(abs(total) // 60, 60)
    return f"{sign}{h:02d}:{m:02d}" if colon else f"{sign}{h:02d}{m:02d}"


def dt_format(dt, pattern):
    """按 Java/JS 常用的 yyyy-MM-dd HH:mm:ss.SSS 风格格式化（与系统语言无关）。"""
    def rep(m):
        t = m.group()
        c, n = t[0], len(t)
        if c == "'":
            return t[1:-1] if n > 2 else "'"
        if c == "y":
            return f"{dt.year % 100:02d}" if n == 2 else f"{dt.year:0{n}d}"
        if c == "M":
            if n >= 4:
                return _DT_MONTHS[dt.month - 1]
            if n == 3:
                return _DT_MONTHS[dt.month - 1][:3]
            return f"{dt.month:0{n}d}"
        if c == "d":
            return f"{dt.day:0{n}d}"
        if c == "H":
            return f"{dt.hour:0{n}d}"
        if c == "h":
            return f"{dt.hour % 12 or 12:0{n}d}"
        if c == "m":
            return f"{dt.minute:0{n}d}"
        if c == "s":
            return f"{dt.second:0{n}d}"
        if c == "S":
            return f"{dt.microsecond:06d}"[:n].ljust(n, "0")
        if c == "E":
            return _DT_DAYS[dt.weekday()] if n >= 4 else _DT_DAYS[dt.weekday()][:3]
        if c == "a":
            return "AM" if dt.hour < 12 else "PM"
        if c == "Z":
            return _dt_offset(dt, colon=False)
        if not dt.utcoffset():
            return "Z"
        return _dt_offset(dt)[:3] if n == 1 else _dt_offset(dt, colon=n >= 3)
    return _DT_TOKEN_RE.sub(rep, pattern)


def dt_relative(ns, now_ns=None):
    diff = (ns - (time.time_ns() if now_ns is None else now_ns)) / 1e9
    a = abs(diff)
    if a < 1:
        return "刚刚"
    for unit_s, name in ((31536000, "年"), (2592000, "个月"), (86400, "天"),
                         (3600, "小时"), (60, "分钟"), (1, "秒")):
        if a >= unit_s:
            return f"{int(a // unit_s)} {name}{'后' if diff > 0 else '前'}"


def dt_workdays(d1, d2):
    """[d1, d2) 内周一至周五的天数。"""
    weeks, rem = divmod((d2 - d1).days, 7)
    start = d1.weekday()
    return weeks * 5 + sum(1 for i in range(rem) if (start + i) % 7 < 5)


def dt_calendar_diff(d1, d2):
    """d1 <= d2，返回自然的 (年, 月, 天)。"""
    months = (d2.year - d1.year) * 12 + d2.month - d1.month
    if d2.day < d1.day:
        months -= 1
    anchor = QDate(d1.year, d1.month, d1.day).addMonths(months)
    days = anchor.daysTo(QDate(d2.year, d2.month, d2.day))
    return months // 12, months % 12, days


def _dt_zone_label(index, ref=None):
    name = DT_ZONES[index][0]
    dt = dt_in_zone(ref or datetime.datetime.now(datetime.timezone.utc), dt_zone(index))
    return f"{name} (UTC{_dt_offset(dt)})"


def _dt_mono():
    return QFont("Consolas", 10) if platform.system() == "Windows" else QFont("Menlo", 13)
