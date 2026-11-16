"""Cron 表达式解析与执行计划：纯计算，不含界面。

支持标准 5 字段（分 时 日 月 周）与 6 字段（秒 分 时 日 月 周，Spring/Quartz 风格）。
"""
import datetime


def parse_field(token, lo, hi, is_dow=False):
    """解析单个 cron 字段：支持 * ? , - /，周日的 7 折算成 0；非法取值抛 ValueError。"""
    token = token.strip()
    if token == "":
        raise ValueError("存在空的字段")
    values = set()
    for part in token.split(","):
        step = 1
        body = part
        if "/" in part:
            body, step_s = part.split("/", 1)
            try:
                step = int(step_s)
            except ValueError:
                raise ValueError(f"步长无效: {part}")
            if step <= 0:
                raise ValueError(f"步长必须为正: {part}")
        body = body.strip()
        if body in ("*", "?"):
            start, end = lo, hi
        elif "-" in body:
            a, b = body.split("-", 1)
            start, end = int(a), int(b)
        else:
            v = int(body)
            if "/" in part:
                start, end = v, hi
            else:
                start = end = v
        if start < lo or end > hi or start > end:
            raise ValueError(f"字段超出范围 [{lo}-{hi}]: {part}")
        for v in range(start, end + 1, step):
            if is_dow and v == 7:
                v = 0
            values.add(v)
    return values


def plan(expr, count, now=None):
    """返回 expr 在 now 之后的 count 个执行时刻；5 年内凑不满 count 次抛 ValueError。"""
    fields = expr.split()
    if len(fields) == 5:
        has_seconds = False
        m_expr, h_expr, dom_expr, mon_expr, dow_expr = fields
        sec_expr = "0"
    elif len(fields) == 6:
        has_seconds = True
        sec_expr, m_expr, h_expr, dom_expr, mon_expr, dow_expr = fields
    else:
        raise ValueError("需要 5 个字段(分 时 日 月 周) 或 6 个字段(秒 分 时 日 月 周)")

    minutes = parse_field(m_expr, 0, 59)
    hours = parse_field(h_expr, 0, 23)
    doms = parse_field(dom_expr, 1, 31)
    mons = parse_field(mon_expr, 1, 12)
    dows = parse_field(dow_expr, 0, 7, is_dow=True)
    secs = parse_field(sec_expr, 0, 59) if has_seconds else {0}

    dom_restricted = dom_expr.strip() not in ("*", "?")
    dow_restricted = dow_expr.strip() not in ("*", "?")

    def day_ok(dt):
        d = dt.day
        w = dt.isoweekday() % 7
        if dom_restricted and dow_restricted:
            return d in doms or w in dows
        if dom_restricted:
            return d in doms
        if dow_restricted:
            return w in dows
        return True

    now = now if now is not None else datetime.datetime.now()
    if has_seconds:
        cur = now.replace(microsecond=0) + datetime.timedelta(seconds=1)
        step = datetime.timedelta(seconds=1)
    else:
        cur = now.replace(second=0, microsecond=0) + datetime.timedelta(minutes=1)
        step = datetime.timedelta(minutes=1)

    end = now + datetime.timedelta(days=366 * 5)
    results = []
    while cur <= end and len(results) < count:
        if cur.month not in mons:
            # jump to first day of next month
            y = cur.year + (1 if cur.month == 12 else 0)
            mo = 1 if cur.month == 12 else cur.month + 1
            cur = datetime.datetime(y, mo, 1, 0, 0, 0)
            continue
        if not day_ok(cur):
            cur = datetime.datetime(cur.year, cur.month, cur.day) + datetime.timedelta(days=1)
            continue
        if cur.hour not in hours:
            cur = datetime.datetime(cur.year, cur.month, cur.day, cur.hour) + datetime.timedelta(hours=1)
            continue
        if cur.minute not in minutes:
            cur = cur.replace(second=0) + datetime.timedelta(minutes=1)
            continue
        if cur.second not in secs:
            cur = cur + step
            continue
        results.append(cur)
        cur = cur + step
    if len(results) < count:
        raise ValueError(f"在 5 年内不足 {count} 次执行")
    return results
