"""提醒事项：规则的时间计算与持久化。

QDate/QDateTime/QTime 只作为值类型使用，不含界面；弹窗卡片与提醒引擎在界面层。
"""
import json
import os
import re

from PyQt5.QtCore import QDate, QDateTime, QTime

REMINDERS_PATH = os.path.join(os.path.expanduser("~"), ".personal_toolbox", "reminders.json")
REPEAT_DAILY = "每天"
REPEAT_WEEKDAY = "工作日"
REPEAT_ONCE = "仅一次"
# 间隔重复：每 every 天/周/月，从 anchor 那天起算（anchor 就是第一班）。
REPEAT_INTERVAL = "间隔重复"
UNIT_CHOICES = ("天", "周", "月")
REPEAT_CHOICES = (REPEAT_DAILY, REPEAT_WEEKDAY, REPEAT_INTERVAL, REPEAT_ONCE)
INTERVAL_MAX = 12
WEEKDAY_NAMES = ("", "周一", "周二", "周三", "周四", "周五", "周六", "周日")
SNOOZE_MINUTES = 10
# 错过太久就不再弹，避免开机时把昨天的提醒一次性补出来；只登记为已触发。
MISSED_QUIET_SECONDS = 3 * 3600


def _hhmm_valid(text):
    return bool(re.match(r"^([01]\d|2[0-3]):[0-5]\d$", text or ""))


def _rule_time(rule):
    return int(rule["time"][:2]), int(rule["time"][3:5])


def interval_fields(rule):
    """间隔规则 -> (anchor, every, unit)；字段不合法时返回 None。"""
    anchor = QDate.fromString(rule.get("anchor", ""), "yyyy-MM-dd")
    if not anchor.isValid():
        return None
    try:
        every = int(rule.get("every", 1))
    except (TypeError, ValueError):
        every = 1
    every = max(1, min(INTERVAL_MAX, every))
    unit = rule.get("unit", "天")
    if unit not in UNIT_CHOICES:
        unit = "天"
    return anchor, every, unit


def _interval_date(anchor, every, unit, index):
    """第 index 班（index>=0）的日期；月按日历偏移算，遇小月钳到月末。"""
    if unit == "周":
        return anchor.addDays(index * every * 7)
    if unit == "月":
        months = index * every
        year = anchor.year() + (anchor.month() - 1 + months) // 12
        month = (anchor.month() - 1 + months) % 12 + 1
        day = min(anchor.day(), QDate(year, month, 1).daysInMonth())
        return QDate(year, month, day)
    return anchor.addDays(index * every)


def _interval_index(anchor, every, unit, day):
    """day 当天或之前最近那一班的下标，可能为负（还没起算）。"""
    if unit == "月":
        months = (day.year() - anchor.year()) * 12 + (day.month() - anchor.month())
        return months // every
    step = every * (7 if unit == "周" else 1)
    return anchor.daysTo(day) // step


def interval_points(anchor, every, unit, time_text, after, count=3):
    """从 after 之后算起，往后 count 个触发时刻（用于表单里预览）。"""
    if not _hhmm_valid(time_text):
        return []
    hh, mm = int(time_text[:2]), int(time_text[3:5])
    pts = []
    index = _interval_index(anchor, every, unit, after.date())
    if index < 0:
        index = 0
    occ = QDateTime(_interval_date(anchor, every, unit, index), QTime(hh, mm))
    while len(pts) < count:
        if occ > after:
            pts.append(occ)
        index += 1
        occ = QDateTime(_interval_date(anchor, every, unit, index), QTime(hh, mm))
        if index > 400:       # 兜底，避免异常字段把循环拖死
            break
    return pts


def load_reminders():
    try:
        with open(REMINDERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {"rules": [], "sound": True}
    rules = data.get("rules") if isinstance(data, dict) else None
    clean = [r for r in (rules or [])
             if isinstance(r, dict) and r.get("name") and _hhmm_valid(r.get("time"))]
    for rule in clean:
        if rule.get("repeat") == "仅当天":
            rule["repeat"] = REPEAT_ONCE
        elif rule.get("repeat") not in REPEAT_CHOICES:
            rule["repeat"] = REPEAT_DAILY
    sound = data.get("sound", True) if isinstance(data, dict) else True
    return {"rules": clean, "sound": bool(sound)}


def save_reminders(state):
    try:
        os.makedirs(os.path.dirname(REMINDERS_PATH), exist_ok=True)
        with open(REMINDERS_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.chmod(REMINDERS_PATH, 0o600)
    except OSError:
        pass


def reminder_occurrence(rule, now):
    """规则在 now 之前最近一次的触发时刻；还没到点返回 None。"""
    if not _hhmm_valid(rule.get("time")):
        return None
    hh, mm = _rule_time(rule)
    repeat = rule.get("repeat", REPEAT_DAILY)
    if repeat == REPEAT_INTERVAL:
        fields = interval_fields(rule)
        if fields is None:
            return None
        anchor, every, unit = fields
        index = _interval_index(anchor, every, unit, now.date())
        while index >= 0:
            occ = QDateTime(_interval_date(anchor, every, unit, index), QTime(hh, mm))
            if occ <= now:
                return occ
            index -= 1
        return None
    if repeat == REPEAT_ONCE:
        day = QDate.fromString(rule.get("date", ""), "yyyy-MM-dd")
        if not day.isValid():
            return None
        occ = QDateTime(day, QTime(hh, mm))
        return occ if occ <= now else None
    for back in range(0, 8):
        day = now.date().addDays(-back)
        if repeat == REPEAT_WEEKDAY and day.dayOfWeek() > 5:
            continue
        occ = QDateTime(day, QTime(hh, mm))
        if occ <= now:
            return occ
    return None


def reminder_upcoming(rule, now):
    """规则在 now 之后最近一次的触发时刻，用于"下一条提醒"提示。"""
    if not _hhmm_valid(rule.get("time")):
        return None
    hh, mm = _rule_time(rule)
    repeat = rule.get("repeat", REPEAT_DAILY)
    if repeat == REPEAT_INTERVAL:
        fields = interval_fields(rule)
        if fields is None:
            return None
        anchor, every, unit = fields
        index = max(0, _interval_index(anchor, every, unit, now.date()))
        for _ in range(3):
            occ = QDateTime(_interval_date(anchor, every, unit, index), QTime(hh, mm))
            if occ > now:
                return occ
            index += 1
        return None
    if repeat == REPEAT_ONCE:
        day = QDate.fromString(rule.get("date", ""), "yyyy-MM-dd")
        if not day.isValid():
            return None
        occ = QDateTime(day, QTime(hh, mm))
        return occ if occ > now else None
    for ahead in range(0, 8):
        day = now.date().addDays(ahead)
        if repeat == REPEAT_WEEKDAY and day.dayOfWeek() > 5:
            continue
        occ = QDateTime(day, QTime(hh, mm))
        if occ > now:
            return occ
    return None


def next_reminder(rules, now):
    best_name, best_when = None, None
    for rule in rules:
        if not rule.get("enabled", True):
            continue
        when = reminder_upcoming(rule, now)
        if when and (best_when is None or when < best_when):
            best_when, best_name = when, rule.get("name", "")
    return best_name, best_when


def reminder_when_text(when, now):
    days = now.date().daysTo(when.date())
    day = {0: "今天", 1: "明天", 2: "后天"}.get(days)
    if day is None:
        day = "%s %s" % (when.toString("MM-dd"), WEEKDAY_NAMES[when.date().dayOfWeek()])
    return "%s %s" % (day, when.toString("HH:mm"))
