"""文本处理：命名风格改写、行操作、统计与字面量互转。

纯函数与纯数据表，不依赖 Qt；界面只负责把 TEXT_OPS 里的条目渲染成按钮。
"""
import ast
import json
import random
import re

TEXT_INVISIBLE_RE = re.compile("[\u00a0\u00ad\u200b-\u200f\u2028-\u202e\u2060-\u2064\ufeff"
                               "\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
TEXT_CJK_RE = re.compile("[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
TEXT_WORD_RE = re.compile(r"[A-Za-z0-9_]+(?:['’-][A-Za-z0-9_]+)*")
_TEXT_CASE_WORD_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+|[^\W\d_A-Za-z]+")


def text_natural_key(line):
    return [int(t) if i % 2 else t.lower() for i, t in enumerate(re.split(r"(\d+)", line))]


def text_case(line, style):
    """单行按 camelCase / snake_case 等命名风格改写，保留首尾空白。"""
    m = re.match(r"(\s*)(.*?)(\s*)$", line, re.S)
    lead, body, trail = m.groups()
    words = _TEXT_CASE_WORD_RE.findall(body)
    if not words:
        return line
    cap = [w[:1].upper() + w[1:].lower() for w in words]
    out = {
        "camel": words[0].lower() + "".join(cap[1:]),
        "pascal": "".join(cap),
        "snake": "_".join(w.lower() for w in words),
        "kebab": "-".join(w.lower() for w in words),
        "constant": "_".join(w.upper() for w in words),
        "dot": ".".join(w.lower() for w in words),
    }[style]
    return lead + out + trail


def text_fullwidth_to_half(text):
    out = []
    for ch in text:
        code = ord(ch)
        if code == 0x3000:
            code = 0x20
        elif 0xFF01 <= code <= 0xFF5E:
            code -= 0xFEE0
        out.append(chr(code))
    return "".join(out)


def text_count_lines(lines):
    """等同 sort | uniq -c | sort -rn：按出现次数降序，同次数保持首次出现顺序。"""
    counts = {}
    for line in lines:
        counts[line] = counts.get(line, 0) + 1
    width = len(str(max(counts.values()))) if counts else 1
    return [f"{n:>{width}}  {line}" for line, n in sorted(counts.items(), key=lambda kv: -kv[1])]


def text_sql_in(lines):
    items = ["'" + line.strip().replace("'", "''") + "'" for line in lines if line.strip()]
    return "(" + ", ".join(items) + ")"


def text_unquote_literal(text):
    s = text.strip()
    if len(s) >= 2 and s[0] == s[-1] == "'":
        value = ast.literal_eval(s)
    else:
        if not (len(s) >= 2 and s[0] == s[-1] == '"'):
            s = '"' + re.sub(r'(?<!\\)((?:\\\\)*)"', r'\1\\"', s) + '"'
        value = json.loads(s, strict=False)
    if not isinstance(value, str):
        raise ValueError("不是字符串字面量")
    return value


def text_stats(text):
    lines = text.split("\n") if text else []
    longest = max(range(len(lines)), key=lambda i: len(lines[i])) if lines else None
    tab_indent = sum(1 for l in lines if l.startswith("\t"))
    space_indent = sum(1 for l in lines if l.startswith(" "))
    if tab_indent and space_indent:
        indent = f"混合（Tab {tab_indent} / 空格 {space_indent} 行）"
    elif tab_indent:
        indent = "Tab"
    elif space_indent:
        widths = [len(l) - len(l.lstrip(" ")) for l in lines if l.startswith(" ") and l.strip()]
        unit = min((w for w in widths if w), default=0)
        indent = f"空格（最小 {unit} 格）" if unit else "空格"
    else:
        indent = "—"
    try:
        gbk = f"{len(text.encode('gbk')):,}"
    except UnicodeEncodeError:
        gbk = "含无法编码字符"
    non_space = len(re.sub(r"\s", "", text))
    return [
        ("字符", f"{len(text):,}"),
        ("不含空白", f"{non_space:,}"),
        ("中文字", f"{len(TEXT_CJK_RE.findall(text)):,}"),
        ("英文单词", f"{len(TEXT_WORD_RE.findall(text)):,}"),
        ("行数", f"{len(lines):,}"),
        ("非空行", f"{sum(1 for l in lines if l.strip()):,}"),
        ("唯一行", f"{len(set(lines)):,}"),
        ("最长行", f"{len(lines[longest]):,}（第 {longest + 1} 行）" if lines else "—"),
        ("UTF-8", f"{len(text.encode('utf-8', 'surrogatepass')):,} B"),
        ("UTF-16", f"{len(text.encode('utf-16-le', 'surrogatepass')):,} B"),
        ("GBK", gbk if gbk.startswith("含") else gbk + " B"),
        ("非 ASCII", f"{sum(1 for ch in text if ord(ch) > 127):,}"),
        ("缩进", indent),
        ("行尾空白", f"{sum(1 for l in lines if l != l.rstrip()):,} 行"),
        ("不可见字符", f"{len(TEXT_INVISIBLE_RE.findall(text)):,}"),
    ]


def _line_op(fn):
    """按行处理；末尾换行原样保留。"""
    def run(text, params):
        trailing = text.endswith("\n")
        lines = text[:-1].split("\n") if trailing else text.split("\n")
        return "\n".join(fn(lines, params)) + ("\n" if trailing else "")
    return run


def _dedupe(lines, _p):
    return list(dict.fromkeys(lines))


def _only_dupes(lines, _p):
    seen = {}
    for line in lines:
        seen[line] = seen.get(line, 0) + 1
    return [line for line in dict.fromkeys(lines) if seen[line] > 1]


def _only_unique(lines, _p):
    seen = {}
    for line in lines:
        seen[line] = seen.get(line, 0) + 1
    return [line for line in lines if seen[line] == 1]


def _squeeze_blank(lines, _p):
    out = []
    for line in lines:
        if line.strip() or not (out and not out[-1].strip()):
            out.append(line)
    return out


def _shuffled(lines, _p):
    lines = list(lines)
    random.shuffle(lines)
    return lines


def _number_lines(lines, _p):
    width = len(str(len(lines)))
    return [f"{i:>{width}}  {line}" for i, line in enumerate(lines, 1)]


TEXT_OPS = {
    "行操作": [
        ("升序排序", _line_op(lambda ls, p: sorted(ls))),
        ("降序排序", _line_op(lambda ls, p: sorted(ls, reverse=True))),
        ("自然排序（file2 < file10）", _line_op(lambda ls, p: sorted(ls, key=text_natural_key))),
        ("忽略大小写排序", _line_op(lambda ls, p: sorted(ls, key=str.lower))),
        ("按长度排序", _line_op(lambda ls, p: sorted(ls, key=len))),
        ("反转行序", _line_op(lambda ls, p: ls[::-1])),
        ("随机打乱", _line_op(_shuffled)),
        None,
        ("去重（保留首次出现）", _line_op(_dedupe)),
        ("只保留重复行", _line_op(_only_dupes)),
        ("只保留唯一行", _line_op(_only_unique)),
        ("统计重复次数（uniq -c）", _line_op(lambda ls, p: text_count_lines(ls))),
        None,
        ("删除空行", _line_op(lambda ls, p: [l for l in ls if l.strip()])),
        ("合并连续空行", _line_op(_squeeze_blank)),
        ("去除首尾空白", _line_op(lambda ls, p: [l.strip() for l in ls])),
        ("去除行尾空白", _line_op(lambda ls, p: [l.rstrip() for l in ls])),
        ("添加行号", _line_op(_number_lines)),
        ("删除行首行号", _line_op(lambda ls, p: [re.sub(r"^\s*\d+(?:[.:)、]\s?|\s+)", "", l) for l in ls])),
    ],
    "转换": [
        ("全部大写", lambda t, p: t.upper()),
        ("全部小写", lambda t, p: t.lower()),
        ("单词首字母大写", lambda t, p: re.sub(r"[A-Za-z]+", lambda m: m.group().capitalize(), t)),
        ("大小写互换", lambda t, p: t.swapcase()),
        None,
        ("camelCase", _line_op(lambda ls, p: [text_case(l, "camel") for l in ls])),
        ("PascalCase", _line_op(lambda ls, p: [text_case(l, "pascal") for l in ls])),
        ("snake_case", _line_op(lambda ls, p: [text_case(l, "snake") for l in ls])),
        ("kebab-case", _line_op(lambda ls, p: [text_case(l, "kebab") for l in ls])),
        ("CONSTANT_CASE", _line_op(lambda ls, p: [text_case(l, "constant") for l in ls])),
        ("dot.case", _line_op(lambda ls, p: [text_case(l, "dot") for l in ls])),
        None,
        ("全角转半角", lambda t, p: text_fullwidth_to_half(t)),
        ("Tab 转 4 空格", lambda t, p: t.replace("\t", "    ")),
        ("4 空格转 Tab", _line_op(lambda ls, p: [re.sub(r"^(?: {4})+", lambda m: "\t" * (len(m.group()) // 4), l) for l in ls])),
        ("清除不可见字符（NBSP 转空格）", lambda t, p: TEXT_INVISIBLE_RE.sub(
            lambda m: " " if m.group() == "\u00a0" else "", t)),
        None,
        ("转为字符串字面量", lambda t, p: json.dumps(t, ensure_ascii=False)),
        ("还原字符串字面量", lambda t, p: text_unquote_literal(t)),
    ],
    "合并拆分": [
        ("多行合并为一行（用分隔符）", _line_op(lambda ls, p: [p["sep"].join(ls)])),
        ("按分隔符拆分为多行", lambda t, p: t.replace(p["sep"], "\n") if p["sep"] else t),
        ("每行加前缀 / 后缀", _line_op(lambda ls, p: [p["prefix"] + l + p["suffix"] for l in ls])),
        None,
        ("生成 SQL IN 列表", _line_op(lambda ls, p: [text_sql_in(ls)])),
        ("生成 JSON 数组", _line_op(lambda ls, p: [json.dumps([l for l in ls if l.strip()], ensure_ascii=False)])),
        ("生成带引号逗号列表", _line_op(lambda ls, p: [", ".join(json.dumps(l, ensure_ascii=False) for l in ls if l.strip())])),
    ],
}


def _text_escape_param(value):
    return value.replace("\\n", "\n").replace("\\t", "\t")
