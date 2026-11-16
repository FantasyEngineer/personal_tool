"""条形码 Code 128：文本编码、条/空宽度与位图绘制。

编码表是纯数据；绘制只依赖 QtGui 的值类型（QImage/QPainter），可单独单元测试。
"""
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QColor, QFont, QImage, QPainter, QPixmap

# Code 128 的 103 个 symbol 的条/空宽度序列（每个 6 位数字，交替条空，首位是条）
_CODE128_PATTERNS = [
    "212222", "222122", "222221", "121223", "121322", "131222", "122213", "122312",
    "132212", "221213", "221312", "231212", "112232", "122132", "122231", "113222",
    "123122", "123221", "223211", "221132", "221231", "213212", "223112", "312131",
    "311222", "321122", "321221", "312212", "322112", "322211", "212123", "212321",
    "232121", "111323", "131123", "131321", "112313", "132113", "132311", "211313",
    "231113", "231311", "112133", "112331", "132131", "113123", "113321", "133121",
    "313121", "211331", "231131", "213113", "213311", "213131", "311123", "311321",
    "331121", "312113", "312311", "332111", "314111", "221411", "431111", "111224",
    "111422", "121124", "121421", "141122", "141221", "112214", "112412", "122114",
    "122411", "142112", "142211", "241211", "221114", "413111", "241112", "134111",
    "111242", "121142", "121241", "114212", "124112", "124211", "411212", "421112",
    "421211", "212141", "214121", "412121", "111143", "111341", "131141", "114113",
    "114311", "411113", "411311", "113141", "114131", "311141", "411131", "211412",
    "211214", "211232",
]
_CODE128_STOP = "2331112"
_CODE128_START_B = 104   # Code Set B：可打印 ASCII 32..126
_CODE128_QUIET = 10       # 左右静默区（模块数）


def code128_values(text):
    """按 Code Set B 把文本编码为 symbol 值序列（含起始符与校验位）。"""
    values = [_CODE128_START_B]
    for ch in text:
        o = ord(ch)
        if o < 32 or o > 126:
            raise ValueError(f"仅支持可打印 ASCII（空格 至 ~），不支持中文等字符：{ch!r}")
        values.append(o - 32)
    checksum = values[0] + sum(i * v for i, v in enumerate(values[1:], 1))
    values.append(checksum % 103)
    return values


def code128_widths(text):
    """返回交替的条/空宽度序列（首个为条），供逐段绘制。"""
    widths = []
    for v in code128_values(text):
        widths.extend(int(d) for d in _CODE128_PATTERNS[v])
    widths.extend(int(d) for d in _CODE128_STOP)
    return widths


def render_code128(text, module=3, height=130):
    """用 QPainter 绘制 Code 128 位图（含底部可读文字），返回 QPixmap 原始分辨率。"""
    widths = code128_widths(text)
    total_modules = sum(widths) + 2 * _CODE128_QUIET
    pm_w = total_modules * module
    img = QImage(pm_w, height + 24, QImage.Format_RGB32)
    painter = QPainter(img)
    painter.fillRect(0, 0, pm_w, height + 24, Qt.white)
    painter.setPen(Qt.NoPen)
    bar = QColor(0, 0, 0)
    x = _CODE128_QUIET * module
    black = True
    for w in widths:
        if black:
            painter.fillRect(QRect(x, 0, w * module, height), bar)
        x += w * module
        black = not black
    font = QFont("Menlo")
    font.setPixelSize(16)
    painter.setFont(font)
    painter.setPen(QColor(0, 0, 0))
    painter.drawText(QRect(0, height, pm_w, 24), Qt.AlignCenter, text)
    painter.end()
    return QPixmap.fromImage(img)
