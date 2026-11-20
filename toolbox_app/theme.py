"""界面外观：字体、控件样式表与通用布局。

这里只放被多个窗口复用的样式与窗口几何，不放任何业务逻辑。
"""
import os
import platform

from PyQt5.QtCore import Qt, QEvent, QPoint, QPointF, QRect, QSize, QObject
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QPixmap, QPolygonF
from PyQt5.QtWidgets import QApplication, QComboBox, QLayout, QStyle, QStyleOptionComboBox

from toolbox_app.constants import TOOL_WIN_H, TOOL_WIN_W


def tool_win_geometry():
    """Uniform default size + centered position for every tool window."""
    w, h = TOOL_WIN_W, TOOL_WIN_H
    x, y = 200, 200
    try:
        screen = QApplication.primaryScreen().availableGeometry()
        w = min(w, screen.width() - 40)
        h = min(h, screen.height() - 40)
        x = screen.x() + (screen.width() - w) // 2
        y = screen.y() + (screen.height() - h) // 2
    except Exception:
        pass
    return x, y, w, h


def ui_font(pt_mac, px_win, bold=False, family_mac="PingFang SC"):
    """QFont for the main window chrome.

    macOS keeps the original point size; Windows pins an explicit pixel size so
    titles and the bottom bar aren't inflated by the point->pixel DPI scaling
    that makes them look oversized next to the pixel-based section buttons.
    """
    if platform.system() == "Windows":
        font = QFont("Microsoft YaHei")
        font.setPixelSize(px_win)
    else:
        font = QFont(family_mac, pt_mac)
    font.setBold(bold)
    return font


def _lineedit_style():
    return """
        QLineEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 6px 8px;
            font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; }
        QLineEdit:focus { border-color: #1A73E8; }
    """


_COMBO_ARROW_PATH = None


def _combo_arrow_path():
    """下拉箭头的 png。样式表里一旦声明了 ::drop-down，Qt 就不再画系统箭头，
    必须自带 image，否则整条下拉框只剩一个空白框（看不出是下拉，也只能点到右侧窄条）。"""
    global _COMBO_ARROW_PATH
    if _COMBO_ARROW_PATH is not None:
        return _COMBO_ARROW_PATH
    folder = os.path.join(os.path.expanduser("~"), ".personal_toolbox")
    path = os.path.join(folder, "combo_arrow.png")
    try:
        os.makedirs(folder, exist_ok=True)
        pm = QPixmap(32, 32)
        pm.fill(Qt.transparent)
        painter = QPainter(pm)
        pen = QPen(QColor("#5F6368"))
        pen.setWidth(3)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(pen)
        painter.drawPolyline(QPolygonF([QPointF(9, 13), QPointF(16, 20), QPointF(23, 13)]))
        painter.end()
        _COMBO_ARROW_PATH = path if pm.save(path, "PNG") else ""
    except (OSError, RuntimeError):
        _COMBO_ARROW_PATH = ""
    return _COMBO_ARROW_PATH


def _combo_style(size=12, mono=False):
    family = ('"Menlo", "Consolas", monospace' if mono
              else '"PingFang SC", "Microsoft YaHei", sans-serif')
    arrow = _combo_arrow_path()
    # 取不到 png 时（只读目录等）退回系统箭头：不写 ::drop-down，Qt 仍会画出原生箭头
    drop = (u'''
        QComboBox::drop-down { border: none; width: 22px; subcontrol-position: center right; }
        QComboBox::down-arrow { image: url("%s"); width: 11px; height: 11px; }
        QComboBox::down-arrow:pressed { top: 1px; }''' % arrow.replace("\\", "/")) if arrow else ""
    return """
        QComboBox { border: 1px solid #D0D0D0; border-radius: 4px; padding: 4px 8px;
            font-family: %s; font-size: %dpx; background: #FFFFFF; color: #333333; }
        QComboBox:hover { border-color: #A8A8A8; }
        QComboBox:focus { border-color: #1A73E8; }
        QComboBox:disabled { background: #F5F5F5; color: #A0A0A0; }%s
    """ % (family, size, drop)


class _ComboClickFilter(QObject):
    """让整个下拉框都能点开。Qt 默认只有右侧箭头那一条会展开弹层，文字区点了没反应，
    看起来就像"要点空白处才有效"。可编辑框例外：文字区要留给输入光标。"""

    def eventFilter(self, obj, event):
        if (not isinstance(obj, QComboBox) or event.type() != QEvent.MouseButtonPress
                or event.button() != Qt.LeftButton):
            return False
        if not obj.isEnabled() or obj.count() == 0 or obj.view().isVisible():
            return False
        if obj.isEditable() and not self._on_arrow(obj, event.pos()):
            return False
        obj.setFocus(Qt.MouseFocusReason)  # 吃掉按下事件后，点击获得焦点这一步要自己补上
        obj.showPopup()
        return True

    @staticmethod
    def _on_arrow(combo, pos):
        opt = QStyleOptionComboBox()
        combo.initStyleOption(opt)
        rect = combo.style().subControlRect(QStyle.CC_ComboBox, opt, QStyle.SC_ComboBoxArrow, combo)
        return rect.contains(pos)


class _SelectAllFilter(QObject):
    """macOS 上 Qt 把物理 Ctrl 映射成 MetaModifier，所以 Ctrl+A 默认不触发全选
    （系统约定的全选是 Cmd+A，对应 ControlModifier）。这里两头都认，Ctrl+A 直接用。"""

    def eventFilter(self, obj, event):
        if event.type() != QEvent.KeyPress or event.key() != Qt.Key_A:
            return False
        mods = event.modifiers()
        if not (mods & (Qt.ControlModifier | Qt.MetaModifier)):
            return False
        if mods & Qt.AltModifier:      # Ctrl+Alt+A 之类不抢
            return False
        select_all = getattr(obj, "selectAll", None)
        if not callable(select_all):
            return False
        select_all()
        return True


def _primary_btn():
    return """
        QPushButton { color: #FFFFFF; background: #1A73E8; border: none;
            border-radius: 4px; font-size: 12px; padding: 0 12px; }
        QPushButton:hover { background: #1557B0; }
    """


def _secondary_btn():
    return """
        QPushButton { color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0;
            border-radius: 4px; font-size: 12px; padding: 0 12px; }
        QPushButton:hover { background: #E0E0E0; }
    """


def _plain_style():
    return """
        QPlainTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
            font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; }
    """


def _output_style():
    return """
        QTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
            font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; background: #FAFAFA; }
    """


def _tab_style():
    return """
        QTabWidget::tab-bar { alignment: left; }
        QTabWidget::pane { background: #FFFFFF; border: 1px solid #D0D0D0; border-radius: 4px; }
        QTabBar::tab { background: #F0F0F0; color: #333333; border: 1px solid #D0D0D0;
            border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px;
            padding: 6px 14px; margin-right: 2px; font-size: 12px; }
        QTabBar::tab:selected { background: #FFFFFF; color: #1A73E8; }
    """


class FlowLayout(QLayout):
    """按可用宽度把固定尺寸的子控件自动换行。

    最小宽度只按单个控件计算，窗口变窄时按钮换行（卡片高度随之变高、可滚动），
    而不是像网格那样顶住内容宽度、把右边的按钮裁掉。
    """

    def __init__(self, parent=None, spacing=8):
        super().__init__(parent)
        self._items = []
        self._spacing = spacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations()

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            if item.widget() is not None and item.widget().isHidden():
                continue
            size = size.expandedTo(item.sizeHint())
        m = self.contentsMargins()
        return size + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _do_layout(self, rect, test_only):
        m = self.contentsMargins()
        area = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, line_height = area.x(), area.y(), 0
        for item in self._items:
            widget = item.widget()
            if item.isEmpty() or (widget is not None and widget.isHidden()):
                continue
            hint = item.sizeHint()
            if x + hint.width() > area.right() + 1 and line_height > 0:
                x = area.x()
                y += line_height + self._spacing
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + self._spacing
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y() + m.bottom()
