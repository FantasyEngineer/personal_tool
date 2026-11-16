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
REPEAT_CHOICES = (REPEAT_DAILY, REPEAT_WEEKDAY, REPEAT_ONCE)
WEEKDAY_NAMES = ("", "周一", "周二", "周三", "周四", "周五", "周六", "周日")
SNOOZE_MINUTES = 10
# 错过太久就不再弹，避免开机时把昨天的提醒一次性补出来；只登记为已触发。
MISSED_QUIET_SECONDS = 3 * 3600


def _hhmm_valid(text):
    return bool(re.match(r"^([01]\d|2[0-3]):[0-5]\d$", text or ""))


def _rule_time(rule):
    return int(rule["time"][:2]), int(rule["time"][3:5])


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
