"""文本差异：行级并排对比、行内字符级差异与文件读取。

纯逻辑，不依赖 Qt；配色与文案常量一并放这里，界面直接引用。
"""
import difflib

DIFF_AUTO_LIMIT = 4000
DIFF_ROW_LIMIT = 5000
DIFF_CHAR_LIMIT = 4000
DIFF_COLORS = {"insert": "#E6F4EA", "delete": "#FCE8E6", "replace": "#FEF7E0"}
DIFF_LABELS = {"equal": "相同", "insert": "新增", "delete": "删除", "replace": "修改"}
DIFF_DELTA_BG = "#F6C7C2"
DIFF_DELTA_FG = "#A50E0E"


def load_text_file(path):
    """Decode a user-picked file: BOM, UTF-8, then GBK, never giving up on bytes."""
    with open(path, "rb") as f:
        raw = f.read()
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def _diff_key(line, ignore_space, ignore_case):
    text = " ".join(line.split()) if ignore_space else line
    return text.lower() if ignore_case else text


def diff_rows(left, right, ignore_space=False, ignore_case=False):
    """行级并排差异：(类型, 左行号, 左内容, 右行号, 右内容)，行号从 1 开始。"""
    l_lines, r_lines = left.splitlines(), right.splitlines()
    cmp_l = [_diff_key(l, ignore_space, ignore_case) for l in l_lines]
    cmp_r = [_diff_key(r, ignore_space, ignore_case) for r in r_lines]
    matcher = difflib.SequenceMatcher(None, cmp_l, cmp_r, autojunk=False)
    rows = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            rows.extend(("equal", i1 + k + 1, l_lines[i1 + k], j1 + k + 1, r_lines[j1 + k])
                        for k in range(i2 - i1))
            continue
        if tag == "delete":
            rows.extend(("delete", k + 1, l_lines[k], None, "") for k in range(i1, i2))
            continue
        if tag == "insert":
            rows.extend(("insert", None, "", k + 1, r_lines[k]) for k in range(j1, j2))
            continue
        pairs = min(i2 - i1, j2 - j1)
        rows.extend(("replace", i1 + k + 1, l_lines[i1 + k], j1 + k + 1, r_lines[j1 + k])
                    for k in range(pairs))
        rows.extend(("delete", k + 1, l_lines[k], None, "") for k in range(i1 + pairs, i2))
        rows.extend(("insert", None, "", k + 1, r_lines[k]) for k in range(j1 + pairs, j2))
    return rows


def diff_segments(left_line, right_line):
    """一行内哪些字符变了：返回 (左区间, 右区间)，每项是 [起点, 终点) 且互不重叠。"""
    if max(len(left_line), len(right_line)) > DIFF_CHAR_LIMIT:
        return ([(0, len(left_line))] if left_line else [],
                [(0, len(right_line))] if right_line else [])
    l_segs, r_segs = [], []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, left_line, right_line,
                                                      autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        if i2 > i1:
            l_segs.append((i1, i2))
        if j2 > j1:
            r_segs.append((j1, j2))
    return l_segs, r_segs


def _text_pieces(text, segments):
    """把一行拆成 (片段, 是否改动)，未命中的空隙补成正常片段。"""
    pieces = []
    pos = 0
    for start, end in segments:
        if start > pos:
            pieces.append((text[pos:start], False))
        pieces.append((text[start:end], True))
        pos = end
    if pos < len(text):
        pieces.append((text[pos:], False))
    return pieces
