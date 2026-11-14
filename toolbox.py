import sys
import os
import platform
import subprocess
import traceback
import faulthandler
import re
import socket
import json
import ast
import base64
import urllib.parse
import hashlib
import xml.dom.minidom
import urllib.request
import time
import uuid
import io
import qrcode
import random
import datetime
import zoneinfo
import email.utils
import colorsys
import decimal
import shutil
import shlex
import csv
import difflib
import hmac
import secrets
import string
import threading
import ctypes
import tempfile
import zipfile
import posixpath
import ntpath
import stat
import plistlib
import yaml
from PIL import Image
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, utils as der_utils
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.asymmetric.ec import ECDSA
from cryptography.exceptions import InvalidSignature, InvalidTag
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QLabel, QPushButton, QFrame,
                              QScrollArea, QMessageBox, QLineEdit,
                              QGraphicsDropShadowEffect, QTextEdit, QSplitter,
                              QPlainTextEdit, QComboBox, QCheckBox, QStackedWidget,
                              QGridLayout, QSpinBox, QTabWidget, QColorDialog,
                              QFileDialog, QInputDialog, QListWidget, QListWidgetItem,
                              QProgressDialog, QSystemTrayIcon, QMenu, QAction,
                              QTreeWidget, QTreeWidgetItem, QHeaderView,
                              QStyledItemDelegate, QStyle, QGraphicsOpacityEffect,
                              QDialog, QFormLayout, QDialogButtonBox,
                              QDateEdit, QDateTimeEdit, QGroupBox, QTimeEdit,
                              QAbstractItemView, QKeySequenceEdit, QProgressBar, QSizePolicy,
                              QStyleOptionComboBox)
from PyQt5.QtCore import Qt, QPoint, QPointF, QRect, QRectF, QThread, QObject, pyqtSignal, QTimer, QUrl, QLockFile, QDate, QDateTime, QTime, QAbstractNativeEventFilter, QEvent, QSize, QStandardPaths
from PyQt5.QtGui import (QFont, QCursor, QTextCursor, QColor, QPen, QPixmap, QPainter, QIcon,
                         QImage, QLinearGradient, QBrush, QDesktopServices, QPalette, QKeySequence,
                         QPainterPath, QPolygonF)


APP_VERSION = "1.0.19"
UPDATE_CHECK_URL = "https://gitee.com/api/v5/repos/jimmy_hou/personal_tool/contents/version.json?ref=main"


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


def get_effective_ip():
    system = platform.system()
    try:
        if system == "Windows":
            output = subprocess.check_output("ipconfig", shell=True, text=True, encoding="gbk", errors="ignore")
            lines = output.splitlines()
            adapters = []
            current = {"name": "", "ip": "", "mac": ""}
            for line in lines:
                adapter_match = re.match(r"^(\S.+):", line)
                if adapter_match:
                    if current["ip"]:
                        adapters.append(current)
                    current = {"name": adapter_match.group(1), "ip": "", "mac": ""}
                ip_match = re.search(r"IPv4\s*[地址address]*[：:]\s*([\d.]+)", line, re.IGNORECASE)
                if ip_match:
                    current["ip"] = ip_match.group(1)
                mac_match = re.search(r"物理地址\s*[：:]\s*([\da-fA-F-]+)", line, re.IGNORECASE)
                if mac_match:
                    current["mac"] = mac_match.group(1).replace("-", ":")
            if current["ip"]:
                adapters.append(current)
            for a in adapters:
                ip = a["ip"]
                if not ip.startswith("127.") and ip:
                    name_lower = a["name"].lower()
                    if "virtual" not in name_lower and "vmware" not in name_lower and "vbox" not in name_lower:
                        return a["ip"], a["mac"], a["name"]
            if adapters:
                return adapters[0]["ip"], adapters[0]["mac"], adapters[0]["name"]
        else:
            output = subprocess.check_output(["ifconfig"], text=True, errors="ignore")
            adapters = []
            current = {"name": "", "ip": "", "mac": ""}
            for line in output.splitlines():
                adapter_match = re.match(r"^(\S+):", line)
                if adapter_match:
                    if current["ip"]:
                        adapters.append(current)
                    current = {"name": adapter_match.group(1), "ip": "", "mac": ""}
                elif line.startswith("\t"):
                    ip_match = re.search(r"inet\s+(?:addr:)?([\d.]+)", line)
                    if ip_match:
                        current["ip"] = ip_match.group(1)
                    mac_match = re.search(r"ether\s+([\da-fA-F:]{17})", line)
                    if mac_match:
                        current["mac"] = mac_match.group(1)
            if current["ip"]:
                adapters.append(current)
            for a in adapters:
                ip = a["ip"]
                if not ip.startswith("127.") and ip:
                    name_lower = a["name"].lower()
                    skip = ["lo", "awdl", "llw", "bridge", "vlan", "utun", "anpi"]
                    if not any(name_lower.startswith(s) for s in skip):
                        return a["ip"], a["mac"], a["name"]
            for a in adapters:
                if not a["ip"].startswith("127.") and a["ip"]:
                    return a["ip"], a["mac"], a["name"]
    except Exception:
        pass
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return ip, "-", "Default"
    except Exception:
        return "N/A", "N/A", "N/A"


_cpu_times_prev = None


def _read_windows_cpu_times():
    import ctypes
    from ctypes import wintypes

    class FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", wintypes.DWORD),
                    ("dwHighDateTime", wintypes.DWORD)]

    idle = FILETIME()
    kernel = FILETIME()
    user = FILETIME()
    if not ctypes.windll.kernel32.GetSystemTimes(
            ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
        return None

    def _to_int(ft):
        return (ft.dwHighDateTime << 32) | ft.dwLowDateTime

    return _to_int(idle), _to_int(kernel), _to_int(user)


def _windows_cpu_percent():
    """CPU usage via GetSystemTimes (no WMI performance counters)."""
    global _cpu_times_prev
    cur = _read_windows_cpu_times()
    if cur is None:
        return None
    prev = _cpu_times_prev
    if prev is None:
        # First sample only: take a short second sample so a value is returned.
        time.sleep(0.1)
        prev, cur = cur, _read_windows_cpu_times()
        if cur is None:
            return None
    _cpu_times_prev = cur
    idle_delta = cur[0] - prev[0]
    total_delta = (cur[1] - prev[1]) + (cur[2] - prev[2])
    if total_delta <= 0:
        return None
    busy = total_delta - idle_delta
    return max(0.0, min(100.0, busy / total_delta * 100.0))


def _windows_memory():
    """Memory usage via GlobalMemoryStatusEx."""
    import ctypes

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
        return None
    total_gb = stat.ullTotalPhys / (1024 ** 3)
    used_gb = (stat.ullTotalPhys - stat.ullAvailPhys) / (1024 ** 3)
    if total_gb <= 0:
        return None
    return used_gb / total_gb * 100.0, used_gb, total_gb


def get_system_stats():
    system = platform.system()
    try:
        if system == "Darwin":
            cpu_out = subprocess.check_output("ps -A -o %cpu", shell=True, text=True)
            cpu_pct = sum(float(l.strip()) for l in cpu_out.strip().splitlines()[1:])
            cores = os.cpu_count() or 1
            cpu_pct = min(cpu_pct / cores, 100.0)

            total_bytes = int(subprocess.check_output("sysctl -n hw.memsize", shell=True, text=True).strip())
            vm_out = subprocess.check_output("vm_stat", shell=True, text=True)
            ps_match = re.search(r'page size of (\d+) bytes', vm_out)
            page_size = int(ps_match.group(1)) if ps_match else 4096
            active = wired = compressed = 0
            for line in vm_out.splitlines():
                if 'Pages active' in line:
                    active = int(re.search(r'(\d+)', line.split(':')[1]).group(1))
                elif 'Pages wired down' in line:
                    wired = int(re.search(r'(\d+)', line.split(':')[1]).group(1))
                elif 'Pages occupied by compressor' in line:
                    compressed = int(re.search(r'(\d+)', line.split(':')[1]).group(1))
            used_bytes = (active + wired + compressed) * page_size
            used_gb = used_bytes / (1024 ** 3)
            total_gb = total_bytes / (1024 ** 3)
            mem_pct = (used_bytes / total_bytes * 100) if total_bytes > 0 else 0
            return cpu_pct, mem_pct, used_gb, total_gb
        elif system == "Windows":
            cpu_pct = _windows_cpu_percent()
            mem = _windows_memory()
            if mem is None:
                return None, None, None, None
            mem_pct, used_gb, total_gb = mem
            return cpu_pct, mem_pct, used_gb, total_gb
    except Exception:
        pass
    return None, None, None, None


def short_process_name(name):
    """macOS 的 ps comm 给的是完整路径，显示时只保留可执行文件名。"""
    name = (name or "").strip()
    if "/" in name:
        name = name.rsplit("/", 1)[-1]
    return name


def list_processes():
    """全量进程快照：名称 / PID / 内存KB / 窗口标题。命令固定，不拼接任何用户输入。"""
    rows = []
    try:
        if platform.system() == "Windows":
            script = ("[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;"
                      "Get-Process | Select-Object Name,Id,WorkingSet,MainWindowTitle"
                      "| ConvertTo-Csv -NoTypeInformation")
            raw = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                                 capture_output=True, timeout=25, **win_no_console()).stdout
            for rec in csv.DictReader(io.StringIO(raw.decode("utf-8", "ignore"))):
                try:
                    pid = int(rec.get("Id", ""))
                    mem = int(rec.get("WorkingSet", "0") or 0)
                except ValueError:
                    continue
                rows.append({"pid": pid,
                             "name": rec.get("Name") or "",
                             "mem_kb": mem // 1024,
                             "title": (rec.get("MainWindowTitle") or "").strip()})
        else:
            output = subprocess.check_output(["ps", "-axo", "pid=,rss=,comm="],
                                             text=True, errors="ignore")
            for line in output.splitlines():
                parts = line.split(None, 2)
                if len(parts) < 3:
                    continue
                try:
                    pid, mem = int(parts[0]), int(parts[1])
                except ValueError:
                    continue
                rows.append({"pid": pid, "name": short_process_name(parts[2]),
                             "mem_kb": mem, "title": ""})
    except Exception:
        pass
    return rows


def process_port_map():
    """PID -> 该进程持有的本地端口集合（按端口号排序）。"""
    owned = {}
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output("netstat -ano", shell=True, text=True,
                                             encoding="gbk", errors="ignore")
            for line in output.splitlines():
                parts = line.split()
                if (len(parts) >= 5 and parts[0].upper().startswith("TCP")) or \
                        (len(parts) >= 4 and parts[0].upper().startswith("UDP")):
                    local, pid = parts[1], parts[-1]
                    _split_endpoint(local, owned, pid)
        else:
            output = subprocess.check_output(["lsof", "-i", "-P", "-n"], text=True, errors="ignore")
            for line in output.splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 9:
                    _split_endpoint(parts[8], owned, parts[1])
    except Exception:
        pass
    return {pid: sorted(ports, key=int) for pid, ports in owned.items()}


def _split_endpoint(endpoint, owned, pid):
    try:
        port = int(endpoint.rsplit(":", 1)[-1])
        pid = int(pid)
    except ValueError:
        return
    owned.setdefault(pid, set()).add(port)


def human_mem(kb):
    mb = kb / 1024.0
    return "%.1f GB" % (mb / 1024.0) if mb >= 1024 else "%.1f MB" % mb


class ProcessListWorker(QThread):
    rows_ready = pyqtSignal(list, str)

    def run(self):
        rows = list_processes()
        port_map = process_port_map()
        for row in rows:
            ports = port_map.get(row["pid"], [])
            row["ports"] = ", ".join(str(p) for p in ports[:8])
            if len(ports) > 8:
                row["ports"] += " …"
        self.rows_ready.emit(rows, "共 %d 个进程" % len(rows))


def kill_process(pid):
    system = platform.system()
    try:
        if system == "Windows":
            subprocess.run(f"taskkill /PID {pid} /F", shell=True, capture_output=True)
        else:
            subprocess.run(["kill", "-9", str(pid)], capture_output=True)
        return True
    except Exception:
        return False


TOOL_WIN_W = 720
TOOL_WIN_H = 480


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


def app_icon():
    """Window/taskbar icon from assets/, resolved for both dev runs and PyInstaller bundles."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    for name in ("icon.ico", "icon.icns", "icon.png"):
        path = os.path.join(base, "assets", name)
        if os.path.exists(path):
            return QIcon(path)
    return QIcon()


HISTORY_LIMIT = 50
JSON_HISTORY_PATH = os.path.join(os.path.expanduser("~"), ".personal_toolbox", "json_history.json")
TOOL_USAGE_HISTORY_PATH = os.path.join(os.path.expanduser("~"), ".personal_toolbox", "tool_usage_history.json")
SEARCH_HISTORY_PATH = os.path.join(os.path.expanduser("~"), ".personal_toolbox", "search_history.json")
SECTION_ORDER_PATH = os.path.join(os.path.expanduser("~"), ".personal_toolbox", "section_order.json")
TOOL_ORDER_PATH = os.path.join(os.path.expanduser("~"), ".personal_toolbox", "tool_order.json")
SHORTCUTS_PATH = os.path.join(os.path.expanduser("~"), ".personal_toolbox", "shortcuts.json")


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


TOOL_RENAMES = {
    "屏幕取色": "取色器", "打卡提醒": "提醒事项", "时间戳": "日期时间",
    "文本对比": "文本工具", "文本统计": "文本工具",
    "二维码": "生成器", "条形码": "生成器", "UUID": "生成器", "随机数": "生成器",
    "Ping 测试": "网络诊断", "DNS 查询": "网络诊断", "路由追踪": "网络诊断",
    "端口扫描": "网络诊断", "网络测速": "网络诊断",
    "JSON/XML": "数据格式", "JSON-YAML": "数据格式", "格式转换": "数据格式",
    "进制转换": "数字转换", "罗马数字": "数字转换", "金额大写": "数字转换",
    "命令速查": "开发速查", "HTTP 状态码": "开发速查",
}
SECTION_RENAMES = {
    "系统工具": "系统与桌面", "加解密/编解码": "编码与安全", "文本处理": "文本与数据",
    "时间工具": "时间与日程", "数学工具": "数值计算", "开发工具": "开发辅助",
    "其他": "系统与桌面", "网络诊断": "系统与桌面",
}


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


class _ProcessItem(QTreeWidgetItem):
    """排序钩子要写在 item 上：Qt 只调用 QTreeWidgetItem 的比较函数，PyQt 里即 __lt__。"""

    def __init__(self, strings, pid, mem_kb):
        super().__init__(strings)
        self.pid = pid
        self.mem_kb = mem_kb

    def __lt__(self, other):
        col = self.treeWidget().sortColumn() if self.treeWidget() else -1
        if col == 1:
            return self.pid < other.pid
        if col == 2:
            return self.mem_kb < other.mem_kb
        return self.text(col).lower() < other.text(col).lower()


class ProcessManagerWindow(QMainWindow):
    """本机进程管理器：全量列表、按名称/PID/窗口标题即时过滤、端口过滤、结束进程。"""

    COLUMNS = ["名称", "PID", "内存", "端口", "窗口标题"]

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("进程管理")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.worker = None
        self.init_ui()
        self.refresh()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(QLabel("搜索:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("进程名 / PID / 窗口标题，可输入中文")
        self.search_input.setStyleSheet(_lineedit_style())
        self.search_input.textChanged.connect(self.refilter)
        row.addWidget(self.search_input, 1)

        row.addWidget(QLabel("端口:"))
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("如 8080")
        self.port_input.setFixedWidth(80)
        self.port_input.setStyleSheet(_lineedit_style())
        self.port_input.textChanged.connect(self.refilter)
        row.addWidget(self.port_input)

        refresh_btn = QPushButton("刷新")
        refresh_btn.setFixedSize(64, 28)
        refresh_btn.setCursor(QCursor(Qt.PointingHandCursor))
        refresh_btn.setStyleSheet(_secondary_btn())
        refresh_btn.clicked.connect(self.refresh)
        row.addWidget(refresh_btn)

        self.kill_btn = QPushButton("结束进程")
        self.kill_btn.setFixedSize(80, 28)
        self.kill_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.kill_btn.setStyleSheet("""
            QPushButton { color: #FFFFFF; background: #FF5F57; border: none;
                border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #E0443E; }
            QPushButton:pressed { background: #C73834; }
            QPushButton:disabled { background: #CCCCCC; }
        """)
        self.kill_btn.clicked.connect(self.kill_selected)
        row.addWidget(self.kill_btn)
        layout.addLayout(row)

        self.status_label = QLabel("正在枚举进程…")
        self.status_label.setFont(QFont("PingFang SC", 10))
        self.status_label.setStyleSheet("color: #999999;")
        layout.addWidget(self.status_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(self.COLUMNS)
        self.tree.setSortingEnabled(True)
        self.tree.sortByColumn(2, Qt.DescendingOrder)
        self.tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.tree.setUniformRowHeights(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(4, QHeaderView.Stretch)
        for col in (1, 2, 3):
            self.tree.header().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.tree.setStyleSheet("""
            QTreeWidget { border: 1px solid #D0D0D0; border-radius: 6px; background: #FFFFFF;
                alternate-background-color: #FAFAFA; font-size: 12px;
                font-family: "Menlo", "Consolas", monospace; }
            QTreeWidget::item { height: 24px; }
            QTreeWidget::item:selected { background: #E8F0FE; color: #1A73E8; }
            QHeaderView::section { background: #F0F0F0; border: none;
                border-bottom: 1px solid #D0D0D0; padding: 5px;
                font-family: "PingFang SC"; font-size: 12px; color: #333333; }
        """)
        layout.addWidget(self.tree)

    def refresh(self):
        if self.worker is not None and self.worker.isRunning():
            return
        self.status_label.setText("正在枚举进程…")
        self.kill_btn.setEnabled(False)
        self.worker = ProcessListWorker()
        self.worker.rows_ready.connect(self.on_rows)
        self.worker.start()

    def on_rows(self, rows, summary):
        self.tree.setSortingEnabled(False)
        self.tree.clear()
        for proc in rows:
            self.tree.addTopLevelItem(_ProcessItem(
                [proc["name"], str(proc["pid"]), human_mem(proc["mem_kb"]),
                 proc.get("ports", ""), proc["title"]], proc["pid"], proc["mem_kb"]))
        self.tree.setSortingEnabled(True)
        self.tree.sortByColumn(2, Qt.DescendingOrder)
        self.kill_btn.setEnabled(True)
        self.status_label.setText(summary)
        self.refilter()

    def refilter(self):
        keyword = self.search_input.text().strip().lower()
        port = self.port_input.text().strip()
        total = self.tree.topLevelItemCount()
        shown = 0
        for i in range(total):
            item = self.tree.topLevelItem(i)
            hit = (not keyword or keyword in item.text(0).lower()
                   or keyword in item.text(1) or keyword in item.text(4).lower())
            if hit and port:
                hit = port in item.text(3)
            item.setHidden(not hit)
            if hit:
                shown += 1
        if keyword or port:
            self.status_label.setText("共 %d 个进程，匹配 %d 个" % (total, shown))

    def kill_selected(self):
        items = [item for item in self.tree.selectedItems() if not item.isHidden()]
        if not items:
            self.status_label.setText("请先选中要结束的进程（可按住 Ctrl/Shift 多选）。")
            return
        preview = ["%s (PID %s)" % (item.text(0), item.text(1)) for item in items[:6]]
        if len(items) > 6:
            preview.append("…")
        answer = QMessageBox.question(
            self, "结束进程确认",
            "确定结束 %d 个进程？\n%s\n\n未保存的数据会丢失。" % (len(items), "\n".join(preview)),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        for item in items:
            kill_process(item.pid)
        self.status_label.setText("已结束 %d 个进程，正在刷新…" % len(items))
        self.refresh()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.worker.wait(3000)
        super().closeEvent(event)


class JsonFormatterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JSON 处理")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        tool_layout = QHBoxLayout()
        tool_layout.setSpacing(8)
        tools = [
            ("生成示例", self.gen_sample),
            ("压缩", self.do_minify),
            ("压缩并转义", self.do_minify_escape),
            ("转义", self.do_escape),
            ("去除转义", self.do_unescape),
            ("中文符号转英文", self.do_fix_punct),
            ("清空", self.do_clear),
        ]
        for text, handler in tools:
            b = QPushButton(text)
            b.setFixedHeight(28)
            b.setCursor(QCursor(Qt.PointingHandCursor))
            b.setStyleSheet("""
                QPushButton { color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0;
                    border-radius: 4px; font-size: 12px; padding: 0 10px; }
                QPushButton:hover { background: #E0E0E0; border-color: #1A73E8; color: #1A73E8; }
            """)
            b.clicked.connect(handler)
            tool_layout.addWidget(b)
        tool_layout.addStretch()
        layout.addLayout(tool_layout)

        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_header = QHBoxLayout()
        left_label = QLabel("输入 JSON")
        left_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        left_label.setStyleSheet("color: #333333;")
        left_header.addWidget(left_label)
        left_header.addStretch()

        format_btn = QPushButton("格式化")
        format_btn.setFixedSize(70, 28)
        format_btn.setCursor(QCursor(Qt.PointingHandCursor))
        format_btn.setStyleSheet("""
            QPushButton {
                color: #FFFFFF;
                background: #1A73E8;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover { background: #1557B0; }
        """)
        format_btn.clicked.connect(self.do_format)
        left_header.addWidget(format_btn)

        left_layout.addLayout(left_header)

        self.input_text = QPlainTextEdit()
        self.input_text.setStyleSheet("""
            QPlainTextEdit {
                border: 1px solid #D0D0D0;
                border-radius: 4px;
                padding: 8px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
                font-size: 13px;
            }
        """)
        left_layout.addWidget(self.input_text)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_header = QHBoxLayout()
        right_label = QLabel("格式化结果")
        right_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        right_label.setStyleSheet("color: #333333;")
        right_header.addWidget(right_label)
        right_header.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索关键字...")
        self.search_input.setFixedWidth(120)
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #D0D0D0;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QLineEdit:focus { border-color: #1A73E8; }
        """)
        self.search_input.returnPressed.connect(self.do_search)
        right_header.addWidget(self.search_input)

        search_btn = QPushButton("搜索")
        search_btn.setFixedSize(50, 28)
        search_btn.setCursor(QCursor(Qt.PointingHandCursor))
        search_btn.setStyleSheet("""
            QPushButton {
                color: #333333;
                background: #F0F0F0;
                border: 1px solid #D0D0D0;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover { background: #E0E0E0; }
        """)
        search_btn.clicked.connect(self.do_search)
        right_header.addWidget(search_btn)

        copy_btn = QPushButton("复制")
        copy_btn.setFixedSize(60, 28)
        copy_btn.setCursor(QCursor(Qt.PointingHandCursor))
        copy_btn.setStyleSheet("""
            QPushButton {
                color: #333333;
                background: #F0F0F0;
                border: 1px solid #D0D0D0;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover { background: #E0E0E0; }
        """)
        copy_btn.clicked.connect(self.do_copy)
        right_header.addWidget(copy_btn)

        right_layout.addLayout(right_header)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #D0D0D0;
                border-radius: 4px;
                padding: 8px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
                font-size: 13px;
                background: #FAFAFA;
            }
        """)
        right_layout.addWidget(self.output_text)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([450, 450])

        layout.addWidget(splitter)

        history_layout = QHBoxLayout()
        history_layout.setSpacing(8)
        history_label = QLabel("历史")
        history_label.setStyleSheet("color: #999999; font-size: 12px;")
        history_layout.addWidget(history_label)

        self.history_combo = QComboBox()
        self.history_combo.setStyleSheet(_combo_style())
        self.history_combo.activated.connect(self.load_history_entry)
        history_layout.addWidget(self.history_combo, 1)
        layout.addLayout(history_layout)

        self.refresh_history()

    def refresh_history(self):
        self._history = load_history(JSON_HISTORY_PATH)
        self.history_combo.blockSignals(True)
        self.history_combo.clear()
        for item in self._history:
            head = (item.get("input") or "").strip().splitlines()
            preview = head[0][:70] if head else ""
            self.history_combo.addItem("%s  %s" % (item.get("time", ""), preview))
        self.history_combo.blockSignals(False)

    def load_history_entry(self, index):
        if 0 <= index < len(self._history):
            self.input_text.setPlainText(self._history[index]["input"])

    def do_format(self):
        raw = self.input_text.toPlainText().strip()
        if not raw:
            self.output_text.setPlainText("")
            return
        try:
            parsed = json.loads(raw)
            formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
            self.output_text.setPlainText(formatted)
            append_history(JSON_HISTORY_PATH, {
                "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "input": raw,
            })
            self.refresh_history()
        except json.JSONDecodeError as e:
            self.output_text.setPlainText(f"JSON 格式错误:\n{e}")

    def gen_sample(self):
        sample = json.dumps({
            "name": "张三",
            "age": 28,
            "active": True,
            "tags": ["开发者", "Python"],
            "address": {"city": "北京", "zip": "100000"},
            "score": 95.5,
            "email": None
        }, indent=2, ensure_ascii=False)
        self.input_text.setPlainText(sample)
        self.do_format()

    def do_minify(self):
        raw = self.input_text.toPlainText().strip()
        if not raw:
            self.output_text.setPlainText("")
            return
        try:
            parsed = json.loads(raw)
            self.output_text.setPlainText(json.dumps(parsed, separators=(',', ':'), ensure_ascii=False))
        except json.JSONDecodeError as e:
            self.output_text.setPlainText(f"JSON 格式错误:\n{e}")

    def do_minify_escape(self):
        raw = self.input_text.toPlainText().strip()
        if not raw:
            self.output_text.setPlainText("")
            return
        try:
            parsed = json.loads(raw)
            minified = json.dumps(parsed, separators=(',', ':'), ensure_ascii=False)
            self.output_text.setPlainText(json.dumps(minified, ensure_ascii=False)[1:-1])
        except json.JSONDecodeError as e:
            self.output_text.setPlainText(f"JSON 格式错误:\n{e}")

    def do_escape(self):
        raw = self.input_text.toPlainText()
        if not raw:
            self.output_text.setPlainText("")
            return
        self.output_text.setPlainText(json.dumps(raw, ensure_ascii=False)[1:-1])

    def do_unescape(self):
        raw = self.input_text.toPlainText().strip()
        if not raw:
            self.output_text.setPlainText("")
            return
        if '\\' not in raw:
            self.output_text.setPlainText(raw)
            return
        try:
            self.output_text.setPlainText(json.loads('"' + raw + '"'))
        except json.JSONDecodeError:
            result = raw.replace('\\\\', '\x00').replace('\\"', '"') \
                        .replace('\\n', '\n').replace('\\t', '\t') \
                        .replace('\\r', '\r').replace('\\/', '/') \
                        .replace('\x00', '\\')
            self.output_text.setPlainText(result)

    def do_fix_punct(self):
        mapping = {
            '｛': '{', '｝': '}', '［': '[', '］': ']',
            '，': ',', '：': ':', '；': ';',
            '“': '"', '”': '"', '‘': "'", '’': "'",
            '（': '(', '）': ')', '　': ' ',
        }
        text = self.input_text.toPlainText()
        for cn, en in mapping.items():
            text = text.replace(cn, en)
        self.input_text.setPlainText(text)
        self.do_format()

    def do_clear(self):
        self.input_text.setPlainText("")
        self.output_text.setPlainText("")

    def do_search(self):
        keyword = self.search_input.text().strip()
        if not keyword:
            return
        text = self.output_text.toPlainText()
        if not text:
            return
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.Start)
        self.output_text.setTextCursor(cursor)
        found = self.output_text.find(keyword)
        if not found:
            QMessageBox.information(self, "搜索结果", "未找到匹配内容", QMessageBox.Ok)

    def do_copy(self):
        text = self.output_text.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            QMessageBox.information(self, "已复制", "已复制到剪贴板", QMessageBox.Ok)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class XmlFormatterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("XML 格式化")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_header = QHBoxLayout()
        left_label = QLabel("输入 XML")
        left_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        left_label.setStyleSheet("color: #333333;")
        left_header.addWidget(left_label)
        left_header.addStretch()

        format_btn = QPushButton("格式化")
        format_btn.setFixedSize(70, 28)
        format_btn.setCursor(QCursor(Qt.PointingHandCursor))
        format_btn.setStyleSheet("""
            QPushButton { color: #FFFFFF; background: #1A73E8; border: none; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #1557B0; }
        """)
        format_btn.clicked.connect(self.do_format)
        left_header.addWidget(format_btn)
        left_layout.addLayout(left_header)

        self.input_text = QPlainTextEdit()
        self.input_text.setStyleSheet("""
            QPlainTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; }
        """)
        left_layout.addWidget(self.input_text)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_header = QHBoxLayout()
        right_label = QLabel("格式化结果")
        right_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        right_label.setStyleSheet("color: #333333;")
        right_header.addWidget(right_label)
        right_header.addStretch()

        copy_btn = QPushButton("复制")
        copy_btn.setFixedSize(60, 28)
        copy_btn.setCursor(QCursor(Qt.PointingHandCursor))
        copy_btn.setStyleSheet("""
            QPushButton { color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #E0E0E0; }
        """)
        copy_btn.clicked.connect(self.do_copy)
        right_header.addWidget(copy_btn)
        right_layout.addLayout(right_header)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("""
            QTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; background: #FAFAFA; }
        """)
        right_layout.addWidget(self.output_text)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([450, 450])
        layout.addWidget(splitter)

    def do_format(self):
        raw = self.input_text.toPlainText().strip()
        if not raw:
            self.output_text.setPlainText("")
            return
        try:
            dom = xml.dom.minidom.parseString(raw)
            formatted = dom.toprettyxml(indent="  ")
            lines = [line for line in formatted.split('\n') if line.strip()]
            self.output_text.setPlainText('\n'.join(lines))
        except Exception as e:
            self.output_text.setPlainText(f"XML 格式错误:\n{e}")

    def do_copy(self):
        text = self.output_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            QMessageBox.information(self, "已复制", "已复制到剪贴板", QMessageBox.Ok)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class Base64Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Base64 编解码")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_header = QHBoxLayout()
        left_label = QLabel("输入内容")
        left_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        left_label.setStyleSheet("color: #333333;")
        left_header.addWidget(left_label)
        left_header.addStretch()

        encode_btn = QPushButton("编码")
        encode_btn.setFixedSize(60, 28)
        encode_btn.setCursor(QCursor(Qt.PointingHandCursor))
        encode_btn.setStyleSheet("""
            QPushButton { color: #FFFFFF; background: #1A73E8; border: none; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #1557B0; }
        """)
        encode_btn.clicked.connect(self.do_encode)
        left_header.addWidget(encode_btn)

        decode_btn = QPushButton("解码")
        decode_btn.setFixedSize(60, 28)
        decode_btn.setCursor(QCursor(Qt.PointingHandCursor))
        decode_btn.setStyleSheet("""
            QPushButton { color: #FFFFFF; background: #34A853; border: none; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #2D8E47; }
        """)
        decode_btn.clicked.connect(self.do_decode)
        left_header.addWidget(decode_btn)
        left_layout.addLayout(left_header)

        self.input_text = QPlainTextEdit()
        self.input_text.setStyleSheet("""
            QPlainTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; }
        """)
        left_layout.addWidget(self.input_text)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_header = QHBoxLayout()
        right_label = QLabel("结果")
        right_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        right_label.setStyleSheet("color: #333333;")
        right_header.addWidget(right_label)
        right_header.addStretch()

        swap_btn = QPushButton("交换")
        swap_btn.setFixedSize(60, 28)
        swap_btn.setCursor(QCursor(Qt.PointingHandCursor))
        swap_btn.setStyleSheet("""
            QPushButton { color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #E0E0E0; }
        """)
        swap_btn.clicked.connect(self.do_swap)
        right_header.addWidget(swap_btn)

        copy_btn = QPushButton("复制")
        copy_btn.setFixedSize(60, 28)
        copy_btn.setCursor(QCursor(Qt.PointingHandCursor))
        copy_btn.setStyleSheet("""
            QPushButton { color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #E0E0E0; }
        """)
        copy_btn.clicked.connect(self.do_copy)
        right_header.addWidget(copy_btn)
        right_layout.addLayout(right_header)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("""
            QTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; background: #FAFAFA; }
        """)
        right_layout.addWidget(self.output_text)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([450, 450])
        layout.addWidget(splitter)

    def do_encode(self):
        raw = self.input_text.toPlainText()
        if not raw:
            self.output_text.setPlainText("")
            return
        try:
            encoded = base64.b64encode(raw.encode('utf-8')).decode('utf-8')
            self.output_text.setPlainText(encoded)
        except Exception as e:
            self.output_text.setPlainText(f"编码错误:\n{e}")

    def do_decode(self):
        raw = self.input_text.toPlainText().strip()
        if not raw:
            self.output_text.setPlainText("")
            return
        try:
            decoded = base64.b64decode(raw).decode('utf-8')
            self.output_text.setPlainText(decoded)
        except Exception as e:
            self.output_text.setPlainText(f"解码错误:\n{e}")

    def do_copy(self):
        text = self.output_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            QMessageBox.information(self, "已复制", "已复制到剪贴板", QMessageBox.Ok)

    def do_swap(self):
        input_text = self.input_text.toPlainText()
        output_text = self.output_text.toPlainText()
        self.input_text.setPlainText(output_text)
        self.output_text.setPlainText(input_text)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class UnicodeEscapeWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Unicode 转义")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_header = QHBoxLayout()
        left_label = QLabel("输入内容")
        left_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        left_label.setStyleSheet("color: #333333;")
        left_header.addWidget(left_label)
        left_header.addStretch()

        encode_btn = QPushButton("转义")
        encode_btn.setFixedSize(60, 28)
        encode_btn.setCursor(QCursor(Qt.PointingHandCursor))
        encode_btn.setStyleSheet("""
            QPushButton { color: #FFFFFF; background: #1A73E8; border: none; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #1557B0; }
        """)
        encode_btn.clicked.connect(self.do_encode)
        left_header.addWidget(encode_btn)

        decode_btn = QPushButton("还原")
        decode_btn.setFixedSize(60, 28)
        decode_btn.setCursor(QCursor(Qt.PointingHandCursor))
        decode_btn.setStyleSheet("""
            QPushButton { color: #FFFFFF; background: #34A853; border: none; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #2D8E47; }
        """)
        decode_btn.clicked.connect(self.do_decode)
        left_header.addWidget(decode_btn)
        left_layout.addLayout(left_header)

        self.input_text = QPlainTextEdit()
        self.input_text.setStyleSheet("""
            QPlainTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; }
        """)
        left_layout.addWidget(self.input_text)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_header = QHBoxLayout()
        right_label = QLabel("结果")
        right_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        right_label.setStyleSheet("color: #333333;")
        right_header.addWidget(right_label)
        right_header.addStretch()

        swap_btn = QPushButton("交换")
        swap_btn.setFixedSize(60, 28)
        swap_btn.setCursor(QCursor(Qt.PointingHandCursor))
        swap_btn.setStyleSheet("""
            QPushButton { color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #E0E0E0; }
        """)
        swap_btn.clicked.connect(self.do_swap)
        right_header.addWidget(swap_btn)

        copy_btn = QPushButton("复制")
        copy_btn.setFixedSize(60, 28)
        copy_btn.setCursor(QCursor(Qt.PointingHandCursor))
        copy_btn.setStyleSheet("""
            QPushButton { color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #E0E0E0; }
        """)
        copy_btn.clicked.connect(self.do_copy)
        right_header.addWidget(copy_btn)
        right_layout.addLayout(right_header)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("""
            QTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; background: #FAFAFA; }
        """)
        right_layout.addWidget(self.output_text)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([450, 450])
        layout.addWidget(splitter)

    def do_encode(self):
        raw = self.input_text.toPlainText()
        out = []
        for ch in raw:
            o = ord(ch)
            if ch == "\\":
                out.append("\\\\")
            elif o < 128:
                out.append(ch)
            elif o <= 0xFFFF:
                out.append("\\u%04x" % o)
            else:
                out.append("\\U%08x" % o)
        self.output_text.setPlainText("".join(out))

    def do_decode(self):
        raw = self.input_text.toPlainText()
        s = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), raw)
        s = re.sub(r"\\U([0-9a-fA-F]{8})", lambda m: chr(int(m.group(1), 16)), s)
        s = s.replace("\\\\", "\\")
        self.output_text.setPlainText(s)

    def do_copy(self):
        text = self.output_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            QMessageBox.information(self, "已复制", "已复制到剪贴板", QMessageBox.Ok)

    def do_swap(self):
        input_text = self.input_text.toPlainText()
        output_text = self.output_text.toPlainText()
        self.input_text.setPlainText(output_text)
        self.output_text.setPlainText(input_text)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class TabbedToolWindow(QMainWindow):
    """One entry point hosting several single-purpose tool windows as tabs."""

    def __init__(self, title, tools):
        super().__init__()
        self.setWindowTitle(title)
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        tabs = QTabWidget()
        tabs.setStyleSheet(_tab_style())
        # Each tab is a central widget lifted out of its own window class; those
        # owner objects hold the slots the tab's buttons are connected to.
        self._owners = []
        for cls, label in tools:
            win = cls()
            self._owners.append(win)
            tabs.addTab(win.takeCentralWidget(), label)
        self.setCentralWidget(tabs)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class CodecWindow(TabbedToolWindow):
    def __init__(self):
        super().__init__("编解码", (
            (Base64Window, "Base64"),
            (UrlEncodeWindow, "URL"),
            (UnicodeEscapeWindow, "Unicode 转义"),
        ))


class DataFormatWindow(TabbedToolWindow):
    def __init__(self):
        super().__init__("数据格式", (
            (JsonFormatterWindow, "JSON"),
            (XmlFormatterWindow, "XML"),
            (JsonYamlWindow, "JSON ↔ YAML"),
        ))


class GeneratorWindow(TabbedToolWindow):
    def __init__(self):
        super().__init__("生成器", (
            (QrCodeWindow, "二维码"),
            (BarcodeWindow, "条形码"),
            (UuidWindow, "UUID"),
            (RandomWindow, "随机数"),
        ))


class NumberConvertWindow(TabbedToolWindow):
    def __init__(self):
        super().__init__("数字转换", (
            (BaseConvertWindow, "进制"),
            (RomanNumeralWindow, "罗马数字"),
            (RmbUppercaseWindow, "金额大写"),
        ))


class NetworkDiagnosticsWindow(TabbedToolWindow):
    def __init__(self):
        super().__init__("网络诊断", (
            (PingWindow, "Ping"),
            (TracerouteWindow, "路由追踪"),
            (DNSWindow, "DNS"),
            (PortScanWindow, "端口扫描"),
            (SpeedTestWindow, "测速"),
        ))
        ping, trace, dns, ports, _speed = self._owners
        self._target_inputs = [ping.target_input, trace.target_input, dns.domain_input, ports.target_input]
        for edit in self._target_inputs:
            edit.setToolTip("目标地址在 Ping、路由追踪、DNS、端口扫描间同步")
            edit.textEdited.connect(self._sync_target)

    def _sync_target(self, text):
        for edit in self._target_inputs:
            if edit.text() != text:
                edit.setText(text)

    def closeEvent(self, event):
        self._owners[-1].close()
        super().closeEvent(event)


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


class _DiffCellDelegate(QStyledItemDelegate):
    """「修改」行的正文自己画：只有真正改动的字符带上红底红字。"""

    TEXT_COLUMNS = (1, 3)

    def paint(self, painter, option, index):
        segments = index.data(Qt.UserRole)
        if (index.column() not in self.TEXT_COLUMNS or not segments
                or option.state & QStyle.State_Selected):
            super().paint(painter, option, index)
            return
        text = index.data(Qt.DisplayRole) or ""
        rect = option.rect
        painter.save()
        painter.setClipRect(rect)
        painter.fillRect(rect, QColor("#FFFFFF"))
        metrics = option.fontMetrics
        painter.setFont(option.font)
        baseline = float(rect.center().y()) + metrics.ascent() - metrics.height() / 2.0
        x = float(rect.left()) + 4
        for piece, changed in _text_pieces(text, segments):
            if not piece:
                continue
            width = metrics.horizontalAdvance(piece)
            if changed:
                painter.fillRect(QRectF(x, float(rect.top()), float(width), float(rect.height())),
                                 QColor(DIFF_DELTA_BG))
                painter.setPen(QPen(QColor(DIFF_DELTA_FG)))
            else:
                painter.setPen(QPen(QColor("#202124")))
            painter.drawText(QPointF(x, baseline), piece)
            x += width
        painter.restore()


class DiffWindow(QMainWindow):
    """左右两段文本的对比：改了哪几行、加了几行、删了几行，一眼看清。"""

    COLUMNS = ("原文行", "原文", "对比行", "对比后")

    def __init__(self):
        super().__init__()
        self.setWindowTitle("文本对比")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.run_diff)
        self._hunks = []
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        options = QHBoxLayout()
        options.setSpacing(10)
        run_btn = QPushButton("对比")
        run_btn.setFixedSize(56, 28)
        run_btn.setCursor(QCursor(Qt.PointingHandCursor))
        run_btn.setStyleSheet(_primary_btn())
        run_btn.clicked.connect(lambda _c: self.run_diff(True))
        options.addWidget(run_btn)
        self.space_check = QCheckBox("忽略空白")
        self.space_check.setStyleSheet("QCheckBox { font-family: 'PingFang SC'; font-size: 12px; }")
        self.space_check.toggled.connect(lambda _c: self.run_diff())
        options.addWidget(self.space_check)
        self.case_check = QCheckBox("忽略大小写")
        self.case_check.setStyleSheet("QCheckBox { font-family: 'PingFang SC'; font-size: 12px; }")
        self.case_check.toggled.connect(lambda _c: self.run_diff())
        options.addWidget(self.case_check)
        self.only_check = QCheckBox("只看差异")
        self.only_check.setStyleSheet("QCheckBox { font-family: 'PingFang SC'; font-size: 12px; }")
        self.only_check.toggled.connect(lambda _c: self.run_diff())
        options.addWidget(self.only_check)
        options.addStretch()

        for text, tip, step in (("↑", "上一处差异", -1), ("↓", "下一处差异", 1)):
            nav_btn = QPushButton(text)
            nav_btn.setFixedSize(30, 28)
            nav_btn.setToolTip(tip)
            nav_btn.setCursor(QCursor(Qt.PointingHandCursor))
            nav_btn.setStyleSheet(_secondary_btn())
            nav_btn.clicked.connect(lambda _c=False, s=step: self.jump_hunk(s))
            options.addWidget(nav_btn)

        swap_btn = QPushButton("交换左右")
        swap_btn.setFixedSize(74, 28)
        swap_btn.setCursor(QCursor(Qt.PointingHandCursor))
        swap_btn.setStyleSheet(_secondary_btn())
        swap_btn.clicked.connect(self.swap_sides)
        options.addWidget(swap_btn)

        copy_btn = QPushButton("复制 diff")
        copy_btn.setFixedSize(74, 28)
        copy_btn.setCursor(QCursor(Qt.PointingHandCursor))
        copy_btn.setStyleSheet(_secondary_btn())
        copy_btn.clicked.connect(self.copy_unified)
        options.addWidget(copy_btn)

        clear_btn = QPushButton("清空")
        clear_btn.setFixedSize(56, 28)
        clear_btn.setCursor(QCursor(Qt.PointingHandCursor))
        clear_btn.setStyleSheet(_secondary_btn())
        clear_btn.clicked.connect(self.do_clear)
        options.addWidget(clear_btn)
        layout.addLayout(options)

        body = QSplitter(Qt.Vertical)
        panes = QWidget()
        pane_layout = QHBoxLayout(panes)
        pane_layout.setContentsMargins(0, 0, 0, 0)
        pane_layout.setSpacing(10)
        self.left_edit, left_pane = self._build_pane("原文", "onlDiffL")
        self.right_edit, right_pane = self._build_pane("对比后", "onlDiffR")
        pane_layout.addWidget(left_pane, 1)
        pane_layout.addWidget(right_pane, 1)
        body.addWidget(panes)

        self.result_tree = QTreeWidget()
        self.result_tree.setColumnCount(len(self.COLUMNS))
        self.result_tree.setHeaderLabels(self.COLUMNS)
        self.result_tree.setRootIsDecorated(False)
        self.result_tree.setAlternatingRowColors(False)
        self.result_tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.result_tree.setItemDelegate(_DiffCellDelegate(self.result_tree))
        self.result_tree.setStyleSheet("""
            QTreeWidget { border: 1px solid #D0D0D0; border-radius: 6px; background: #FFFFFF;
                font-family: "Menlo", "Consolas", monospace; font-size: 12px; }
            QTreeWidget::item { padding: 2px 4px; }
            QHeaderView::section { background: #F5F5F5; border: none; padding: 4px;
                font-family: "PingFang SC"; font-size: 11px; color: #666666; }
        """)
        header = self.result_tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        body.addWidget(self.result_tree)
        body.setStretchFactor(0, 2)
        body.setStretchFactor(1, 3)
        layout.addWidget(body, 1)

        self.status_label = QLabel("粘贴两段文本即可自动对比；也可以点「打开」直接读文件。")
        self.status_label.setFont(QFont("PingFang SC", 11))
        self.status_label.setStyleSheet("color: #999999;")
        layout.addWidget(self.status_label)

    def _build_pane(self, title, object_name):
        container = QWidget()
        box = QVBoxLayout(container)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(6)

        row = QHBoxLayout()
        label = QLabel(title)
        label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        label.setStyleSheet("color: #333333;")
        row.addWidget(label)
        row.addStretch()
        open_btn = QPushButton("打开")
        open_btn.setFixedSize(52, 24)
        open_btn.setCursor(QCursor(Qt.PointingHandCursor))
        open_btn.setStyleSheet(_secondary_btn())
        row.addWidget(open_btn)
        box.addLayout(row)

        edit = QPlainTextEdit()
        edit.setObjectName(object_name)
        edit.setStyleSheet(_plain_style())
        edit.setPlaceholderText("在此粘贴 %s ..." % title)
        edit.textChanged.connect(self.schedule_diff)
        box.addWidget(edit, 1)
        open_btn.clicked.connect(lambda _c, e=edit: self.load_into(e))
        return edit, container

    def load_into(self, edit):
        path, _selected = QFileDialog.getOpenFileName(self, "选择文本文件", os.path.expanduser("~"),
                                                    "文本文件 (*.txt *.md *.json *.yaml *.py *.log);;所有文件 (*)")
        if not path:
            return
        try:
            edit.setPlainText(load_text_file(path))
        except OSError as e:
            self.status_label.setText("读取失败：%s" % e)
            return
        self.status_label.setText("已读入 %s" % path)

    def schedule_diff(self):
        self._timer.start(350)

    def swap_sides(self):
        left, right = self.left_edit.toPlainText(), self.right_edit.toPlainText()
        self.left_edit.setPlainText(right)
        self.right_edit.setPlainText(left)

    def do_clear(self):
        self.left_edit.clear()
        self.right_edit.clear()
        self.result_tree.clear()
        self.status_label.setText("已清空。")

    def run_diff(self, force=False):
        self._timer.stop()
        left = self.left_edit.toPlainText()
        right = self.right_edit.toPlainText()
        if not left and not right:
            self.result_tree.clear()
            self.status_label.setText("两段文本都是空的。")
            return
        l_count, r_count = len(left.splitlines()), len(right.splitlines())
        if max(l_count, r_count) > DIFF_AUTO_LIMIT and not force:
            self.result_tree.clear()
            self.status_label.setText("文本较大（%d / %d 行），点「对比」强制执行。" % (l_count, r_count))
            return
        rows = diff_rows(left, right, self.space_check.isChecked(), self.case_check.isChecked())
        counts = {kind: 0 for kind in DIFF_LABELS}
        for row in rows:
            counts[row[0]] += 1
        starts = {i for i, row in enumerate(rows)
                  if row[0] != "equal" and (i == 0 or rows[i - 1][0] == "equal")}
        if self.only_check.isChecked():
            shown = [(i, row) for i, row in enumerate(rows) if row[0] != "equal"]
        else:
            shown = list(enumerate(rows))
        self.result_tree.clear()
        self._hunks = []
        limit = min(len(shown), DIFF_ROW_LIMIT)
        for index, (kind, l_no, l_text, r_no, r_text) in shown[:limit]:
            if index in starts:
                self._hunks.append(self.result_tree.topLevelItemCount())
            item = QTreeWidgetItem(["" if l_no is None else str(l_no), l_text,
                                   "" if r_no is None else str(r_no), r_text])
            color = DIFF_COLORS.get(kind)
            if color:
                for column in range(len(self.COLUMNS)):
                    item.setBackground(column, QColor(color))
                    item.setToolTip(column, DIFF_LABELS[kind])
            if kind == "replace":
                l_segs, r_segs = diff_segments(l_text, r_text)
                for column, segs in ((1, l_segs), (3, r_segs)):
                    item.setData(column, Qt.UserRole, segs)
                    item.setBackground(column, QColor("#FFFFFF"))
            self.result_tree.addTopLevelItem(item)
        if not any(counts[kind] for kind in ("insert", "delete", "replace")):
            self.status_label.setText("两段文本一致（%d 行%s）。"
                                      % (counts["equal"], "，忽略空白/大小写"
                                         if (self.space_check.isChecked() or self.case_check.isChecked()) else ""))
            self.status_label.setStyleSheet("color: #188038; font-family: 'PingFang SC'; font-size: 11px;")
            return
        self.status_label.setStyleSheet("color: #999999; font-family: 'PingFang SC'; font-size: 11px;")
        text = ("差异 %d 处：修改 %d · 新增 %d · 删除 %d · 相同 %d 行 · ↑↓ 跳转"
                % (len(self._hunks), counts["replace"], counts["insert"], counts["delete"], counts["equal"]))
        if len(shown) > limit:
            text += "（仅显示前 %d 行）" % limit
        if self.only_check.isChecked():
            text += " · 已过滤相同行"
        self.status_label.setText(text)

    def jump_hunk(self, step):
        count = self.result_tree.topLevelItemCount()
        hunks = [h for h in self._hunks if h < count]
        if not hunks:
            return
        current = self.result_tree.currentItem()
        pos = self.result_tree.indexOfTopLevelItem(current) if current else (-1 if step > 0 else count)
        later = [h for h in hunks if h > pos] if step > 0 else [h for h in hunks if h < pos]
        target = (later[0] if step > 0 else later[-1]) if later else (hunks[0] if step > 0 else hunks[-1])
        item = self.result_tree.topLevelItem(target)
        self.result_tree.setCurrentItem(item)
        self.result_tree.scrollToItem(item, QAbstractItemView.PositionAtCenter)
        self.result_tree.setFocus()

    def copy_unified(self):
        left = self.left_edit.toPlainText().splitlines()
        right = self.right_edit.toPlainText().splitlines()
        diff = list(difflib.unified_diff(left, right, "原文", "对比后", lineterm="", n=3))
        if not diff:
            self.status_label.setText("两段文本没有差异。")
            return
        QApplication.clipboard().setText("\n".join(diff))
        self.status_label.setText("已复制标准 diff（%d 行）。" % len(diff))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


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


class TextProcessWindow(QMainWindow):
    """文本处理：行操作 / 转换 / 合并拆分（作用于选区或全文，可撤销）+ 实时统计。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("文本处理")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self._stat_timer = QTimer(self)
        self._stat_timer.setSingleShot(True)
        self._stat_timer.timeout.connect(self.refresh_stats)
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(8)

        menu_style = """
            QMenu { background: #FFFFFF; border: 1px solid #D0D0D0; padding: 4px; font-size: 12px; }
            QMenu::item { padding: 5px 22px 5px 14px; }
            QMenu::item:selected { background: #E8F0FE; color: #1A73E8; }
            QMenu::separator { height: 1px; background: #E8EAED; margin: 4px 6px; }
        """
        bar = QHBoxLayout()
        bar.setSpacing(6)
        for name, ops in TEXT_OPS.items():
            btn = QPushButton(name + " ▾")
            btn.setFixedHeight(28)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setStyleSheet(_primary_btn() + "QPushButton::menu-indicator { width: 0; }")
            menu = QMenu(btn)
            menu.setStyleSheet(menu_style)
            for op in ops:
                if op is None:
                    menu.addSeparator()
                    continue
                label, fn = op
                menu.addAction(label).triggered.connect(lambda _c=False, l=label, f=fn: self.apply_op(l, f))
            btn.setMenu(menu)
            bar.addWidget(btn)
        bar.addStretch()
        self.wrap_check = QCheckBox("自动换行")
        self.wrap_check.setStyleSheet("QCheckBox { font-size: 12px; }")
        self.wrap_check.toggled.connect(lambda on: self.editor.setLineWrapMode(
            QPlainTextEdit.WidgetWidth if on else QPlainTextEdit.NoWrap))
        bar.addWidget(self.wrap_check)
        for text, slot in (("打开", self.open_file), ("复制", self.copy_all), ("清空", self.do_clear)):
            btn = QPushButton(text)
            btn.setFixedHeight(28)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setStyleSheet(_secondary_btn())
            btn.clicked.connect(slot)
            bar.addWidget(btn)
            if text == "复制":
                self.copy_btn = btn
        layout.addLayout(bar)

        params = QHBoxLayout()
        params.setSpacing(6)
        self.param_edits = {}
        for key, label, default, width in (("sep", "分隔符", ",", 60), ("prefix", "前缀", "", 90),
                                           ("suffix", "后缀", "", 90)):
            tip = QLabel(label)
            tip.setStyleSheet("color: #5F6368; font-size: 12px;")
            params.addWidget(tip)
            edit = QLineEdit(default)
            edit.setFixedWidth(width)
            edit.setStyleSheet(_lineedit_style())
            edit.setToolTip("支持 \\n 换行、\\t 制表符")
            params.addWidget(edit)
            self.param_edits[key] = edit
        params.addStretch()
        hint = QLabel("有选区时只处理选中部分 · Ctrl+Z 撤销")
        hint.setStyleSheet("color: #9AA0A6; font-size: 11px;")
        params.addWidget(hint)
        layout.addLayout(params)

        body = QSplitter(Qt.Horizontal)
        self.editor = QPlainTextEdit()
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.editor.setFont(QFont("Consolas", 10) if platform.system() == "Windows" else QFont("Menlo", 12))
        self.editor.setStyleSheet("QPlainTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 6px; }")
        self.editor.setPlaceholderText("粘贴或输入文本，用上方菜单排序、去重、转换命名风格、生成 SQL IN 列表等")
        self.editor.textChanged.connect(lambda: self._stat_timer.start(150))
        self.editor.cursorPositionChanged.connect(self.refresh_cursor)
        self.editor.selectionChanged.connect(lambda: self._stat_timer.start(150))
        body.addWidget(self.editor)

        panel = QWidget()
        panel.setObjectName("textStatPanel")
        panel.setStyleSheet("#textStatPanel { background: #F8F9FA; border: 1px solid #E3E6EA; border-radius: 4px; }")
        grid = QGridLayout(panel)
        grid.setContentsMargins(10, 8, 10, 8)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(3)
        self.stat_scope = QLabel("全文")
        self.stat_scope.setStyleSheet("color: #1A73E8; font-size: 12px; font-weight: bold; background: transparent;")
        grid.addWidget(self.stat_scope, 0, 0, 1, 2)
        self.stat_values = []
        for r, (name, _) in enumerate(text_stats(""), 1):
            key = QLabel(name)
            key.setStyleSheet("color: #5F6368; font-size: 12px; background: transparent;")
            value = QLabel("0")
            value.setStyleSheet("color: #202124; font-size: 12px; font-weight: bold; background: transparent;")
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)
            grid.addWidget(key, r, 0)
            grid.addWidget(value, r, 1)
            self.stat_values.append(value)
        grid.setRowStretch(len(self.stat_values) + 1, 1)
        panel.setMinimumWidth(200)
        body.addWidget(panel)
        body.setStretchFactor(0, 1)
        body.setSizes([480, 210])
        layout.addWidget(body, 1)

        status = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #5F6368; font-size: 11px;")
        status.addWidget(self.status_label, 1)
        self.cursor_label = QLabel("")
        self.cursor_label.setStyleSheet("color: #9AA0A6; font-size: 11px;")
        status.addWidget(self.cursor_label)
        layout.addLayout(status)
        self.refresh_stats()
        self.refresh_cursor()

    def _params(self):
        return {k: _text_escape_param(e.text()) for k, e in self.param_edits.items()}

    def _target(self):
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            return cursor, cursor.selectedText().replace("\u2029", "\n"), True
        cursor.select(QTextCursor.Document)
        return cursor, self.editor.toPlainText(), False

    def apply_op(self, label, fn):
        self.editor.setFocus()
        cursor, text, partial = self._target()
        if not text:
            self.status_label.setText("没有可处理的文本。")
            return
        try:
            result = fn(text, self._params())
        except (ValueError, TypeError, SyntaxError) as e:
            self.status_label.setText(f"{label}失败：{e}")
            return
        if result == text:
            self.status_label.setText(f"{label}：内容没有变化。")
            return
        start = cursor.selectionStart()
        cursor.beginEditBlock()
        cursor.insertText(result)
        cursor.endEditBlock()
        if partial:
            cursor.setPosition(start)
            cursor.setPosition(start + len(result), QTextCursor.KeepAnchor)
            self.editor.setTextCursor(cursor)
        before, after = text.count("\n") + 1, result.count("\n") + 1
        delta = f"，{before} → {after} 行" if before != after else ""
        scope = "选区" if partial else "全文"
        self.status_label.setText(f"已对{scope}执行「{label}」{delta}（Ctrl+Z 撤销）")

    def refresh_stats(self):
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            text = cursor.selectedText().replace("\u2029", "\n")
            self.stat_scope.setText("选区")
        else:
            text = self.editor.toPlainText()
            self.stat_scope.setText("全文")
        for label, (_, value) in zip(self.stat_values, text_stats(text)):
            label.setText(value)

    def refresh_cursor(self):
        cursor = self.editor.textCursor()
        info = f"行 {cursor.blockNumber() + 1}，列 {cursor.positionInBlock() + 1}"
        if cursor.hasSelection():
            info += f"  ·  已选 {abs(cursor.position() - cursor.anchor())} 字符"
        self.cursor_label.setText(info)

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择文本文件", os.path.expanduser("~"),
                                              "文本文件 (*.txt *.md *.csv *.log *.json *.yaml *.yml *.xml *.sql *.py);;所有文件 (*)")
        if not path:
            return
        try:
            with open(path, "rb") as f:
                raw = f.read()
            text = load_text_file(path)
        except OSError as e:
            self.status_label.setText(f"读取失败：{e}")
            return
        crlf = raw.count(b"\r\n")
        lf = raw.count(b"\n") - crlf
        ending = "CRLF" if crlf and not lf else "LF" if lf and not crlf else "混合换行" if crlf else "无换行"
        bom = " · 带 BOM" if raw.startswith(b"\xef\xbb\xbf") else ""
        self.editor.setPlainText(text)
        self.status_label.setText(f"已打开 {os.path.basename(path)} · {len(raw):,} B · {ending}{bom}")

    def copy_all(self):
        text = self.editor.toPlainText()
        if not text:
            return
        QApplication.clipboard().setText(text)
        self.copy_btn.setText("已复制")
        QTimer.singleShot(900, lambda: self.copy_btn.setText("复制"))

    def do_clear(self):
        cursor = self.editor.textCursor()
        cursor.select(QTextCursor.Document)
        cursor.removeSelectedText()
        self.editor.setFocus()
        self.status_label.setText("已清空（Ctrl+Z 可恢复）")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class TextToolWindow(TabbedToolWindow):
    def __init__(self):
        super().__init__("文本工具", (
            (TextProcessWindow, "处理与统计"),
            (DiffWindow, "文本对比"),
        ))


class ImageToolWindow(QMainWindow):
    SAVE_FORMATS = ["PNG", "JPEG", "WEBP", "GIF", "BMP", "TIFF"]
    MIME = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp",
            "GIF": "image/gif", "BMP": "image/bmp", "TIFF": "image/tiff"}
    EXT = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp", "GIF": "gif", "BMP": "bmp", "TIFF": "tiff"}
    IMAGE_EXTS = ("png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff", "tif")
    QUALITY_FORMATS = ("JPEG", "WEBP")
    # 300dpi 换算的常用尺寸：证件类为竖版，冲印类的“几寸”指长边英寸
    PHOTO_SIZE_GROUPS = [
        ("证件照", [
            ("1寸 295×413 (2.5×3.5cm)", 295, 413),
            ("小二寸 413×531 (3.5×4.5cm)", 413, 531),
            ("大一寸 390×567 (3.3×4.8cm)", 390, 567),
            ("2寸 413×626 (3.5×5.3cm)", 413, 626),
            ("3寸 650×993 (5.5×8.4cm)", 650, 993),
        ]),
        ("冲印", [
            ("5寸 1050×1500 (8.9×12.7cm)", 1050, 1500),
            ("6寸 1200×1800 (10.2×15.2cm)", 1200, 1800),
            ("7寸 1500×2100 (12.7×17.8cm)", 1500, 2100),
        ]),
    ]

    SEC_BTN = """
        QPushButton { color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0;
            border-radius: 4px; font-size: 12px; }
        QPushButton:hover { background: #E0E0E0; }
    """
    PRIMARY_BTN = """
        QPushButton { color: #FFFFFF; background: #1A73E8; border: none; border-radius: 4px; font-size: 12px; }
        QPushButton:hover { background: #1557B0; }
    """
    FIELD = """
        border: 1px solid #D0D0D0; border-radius: 4px; padding: 4px 6px;
        font-family: "Menlo", "Consolas", monospace; font-size: 13px; background: #FFFFFF;
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("图片处理")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.setAcceptDrops(True)
        self.pil_img = None
        self.src_path = None
        self.raw_bytes = None
        self.src_format = None
        self._aspect_lock = False
        self.init_ui()

    def _sec_btn(self, text):
        b = QPushButton(text)
        b.setFixedHeight(30)
        b.setCursor(QCursor(Qt.PointingHandCursor))
        b.setStyleSheet(self.SEC_BTN)
        return b

    def _pri_btn(self, text):
        b = QPushButton(text)
        b.setFixedHeight(30)
        b.setCursor(QCursor(Qt.PointingHandCursor))
        b.setStyleSheet(self.PRIMARY_BTN)
        return b

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        top = QHBoxLayout()
        self.preview = QLabel()
        self.preview.setFixedSize(180, 170)
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setCursor(QCursor(Qt.PointingHandCursor))
        self.preview.setText("拖入图片\n或点击选择")
        self.preview.setStyleSheet(
            "QLabel { border: 2px dashed #C0C0C0; border-radius: 8px; color: #999999;"
            " font-family: 'PingFang SC'; font-size: 13px; background: #FAFAFA; }")
        self.preview.mousePressEvent = lambda e: self.choose_file()
        top.addWidget(self.preview)

        right = QVBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("文件路径")
        self.path_edit.setStyleSheet(
            "QLineEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 4px 6px;"
            " font-family: 'PingFang SC'; font-size: 12px; color: #666; background: #FFFFFF; }")
        right.addWidget(self.path_edit)

        self.info_label = QLabel("未选择图片")
        self.info_label.setFont(QFont("PingFang SC", 12))
        self.info_label.setStyleSheet("color: #333333;")
        self.info_label.setWordWrap(True)
        right.addWidget(self.info_label)

        btn_row = QHBoxLayout()
        choose_btn = self._sec_btn("选择文件")
        choose_btn.setFixedWidth(90)
        choose_btn.clicked.connect(self.choose_file)
        btn_row.addWidget(choose_btn)
        clear_btn = self._sec_btn("清除")
        clear_btn.setFixedWidth(70)
        clear_btn.clicked.connect(self.clear_image)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        right.addLayout(btn_row)
        right.addStretch()
        top.addLayout(right, 1)
        layout.addLayout(top)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::tab-bar { alignment: left; }
            QTabBar::tab { font-family: "PingFang SC"; font-size: 12px; padding: 6px 14px;
                color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0; border-bottom: none;
                border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { color: #1A73E8; background: #FFFFFF; }
            QTabWidget::pane { border: 1px solid #D0D0D0; border-radius: 4px; }
        """)
        tabs.addTab(self._build_b64_tab(), "转 Base64")
        tabs.addTab(self._build_convert_tab(), "格式转换")
        tabs.addTab(self._build_resize_tab(), "缩放压缩")
        layout.addWidget(tabs, 1)

    def _build_b64_tab(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(10)

        row = QHBoxLayout()
        self.b64_prefix = QCheckBox("包含 data URI 前缀 (data:image/...;base64,)")
        self.b64_prefix.setChecked(True)
        self.b64_prefix.setStyleSheet("QCheckBox { font-family: 'PingFang SC'; font-size: 12px; color: #333; }")
        self.b64_prefix.toggled.connect(self._regen_b64)
        row.addWidget(self.b64_prefix)
        row.addStretch()

        self.b64_btn = self._pri_btn("生成 Base64")
        self.b64_btn.setFixedWidth(110)
        self.b64_btn.clicked.connect(self.generate_base64)
        row.addWidget(self.b64_btn)
        copy_btn = self._sec_btn("复制")
        copy_btn.setFixedWidth(70)
        copy_btn.clicked.connect(self.copy_base64)
        self.b64_copy_btn = copy_btn
        row.addWidget(copy_btn)
        v.addLayout(row)

        self.b64_out = QPlainTextEdit()
        self.b64_out.setReadOnly(True)
        self.b64_out.setStyleSheet(
            "QPlainTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;"
            " font-family: 'Menlo', 'Consolas', monospace; font-size: 12px; background: #FAFAFA; }")
        v.addWidget(self.b64_out, 1)
        return page

    def _build_convert_tab(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(10)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        grid.addWidget(self._lab("目标格式"), 0, 0)
        self.conv_fmt = QComboBox()
        self.conv_fmt.addItems(self.SAVE_FORMATS)
        self.conv_fmt.setStyleSheet(_combo_style(size=13, mono=True))
        self.conv_fmt.currentIndexChanged.connect(lambda i: self._toggle_quality(self.conv_fmt.currentText(), self.conv_quality))
        grid.addWidget(self.conv_fmt, 0, 1)

        grid.addWidget(self._lab("质量 (1-100)"), 0, 2)
        self.conv_quality = QSpinBox()
        self.conv_quality.setRange(1, 100)
        self.conv_quality.setValue(90)
        self.conv_quality.setFixedWidth(80)
        self.conv_quality.setStyleSheet("QSpinBox { %s }" % self.FIELD)
        grid.addWidget(self.conv_quality, 0, 3)

        save_btn = self._pri_btn("保存为…")
        save_btn.setFixedWidth(110)
        save_btn.clicked.connect(self.convert_save)
        grid.addWidget(save_btn, 1, 3, Qt.AlignRight)
        v.addLayout(grid)

        self.conv_status = QLabel("仅 JPEG / WEBP 支持质量设置。")
        self.conv_status.setStyleSheet("color: #999999; font-family: 'PingFang SC'; font-size: 12px;")
        v.addWidget(self.conv_status)
        v.addStretch()
        self._toggle_quality("JPEG", self.conv_quality)
        return page

    def _build_resize_tab(self):
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(10)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

        grid.addWidget(self._lab("宽 (px)"), 0, 0)
        self.rw = QLineEdit()
        self.rw.setStyleSheet("QLineEdit { %s }" % self.FIELD)
        self.rw.textChanged.connect(lambda: self._aspect_sync("w"))
        grid.addWidget(self.rw, 0, 1)

        grid.addWidget(self._lab("高 (px)"), 0, 2)
        self.rh = QLineEdit()
        self.rh.setStyleSheet("QLineEdit { %s }" % self.FIELD)
        self.rh.textChanged.connect(lambda: self._aspect_sync("h"))
        grid.addWidget(self.rh, 0, 3)

        self.keep_aspect = QCheckBox("保持比例")
        self.keep_aspect.setChecked(True)
        self.keep_aspect.setStyleSheet("QCheckBox { font-family: 'PingFang SC'; font-size: 12px; color: #333; }")
        grid.addWidget(self.keep_aspect, 1, 0, 1, 2)

        grid.addWidget(self._lab("格式"), 1, 2)
        self.r_fmt = QComboBox()
        self.r_fmt.addItems(self.SAVE_FORMATS)
        self.r_fmt.setStyleSheet(_combo_style(size=13, mono=True))
        self.r_fmt.currentIndexChanged.connect(lambda i: self._toggle_quality(self.r_fmt.currentText(), self.r_quality))
        grid.addWidget(self.r_fmt, 1, 3)

        grid.addWidget(self._lab("质量"), 2, 0)
        self.r_quality = QSpinBox()
        self.r_quality.setRange(1, 100)
        self.r_quality.setValue(85)
        self.r_quality.setFixedWidth(80)
        self.r_quality.setStyleSheet("QSpinBox { %s }" % self.FIELD)
        grid.addWidget(self.r_quality, 2, 1)

        rsave = self._pri_btn("保存为…")
        rsave.setFixedWidth(110)
        rsave.clicked.connect(self.resize_save)
        grid.addWidget(rsave, 2, 3, Qt.AlignRight)

        grid.addWidget(self._lab("常用尺寸"), 3, 0)
        self.r_preset = QComboBox()
        self.r_preset.addItem("自定义", None)
        for group, sizes in self.PHOTO_SIZE_GROUPS:
            self.r_preset.insertSeparator(self.r_preset.count())
            header = self.r_preset.count()
            self.r_preset.addItem(group)
            # Non-selectable group heading: separators alone do not label the group.
            self.r_preset.model().item(header).setFlags(Qt.NoItemFlags)
            for label, pw, ph in sizes:
                self.r_preset.addItem(label, (pw, ph))
        self.r_preset.setStyleSheet(_combo_style(size=13, mono=True))
        self.r_preset.currentIndexChanged.connect(self._apply_preset)
        grid.addWidget(self.r_preset, 3, 1, 1, 2)

        self.r_crop = QCheckBox("居中裁剪填充")
        self.r_crop.setStyleSheet("QCheckBox { font-family: 'PingFang SC'; font-size: 12px; color: #333; }")
        self.r_crop.setToolTip("按目标比例从中心裁掉多余部分，避免证件照被拉伸变形")
        grid.addWidget(self.r_crop, 3, 3, Qt.AlignRight)
        v.addLayout(grid)

        self.r_status = QLabel("留空的维度按比例自动计算；修改宽/高即可联动。")
        self.r_status.setStyleSheet("color: #999999; font-family: 'PingFang SC'; font-size: 12px;")
        v.addWidget(self.r_status)
        v.addStretch()
        self._toggle_quality("PNG", self.r_quality)
        return page

    @staticmethod
    def _lab(text):
        l = QLabel(text)
        l.setStyleSheet("color: #333333; font-family: 'PingFang SC'; font-size: 12px;")
        return l

    @staticmethod
    def _toggle_quality(fmt, spin):
        spin.setEnabled(fmt in ImageToolWindow.QUALITY_FORMATS)

    # ---- load / preview ----
    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "",
            "图片 (*.png *.jpg *.jpeg *.webp *.gif *.bmp *.tiff *.tif)")
        if path:
            self.load_image(path)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().rsplit(".", 1)[-1] in self.IMAGE_EXTS:
                    event.acceptProposedAction()
                    return

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if p.lower().rsplit(".", 1)[-1] in self.IMAGE_EXTS:
                self.load_image(p)
                break

    def load_image(self, path):
        try:
            with open(path, "rb") as f:
                raw = f.read()
            img = Image.open(io.BytesIO(raw))
            img.load()
        except Exception as e:
            QMessageBox.warning(self, "打开失败", f"无法读取图片:\n{e}")
            return
        self.pil_img = img
        self.src_path = path
        self.raw_bytes = raw
        self.src_format = (img.format or path.lower().rsplit(".", 1)[-1]).upper()
        self.path_edit.setText(os.path.basename(path))
        self.info_label.setText(
            "格式: %s    尺寸: %d × %d    模式: %s\n大小: %s" % (
                self.src_format, img.width, img.height, img.mode, self._human_size(len(raw))))
        self.b64_out.setPlainText("")
        self.r_status.setText("图片已加载，可缩放 / 压缩后另存。")
        self._refresh_preview()

    def clear_image(self):
        self.pil_img = None
        self.src_path = None
        self.raw_bytes = None
        self.src_format = None
        self.path_edit.setText("")
        self.info_label.setText("未选择图片")
        self.b64_out.setPlainText("")
        self.rw.clear()
        self.rh.clear()
        self.preview.setText("拖入图片\n或点击选择")
        self.preview.setPixmap(QPixmap())
        self.preview.setStyleSheet(
            "QLabel { border: 2px dashed #C0C0C0; border-radius: 8px; color: #999999;"
            " font-family: 'PingFang SC'; font-size: 13px; background: #FAFAFA; }")

    def _refresh_preview(self):
        if not self.pil_img:
            return
        try:
            thumb = self.pil_img.convert("RGB").copy()
            thumb.thumbnail((176, 158))
            buf = io.BytesIO()
            thumb.save(buf, "PNG")
            pm = QPixmap()
            pm.loadFromData(buf.getvalue())
            self.preview.setPixmap(pm)
            self.preview.setStyleSheet("QLabel { border: 1px solid #D0D0D0; border-radius: 8px; background: #FAFAFA; }")
        except Exception:
            pass

    @staticmethod
    def _human_size(n):
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024:
                return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
            n /= 1024.0
        return f"{n:.1f} TB"

    def _require(self):
        if not self.pil_img:
            QMessageBox.information(self, "提示", "请先选择或拖入一张图片")
            return False
        return True

    # ---- Base64 ----
    def generate_base64(self):
        if not self._require():
            return
        b64 = base64.b64encode(self.raw_bytes).decode("ascii")
        if self.b64_prefix.isChecked():
            mime = self.MIME.get(self.src_format, "image/png")
            text = f"data:{mime};base64,{b64}"
        else:
            text = b64
        self.b64_out.setPlainText(text)

    def _regen_b64(self):
        if self.pil_img and self.b64_out.toPlainText():
            self.generate_base64()

    def copy_base64(self):
        text = self.b64_out.toPlainText()
        if not text:
            return
        QApplication.clipboard().setText(text)
        self.b64_copy_btn.setText("已复制")
        QTimer.singleShot(1200, lambda: self.b64_copy_btn.setText("复制"))

    # ---- conversion ----
    def _prepare(self, img, fmt):
        if fmt == "JPEG":
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                rgba = img.convert("RGBA")
                bg.paste(rgba, mask=rgba.split()[-1])
                return bg
            return img.convert("RGB")
        if fmt == "BMP":
            return img.convert("RGB") if img.mode not in ("1", "L", "RGB") else img
        if fmt == "TIFF":
            return img.convert("RGB") if img.mode not in ("L", "RGB") else img
        if fmt == "GIF":
            return img.convert("P", palette=Image.ADAPTIVE)
        return img

    def convert_save(self):
        if not self._require():
            return
        fmt = self.conv_fmt.currentText()
        base = os.path.splitext(self.src_path)[0] if self.src_path else "image"
        save_path, _ = QFileDialog.getSaveFileName(
            self, "保存图片", base + "." + self.EXT[fmt],
            "%s (*.%s)" % (fmt, self.EXT[fmt]))
        if not save_path:
            return
        self._save(self.pil_img, fmt, self.conv_quality.value(), save_path, self.conv_status)

    def resize_save(self):
        if not self._require():
            return
        w, h = self._target_size()
        if not w or not h:
            self.r_status.setText("请填写有效的宽或高。")
            self.r_status.setStyleSheet("color: #D93025; font-family: 'PingFang SC'; font-size: 12px;")
            return
        try:
            src = self.pil_img
            if self.r_crop.isChecked():
                src = self._crop_to_aspect(src, w, h)
            resized = src.resize((w, h), Image.LANCZOS)
        except Exception as e:
            self.r_status.setText(f"缩放失败: {e}")
            self.r_status.setStyleSheet("color: #D93025; font-family: 'PingFang SC'; font-size: 12px;")
            return
        fmt = self.r_fmt.currentText()
        base = os.path.splitext(self.src_path)[0] if self.src_path else "image"
        save_path, _ = QFileDialog.getSaveFileName(
            self, "保存缩放图", f"{base}_{w}x{h}." + self.EXT[fmt],
            "%s (*.%s)" % (fmt, self.EXT[fmt]))
        if not save_path:
            return
        self._save(resized, fmt, self.r_quality.value(), save_path, self.r_status)

    def _apply_preset(self, index):
        size = self.r_preset.itemData(index)
        if not size:
            return
        w, h = size
        # Block the aspect linkage while filling both fields, otherwise the width
        # change would rewrite the preset height from the source image ratio.
        self._aspect_lock = True
        try:
            self.rw.setText(str(w))
            self.rh.setText(str(h))
        finally:
            self._aspect_lock = False
        self.r_crop.setChecked(True)
        self.r_status.setText("已选 %s，居中裁剪填充。" % self.r_preset.itemText(index))
        self.r_status.setStyleSheet("color: #666666; font-family: 'PingFang SC'; font-size: 12px;")

    @staticmethod
    def _crop_to_aspect(img, w, h):
        target = w / float(h)
        ow, oh = img.width, img.height
        if abs(ow / float(oh) - target) < 1e-3:
            return img
        if ow / float(oh) > target:
            crop_w = max(1, int(round(oh * target)))
            left = (ow - crop_w) // 2
            return img.crop((left, 0, left + crop_w, oh))
        crop_h = max(1, int(round(ow / target)))
        top = (oh - crop_h) // 2
        return img.crop((0, top, ow, top + crop_h))

    def _save(self, img, fmt, quality, save_path, status_label):
        try:
            out = self._prepare(img, fmt)
            params = {}
            if fmt in self.QUALITY_FORMATS:
                params["quality"] = quality
            if fmt == "PNG":
                params["optimize"] = True
            out.save(save_path, fmt, **params)
            size = os.path.getsize(save_path)
            status_label.setText("已保存: %s  (%s)" % (os.path.basename(save_path), self._human_size(size)))
            status_label.setStyleSheet("color: #188038; font-family: 'PingFang SC'; font-size: 12px;")
        except Exception as e:
            status_label.setText(f"保存失败: {e}")
            status_label.setStyleSheet("color: #D93025; font-family: 'PingFang SC'; font-size: 12px;")

    # ---- aspect link ----
    def _target_size(self):
        try:
            w = int(self.rw.text()) if self.rw.text().strip() else None
            h = int(self.rh.text()) if self.rh.text().strip() else None
        except ValueError:
            return None, None
        if self.pil_img:
            ow, oh = self.pil_img.width, self.pil_img.height
            if w and not h:
                h = max(1, round(w * oh / ow))
            elif h and not w:
                w = max(1, round(h * ow / oh))
        return w, h

    def _aspect_sync(self, changed):
        if not self.pil_img or self._aspect_lock or not self.keep_aspect.isChecked():
            return
        ow, oh = self.pil_img.width, self.pil_img.height
        self._aspect_lock = True
        try:
            if changed == "w":
                if self.rw.text().strip().isdigit():
                    self.rh.setText(str(max(1, round(int(self.rw.text()) * oh / ow))))
            else:
                if self.rh.text().strip().isdigit():
                    self.rw.setText(str(max(1, round(int(self.rh.text()) * ow / oh))))
        finally:
            self._aspect_lock = False

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class RmbUppercaseWindow(QMainWindow):
    DIGITS = "零壹贰叁肆伍陆柒捌玖"
    SEC = ["", "万", "亿", "万亿", "亿亿", "万亿亿"]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("金额大写")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(12)

        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(10)

        in_label = QLabel("输入金额(元)")
        in_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        in_label.setStyleSheet("color: #333333;")
        form.addWidget(in_label, 0, 0)

        self.amount_edit = QLineEdit()
        self.amount_edit.setPlaceholderText("如 1234.56 或 1,234,000 (支持负数)")
        self.amount_edit.setStyleSheet("""
            QLineEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 6px 8px;
                font-family: "Menlo", "Consolas", monospace; font-size: 13px; }
            QLineEdit:focus { border-color: #1A73E8; }
        """)
        self.amount_edit.textChanged.connect(self.convert)
        form.addWidget(self.amount_edit, 0, 1)

        clear_btn = QPushButton("清空")
        clear_btn.setFixedSize(70, 30)
        clear_btn.setCursor(QCursor(Qt.PointingHandCursor))
        clear_btn.setStyleSheet("""
            QPushButton { color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #E0E0E0; }
        """)
        clear_btn.clicked.connect(self.do_clear)
        form.addWidget(clear_btn, 0, 2)

        layout.addLayout(form)

        self.status_label = QLabel("输入数字金额，自动转换为中文大写(人民币)。")
        self.status_label.setFont(QFont("PingFang SC", 11))
        self.status_label.setStyleSheet("color: #999999;")
        layout.addWidget(self.status_label)

        out_label = QLabel("中文大写")
        out_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        out_label.setStyleSheet("color: #333333;")
        layout.addWidget(out_label)

        row = QHBoxLayout()
        self.result_edit = QLineEdit()
        self.result_edit.setReadOnly(True)
        self.result_edit.setStyleSheet("""
            QLineEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px 10px;
                font-family: "PingFang SC", "Microsoft YaHei"; font-size: 16px; color: #1A73E8; background: #FAFAFA; }
        """)
        row.addWidget(self.result_edit, 1)

        copy_btn = QPushButton("复制")
        copy_btn.setFixedSize(70, 34)
        copy_btn.setCursor(QCursor(Qt.PointingHandCursor))
        copy_btn.setStyleSheet("""
            QPushButton { color: #FFFFFF; background: #1A73E8; border: none; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #1557B0; }
        """)
        copy_btn.clicked.connect(self.do_copy)
        row.addWidget(copy_btn)
        layout.addLayout(row)
        layout.addStretch()

    def set_status(self, text, ok=True):
        self.status_label.setText(text)
        self.status_label.setStyleSheet("color: %s; font-size: 11px;" % ("#188038" if ok else "#D93025"))

    def do_clear(self):
        self.amount_edit.blockSignals(True)
        self.amount_edit.clear()
        self.amount_edit.blockSignals(False)
        self.result_edit.setText("")
        self.status_label.setText("输入数字金额，自动转换为中文大写(人民币)。")
        self.status_label.setStyleSheet("color: #999999; font-size: 11px;")

    def do_copy(self):
        text = self.result_edit.text()
        if text:
            QApplication.clipboard().setText(text)
            self.set_status("已复制到剪贴板", ok=True)

    def _group4(self, g):
        units = ["", "拾", "佰", "仟"]
        res = ""
        zero = False
        for pos in range(3, -1, -1):
            digit = (g // (10 ** pos)) % 10
            if digit == 0:
                if res:
                    zero = True
            else:
                if zero:
                    res += "零"
                    zero = False
                res += self.DIGITS[digit] + units[pos]
        return res

    def _int_to_cn(self, num):
        if num == 0:
            return "零"
        groups = []
        while num > 0:
            groups.append(num % 10000)
            num //= 10000
        out = ""
        for i in range(len(groups) - 1, -1, -1):
            g = groups[i]
            if g == 0:
                continue
            if out and g < 1000:
                out += "零"
            out += self._group4(g) + self.SEC[i]
        return out

    def convert(self):
        s = self.amount_edit.text().strip().replace(",", "").replace("，", "")
        if not s:
            self.result_edit.setText("")
            self.status_label.setText("输入数字金额，自动转换为中文大写(人民币)。")
            self.status_label.setStyleSheet("color: #999999; font-size: 11px;")
            return
        neg = s.startswith("-")
        if neg:
            s = s[1:]
        if not re.match(r"^\d*\.?\d+$", s):
            self.result_edit.setText("")
            self.set_status("请输入合法的数字金额", ok=False)
            return
        try:
            val = decimal.Decimal(s).quantize(decimal.Decimal("0.01"), rounding=decimal.ROUND_HALF_UP)
        except decimal.InvalidOperation:
            self.set_status("数值超出范围", ok=False)
            return
        int_part = int(val)
        frac = int((val - int_part) * 100)
        jiao, fen = frac // 10, frac % 10
        if len(str(int_part)) > 20:
            self.set_status("整数部分过大(最多支持到万亿亿)", ok=False)
            return

        if int_part == 0 and frac == 0:
            result = "零元整"
        else:
            parts = []
            if int_part > 0:
                parts.append(self._int_to_cn(int_part) + "元")
            if jiao == 0 and fen == 0:
                parts.append("整")
            else:
                if jiao > 0:
                    parts.append(self.DIGITS[jiao] + "角")
                elif int_part > 0:
                    parts.append("零")
                if fen > 0:
                    parts.append(self.DIGITS[fen] + "分")
            result = "".join(parts)
        if neg and result != "零元整":
            result = "负" + result
        self.result_edit.setText(result)
        self.set_status("转换成功", ok=True)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class RomanNumeralWindow(QMainWindow):
    VALS = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    SYMS = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    CHAR = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}

    def __init__(self):
        super().__init__()
        self.setWindowTitle("罗马数字转换")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(12)

        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(10)

        in_label = QLabel("输入")
        in_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        in_label.setStyleSheet("color: #333333;")
        form.addWidget(in_label, 0, 0)

        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("阿拉伯数字(1-3999) 或 罗马数字,如 MCMXCIV")
        self.input_edit.setStyleSheet("""
            QLineEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 6px 8px;
                font-family: "Menlo", "Consolas", monospace; font-size: 13px; }
            QLineEdit:focus { border-color: #1A73E8; }
        """)
        self.input_edit.textChanged.connect(self.convert)
        form.addWidget(self.input_edit, 0, 1)

        clear_btn = QPushButton("清空")
        clear_btn.setFixedSize(70, 30)
        clear_btn.setCursor(QCursor(Qt.PointingHandCursor))
        clear_btn.setStyleSheet("""
            QPushButton { color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #E0E0E0; }
        """)
        clear_btn.clicked.connect(self.do_clear)
        form.addWidget(clear_btn, 0, 2)
        layout.addLayout(form)

        self.status_label = QLabel("自动识别输入方向：数字转罗马，或罗马转数字。")
        self.status_label.setFont(QFont("PingFang SC", 11))
        self.status_label.setStyleSheet("color: #999999;")
        layout.addWidget(self.status_label)

        self.arab_edit, arab_row = self._result_row("阿拉伯数字")
        layout.addLayout(arab_row)
        self.roman_edit, roman_row = self._result_row("罗马数字")
        layout.addLayout(roman_row)
        layout.addStretch()

    def _result_row(self, title):
        box = QVBoxLayout()
        lab = QLabel(title)
        lab.setFont(QFont("PingFang SC", 11, QFont.Bold))
        lab.setStyleSheet("color: #333333;")
        box.addWidget(lab)
        row = QHBoxLayout()
        edit = QLineEdit()
        edit.setReadOnly(True)
        edit.setStyleSheet("""
            QLineEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 6px 8px;
                font-family: "Menlo", "Consolas", monospace; font-size: 14px; color: #1A73E8; background: #FAFAFA; }
        """)
        row.addWidget(edit, 1)
        btn = QPushButton("复制")
        btn.setFixedSize(70, 32)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setStyleSheet("""
            QPushButton { color: #FFFFFF; background: #1A73E8; border: none; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #1557B0; }
        """)
        btn.clicked.connect(lambda _=False, e=edit: self._copy(e))
        row.addWidget(btn)
        box.addLayout(row)
        return edit, box

    def _copy(self, edit):
        text = edit.text()
        if text:
            QApplication.clipboard().setText(text)
            self.set_status("已复制到剪贴板", ok=True)

    def set_status(self, text, ok=True):
        self.status_label.setText(text)
        self.status_label.setStyleSheet("color: %s; font-size: 11px;" % ("#188038" if ok else "#D93025"))

    def do_clear(self):
        self.input_edit.blockSignals(True)
        self.input_edit.clear()
        self.input_edit.blockSignals(False)
        self.arab_edit.setText("")
        self.roman_edit.setText("")
        self.status_label.setText("自动识别输入方向：数字转罗马，或罗马转数字。")
        self.status_label.setStyleSheet("color: #999999; font-size: 11px;")

    def to_roman(self, num):
        out = ""
        for v, sym in zip(self.VALS, self.SYMS):
            while num >= v:
                out += sym
                num -= v
        return out

    def roman_to_int(self, s):
        total = 0
        prev = 0
        for ch in reversed(s):
            v = self.CHAR.get(ch)
            if v is None:
                return None
            if v < prev:
                total -= v
            else:
                total += v
                prev = v
        return total

    def convert(self):
        raw = self.input_edit.text().strip()
        if not raw:
            self.arab_edit.setText("")
            self.roman_edit.setText("")
            self.status_label.setText("自动识别输入方向：数字转罗马，或罗马转数字。")
            self.status_label.setStyleSheet("color: #999999; font-size: 11px;")
            return
        if raw.isdigit():
            n = int(raw)
            if n < 1 or n > 3999:
                self.arab_edit.setText("")
                self.roman_edit.setText("")
                self.set_status("数字需在 1-3999 之间(罗马数字标准范围)", ok=False)
                return
            self.arab_edit.setText(str(n))
            self.roman_edit.setText(self.to_roman(n))
            self.set_status("数字 → 罗马", ok=True)
        else:
            up = raw.upper().replace(" ", "")
            if any(c not in self.CHAR for c in up):
                self.arab_edit.setText("")
                self.roman_edit.setText("")
                self.set_status("含非法字符，罗马数字仅由 I V X L C D M 组成", ok=False)
                return
            n = self.roman_to_int(up)
            if n is None or n < 1 or n > 3999:
                self.arab_edit.setText("")
                self.roman_edit.setText("")
                self.set_status("无法转换为有效罗马数字(范围 1-3999)", ok=False)
                return
            canonical = self.to_roman(n)
            self.arab_edit.setText(str(n))
            self.roman_edit.setText(canonical)
            if canonical != up:
                self.set_status("罗马 → 数字 (%s 非标准写法，规范为 %s)" % (raw.upper(), canonical), ok=True)
            else:
                self.set_status("罗马 → 数字", ok=True)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class ScreenPickOverlay(QWidget):
    """全屏透明取色罩：跟随鼠标的放大镜 loupe。C 复制并退出、X 切换 HEX/RGB、左键/右键/ESC 退出。
    复制只进剪贴板，复制后放大镜消失，不弹出任何应用窗口。"""

    copied = pyqtSignal(QColor)
    closed = pyqtSignal()
    SRC = 25          # 采样边长（奇数，中心即光标像素）
    ZOOM = 10         # 放大倍数
    OFFSET = 28       # loupe 相对光标的偏移，避免采样到自身

    def __init__(self):
        # 普通窗口 + WA_ShowWithoutActivating + AppKit 抬层级：罩在最前但不切换前台应用，
        # 被取色的应用保持原样。不用 showFullScreen()（原生全屏 Space 切换会黑屏）。
        super().__init__(None, Qt.Window | Qt.FramelessWindowHint |
                         Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)
        self._pos = QCursor.pos()
        self._center = QColor("#FFFFFF")
        self._hint = ""
        self._prev_pid = None
        self._format = "HEX"
        self._key_prev = {"esc": False, "c": False, "x": False, "lmb": False, "rmb": False}
        self._cg = None
        # 不抢焦点，故 ESC/C/X 用 HID 键态轮询读取（无需辅助功能权限）
        self._key_timer = QTimer(self)
        self._key_timer.setInterval(40)
        self._key_timer.timeout.connect(self._poll_keys)

    def start(self):
        self._pos = QCursor.pos()
        self._prev_pid = _mac_frontmost_pid()
        self._key_prev = {"esc": False, "c": False, "x": False, "lmb": False, "rmb": False}
        if platform.system() == "Windows":
            self._key_prev = {
                key: bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)
                for key, vk in (("esc", 0x1B), ("c", 0x43), ("x", 0x58),
                                ("lmb", 0x01), ("rmb", 0x02))
            }
        geo = QRect()
        for s in QApplication.screens():
            geo = geo.united(s.geometry())
        if geo.isNull():
            geo = QApplication.primaryScreen().geometry()
        self.setGeometry(geo)
        # 只 show()（WA_ShowWithoutActivating）；raise_/activateWindow/setFocus/
        # makeKeyAndOrderFront 都会把本应用切到前台、挤掉被取色的应用，一律不用。
        self.show()
        if _mac_is_cocoa():
            try:
                _mac_picker_nonactivating(self)
            except Exception:
                pass
        self._key_timer.start()
        self.update()

    def _poll_keys(self):
        # 半透明置顶窗在 Windows 上常收不到 hover 的 mouseMoveEvent，
        # 这里借定时器主动读取光标位置，保证放大镜始终跟随鼠标移动。
        pos = QCursor.pos()
        if pos != self._pos:
            self._pos = pos
            self.update()
        try:
            if platform.system() == "Darwin":
                if self._cg is None:
                    from ctypes.util import find_library
                    self._cg = ctypes.cdll.LoadLibrary(find_library("CoreGraphics"))
                    self._cg.CGEventSourceKeyState.restype = ctypes.c_bool
                    self._cg.CGEventSourceKeyState.argtypes = [
                        ctypes.c_int, ctypes.c_uint16]
                # kCGEventSourceStateHIDSystemState=1; kVK_Escape=53, C=8, X=7
                state = {"esc": self._cg.CGEventSourceKeyState(1, 53),
                         "c": self._cg.CGEventSourceKeyState(1, 8),
                         "x": self._cg.CGEventSourceKeyState(1, 7)}
            elif platform.system() == "Windows":
                g = ctypes.windll.user32.GetAsyncKeyState
                state = {"esc": bool(g(0x1B) & 0x8000),
                         "c": bool(g(0x43) & 0x8000),
                         "x": bool(g(0x58) & 0x8000),
                         "lmb": bool(g(0x01) & 0x8000),
                         "rmb": bool(g(0x02) & 0x8000)}
            else:
                return
            for key, pressed in state.items():
                rising = pressed and not self._key_prev[key]
                self._key_prev[key] = pressed
                if not rising:
                    continue
                if key == "esc":
                    self.close()
                    return
                elif key == "c":
                    self._copy_current()
                    return
                elif key == "x":
                    self._toggle_format()
                elif key in ("lmb", "rmb"):
                    self.close()
                    return
        except Exception:
            write_startup_log("屏幕取色输入读取失败：\n" + traceback.format_exc())
            self.close()

    def _format_value(self, fmt):
        r, g, b, _ = self._center.getRgb()
        if fmt == "HEX":
            return self._center.name().upper()
        return "rgb(%d, %d, %d)" % (r, g, b)

    def _copy_current(self):
        text = self._format_value(self._format)
        QApplication.clipboard().setText(text)
        self.copied.emit(QColor(self._center))
        # 复制即退出取色：放大镜消失，owner 静默不弹窗
        self.close()

    def _toggle_format(self):
        self._format = "RGB" if self._format == "HEX" else "HEX"
        self.update()

    def mouseMoveEvent(self, event):
        self._pos = event.globalPos()
        self.update()

    def mousePressEvent(self, event):
        # 左键/右键都退出；复制改由 C 键触发，不再弹窗
        if event.button() in (Qt.LeftButton, Qt.RightButton):
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_C:
            self._copy_current()
        elif event.key() == Qt.Key_X:
            self._toggle_format()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self._key_timer.stop()
        # 退出时把前台交还给取色前的应用，不让它退到后台
        if self._prev_pid:
            _mac_reactivate(self._prev_pid)
        self.closed.emit()
        super().closeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        screen = QApplication.screenAt(self._pos) or QApplication.primaryScreen()
        geo = screen.geometry()
        half = self.SRC // 2
        # QCursor.pos() 是逻辑坐标，而 grabWindow 按物理像素取图；
        # Windows 显示缩放≠100% 时两者错位，需换算到该屏内的物理像素坐标，
        # 同时减去屏幕原点以支持多显示器（副屏原点可能非 0,0）。
        dpr = screen.devicePixelRatio()
        local = self._pos - geo.topLeft()
        px = int(round(local.x() * dpr))
        py = int(round(local.y() * dpr))
        grab = screen.grabWindow(0, px - half, py - half, self.SRC, self.SRC)
        grab.setDevicePixelRatio(1.0)
        loupe = self.SRC * self.ZOOM
        # loupe 位置：光标右下，夹在屏幕内
        lx = min(max(self._pos.x() + self.OFFSET, geo.x()), geo.right() - loupe - 8)
        ly = min(max(self._pos.y() + self.OFFSET, geo.y()), geo.bottom() - loupe - 76)
        box = QRect(lx, ly, loupe, loupe)

        if grab.isNull():
            self._hint = "无法读取屏幕：请在系统隐私设置中授予屏幕录制权限"
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 255, 255, 235))
            painter.drawRoundedRect(box, 6, 6)
            painter.setPen(QColor("#D93025"))
            painter.setFont(QFont("PingFang SC", 11))
            painter.drawText(box.adjusted(12, 12, -12, -12),
                             Qt.AlignCenter | Qt.TextWordWrap, self._hint)
            painter.end()
            return

        img = grab.toImage()
        self._center = img.pixelColor(half, half)
        mag = img.scaled(loupe, loupe, Qt.IgnoreAspectRatio, Qt.FastTransformation)
        painter.drawImage(box, mag)

        # 像素网格
        painter.setPen(QColor(255, 255, 255, 40))
        for i in range(1, self.SRC):
            painter.drawLine(box.x() + i * self.ZOOM, box.y(),
                             box.x() + i * self.ZOOM, box.bottom())
            painter.drawLine(box.x(), box.y() + i * self.ZOOM,
                             box.right(), box.y() + i * self.ZOOM)
        # 中心像素高亮 + 十字
        cx = box.x() + half * self.ZOOM
        cy = box.y() + half * self.ZOOM
        painter.setPen(QPen(QColor("#FFFFFF"), 2))
        painter.drawRect(cx, cy, self.ZOOM, self.ZOOM)
        painter.setPen(QPen(QColor("#000000"), 1))
        painter.drawRect(cx - 1, cy - 1, self.ZOOM + 2, self.ZOOM + 2)
        # 外框
        painter.setPen(QPen(QColor("#1A73E8"), 2))
        painter.drawRoundedRect(box.adjusted(-1, -1, 1, 1), 6, 6)

        # 信息条：色块 + 当前格式值 / 另一格式 / 按键提示（三行，避免重叠）
        info = QRect(box.x(), box.bottom() + 6, loupe, 64)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 235))
        painter.drawRoundedRect(info, 6, 6)
        painter.setBrush(self._center)
        painter.setPen(QPen(QColor("#D0D0D0"), 1))
        painter.drawRoundedRect(info.x() + 8, info.y() + 12, 40, 40, 4, 4)
        other = "RGB" if self._format == "HEX" else "HEX"
        painter.setPen(QColor("#1F2328"))
        painter.setFont(QFont("Menlo", 12, QFont.Bold))
        painter.drawText(info.x() + 56, info.y() + 22, self._format_value(self._format))
        painter.setFont(QFont("Menlo", 10))
        painter.setPen(QColor("#57606A"))
        painter.drawText(info.x() + 56, info.y() + 38, self._format_value(other))
        painter.setFont(QFont("PingFang SC", 9))
        painter.setPen(QColor("#8B949E"))
        painter.drawText(info.x() + 56, info.y() + 54, "C 复制并退出 · X 切换 · 左键/ESC 退出")
        painter.end()


def capture_desktop():
    if platform.system() == "Darwin":
        from ctypes.util import find_library
        cg = ctypes.cdll.LoadLibrary(find_library("CoreGraphics"))
        if hasattr(cg, "CGPreflightScreenCaptureAccess"):
            cg.CGPreflightScreenCaptureAccess.restype = ctypes.c_bool
            if not cg.CGPreflightScreenCaptureAccess():
                raise ValueError("请在系统设置 → 隐私与安全性 → 屏幕录制中授权工具箱，然后重新启动")
    screens = QApplication.screens()
    geometry = QRect()
    for screen in screens:
        geometry = geometry.united(screen.geometry())
    dpr = max(screen.devicePixelRatio() for screen in screens)
    desktop = QPixmap(round(geometry.width() * dpr), round(geometry.height() * dpr))
    desktop.setDevicePixelRatio(dpr)
    desktop.fill(Qt.black)
    painter = QPainter(desktop)
    try:
        for screen in screens:
            image = screen.grabWindow(0)
            if image.isNull():
                raise ValueError("无法读取屏幕，请检查系统的屏幕录制权限")
            painter.drawPixmap(screen.geometry().translated(-geometry.topLeft()), image)
    finally:
        painter.end()
    return desktop, geometry


def crop_desktop(desktop, rectangle):
    dpr = desktop.devicePixelRatio()
    left, top = round(rectangle.x() * dpr), round(rectangle.y() * dpr)
    right, bottom = round((rectangle.x() + rectangle.width()) * dpr), round((rectangle.y() + rectangle.height()) * dpr)
    image = desktop.copy(left, top, right - left, bottom - top)
    image.setDevicePixelRatio(dpr)
    return image


def save_screenshot(parent, image):
    name = "截图_%s.png" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path, _ = QFileDialog.getSaveFileName(parent, "保存截图", name, "PNG 图片 (*.png)")
    if not path:
        return False
    if not image.save(path, "PNG"):
        QMessageBox.warning(parent, "保存失败", "无法写入图片，请检查文件路径与权限")
        return False
    return True


def screenshot_ocr_command(image_path):
    env = os.environ.copy()
    if platform.system() == "Windows":
        script = r'''
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$stream = $null
$bitmap = $null
try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    $awaitMethod = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq "AsTask" -and $_.IsGenericMethod -and
        $_.GetGenericArguments().Count -eq 1 -and $_.GetParameters().Count -eq 1
    } | Select-Object -First 1
    function Await($operation, [Type]$resultType) {
        $task = $awaitMethod.MakeGenericMethod($resultType).Invoke($null, @($operation))
        $task.GetAwaiter().GetResult()
    }
    $ocr = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
    $language = $ocr::AvailableRecognizerLanguages | Where-Object {
        $_.LanguageTag -like "zh-Hans*"
    } | Select-Object -First 1
    if ($null -ne $language) {
        $engine = $ocr::TryCreateFromLanguage($language)
    } else {
        $engine = $ocr::TryCreateFromUserProfileLanguages()
    }
    if ($null -eq $engine) {
        throw "系统没有可用的 OCR 语言包，请在 Windows 设置的语言选项中安装中文或英文语言包。"
    }
    $file = Await ([Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]::GetFileFromPathAsync($env:PERSONAL_TOOLBOX_OCR_IMAGE)) ([Windows.Storage.StorageFile])
    $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $transform = [Windows.Graphics.Imaging.BitmapTransform, Windows.Foundation, ContentType = WindowsRuntime]::new()
    $ratio = [Math]::Min(1.0, [double]$ocr::MaxImageDimension / [Math]::Max($decoder.PixelWidth, $decoder.PixelHeight))
    $transform.ScaledWidth = [uint32][Math]::Max(1, [Math]::Floor($decoder.PixelWidth * $ratio))
    $transform.ScaledHeight = [uint32][Math]::Max(1, [Math]::Floor($decoder.PixelHeight * $ratio))
    $bitmap = Await ($decoder.GetSoftwareBitmapAsync(
        [Windows.Graphics.Imaging.BitmapPixelFormat]::Bgra8,
        [Windows.Graphics.Imaging.BitmapAlphaMode]::Ignore,
        $transform,
        [Windows.Graphics.Imaging.ExifOrientationMode]::IgnoreExifOrientation,
        [Windows.Graphics.Imaging.ColorManagementMode]::DoNotColorManage
    )) ([Windows.Graphics.Imaging.SoftwareBitmap])
    $result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
    $englishWords = @()
    if ($engine.RecognizerLanguage.LanguageTag -like "zh-*") {
        $englishLanguage = $ocr::AvailableRecognizerLanguages | Where-Object {
            $_.LanguageTag -like "en-*"
        } | Select-Object -First 1
        if ($null -ne $englishLanguage) {
            $englishEngine = $ocr::TryCreateFromLanguage($englishLanguage)
            $englishResult = Await ($englishEngine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
            $englishWords = @($englishResult.Lines | ForEach-Object { $_.Words })
        }
    }
    $lines = foreach ($line in $result.Lines) {
        $words = @($line.Words)
        $replacements = @{}
        $skipped = @{}
        foreach ($englishWord in $englishWords) {
            $other = $englishWord.BoundingRect
            $matches = @()
            $compact = ""
            for ($index = 0; $index -lt $words.Count; $index++) {
                $rect = $words[$index].BoundingRect
                $width = [Math]::Max(0, [Math]::Min($rect.X + $rect.Width, $other.X + $other.Width) - [Math]::Max($rect.X, $other.X))
                $height = [Math]::Max(0, [Math]::Min($rect.Y + $rect.Height, $other.Y + $other.Height) - [Math]::Max($rect.Y, $other.Y))
                if ($width / $rect.Width -gt 0.8 -and $height / [Math]::Min($rect.Height, $other.Height) -gt 0.5) {
                    $matches += $index
                    $compact += $words[$index].Text
                }
            }
            if ($matches.Count -gt 0 -and [regex]::Matches($compact, "[\u3400-\u9FFF]").Count * 2 -lt $compact.Length) {
                $replacements[$matches[0]] = $englishWord.Text
                for ($index = 1; $index -lt $matches.Count; $index++) {
                    $skipped[$matches[$index]] = $true
                }
            }
        }
        $parts = for ($index = 0; $index -lt $words.Count; $index++) {
            if ($replacements.ContainsKey($index)) {
                $replacements[$index]
            } elseif (!$skipped.ContainsKey($index)) {
                $words[$index].Text
            }
        }
        [regex]::Replace(($parts -join " "), "(?<=[\u3400-\u9FFF])\s+(?=[\u3400-\u9FFF])", "")
    }
    $text = $lines -join "`n"
    ConvertTo-Json -InputObject $text -Compress
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
} finally {
    if ($null -ne $bitmap) { $bitmap.Dispose() }
    if ($null -ne $stream) { $stream.Dispose() }
}
'''
        env["PERSONAL_TOOLBOX_OCR_IMAGE"] = image_path
        powershell = os.path.join(os.environ["SystemRoot"], "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
        encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        return [powershell, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded], env
    if platform.system() == "Darwin":
        script = r'''
ObjC.import('Vision');
ObjC.import('Foundation');
function run(argv) {
    var request = $.VNRecognizeTextRequest.alloc.init;
    request.recognitionLevel = $.VNRequestTextRecognitionLevelAccurate;
    request.usesLanguageCorrection = true;
    var error = Ref();
    var supported = ObjC.deepUnwrap($.VNRecognizeTextRequest.supportedRecognitionLanguagesForRecognitionLevelRevisionError(
        request.recognitionLevel, request.revision, error));
    request.recognitionLanguages = supported.filter(function(language) {
        return language === 'zh-Hans' || language === 'en-US';
    });
    var handler = $.VNImageRequestHandler.alloc.initWithURLOptions(
        $.NSURL.fileURLWithPath(argv[0]), $.NSDictionary.dictionary);
    if (!handler.performRequestsError([request], error)) {
        throw new Error(ObjC.unwrap(error[0].localizedDescription));
    }
    var lines = [];
    var results = request.results;
    for (var index = 0; index < results.count; index++) {
        var candidate = results.objectAtIndex(index).topCandidates(1).firstObject;
        lines.push(ObjC.unwrap(candidate.string));
    }
    return JSON.stringify(lines.join('\n'));
}
'''
        return ["/usr/bin/osascript", "-l", "JavaScript", "-e", script, image_path], env
    raise RuntimeError("文字识别需要 Windows 10 及以上或 macOS 10.15 及以上的系统 OCR 引擎。")


class ScreenshotOcrWorker(QThread):
    result_ready = pyqtSignal(str, str)

    def __init__(self, image, parent):
        super().__init__(parent)
        self.image = image.toImage()
        self._cancelled = threading.Event()
        self._process = None

    def cancel(self):
        self._cancelled.set()
        process = self._process
        if process is not None:
            try:
                process.kill()
            except OSError:
                pass

    def run(self):
        text, error = "", ""
        try:
            with tempfile.TemporaryDirectory(prefix="toolbox_ocr_") as directory:
                image_path = os.path.join(directory, "selection.png")
                if not self.image.save(image_path, "PNG"):
                    raise RuntimeError("无法写入识别图片，请检查系统临时目录的写入权限。")
                if self._cancelled.is_set():
                    return
                command, env = screenshot_ocr_command(image_path)
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                           env=env, **win_no_console())
                self._process = process
                if self._cancelled.is_set():
                    process.kill()
                try:
                    stdout, stderr = process.communicate(timeout=45)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()
                    raise RuntimeError("识别超过 45 秒，请缩小选区后重试。")
                if self._cancelled.is_set():
                    return
                if process.returncode:
                    raise RuntimeError(stderr.decode("utf-8", errors="replace").strip()[:200] or "系统 OCR 识别失败。")
                text = json.loads(stdout.decode("utf-8-sig")).strip()
        except (OSError, RuntimeError, ValueError) as exc:
            error = str(exc)
        finally:
            self._process = None
        if not self._cancelled.is_set():
            self.result_ready.emit(text, error)


class ScreenshotTextWindow(QDialog):
    def __init__(self, parent):
        super().__init__(parent, Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("识别文字")
        self.resize(380, 340)
        self.setMinimumSize(280, 220)
        self.setCursor(Qt.ArrowCursor)
        self.setStyleSheet("QDialog { background: #F6F8FC; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)
        hint = QLabel("可编辑文字，选中后按 Ctrl+C 复制；关闭此窗保留截图。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #697386; font-size: 12px;")
        layout.addWidget(hint)
        self.editor = QPlainTextEdit()
        self.editor.setFont(ui_font(12, 14))
        self.editor.setStyleSheet("QPlainTextEdit { background: white; color: #263449; border: 1px solid #DAE2ED; border-radius: 6px; padding: 8px; }")
        layout.addWidget(self.editor, 1)
        footer = QHBoxLayout()
        self.status = QLabel()
        self.status.setStyleSheet("color: #697386; font-size: 12px;")
        footer.addWidget(self.status, 1)
        self.copy_button = QPushButton("复制全部")
        self.copy_button.setFixedSize(96, 32)
        self.copy_button.setAutoDefault(False)
        self.copy_button.setFocusPolicy(Qt.NoFocus)
        self.copy_button.setCursor(Qt.PointingHandCursor)
        self.copy_button.setStyleSheet(_primary_btn())
        self.copy_button.clicked.connect(self._copy)
        footer.addWidget(self.copy_button)
        layout.addLayout(footer)
        self.editor.selectionChanged.connect(self._update_copy)
        self.editor.textChanged.connect(self._update_copy)

    def _update_copy(self):
        selected = self.editor.textCursor().hasSelection()
        self.copy_button.setText("复制选中" if selected else "复制全部")
        self.copy_button.setEnabled(bool(self.editor.toPlainText()))
        self.status.setText("选中后可单独复制" if selected else "%d 个字符" % len(self.editor.toPlainText()))

    def _copy(self):
        if self.editor.textCursor().hasSelection():
            self.editor.copy()
            self.status.setText("已复制选中文字")
        else:
            QApplication.clipboard().setText(self.editor.toPlainText())
            self.status.setText("已复制全部文字")

    def show_result(self, text, selection, toolbar):
        self.editor.setPlainText(text)
        self.show()
        screen = QApplication.screenAt(selection.center()) or QApplication.primaryScreen()
        area = screen.availableGeometry().adjusted(8, 8, -8, -8)
        size = self.frameGeometry().size()
        x = max(area.left(), min(selection.left(), area.right() - size.width() + 1))
        y = max(area.top(), min(selection.top(), area.bottom() - size.height() + 1))
        candidates = [QPoint(selection.right() + 13, y),
                      QPoint(selection.left() - size.width() - 12, y),
                      QPoint(x, selection.bottom() + 13),
                      QPoint(x, selection.top() - size.height() - 12)]
        position = next((point for point in candidates
                         if area.contains(QRect(point, size)) and not toolbar.intersects(QRect(point, size))),
                        QPoint(area.right() - size.width() + 1, y))
        self.move(position)
        self.raise_()
        self.activateWindow()
        self.editor.setFocus()


class CaptureOverlay(QWidget):
    captured = pyqtSignal(QPixmap, str, QRect)
    cancelled = pyqtSignal()
    ocr_requested = pyqtSignal(QPixmap)
    LOUPE_SOURCE = 15
    LOUPE_ZOOM = 10

    def __init__(self, desktop, geometry, auto_copy=False, selection=None):
        super().__init__(None, Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setGeometry(geometry)
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)
        self.desktop = desktop
        self._desktop_image = desktop.toImage()
        self._desktop_image.setDevicePixelRatio(1.0)
        self._pixel_pos = None
        self._pixel_point = QPoint()
        self._pixel_color = QColor()
        self._pixel_format = "HEX"
        self._ocr_busy = False
        self.ocr_result_window = None
        self._auto_copy = auto_copy
        self._selection = selection.intersected(self.rect()) if selection is not None else QRect()
        self._accepted = False
        self._origin = None
        self._drag = None
        self._start_rect = QRect()
        self._mode = "select"
        self._color = QColor("#F44336")
        self._width = 2
        self._annotations = []
        self._redo = []
        self._current = None
        self.toolbar = QFrame(self)
        self.toolbar.setObjectName("captureToolbar")
        self.toolbar.setStyleSheet(
            "QFrame#captureToolbar { background: #FFFFFF; border: 1px solid #D9E0EA; border-radius: 6px; }"
            "QPushButton { background: transparent; border: none; border-radius: 4px; }"
            "QPushButton:hover { background: #EDF4FF; }"
            "QPushButton:checked { background: #DCEBFF; }")
        layout = QVBoxLayout(self.toolbar)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        buttons = QHBoxLayout()
        buttons.setSpacing(2)
        self.tool_buttons = {}
        for name, tip in (("select", "移动 / 调整选区"), ("rectangle", "矩形"), ("arrow", "箭头"),
                          ("pen", "画笔"), ("text", "文字"), ("undo", "撤销 · Ctrl+Z"),
                          ("redo", "重做 · Ctrl+Shift+Z"), ("ocr", "识别文字 · Ctrl+O · 本地识别，旁窗查看并手动复制"),
                          ("save", "保存 PNG · Ctrl+S"), ("pin", "贴到桌面 · Ctrl+T"),
                          ("copy", "复制并完成 · Enter / Ctrl+C"), ("cancel", "取消 · Esc")):
            button = QPushButton()
            button.setFixedSize(30, 30)
            button.setIcon(self._icon(name))
            button.setIconSize(QSize(20, 20))
            button.setToolTip(tip)
            button.setFocusPolicy(Qt.NoFocus)
            button.setCursor(Qt.PointingHandCursor)
            if name in ("select", "rectangle", "arrow", "pen", "text"):
                button.setCheckable(True)
                button.clicked.connect(lambda checked, mode=name: self._set_mode(mode))
            elif name == "undo":
                button.clicked.connect(self._undo)
            elif name == "redo":
                button.clicked.connect(self._redo_annotation)
            elif name == "ocr":
                button.clicked.connect(self._start_ocr)
            elif name == "cancel":
                button.clicked.connect(self.close)
            else:
                button.clicked.connect(lambda checked, action=name: self._complete(action))
            self.tool_buttons[name] = button
            buttons.addWidget(button)
            if name in ("text", "redo"):
                separator = QFrame()
                separator.setFrameShape(QFrame.VLine)
                separator.setStyleSheet("color: #E3E8EF;")
                buttons.addWidget(separator)
        layout.addLayout(buttons)
        self.ocr_status = QLabel()
        self.ocr_status.setWordWrap(True)
        self.ocr_status.setMaximumWidth(380)
        self.ocr_status.setStyleSheet("color: #697386; font-size: 12px; padding: 2px 4px;")
        layout.addWidget(self.ocr_status)
        self.ocr_status.hide()
        self.palette_row = QWidget()
        palette_layout = QHBoxLayout(self.palette_row)
        palette_layout.setContentsMargins(2, 0, 2, 0)
        palette_layout.setSpacing(7)
        self.color_buttons = {}
        for value in ("#F44336", "#FFB020", "#27AE60", "#2684FF", "#FFFFFF", "#202B3D"):
            button = QPushButton()
            button.setFixedSize(18, 18)
            button.setFocusPolicy(Qt.NoFocus)
            button.setToolTip(value)
            button.clicked.connect(lambda checked, color=value: self._set_color(color))
            self.color_buttons[value] = button
            palette_layout.addWidget(button)
        palette_layout.addStretch()
        self.width_buttons = {}
        for width in (2, 4, 6):
            button = QPushButton()
            button.setFixedSize(24, 22)
            button.setCheckable(True)
            button.setChecked(width == self._width)
            button.setFocusPolicy(Qt.NoFocus)
            button.setToolTip("%s px" % width)
            icon = QPixmap(16, 16)
            icon.fill(Qt.transparent)
            painter = QPainter(icon)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#344054"))
            painter.drawEllipse(QPointF(8, 8), width / 2 + 1, width / 2 + 1)
            painter.end()
            button.setIcon(QIcon(icon))
            button.clicked.connect(lambda checked, value=width: self._set_width(value))
            self.width_buttons[width] = button
            palette_layout.addWidget(button)
        layout.addWidget(self.palette_row)
        self._set_color(self._color.name().upper())
        self._set_mode("select")
        self.toolbar.hide()
        if not self._selection.isEmpty():
            self._position_toolbar()
        self._update_pixel()
        self._pixel_timer = QTimer(self)
        self._pixel_timer.setInterval(40)
        self._pixel_timer.timeout.connect(self._update_pixel)
        self._pixel_timer.start()

    def _update_pixel(self, point=None):
        point = self.mapFromGlobal(QCursor.pos()) if point is None else point
        point = QPoint(min(max(point.x(), 0), self.width() - 1),
                       min(max(point.y(), 0), self.height() - 1))
        if point == self._pixel_pos:
            return
        self._pixel_pos = point
        dpr = self.desktop.devicePixelRatio()
        self._pixel_point = QPoint(min(round(point.x() * dpr), self._desktop_image.width() - 1),
                                   min(round(point.y() * dpr), self._desktop_image.height() - 1))
        self._pixel_color = self._desktop_image.pixelColor(self._pixel_point)
        self.update()

    def _pixel_value(self, fmt):
        if fmt == "HEX":
            return self._pixel_color.name().upper()
        return "rgb(%s, %s, %s)" % (self._pixel_color.red(), self._pixel_color.green(), self._pixel_color.blue())

    def _loupe_rect(self):
        if self.ocr_result_window is not None and self.ocr_result_window.isVisible():
            return QRect()
        if self._ocr_busy or self._mode != "select" or (self.toolbar.isVisible() and self.toolbar.geometry().contains(self._pixel_pos)):
            return QRect()
        screen = QApplication.screenAt(self.mapToGlobal(self._pixel_pos)) or QApplication.primaryScreen()
        area = screen.geometry().translated(-self.geometry().topLeft()).intersected(self.rect())
        width, height = 224, 254
        x, y = self._pixel_pos.x() + 24, self._pixel_pos.y() + 24
        if x + width > area.x() + area.width() - 8:
            x = self._pixel_pos.x() - width - 24
        if y + height > area.y() + area.height() - 8:
            y = self._pixel_pos.y() - height - 24
        x = max(area.x() + 8, min(x, area.x() + area.width() - width - 8))
        y = max(area.y() + 8, min(y, area.y() + area.height() - height - 8))
        box = QRect(x, y, width, height)
        if self.toolbar.isVisible() and box.intersects(self.toolbar.geometry()):
            above = self.toolbar.y() - height - 8
            below = self.toolbar.y() + self.toolbar.height() + 8
            if above >= area.y() + 8:
                box.moveTop(above)
            elif below + height <= area.y() + area.height() - 8:
                box.moveTop(below)
        return box

    def _draw_loupe(self, painter):
        box = self._loupe_rect()
        if box.isEmpty():
            return
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor("#CBD5E1"), 1))
        painter.setBrush(Qt.white)
        painter.drawRoundedRect(box.adjusted(0, 0, -1, -1), 6, 6)
        size = self.LOUPE_SOURCE * self.LOUPE_ZOOM
        grid = QRect(box.x() + (box.width() - size) // 2, box.y() + 8, size, size)
        half = self.LOUPE_SOURCE // 2
        sample = self._desktop_image.copy(self._pixel_point.x() - half, self._pixel_point.y() - half,
                                          self.LOUPE_SOURCE, self.LOUPE_SOURCE)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, False)
        painter.drawImage(grid, sample)
        painter.setPen(QColor(255, 255, 255, 60))
        for index in range(1, self.LOUPE_SOURCE):
            painter.drawLine(grid.x() + index * self.LOUPE_ZOOM, grid.y(),
                             grid.x() + index * self.LOUPE_ZOOM, grid.bottom())
            painter.drawLine(grid.x(), grid.y() + index * self.LOUPE_ZOOM,
                             grid.right(), grid.y() + index * self.LOUPE_ZOOM)
        center = QRect(grid.x() + half * self.LOUPE_ZOOM, grid.y() + half * self.LOUPE_ZOOM,
                       self.LOUPE_ZOOM, self.LOUPE_ZOOM)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(Qt.black, 1))
        painter.drawRect(center.adjusted(-1, -1, 0, 0))
        painter.setPen(QPen(Qt.white, 1))
        painter.drawRect(center.adjusted(0, 0, -1, -1))
        painter.setPen(QPen(QColor("#CBD5E1"), 1))
        painter.drawRect(grid.adjusted(0, 0, -1, -1))
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(self._pixel_color)
        painter.drawRoundedRect(QRect(box.x() + 12, box.y() + 172, 28, 32), 3, 3)
        painter.setPen(QColor("#202B3D"))
        font = ui_font(11, 13)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(box.x() + 50, box.y() + 184, self._pixel_value(self._pixel_format))
        painter.setFont(ui_font(10, 12))
        painter.setPen(QColor("#697386"))
        other = "RGB" if self._pixel_format == "HEX" else "HEX"
        painter.drawText(box.x() + 50, box.y() + 202, self._pixel_value(other))
        position = self.mapToGlobal(self._pixel_pos)
        painter.setFont(ui_font(9, 11))
        painter.drawText(box.x() + 12, box.y() + 224, "X: %s   Y: %s" % (position.x(), position.y()))
        painter.drawText(box.x() + 12, box.y() + 244, "C 复制%s并退出 · X 切换" % self._pixel_format)
        painter.restore()

    def _icon(self, name):
        image = QPixmap(20, 20)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor("#2684FF" if name in ("pin", "copy") else "#344054"), 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        if name == "select":
            painter.drawPolygon(QPolygonF([QPointF(4, 2), QPointF(15, 11), QPointF(10, 12), QPointF(8, 17)]))
        elif name == "rectangle":
            painter.drawRect(QRectF(3, 4, 14, 12))
        elif name == "arrow":
            painter.drawLine(3, 16, 16, 3)
            painter.drawLine(9, 3, 16, 3)
            painter.drawLine(16, 3, 16, 10)
        elif name == "pen":
            path = QPainterPath(QPointF(2, 15))
            path.cubicTo(6, 2, 8, 19, 12, 8)
            path.cubicTo(15, 1, 16, 5, 18, 4)
            painter.drawPath(path)
        elif name == "text":
            painter.drawLine(3, 4, 17, 4)
            painter.drawLine(10, 4, 10, 17)
            painter.drawLine(6, 17, 14, 17)
        elif name in ("undo", "redo"):
            if name == "redo":
                painter.translate(20, 0)
                painter.scale(-1, 1)
            painter.drawArc(QRectF(4, 5, 13, 12), -70 * 16, 230 * 16)
            painter.drawLine(3, 4, 3, 10)
            painter.drawLine(3, 10, 9, 10)
        elif name == "ocr":
            painter.drawLine(2, 6, 2, 2)
            painter.drawLine(2, 2, 6, 2)
            painter.drawLine(14, 2, 18, 2)
            painter.drawLine(18, 2, 18, 6)
            painter.drawLine(2, 14, 2, 18)
            painter.drawLine(2, 18, 6, 18)
            painter.drawLine(14, 18, 18, 18)
            painter.drawLine(18, 18, 18, 14)
            painter.setFont(ui_font(9, 11, True))
            painter.drawText(QRect(3, 3, 14, 14), Qt.AlignCenter, "A")
        elif name == "save":
            painter.drawRect(QRectF(3, 3, 14, 14))
            painter.drawRect(QRectF(6, 3, 8, 5))
            painter.drawRect(QRectF(6, 12, 8, 5))
        elif name == "pin":
            painter.drawLine(6, 3, 14, 3)
            painter.drawLine(7, 3, 7, 8)
            painter.drawLine(13, 3, 13, 8)
            painter.drawPolygon(QPolygonF([QPointF(7, 8), QPointF(4, 12), QPointF(16, 12), QPointF(13, 8)]))
            painter.drawLine(10, 12, 10, 18)
        elif name == "copy":
            painter.drawRect(QRectF(3, 3, 10, 11))
            painter.setBrush(Qt.white)
            painter.drawRect(QRectF(7, 7, 10, 11))
        elif name == "cancel":
            painter.drawLine(5, 5, 15, 15)
            painter.drawLine(5, 15, 15, 5)
        painter.end()
        return QIcon(image)

    def _set_mode(self, mode):
        self._mode = mode
        for name, button in self.tool_buttons.items():
            if button.isCheckable():
                button.setChecked(name == mode)
        self.palette_row.setVisible(mode != "select")
        self.setCursor(Qt.SizeAllCursor if mode == "select" and not self._selection.isEmpty() else Qt.CrossCursor)
        if not self._selection.isEmpty():
            self._position_toolbar()
        self.update()

    def _set_color(self, color):
        self._color = QColor(color)
        for value, button in self.color_buttons.items():
            border = "2px solid #2684FF" if value == color else "1px solid #CBD5E1"
            button.setStyleSheet("QPushButton { background: %s; border: %s; border-radius: 9px; }" % (value, border))

    def _set_width(self, width):
        self._width = width
        for value, button in self.width_buttons.items():
            button.setChecked(value == width)

    def _position_toolbar(self):
        self.toolbar.adjustSize()
        screen = QApplication.screenAt(self.mapToGlobal(self._selection.center())) or QApplication.primaryScreen()
        area = screen.geometry().translated(-self.geometry().topLeft()).intersected(self.rect())
        x = min(max(self._selection.x() + self._selection.width() - self.toolbar.width(), area.x() + 8),
                area.x() + area.width() - self.toolbar.width() - 8)
        y = self._selection.y() + self._selection.height() + 12
        if y + self.toolbar.height() > area.y() + area.height() - 8:
            y = self._selection.y() - self.toolbar.height() - 12
        y = max(area.y() + 8, min(y, area.y() + area.height() - self.toolbar.height() - 8))
        self.toolbar.move(x, y)
        self.toolbar.show()
        self.tool_buttons["undo"].setEnabled(bool(self._annotations) and not self._ocr_busy)
        self.tool_buttons["redo"].setEnabled(bool(self._redo) and not self._ocr_busy)

    def _set_ocr_busy(self, busy):
        self._ocr_busy = busy
        for name, button in self.tool_buttons.items():
            button.setEnabled(name == "cancel" or not busy)
        self.palette_row.setEnabled(not busy)
        self.setCursor(Qt.WaitCursor if busy else Qt.CrossCursor)
        self.update()

    def _start_ocr(self):
        if self._selection.isEmpty() or self._ocr_busy or self._origin is not None:
            return
        if self.ocr_result_window is not None:
            self.ocr_result_window.hide()
        self.ocr_status.setText("正在本地识别文字… · Esc 退出")
        self.ocr_status.show()
        self._set_ocr_busy(True)
        self._position_toolbar()
        self.ocr_requested.emit(crop_desktop(self.desktop, self._selection))

    def set_ocr_result(self, text, error):
        self._set_ocr_busy(False)
        if error or not text:
            self.ocr_status.setText("识别失败：" + error if error else "未识别到文字，请调整选区或放大原页面后重试。")
            self._position_toolbar()
            return
        self.ocr_status.setText("识别完成 · 在旁窗选中文字复制 · 可调整选区后再次识别")
        self._position_toolbar()
        if self.ocr_result_window is None:
            self.ocr_result_window = ScreenshotTextWindow(self)
            self.ocr_result_window.finished.connect(lambda _: self.update())
        self.ocr_result_window.show_result(
            text, self._selection.translated(self.geometry().topLeft()),
            QRect(self.toolbar.mapToGlobal(QPoint()), self.toolbar.size()))

    def _handles(self):
        rect = self._selection
        left, top = rect.x(), rect.y()
        right, bottom = left + rect.width(), top + rect.height()
        cx, cy = left + rect.width() // 2, top + rect.height() // 2
        return {"nw": QPoint(left, top), "n": QPoint(cx, top), "ne": QPoint(right, top),
                "e": QPoint(right, cy), "se": QPoint(right, bottom), "s": QPoint(cx, bottom),
                "sw": QPoint(left, bottom), "w": QPoint(left, cy)}

    def _hit_handle(self, point):
        if self._selection.isEmpty():
            return None
        distances = [(abs(point.x() - pos.x()) + abs(point.y() - pos.y()), name)
                     for name, pos in self._handles().items()
                     if abs(point.x() - pos.x()) <= 7 and abs(point.y() - pos.y()) <= 7]
        return min(distances)[1] if distances else None

    def _draw_annotations(self, painter):
        painter.save()
        painter.translate(self._selection.topLeft())
        painter.setClipRect(QRect(0, 0, self._selection.width(), self._selection.height()))
        painter.setRenderHint(QPainter.Antialiasing)
        items = self._annotations + ([self._current] if self._current else [])
        for item in items:
            points = item["points"]
            painter.setPen(QPen(item["color"], item["width"], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.setBrush(Qt.NoBrush)
            if item["tool"] == "rectangle":
                painter.drawRect(QRectF(points[0], points[-1]).normalized())
            elif item["tool"] == "arrow":
                start, end = points[0], points[-1]
                delta = end - start
                length = (delta.x() ** 2 + delta.y() ** 2) ** 0.5
                painter.drawLine(start, end)
                if length > 1:
                    tip = min(length, 10 + item["width"] * 2)
                    base = end - delta * (tip / length)
                    normal = QPointF(-delta.y(), delta.x()) * (tip * 0.45 / length)
                    painter.setBrush(item["color"])
                    painter.drawPolygon(QPolygonF([end, base + normal, base - normal]))
            elif item["tool"] == "pen":
                path = QPainterPath(points[0])
                for point in points[1:]:
                    path.lineTo(point)
                if len(points) == 1:
                    painter.drawPoint(points[0])
                else:
                    painter.drawPath(path)
            elif item["tool"] == "text":
                font = ui_font(14, 18)
                font.setPixelSize(16 + item["width"] * 2)
                painter.setFont(font)
                painter.drawText(points[0] + QPointF(0, painter.fontMetrics().ascent()), item["text"])
        painter.restore()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.desktop)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 105))
        if not self._selection.isEmpty():
            painter.save()
            painter.setClipRect(self._selection)
            painter.drawPixmap(0, 0, self.desktop)
            painter.restore()
            self._draw_annotations(painter)
            painter.setPen(QPen(QColor("#2684FF"), 1))
            painter.drawRect(self._selection.adjusted(0, 0, -1, -1))
            if self._mode == "select" and not self._ocr_busy:
                painter.setBrush(Qt.white)
                for point in self._handles().values():
                    painter.drawRect(QRect(point.x() - 3, point.y() - 3, 6, 6))
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        area = screen.geometry().translated(-self.geometry().topLeft())
        painter.setFont(ui_font(11, 13))
        text = "拖动框选 · C 复制颜色 · X 切换 · Esc 取消"
        if self._ocr_busy:
            text = "正在本地识别文字 · Esc 退出"
        elif not self._selection.isEmpty():
            dpr = self.desktop.devicePixelRatio()
            text = "%s × %s px · 拖动调整 · Enter 复制 · Ctrl+O 识别文字 · Ctrl+T 贴图" % (
                round(self._selection.width() * dpr), round(self._selection.height() * dpr))
        width = painter.fontMetrics().horizontalAdvance(text) + 24
        hint = QRect(area.x() + 16, area.y() + 16, width, 30)
        painter.fillRect(hint, QColor("#202B3D"))
        painter.setPen(Qt.white)
        painter.drawText(hint, Qt.AlignCenter, text)
        self._draw_loupe(painter)

    def mousePressEvent(self, event):
        if self._ocr_busy:
            if event.button() == Qt.RightButton:
                self.close()
            return
        if event.button() == Qt.RightButton:
            if self._selection.isEmpty() or self._auto_copy:
                self.close()
            else:
                self._selection = QRect()
                self._annotations.clear()
                self._redo.clear()
                self._current = None
                self._origin = self._drag = None
                self._set_mode("select")
                self.ocr_status.hide()
                if self.ocr_result_window is not None:
                    self.ocr_result_window.hide()
                self.toolbar.hide()
                self.update()
            return
        if event.button() != Qt.LeftButton:
            return
        point = event.pos()
        self._origin = point
        self._start_rect = QRect(self._selection)
        if self._mode != "select" and self._selection.contains(point):
            if self._mode == "text":
                self._origin = None
                text, ok = QInputDialog.getText(self, "添加文字", "文字内容：")
                if ok and text.strip():
                    self._annotations.append({"tool": "text", "points": [QPointF(point - self._selection.topLeft())],
                                              "color": QColor(self._color), "width": self._width, "text": text})
                    self._redo.clear()
                    self._position_toolbar()
                    self.update()
                return
            self._drag = "draw"
            relative = QPointF(point - self._selection.topLeft())
            self._current = {"tool": self._mode, "points": [relative], "color": QColor(self._color), "width": self._width}
        else:
            if self.ocr_result_window is not None:
                self.ocr_result_window.hide()
            self.ocr_status.hide()
            handle = self._hit_handle(point)
            if handle and self._mode == "select":
                self._drag = handle
            elif self._selection.contains(point):
                self._drag = "move"
            else:
                self._drag = "new"
                self._selection = QRect()
                self.ocr_status.hide()
                self._annotations.clear()
                self._redo.clear()
                self._set_mode("select")
            self.toolbar.hide()
        self.update()

    def mouseMoveEvent(self, event):
        point = QPoint(min(max(event.pos().x(), 0), self.width()), min(max(event.pos().y(), 0), self.height()))
        self._update_pixel(point)
        if self._ocr_busy:
            return
        if self._origin is None:
            handle = self._hit_handle(point) if self._mode == "select" else None
            cursors = {"nw": Qt.SizeFDiagCursor, "se": Qt.SizeFDiagCursor, "ne": Qt.SizeBDiagCursor,
                       "sw": Qt.SizeBDiagCursor, "n": Qt.SizeVerCursor, "s": Qt.SizeVerCursor,
                       "w": Qt.SizeHorCursor, "e": Qt.SizeHorCursor}
            cursor = cursors.get(handle, Qt.SizeAllCursor if self._mode == "select" and self._selection.contains(point) else Qt.CrossCursor)
            self.setCursor(cursor)
            return
        if self._drag == "new":
            self._selection = QRect(min(point.x(), self._origin.x()), min(point.y(), self._origin.y()),
                                    abs(point.x() - self._origin.x()), abs(point.y() - self._origin.y())).intersected(self.rect())
        elif self._drag == "move":
            delta = point - self._origin
            rect = self._start_rect
            dx = min(max(delta.x(), -rect.x()), self.width() - rect.x() - rect.width())
            dy = min(max(delta.y(), -rect.y()), self.height() - rect.y() - rect.height())
            self._selection = rect.translated(dx, dy)
        elif self._drag == "draw":
            relative = QPointF(point - self._selection.topLeft())
            if self._current["tool"] == "pen":
                self._current["points"].append(relative)
            else:
                self._current["points"] = [self._current["points"][0], relative]
        elif self._drag:
            rect = self._start_rect
            left, top, right, bottom = rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height()
            if "w" in self._drag:
                left = min(point.x(), right - 2)
            if "e" in self._drag:
                right = max(point.x(), left + 2)
            if "n" in self._drag:
                top = min(point.y(), bottom - 2)
            if "s" in self._drag:
                bottom = max(point.y(), top + 2)
            self._selection = QRect(left, top, right - left, bottom - top)
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or self._origin is None:
            return
        self.mouseMoveEvent(event)
        self._origin = None
        if self._drag == "draw":
            self._annotations.append(self._current)
            self._current = None
            self._redo.clear()
        self._drag = None
        if self._selection.width() < 2 or self._selection.height() < 2:
            self._selection = QRect()
            self.update()
            return
        if self._auto_copy:
            self._complete("copy")
        else:
            self._position_toolbar()
            self.update()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and self._mode == "select" and self._selection.contains(event.pos()):
            self._origin = self._drag = None
            self._complete("copy")
        else:
            self.mousePressEvent(event)

    def _undo(self):
        if self._annotations:
            self._redo.append(self._annotations.pop())
            self._position_toolbar()
            self.update()

    def _redo_annotation(self):
        if self._redo:
            self._annotations.append(self._redo.pop())
            self._position_toolbar()
            self.update()

    def result_image(self):
        image = crop_desktop(self.desktop, self._selection)
        painter = QPainter(image)
        painter.translate(-self._selection.topLeft())
        self._draw_annotations(painter)
        painter.end()
        return image

    def _complete(self, action):
        if self._ocr_busy or self._selection.isEmpty():
            return
        image = self.result_image()
        if action == "save" and not save_screenshot(self, image):
            return
        self._accepted = True
        self.captured.emit(image, action, self._selection.translated(self.geometry().topLeft()))
        self.close()

    def keyPressEvent(self, event):
        key, mods = event.key(), event.modifiers()
        if key == Qt.Key_Escape:
            self.close()
        elif self._ocr_busy:
            return
        elif mods & Qt.ControlModifier and key == Qt.Key_O:
            self._start_ocr()
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            self._complete("copy")
        elif mods & Qt.ControlModifier and key in (Qt.Key_C, Qt.Key_S, Qt.Key_T):
            self._complete({Qt.Key_C: "copy", Qt.Key_S: "save", Qt.Key_T: "pin"}[key])
        elif mods & Qt.ControlModifier and key == Qt.Key_Z:
            self._redo_annotation() if mods & Qt.ShiftModifier else self._undo()
        elif key == Qt.Key_C and mods == Qt.NoModifier:
            self._update_pixel()
            QApplication.clipboard().setText(self._pixel_value(self._pixel_format))
            self.close()
        elif key == Qt.Key_X and mods == Qt.NoModifier:
            self._pixel_format = "RGB" if self._pixel_format == "HEX" else "HEX"
            self.update()
        elif key in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down) and not self._selection.isEmpty():
            if self.ocr_result_window is not None:
                self.ocr_result_window.hide()
            self.ocr_status.hide()
            step = 10 if mods & Qt.ShiftModifier else 1
            dx = {Qt.Key_Left: -step, Qt.Key_Right: step}.get(key, 0)
            dy = {Qt.Key_Up: -step, Qt.Key_Down: step}.get(key, 0)
            rect = self._selection
            dx = min(max(dx, -rect.x()), self.width() - rect.x() - rect.width())
            dy = min(max(dy, -rect.y()), self.height() - rect.y() - rect.height())
            self._selection.translate(dx, dy)
            self._position_toolbar()
            self.update()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self._pixel_timer.stop()
        if self.ocr_result_window is not None:
            self.ocr_result_window.close()
        if not self._accepted:
            self.cancelled.emit()
        super().closeEvent(event)


class CustomCaptureDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("自定义截屏")
        self.resize(360, 260)
        layout = QVBoxLayout(self)
        hint = QLabel("按屏幕内的逻辑坐标指定截图区域，自动适配显示缩放。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #697386; font-size: 12px;")
        layout.addWidget(hint)
        form = QFormLayout()
        self.screen_combo = QComboBox()
        self.screens = QApplication.screens()
        for screen in self.screens:
            geo = screen.geometry()
            self.screen_combo.addItem("%s  (%s × %s)" % (screen.name(), geo.width(), geo.height()))
        self.x_edit, self.y_edit, self.width_edit, self.height_edit = (QSpinBox() for _ in range(4))
        for label, field in (("屏幕", self.screen_combo), ("左侧 X", self.x_edit), ("顶部 Y", self.y_edit),
                             ("宽度", self.width_edit), ("高度", self.height_edit)):
            form.addRow(label, field)
        layout.addLayout(form)
        self.screen_combo.currentIndexChanged.connect(self._update_limits)
        self.x_edit.valueChanged.connect(self._update_size_limits)
        self.y_edit.valueChanged.connect(self._update_size_limits)
        self._update_limits()
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("截屏")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_limits(self, *_):
        geo = self.screens[self.screen_combo.currentIndex()].geometry()
        self.x_edit.setRange(0, geo.width() - 1)
        self.y_edit.setRange(0, geo.height() - 1)
        self._update_size_limits()
        self.width_edit.setValue(min(640, self.width_edit.maximum()))
        self.height_edit.setValue(min(480, self.height_edit.maximum()))

    def _update_size_limits(self, *_):
        geo = self.screens[self.screen_combo.currentIndex()].geometry()
        self.width_edit.setRange(1, geo.width() - self.x_edit.value())
        self.height_edit.setRange(1, geo.height() - self.y_edit.value())

    def capture_rect(self):
        geo = self.screens[self.screen_combo.currentIndex()].geometry()
        return QRect(geo.x() + self.x_edit.value(), geo.y() + self.y_edit.value(),
                     self.width_edit.value(), self.height_edit.value())


class PinnedImageWindow(QWidget):
    closed = pyqtSignal(object)

    def __init__(self, image, origin=None):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("桌面贴图")
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAttribute(Qt.WA_StyledBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self.image = image
        self._drag_offset = None
        self._scale = 1.0
        self.preview = QLabel(self)
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setStyleSheet("PinnedImageWindow { background: #FFFFFF; border: 1px solid #82AFF0; }")
        self.close_btn = QPushButton("×", self)
        self.close_btn.setFixedSize(22, 22)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setToolTip("关闭贴图 · 双击图片仅隐藏")
        self.close_btn.setFocusPolicy(Qt.NoFocus)
        self.close_btn.setStyleSheet("QPushButton { color: #344054; background: #FFFFFF; border: 1px solid #D9E0EA; border-radius: 3px; font-size: 18px; } QPushButton:hover { color: white; background: #E5484D; border-color: #E5484D; }")
        self.close_btn.clicked.connect(self.close)
        self.info = QLabel(self)
        self.info.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.info.setStyleSheet("color: white; background: rgba(32, 43, 61, 190); border-radius: 3px; padding: 3px 6px; font-size: 11px;")
        if origin is not None:
            self._resize_image()
            # 图片在窗口内有 2px 边框，向左上偏移使像素与原屏幕位置重合。
            self.move(origin - QPoint(2, 2))
        else:
            screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
            area = screen.availableGeometry()
            logical = image.size() / image.devicePixelRatio()
            self._scale = min(1.0, area.width() * 0.75 / logical.width(), area.height() * 0.75 / logical.height())
            self._resize_image()
            position = QCursor.pos() + QPoint(18, 18)
            self.move(min(max(position.x(), area.x()), area.x() + area.width() - self.width()),
                      min(max(position.y(), area.y()), area.y() + area.height() - self.height()))
        self.close_btn.hide()
        self.info.hide()

    def _resize_image(self):
        logical = self.image.size() / self.image.devicePixelRatio()
        self.resize(max(32, round(logical.width() * self._scale)) + 4,
                    max(32, round(logical.height() * self._scale)) + 4)
        self._update_info()

    def _update_info(self):
        self.info.setText("%s%% · 透明度 %s%%" % (round(self._scale * 100), round((1 - self.windowOpacity()) * 100)))
        self.info.adjustSize()
        self.info.move(5, max(5, self.height() - self.info.height() - 5))

    def resizeEvent(self, event):
        self.preview.setGeometry(self.rect().adjusted(2, 2, -2, -2))
        dpr = self.devicePixelRatioF()
        pixmap = self.image.scaled(self.preview.size() * dpr, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        pixmap.setDevicePixelRatio(dpr)
        self.preview.setPixmap(pixmap)
        self.close_btn.move(self.width() - 26, 4)
        self.close_btn.raise_()
        self.info.raise_()
        self._update_info()
        super().resizeEvent(event)

    def enterEvent(self, event):
        self.close_btn.show()
        self.info.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.close_btn.hide()
        self.info.hide()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setFocus()
            self._drag_offset = event.globalPos() - self.pos()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = None
            self.hide()

    def _zoom(self, scale, anchor=None):
        anchor = QPointF(anchor if anchor is not None else self.rect().center())
        global_anchor = QPointF(self.pos()) + anchor
        ratio_x, ratio_y = anchor.x() / self.width(), anchor.y() / self.height()
        self._scale = min(5.0, max(0.1, scale))
        self._resize_image()
        self.move(round(global_anchor.x() - self.width() * ratio_x), round(global_anchor.y() - self.height() * ratio_y))

    def _set_opacity(self, value):
        self.setWindowOpacity(min(1.0, max(0.1, value)))
        self._update_info()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta:
            if event.modifiers() & Qt.ControlModifier:
                self._set_opacity(self.windowOpacity() + (0.1 if delta > 0 else -0.1))
            else:
                self._zoom(self._scale * (1.1 if delta > 0 else 1 / 1.1), event.pos())
        event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("复制图片\tCtrl+C", lambda: QApplication.clipboard().setImage(self.image.toImage()))
        menu.addAction("保存 PNG\tCtrl+S", lambda: save_screenshot(self, self.image))
        menu.addAction("原始大小\t0", lambda: self._zoom(1.0))
        opacity = menu.addMenu("不透明度 · Ctrl+滚轮")
        for percent in (100, 75, 50, 25):
            action = opacity.addAction("%s%%" % percent)
            action.setCheckable(True)
            action.setChecked(abs(self.windowOpacity() - percent / 100) < 0.01)
            action.triggered.connect(lambda checked, value=percent: self._set_opacity(value / 100))
        menu.addSeparator()
        menu.addAction("隐藏贴图\t双击 / Esc", self.hide)
        menu.addAction("关闭贴图\tDelete", self.close)
        menu.exec_(event.globalPos())

    def keyPressEvent(self, event):
        key, mods = event.key(), event.modifiers()
        if key == Qt.Key_Escape:
            self.hide()
        elif key == Qt.Key_Delete:
            self.close()
        elif key == Qt.Key_C and mods & Qt.ControlModifier:
            QApplication.clipboard().setImage(self.image.toImage())
        elif key == Qt.Key_S and mods & Qt.ControlModifier:
            save_screenshot(self, self.image)
        elif key == Qt.Key_0 and not mods:
            self._zoom(1.0)
        elif key in (Qt.Key_Plus, Qt.Key_Equal, Qt.Key_Minus):
            increase = key != Qt.Key_Minus
            if mods & Qt.ControlModifier:
                self._set_opacity(self.windowOpacity() + (0.1 if increase else -0.1))
            else:
                self._zoom(self._scale * (1.1 if increase else 1 / 1.1))
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self.closed.emit(self)
        super().closeEvent(event)


class ScreenshotTool(QObject):
    def __init__(self, main):
        super().__init__(main)
        self.main = main
        self.overlay = None
        self.pins = []
        self._ocr_worker = None
        self._ocr_workers = []
        self._restore_windows = []
        self._auto_copy = False
        self._rectangle = None
        self._prev_pid = None
        self._prev_hwnd = None
        self._quitting = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._take_capture)
        QApplication.instance().aboutToQuit.connect(self.stop)

    def capture(self):
        self._begin_capture(False)

    def capture_copy(self):
        self._begin_capture(True)

    def custom_capture(self):
        if self.overlay is not None or self._timer.isActive():
            return
        dialog = CustomCaptureDialog(self.main)
        if dialog.exec_() == QDialog.Accepted:
            self._begin_capture(False, dialog.capture_rect())

    def _begin_capture(self, auto_copy, rectangle=None):
        if self.overlay is not None:
            self.overlay.close()
            return
        if self._timer.isActive():
            return
        self._prev_pid = _mac_frontmost_pid()
        if platform.system() == "Windows":
            ctypes.windll.user32.GetForegroundWindow.restype = ctypes.c_void_p
            self._prev_hwnd = ctypes.windll.user32.GetForegroundWindow()
        self._auto_copy = auto_copy
        self._rectangle = rectangle
        self._restore_windows = [self.main] if self.main.isVisible() else []
        for window in self._restore_windows:
            window.hide()
        self._timer.start(180)

    def _take_capture(self):
        try:
            desktop, geometry = capture_desktop()
        except (OSError, ValueError) as exc:
            self._restore()
            QMessageBox.warning(self.main, "截图失败", str(exc))
            return
        selection = self._rectangle.translated(-geometry.topLeft()) if self._rectangle is not None else None
        self.overlay = CaptureOverlay(desktop, geometry, self._auto_copy, selection)
        self.overlay.captured.connect(self._finish_capture)
        self.overlay.cancelled.connect(self._cancel_capture)
        self.overlay.ocr_requested.connect(self._recognize_text)
        self.overlay.show()
        self.overlay.raise_()
        self.overlay.activateWindow()
        self.overlay.setFocus()

    def _restore(self):
        windows, self._restore_windows = self._restore_windows, []
        if not self._quitting:
            for window in windows:
                nonactivating = window.testAttribute(Qt.WA_ShowWithoutActivating)
                window.setAttribute(Qt.WA_ShowWithoutActivating)
                window.show()
                window.setAttribute(Qt.WA_ShowWithoutActivating, nonactivating)
            if self._prev_pid:
                _mac_reactivate(self._prev_pid)
            if self._prev_hwnd:
                user32 = ctypes.windll.user32
                user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
                user32.SetForegroundWindow(self._prev_hwnd)
        self._prev_pid = None
        self._prev_hwnd = None

    def _recognize_text(self, image):
        worker = ScreenshotOcrWorker(image, self)
        self._ocr_worker = worker
        self._ocr_workers.append(worker)
        worker.result_ready.connect(self._ocr_result)
        worker.finished.connect(self._ocr_worker_finished)
        worker.start()

    def _ocr_result(self, text, error):
        if self.sender() is self._ocr_worker and self.overlay is not None:
            self._ocr_worker = None
            self.overlay.set_ocr_result(text, error)

    def _ocr_worker_finished(self):
        worker = self.sender()
        self._ocr_workers.remove(worker)
        worker.deleteLater()

    def _cancel_ocr(self):
        worker, self._ocr_worker = self._ocr_worker, None
        if worker is not None:
            worker.cancel()

    def _cancel_capture(self):
        self._cancel_ocr()
        self.overlay = None
        self._restore()

    def _finish_capture(self, image, action, rectangle):
        self.overlay = None
        self._restore()
        if action in ("copy", "pin"):
            QApplication.clipboard().setImage(image.toImage())
        if action == "pin":
            self.pin(image, rectangle.topLeft())

    def paste(self):
        clipboard = QApplication.clipboard().mimeData()
        image = QApplication.clipboard().pixmap() if clipboard and clipboard.hasImage() else QPixmap()
        if image.isNull() and clipboard and clipboard.hasUrls():
            urls = clipboard.urls()
            if len(urls) == 1 and urls[0].isLocalFile():
                image = QPixmap(urls[0].toLocalFile())
        if image.isNull():
            QMessageBox.information(self.main, "贴图", "剪贴板中没有图片，请先复制一张图片或截屏")
            return
        self.pin(image)

    def pin(self, image, origin=None):
        pin = PinnedImageWindow(image, origin)
        pin.closed.connect(self._remove_pin)
        self.pins.append(pin)
        pin.show()
        pin.raise_()
        return pin

    def _remove_pin(self, pin):
        self.pins.remove(pin)

    def toggle_pins(self):
        show = not any(pin.isVisible() for pin in self.pins)
        for pin in self.pins:
            pin.setVisible(show)

    def stop(self):
        self._quitting = True
        self._timer.stop()
        if self.overlay is not None:
            self.overlay.close()
            self.overlay = None
        for pin in list(self.pins):
            pin.close()
        for worker in list(self._ocr_workers):
            worker.cancel()
        for worker in list(self._ocr_workers):
            worker.wait()
        self._restore_windows.clear()


class ColorWindow(QMainWindow):
    FORMATS = ["HEX", "RGB", "RGBA", "HSL", "HSV", "CMYK"]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("颜色转换")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self._rgb = None
        self._alpha = 255
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        # ---- input row ----
        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(10)

        in_label = QLabel("颜色输入")
        in_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        in_label.setStyleSheet("color: #333333;")
        form.addWidget(in_label, 0, 0)

        self.color_edit = QLineEdit()
        self.color_edit.setPlaceholderText("#FF8800 / #F80 / rgb(255,136,0) / hsl(36,100%,50%) / orange …")
        self.color_edit.setStyleSheet("""
            QLineEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 6px 8px;
                font-family: "Menlo", "Consolas", monospace; font-size: 13px; }
            QLineEdit:focus { border-color: #1A73E8; }
        """)
        self.color_edit.textChanged.connect(self.convert)
        form.addWidget(self.color_edit, 0, 1, 1, 2)

        pick_btn = QPushButton("调色板")
        pick_btn.setFixedSize(70, 30)
        pick_btn.setCursor(QCursor(Qt.PointingHandCursor))
        pick_btn.setStyleSheet("""
            QPushButton { color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #E0E0E0; }
        """)
        pick_btn.clicked.connect(self.do_pick)
        form.addWidget(pick_btn, 0, 3)

        clear_btn = QPushButton("清空")
        clear_btn.setFixedSize(70, 30)
        clear_btn.setCursor(QCursor(Qt.PointingHandCursor))
        clear_btn.setStyleSheet("""
            QPushButton { color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #E0E0E0; }
        """)
        clear_btn.clicked.connect(self.do_clear)
        form.addWidget(clear_btn, 0, 4)

        layout.addLayout(form)

        # ---- preview + status ----
        preview_row = QHBoxLayout()
        self.swatch = QFrame()
        self.swatch.setFixedSize(48, 48)
        self.swatch.setStyleSheet("border: 1px solid #D0D0D0; border-radius: 6px; background: #FFFFFF;")
        preview_row.addWidget(self.swatch)

        self.status_label = QLabel("输入任意颜色字符串，自动转换为所有格式。")
        self.status_label.setFont(QFont("PingFang SC", 11))
        self.status_label.setStyleSheet("color: #999999;")
        self.status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        preview_row.addWidget(self.status_label, 1)
        layout.addLayout(preview_row)

        # ---- format outputs ----
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        self.value_edits = {}
        for row, fmt in enumerate(self.FORMATS):
            name = QLabel(fmt)
            name.setFont(QFont("Menlo", 12, QFont.Bold))
            name.setStyleSheet("color: #333333;")
            name.setFixedWidth(56)
            grid.addWidget(name, row, 0)

            val = QLineEdit()
            val.setReadOnly(True)
            val.setStyleSheet("""
                QLineEdit { border: none; border-bottom: 1px solid #E0E0E0; padding: 4px 6px;
                    font-family: "Menlo", "Consolas", monospace; font-size: 13px; color: #1A73E8; background: #FFFFFF; }
            """)
            grid.addWidget(val, row, 1)
            self.value_edits[fmt] = val

            copy_btn = QPushButton("复制")
            copy_btn.setFixedSize(56, 26)
            copy_btn.setCursor(QCursor(Qt.PointingHandCursor))
            copy_btn.setStyleSheet("""
                QPushButton { color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0; border-radius: 4px; font-size: 11px; }
                QPushButton:hover { background: #E0E0E0; }
            """)
            copy_btn.clicked.connect(lambda _=False, f=fmt: self.copy_value(f))
            grid.addWidget(copy_btn, row, 2)

        layout.addLayout(grid)
        layout.addStretch()

    def set_status(self, text, ok=True):
        self.status_label.setText(text)
        self.status_label.setStyleSheet("color: %s;" % ("#188038" if ok else "#D93025"))

    def do_clear(self):
        self.color_edit.blockSignals(True)
        self.color_edit.clear()
        self.color_edit.blockSignals(False)
        for fmt in self.FORMATS:
            self.value_edits[fmt].setText("")
        self._rgb = None
        self.swatch.setStyleSheet("border: 1px solid #D0D0D0; border-radius: 6px; background: #FFFFFF;")
        self.status_label.setText("输入任意颜色字符串，自动转换为所有格式。")
        self.status_label.setStyleSheet("color: #999999;")

    def do_pick(self):
        init = QColor(*self._rgb) if self._rgb else QColor("#FFFFFF")
        color = QColorDialog.getColor(init, self, "选择颜色")
        if color.isValid():
            self.color_edit.setText(color.name().upper())

    def copy_value(self, fmt):
        text = self.value_edits[fmt].text()
        if text:
            QApplication.clipboard().setText(text)
            self.set_status(f"已复制 {fmt}: {text}", ok=True)

    # ---- parsing ----
    @staticmethod
    def _num(tok):
        return float(tok[:-1]) if tok.endswith("%") else float(tok)

    def _parse(self, s):
        s = s.strip()
        if not s:
            return None
        m = re.match(r"(rgba?|hsla?|hsva?)\s*\((.+)\)", s, re.I)
        if m:
            kind = m.group(1).lower()
            inner = m.group(2).replace("/", ",")
            toks = [t for t in re.split(r"[,\s]+", inner.strip()) if t]
            nums = [self._num(t.rstrip("deg")) for t in toks]
            if kind.startswith("rgb"):
                if len(nums) < 3:
                    return None
                r = nums[0] * 255 / 100 if "%" in toks[0] else nums[0]
                g = nums[1] * 255 / 100 if "%" in toks[1] else nums[1]
                b = nums[2] * 255 / 100 if "%" in toks[2] else nums[2]
                a = self._alpha_from(toks[3] if len(toks) > 3 else None)
                return self._clamp_rgb(r, g, b), a
            # hsl / hsv
            if len(nums) < 3:
                return None
            h = nums[0] % 360
            sat = nums[1] / 100.0
            lit = nums[2] / 100.0
            a = self._alpha_from(toks[3] if len(toks) > 3 else None)
            if kind.startswith("hsl"):
                r, g, b = colorsys.hls_to_rgb(h / 360.0, lit, sat)
            else:
                r, g, b = colorsys.hsv_to_rgb(h / 360.0, sat, lit)
            return self._clamp_rgb(r * 255, g * 255, b * 255), a

        qc = QColor(s)
        if qc.isValid() and qc.name() != "#000000":
            return (qc.red(), qc.green(), qc.blue()), qc.alpha()
        if s.lower() == "black" or s.replace("#", "").lower() in ("000", "000000"):
            return (0, 0, 0), qc.alpha() if qc.isValid() else 255
        return None

    @staticmethod
    def _alpha_from(tok):
        if tok is None:
            return 255
        val = float(tok[:-1]) / 100.0 if tok.endswith("%") else float(tok)
        if val > 1.0:
            val = val / 255.0
        return int(max(0.0, min(1.0, val)) * 255)

    @staticmethod
    def _clamp_rgb(r, g, b):
        def c(x):
            return int(max(0, min(255, round(x))))
        return c(r), c(g), c(b)

    # ---- conversion output ----
    def convert(self):
        s = self.color_edit.text().strip()
        if not s:
            self.do_clear()
            return
        parsed = self._parse(s)
        if not parsed:
            self.set_status(f"无法识别: {s}", ok=False)
            for fmt in self.FORMATS:
                self.value_edits[fmt].setText("")
            return
        rgb, alpha = parsed
        self._rgb = rgb
        self._alpha = alpha
        r, g, b = rgb
        self.swatch.setStyleSheet(
            "border: 1px solid #D0D0D0; border-radius: 6px; background: rgb(%d,%d,%d);" % (r, g, b))

        h01, l01, s01 = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
        h_deg = round(h01 * 360) % 360
        hsl_s = round(s01 * 100)
        hsl_l = round(l01 * 100)

        hh01, sv01, vv01 = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        hsv_h = round(hh01 * 360) % 360
        hsv_s = round(sv01 * 100)
        hsv_v = round(vv01 * 100)

        rn, gn, bn = r / 255.0, g / 255.0, b / 255.0
        k = 1 - max(rn, gn, bn)
        if k >= 1.0:
            c, mg, y = 0, 0, 0
        else:
            c = (1 - rn - k) / (1 - k)
            mg = (1 - gn - k) / (1 - k)
            y = (1 - bn - k) / (1 - k)
        cmyk = (round(c * 100), round(mg * 100), round(y * 100), round(k * 100))

        a_norm = round(alpha / 255.0, 3)
        hex_main = "#%02X%02X%02X" % (r, g, b)
        hex_val = hex_main if alpha == 255 else "#%02X%02X%02X%02X" % (r, g, b, alpha)

        self.value_edits["HEX"].setText(hex_val)
        self.value_edits["RGB"].setText("rgb(%d, %d, %d)" % (r, g, b))
        self.value_edits["RGBA"].setText("rgba(%d, %d, %d, %g)" % (r, g, b, a_norm))
        self.value_edits["HSL"].setText("hsl(%d, %d%%, %d%%)" % (h_deg, hsl_s, hsl_l))
        self.value_edits["HSV"].setText("hsv(%d, %d%%, %d%%)" % (hsv_h, hsv_s, hsv_v))
        self.value_edits["CMYK"].setText("cmyk(%d%%, %d%%, %d%%, %d%%)" % cmyk)
        self.set_status(f"解析成功 → {hex_val}", ok=True)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class CronWindow(QMainWindow):
    CRON_EXAMPLES = [
        ("* * * * *", "每分钟"),
        ("*/1 * * * *", "每分钟(显式步长)"),
        ("*/5 * * * *", "每 5 分钟"),
        ("*/10 * * * *", "每 10 分钟"),
        ("*/15 * * * *", "每 15 分钟"),
        ("*/30 * * * *", "每 30 分钟"),
        ("0 * * * *", "每小时整点"),
        ("30 * * * *", "每小时 30 分"),
        ("0 */2 * * *", "每 2 小时整点"),
        ("0 */6 * * *", "每 6 小时整点"),
        ("0 0 * * *", "每天 00:00"),
        ("0 8 * * *", "每天 08:00"),
        ("30 8 * * *", "每天 08:30"),
        ("0 12 * * *", "每天 12:00"),
        ("0 18 * * *", "每天 18:00"),
        ("0 9-18 * * *", "每天 9-18 点整点"),
        ("0 9 * * 1-5", "工作日 09:00"),
        ("0 0 * * 0", "每周日 00:00"),
        ("0 0 * * 1", "每周一 00:00"),
        ("0 12 * * 6", "每周六 12:00"),
        ("0 0 1 * *", "每月 1 号 00:00"),
        ("0 0 15 * *", "每月 15 号 00:00"),
        ("0 0 1 1 *", "每年 1 月 1 日 00:00"),
        ("30 4 1,15 * *", "每月 1、15 号 04:30"),
        ("30 4 * 1,6 *", "1 月和 6 月的 04:30"),
        ("*/10 9-18 * * 1-5", "工作日 9-18 点每 10 分钟"),
        ("0 */30 9-17 * * *", "9-17 点每 30 分钟"),
        ("0 0 1 1,7 *", "1 月和 7 月 1 号 00:00"),
        ("0 0,30 * * * *", "每小时的 0 分和 30 分"),
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cron 表达式")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(10)

        expr_label = QLabel("Cron 表达式")
        expr_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        expr_label.setStyleSheet("color: #333333;")
        form.addWidget(expr_label, 0, 0)

        self.expr_edit = QLineEdit()
        self.expr_edit.setPlaceholderText("分 时 日 月 周   (可含秒: 秒 分 时 日 月 周)，例如  0 9 * * 1-5")
        self.expr_edit.setStyleSheet("""
            QLineEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 6px 8px;
                font-family: "Menlo", "Consolas", "PingFang SC", monospace; font-size: 13px; }
            QLineEdit:focus { border-color: #1A73E8; }
        """)
        self.expr_edit.returnPressed.connect(self.do_view)
        form.addWidget(self.expr_edit, 0, 1, 1, 3)

        cnt_label = QLabel("未来次数")
        cnt_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        cnt_label.setStyleSheet("color: #333333;")
        form.addWidget(cnt_label, 1, 0)

        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 1000)
        self.count_spin.setValue(10)
        self.count_spin.setFixedWidth(90)
        self.count_spin.setStyleSheet("""
            QSpinBox { border: 1px solid #D0D0D0; border-radius: 4px; padding: 3px;
                font-family: "PingFang SC", monospace; font-size: 13px; }
        """)
        self.count_spin.editingFinished.connect(self.do_view)
        form.addWidget(self.count_spin, 1, 1, Qt.AlignLeft)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        example_btn = QPushButton("示例")
        example_btn.setFixedSize(70, 30)
        example_btn.setCursor(QCursor(Qt.PointingHandCursor))
        example_btn.setStyleSheet("""
            QPushButton { color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #E0E0E0; }
        """)
        example_btn.clicked.connect(self.do_example)
        btn_row.addWidget(example_btn)

        clear_btn = QPushButton("清空")
        clear_btn.setFixedSize(70, 30)
        clear_btn.setCursor(QCursor(Qt.PointingHandCursor))
        clear_btn.setStyleSheet("""
            QPushButton { color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #E0E0E0; }
        """)
        clear_btn.clicked.connect(self.do_clear)
        btn_row.addWidget(clear_btn)

        btn_row.addStretch()

        view_btn = QPushButton("查看计划")
        view_btn.setFixedSize(90, 30)
        view_btn.setCursor(QCursor(Qt.PointingHandCursor))
        view_btn.setStyleSheet("""
            QPushButton { color: #FFFFFF; background: #1A73E8; border: none; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #1557B0; }
        """)
        view_btn.clicked.connect(self.do_view)
        btn_row.addWidget(view_btn)

        form.addLayout(btn_row, 1, 2, 1, 2)

        preset_label = QLabel("常用表达式")
        preset_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        preset_label.setStyleSheet("color: #333333;")
        form.addWidget(preset_label, 2, 0)

        self.preset_combo = QComboBox()
        self.preset_combo.addItem("— 选择常用表达式 —", None)
        for expr, desc in self.CRON_EXAMPLES:
            self.preset_combo.addItem(f"{desc}   ·   {expr}", expr)
        self.preset_combo.currentIndexChanged.connect(self.on_preset_selected)
        self.preset_combo.setStyleSheet(_combo_style(size=13, mono=True))
        form.addWidget(self.preset_combo, 2, 1, 1, 3)

        layout.addLayout(form)

        self.status_label = QLabel("输入表达式后点击“查看计划”，将列出当前时间之后的执行时间点。")
        self.status_label.setFont(QFont("PingFang SC", 11))
        self.status_label.setStyleSheet("color: #999999;")
        self.status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.status_label)

        self.output_text = QPlainTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("""
            QPlainTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
                font-family: "Menlo", "Consolas", "PingFang SC", monospace; font-size: 13px; background: #FAFAFA; }
        """)

        self.help_text = QTextEdit()
        self.help_text.setReadOnly(True)
        self.help_text.setStyleSheet("""
            QTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 10px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; background: #FFFFFF; }
        """)
        self.help_text.setHtml(self.build_help_html())

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::tab-bar { alignment: left; }
            QTabBar::tab { font-family: "PingFang SC"; font-size: 12px; padding: 6px 14px;
                color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0; border-bottom: none;
                border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { color: #1A73E8; background: #FFFFFF; }
            QTabWidget::pane { border: 1px solid #D0D0D0; border-radius: 4px; }
        """)
        tabs.addTab(self.output_text, "执行计划")
        tabs.addTab(self.help_text, "书写规范")
        layout.addWidget(tabs, 1)

        self._example_idx = 0

    def build_help_html(self):
        rows = []
        for expr, desc in self.CRON_EXAMPLES:
            rows.append(
                "<tr><td><code>%s</code></td><td>%s</td></tr>" % (expr.replace(" ", "&nbsp;"), desc)
            )
        examples_table = "\n".join(rows)
        return """
<div style="font-size:13px; color:#333333; line-height:1.55;">
<p style="margin-bottom:6px;"><b style="color:#1A73E8;">一、字段结构</b></p>
<p>Cron 表达式由 <b>5 个字段</b>（标准 crontab）或 <b>6 个字段</b>（含秒，Spring/Quartz 风格）组成，用空格分隔：</p>
<pre style="background:#F5F7FA; padding:8px; border:1px solid #E0E0E0; font-family:Menlo,Consolas,monospace; font-size:12px;">
 ┌───────────── 分       (0-59)
 │  ┌────────── 时       (0-23)
 │  │  ┌─────── 日       (1-31)   一个月中的哪天
 │  │  │  ┌──── 月       (1-12)
 │  │  │  │  ┌─ 周       (0-6)    0=周日，也接受 7
 *  *  *  *  *          ← 标准 5 字段
 秒 分 时 日 月 周       ← 6 字段时，秒在最前面 (0-59)
</pre>
<p style="margin-top:10px; margin-bottom:6px;"><b style="color:#1A73E8;">二、每个位置的含义</b></p>
<table width="100%%" cellspacing="0" cellpadding="4" style="border:1px solid #D0D0D0; border-collapse:collapse;">
<tr style="background:#F5F7FA;"><th align="left">位置</th><th align="left">字段</th><th align="left">取值范围</th><th align="left">含义</th></tr>
<tr><td>1</td><td>秒（可选）</td><td>0-59</td><td>仅在 6 字段格式中出现，位于最前</td></tr>
<tr><td>1/2</td><td>分 minute</td><td>0-59</td><td>小时中的第几分钟</td></tr>
<tr><td>2/3</td><td>时 hour</td><td>0-23</td><td>一天中的第几小时（24 小时制）</td></tr>
<tr><td>3/4</td><td>日 day-of-month</td><td>1-31</td><td>一个月中的哪一天</td></tr>
<tr><td>4/5</td><td>月 month</td><td>1-12</td><td>一年中的哪个月</td></tr>
<tr><td>5/6</td><td>周 day-of-week</td><td>0-7</td><td>星期几，0 与 7 均表示周日，1=周一</td></tr>
</table>
<p style="margin-top:10px; margin-bottom:6px;"><b style="color:#1A73E8;">三、特殊字符</b></p>
<table width="100%%" cellspacing="0" cellpadding="4" style="border:1px solid #D0D0D0; border-collapse:collapse;">
<tr style="background:#F5F7FA;"><th align="left">字符</th><th align="left">名称</th><th align="left">说明</th><th align="left">示例</th></tr>
<tr><td><code>*</code></td><td>任意</td><td>该字段所有允许值都匹配</td><td><code>* * * * *</code> 每分钟</td></tr>
<tr><td><code>,</code></td><td>列表</td><td>枚举多个离散值</td><td><code>1,3,5</code> → 1、3、5</td></tr>
<tr><td><code>-</code></td><td>区间</td><td>从 a 到 b 的连续值</td><td><code>9-18</code> → 9 到 18</td></tr>
<tr><td><code>/</code></td><td>步长</td><td>按间隔取值，常与 * 或区间搭配</td><td><code>*/10</code>、<code>0/30</code>、<code>1-10/2</code></td></tr>
<tr><td><code>?</code></td><td>不指定</td><td>仅用于“日/周”，等同 *（避免冲突）</td><td><code>0 0 ? * 1</code></td></tr>
</table>
<p style="margin-top:10px; margin-bottom:6px;"><b style="color:#1A73E8;">四、注意事项</b></p>
<ul style="margin-top:0; padding-left:20px;">
<li>“日”和“周”如果<b>同时被限定</b>（都不是 <code>*</code>），按标准 cron 取<b>“或”</b>：任一命中即执行。</li>
<li>周字段 0 和 7 都表示周日；1=周一 … 6=周六。</li>
<li>本工具按<b>分钟</b>粒度计算（6 字段时秒位生效），最多向后查找 5 年。</li>
</ul>
<p style="margin-top:10px; margin-bottom:6px;"><b style="color:#1A73E8;">五、常用表达式速查</b></p>
<table width="100%%" cellspacing="0" cellpadding="4" style="border:1px solid #D0D0D0; border-collapse:collapse;">
<tr style="background:#F5F7FA;"><th align="left">表达式</th><th align="left">含义</th></tr>
%s
</table>
</div>
""" % examples_table

    def set_status(self, text, ok=True):
        self.status_label.setText(text)
        self.status_label.setStyleSheet("color: %s;" % ("#188038" if ok else "#D93025"))

    def do_clear(self):
        self.expr_edit.clear()
        self.output_text.setPlainText("")
        self.status_label.setText("输入表达式后点击“查看计划”，将列出当前时间之后的执行时间点。")
        self.status_label.setStyleSheet("color: #999999;")

    def on_preset_selected(self, index):
        expr = self.preset_combo.itemData(index)
        if not expr:
            return
        self.expr_edit.setText(expr)
        self.do_view()

    def do_example(self):
        expr, desc = self.CRON_EXAMPLES[self._example_idx % len(self.CRON_EXAMPLES)]
        self._example_idx += 1
        self.expr_edit.setText(expr)
        self.do_view(extra=desc)

    def do_view(self, extra=None):
        expr = self.expr_edit.text().strip()
        if not expr:
            self.output_text.setPlainText("")
            self.status_label.setText("请输入 Cron 表达式。")
            self.status_label.setStyleSheet("color: #999999;")
            return
        try:
            plan = self.compute(expr, self.count_spin.value())
        except ValueError as e:
            self.output_text.setPlainText("")
            self.set_status(f"表达式错误: {e}", ok=False)
            return
        now = datetime.datetime.now()
        lines = []
        week = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        for i, dt in enumerate(plan, 1):
            wd = week[dt.isoweekday() - 1]
            lines.append(f"#{i:<3} {dt.strftime('%Y-%m-%d %H:%M:%S')}  {wd}")
        self.output_text.setPlainText("\n".join(lines))
        shown = len(plan)
        head = f"以当前时间 {now.strftime('%Y-%m-%d %H:%M:%S')} 起，共 {shown} 次执行计划"
        if extra:
            head = f"{expr}  ({extra}) —  " + head
        else:
            head = f"{expr} —  " + head
        self.set_status(head, ok=True)

    # ---- cron parsing ----
    @staticmethod
    def _parse_field(token, lo, hi, is_dow=False):
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

    def compute(self, expr, count):
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

        minutes = self._parse_field(m_expr, 0, 59)
        hours = self._parse_field(h_expr, 0, 23)
        doms = self._parse_field(dom_expr, 1, 31)
        mons = self._parse_field(mon_expr, 1, 12)
        dows = self._parse_field(dow_expr, 0, 7, is_dow=True)
        secs = self._parse_field(sec_expr, 0, 59) if has_seconds else {0}

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

        now = datetime.datetime.now()
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

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class UrlEncodeWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("URL 编解码")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        splitter = QSplitter(Qt.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_header = QHBoxLayout()
        left_label = QLabel("输入内容")
        left_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        left_label.setStyleSheet("color: #333333;")
        left_header.addWidget(left_label)
        left_header.addStretch()

        encode_btn = QPushButton("编码")
        encode_btn.setFixedSize(60, 28)
        encode_btn.setCursor(QCursor(Qt.PointingHandCursor))
        encode_btn.setStyleSheet("""
            QPushButton { color: #FFFFFF; background: #1A73E8; border: none; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #1557B0; }
        """)
        encode_btn.clicked.connect(self.do_encode)
        left_header.addWidget(encode_btn)

        decode_btn = QPushButton("解码")
        decode_btn.setFixedSize(60, 28)
        decode_btn.setCursor(QCursor(Qt.PointingHandCursor))
        decode_btn.setStyleSheet("""
            QPushButton { color: #FFFFFF; background: #34A853; border: none; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #2D8E47; }
        """)
        decode_btn.clicked.connect(self.do_decode)
        left_header.addWidget(decode_btn)
        left_layout.addLayout(left_header)

        self.input_text = QPlainTextEdit()
        self.input_text.setStyleSheet("""
            QPlainTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; }
        """)
        left_layout.addWidget(self.input_text)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_header = QHBoxLayout()
        right_label = QLabel("结果")
        right_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        right_label.setStyleSheet("color: #333333;")
        right_header.addWidget(right_label)
        right_header.addStretch()

        swap_btn = QPushButton("交换")
        swap_btn.setFixedSize(60, 28)
        swap_btn.setCursor(QCursor(Qt.PointingHandCursor))
        swap_btn.setStyleSheet("""
            QPushButton { color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #E0E0E0; }
        """)
        swap_btn.clicked.connect(self.do_swap)
        right_header.addWidget(swap_btn)

        copy_btn = QPushButton("复制")
        copy_btn.setFixedSize(60, 28)
        copy_btn.setCursor(QCursor(Qt.PointingHandCursor))
        copy_btn.setStyleSheet("""
            QPushButton { color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #E0E0E0; }
        """)
        copy_btn.clicked.connect(self.do_copy)
        right_header.addWidget(copy_btn)
        right_layout.addLayout(right_header)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("""
            QTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; background: #FAFAFA; }
        """)
        right_layout.addWidget(self.output_text)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([450, 450])
        layout.addWidget(splitter)

    def do_encode(self):
        raw = self.input_text.toPlainText()
        if not raw:
            self.output_text.setPlainText("")
            return
        try:
            encoded = urllib.parse.quote(raw, safe='')
            self.output_text.setPlainText(encoded)
        except Exception as e:
            self.output_text.setPlainText(f"编码错误:\n{e}")

    def do_decode(self):
        raw = self.input_text.toPlainText().strip()
        if not raw:
            self.output_text.setPlainText("")
            return
        try:
            decoded = urllib.parse.unquote(raw)
            self.output_text.setPlainText(decoded)
        except Exception as e:
            self.output_text.setPlainText(f"解码错误:\n{e}")

    def do_copy(self):
        text = self.output_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            QMessageBox.information(self, "已复制", "已复制到剪贴板", QMessageBox.Ok)

    def do_swap(self):
        input_text = self.input_text.toPlainText()
        output_text = self.output_text.toPlainText()
        self.input_text.setPlainText(output_text)
        self.output_text.setPlainText(input_text)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class HashWindow(QMainWindow):
    MODE_BTN_STYLE = """
        QPushButton { color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0;
            border-radius: 4px; font-size: 12px; }
        QPushButton:hover { background: #E0E0E0; }
        QPushButton:checked { color: #FFFFFF; background: #1A73E8; border: none; }
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("哈希计算")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.setAcceptDrops(True)
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        mode_layout = QHBoxLayout()
        self.text_mode_btn = QPushButton("文本哈希")
        self.text_mode_btn.setFixedSize(90, 30)
        self.text_mode_btn.setCheckable(True)
        self.text_mode_btn.setChecked(True)
        self.text_mode_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.text_mode_btn.setStyleSheet(self.MODE_BTN_STYLE)
        self.text_mode_btn.clicked.connect(lambda: self.switch_mode(0))
        mode_layout.addWidget(self.text_mode_btn)

        self.file_mode_btn = QPushButton("文件哈希")
        self.file_mode_btn.setFixedSize(90, 30)
        self.file_mode_btn.setCheckable(True)
        self.file_mode_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.file_mode_btn.setStyleSheet(self.MODE_BTN_STYLE)
        self.file_mode_btn.clicked.connect(lambda: self.switch_mode(1))
        mode_layout.addWidget(self.file_mode_btn)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        self.stack = QStackedWidget()

        text_page = QWidget()
        text_page_layout = QVBoxLayout(text_page)
        text_page_layout.setContentsMargins(0, 0, 0, 0)
        input_label = QLabel("输入内容")
        input_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        input_label.setStyleSheet("color: #333333;")
        text_page_layout.addWidget(input_label)
        self.input_text = QPlainTextEdit()
        self.input_text.setStyleSheet("""
            QPlainTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; }
        """)
        text_page_layout.addWidget(self.input_text)
        calc_btn = QPushButton("计算哈希")
        calc_btn.setFixedSize(100, 32)
        calc_btn.setCursor(QCursor(Qt.PointingHandCursor))
        calc_btn.setStyleSheet("""
            QPushButton { color: #FFFFFF; background: #1A73E8; border: none; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #1557B0; }
        """)
        calc_btn.clicked.connect(self.do_calc)
        text_page_layout.addWidget(calc_btn, alignment=Qt.AlignCenter)

        file_page = QWidget()
        file_page_layout = QVBoxLayout(file_page)
        file_page_layout.setContentsMargins(0, 0, 0, 0)
        file_label = QLabel("选择文件")
        file_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        file_label.setStyleSheet("color: #333333;")
        file_page_layout.addWidget(file_label)
        self.drop_label = QLabel("将文件拖到此处，或点击下方选择文件")
        self.drop_label.setAlignment(Qt.AlignCenter)
        self.drop_label.setMinimumHeight(120)
        self.drop_label.setStyleSheet("""
            QLabel { color: #666666; font-size: 13px; border: 1px dashed #B0B0B0;
                border-radius: 6px; background: #FAFAFA; }
        """)
        file_page_layout.addWidget(self.drop_label)
        choose_btn = QPushButton("选择文件")
        choose_btn.setFixedSize(100, 32)
        choose_btn.setCursor(QCursor(Qt.PointingHandCursor))
        choose_btn.setStyleSheet("""
            QPushButton { color: #FFFFFF; background: #1A73E8; border: none; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #1557B0; }
        """)
        choose_btn.clicked.connect(self.choose_file)
        file_page_layout.addWidget(choose_btn, alignment=Qt.AlignCenter)

        self.stack.addWidget(text_page)
        self.stack.addWidget(file_page)
        layout.addWidget(self.stack, 1)

        result_label = QLabel("计算结果")
        result_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        result_label.setStyleSheet("color: #333333;")
        layout.addWidget(result_label)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(160)
        self.result_text.setStyleSheet("""
            QTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; background: #FAFAFA; }
        """)
        layout.addWidget(self.result_text)

    def switch_mode(self, index):
        self.stack.setCurrentIndex(index)
        self.text_mode_btn.setChecked(index == 0)
        self.file_mode_btn.setChecked(index == 1)

    def do_calc(self):
        raw = self.input_text.toPlainText()
        if not raw:
            self.result_text.setPlainText("")
            return
        data = raw.encode('utf-8')
        self._show_hashes(data)

    def _show_hashes(self, data):
        results = []
        for name, func in [("MD5", hashlib.md5), ("SHA1", hashlib.sha1),
                           ("SHA256", hashlib.sha256), ("SHA512", hashlib.sha512)]:
            results.append(f"{name}: {func(data).hexdigest()}")
        self.result_text.setPlainText('\n'.join(results))

    def choose_file(self):
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "选择文件")
        if path:
            self.compute_file(path)

    def dragEnterEvent(self, event):
        if self.stack.currentIndex() == 1 and event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            self.compute_file(url.toLocalFile())
            break

    def compute_file(self, path):
        self.drop_label.setText(os.path.basename(path))
        try:
            hashes = [hashlib.md5(), hashlib.sha1(), hashlib.sha256(), hashlib.sha512()]
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    for h in hashes:
                        h.update(chunk)
            size = os.path.getsize(path)
            results = [f"文件: {os.path.basename(path)}  ({size} 字节)"]
            for name, h in zip(["MD5", "SHA1", "SHA256", "SHA512"], hashes):
                results.append(f"{name}: {h.hexdigest()}")
            self.result_text.setPlainText('\n'.join(results))
        except Exception as e:
            self.result_text.setPlainText(f"计算失败:\n{e}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


JWT_HS_ALGS = {"HS256": hashlib.sha256, "HS384": hashlib.sha384, "HS512": hashlib.sha512}
JWT_PUB_ALGS = {"RS256": hashes.SHA256, "RS384": hashes.SHA384, "RS512": hashes.SHA512,
                "PS256": hashes.SHA256, "PS384": hashes.SHA384, "PS512": hashes.SHA512,
                "ES256": hashes.SHA256, "ES384": hashes.SHA384, "ES512": hashes.SHA512}
# ES* 的签名是定长 r||s；ES512 走 P-521，所以每段 66 字节
JWT_EC_PART = {"ES256": 32, "ES384": 48, "ES512": 66}
JWT_TIME_CLAIMS = (("iat", "签发"), ("nbf", "生效"), ("exp", "过期"))


def b64url_encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64url_decode(text):
    try:
        return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    except ValueError:
        raise ValueError("Base64URL 段解不开：%s" % text[:24])


def jwt_parts(token):
    """拆 JWT，返回 (头部, 载荷, 签名, 待签名内容)。"""
    parts = token.strip().split(".")
    if len(parts) < 2:
        raise ValueError("看不到 . 分隔的段，不像 JWT")
    try:
        header = json.loads(b64url_decode(parts[0]).decode("utf-8", "replace"))
        payload = json.loads(b64url_decode(parts[1]).decode("utf-8", "replace"))
    except ValueError:
        raise ValueError("头部或载荷不是 JSON，检查是否粘全了三段")
    if not isinstance(header, dict) or not isinstance(payload, dict):
        raise ValueError("头部和载荷得是 JSON 对象")
    signature = b64url_decode(parts[2]) if len(parts) > 2 and parts[2] else b""
    return header, payload, signature, ".".join(parts[:2]).encode()


def load_pem_key(text):
    """先当公钥读，读不通再当私钥读；私钥里也带公钥，本地自测方便。"""
    data = text.strip().encode("utf-8")
    try:
        return serialization.load_pem_public_key(data)
    except ValueError:
        return serialization.load_pem_private_key(data, password=None)


def as_public(key):
    """私钥对象顺手取它的公钥；本来就是公钥则原样返回。"""
    return key.public_key() if hasattr(key, "public_key") else key


def jwt_verify(alg, signing_input, signature, key_text):
    """返回 (True/False/None, 说明)；None 表示手头条件验不了。"""
    if alg.lower() == "none":
        return None, "alg=none，这个 token 压根没签名，别信"
    if not signature:
        return None, "缺少签名段，只能看内容"
    if alg in JWT_HS_ALGS:
        if not key_text.strip():
            return None, "要验 %s 还需要填共享密钥" % alg
        mac = hmac.new(key_text.encode("utf-8"), signing_input, JWT_HS_ALGS[alg]).digest()
        if hmac.compare_digest(mac, signature):
            return True, "%s 验签通过（共享密钥）" % alg
        return False, "%s 验签失败：密钥不对，或 token 被改过" % alg
    if alg not in JWT_PUB_ALGS:
        return None, "算法 %s 还不支持验签，只看内容" % alg
    if not key_text.strip():
        return None, "要验 %s 还需要填 PEM 公钥" % alg
    hash_cls = JWT_PUB_ALGS[alg]
    try:
        public = as_public(load_pem_key(key_text))
    except Exception as e:
        return None, "公钥读不出来：%s" % e
    try:
        if alg.startswith("RS"):
            public.verify(signature, signing_input, asym_padding.PKCS1v15(), hash_cls())
        elif alg.startswith("PS"):
            public.verify(signature, signing_input,
                          asym_padding.PSS(mgf=asym_padding.MGF1(hash_cls()),
                                            salt_length=hash_cls().digest_size), hash_cls())
        else:
            half = JWT_EC_PART[alg]
            if len(signature) != half * 2:
                return None, "%s 签名长度应为 %d 字节，实际 %d" % (alg, half * 2, len(signature))
            r = int.from_bytes(signature[:half], "big")
            s = int.from_bytes(signature[half:], "big")
            public.verify(der_utils.encode_dss_signature(r, s), signing_input, ECDSA(hash_cls()))
    except InvalidSignature:
        return False, "%s 验签失败：签名和密钥不匹配" % alg
    except Exception as e:
        return None, "%s 没法验签：%s" % (alg, e)
    return True, "%s 验签通过" % alg


def span_text(seconds):
    seconds = int(abs(seconds))
    for unit, size in (("天", 86400), ("小时", 3600), ("分钟", 60)):
        if seconds >= size:
            return "%d%s" % (seconds // size, unit)
    return "%d秒" % seconds


def jwt_claim_notes(payload):
    notes = []
    now = time.time()
    for name, cn in JWT_TIME_CLAIMS:
        val = payload.get(name)
        if not isinstance(val, (int, float)):
            continue
        local = datetime.datetime.fromtimestamp(val).strftime("%Y-%m-%d %H:%M:%S")
        note = "%s %s：%s" % (cn, name, local)
        if name == "exp":
            note += "（已过期 %s）" % span_text(val - now) if val < now else "（还剩 %s）" % span_text(val - now)
        notes.append(note)
    return notes


class _CryptoPage(QWidget):
    """加解密各页共用的布局小工具。"""

    def __init__(self):
        super().__init__()
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(15, 15, 15, 10)
        self.box.setSpacing(8)

    def label(self, text):
        item = QLabel(text)
        item.setFont(QFont("PingFang SC", 12, QFont.Bold))
        item.setStyleSheet("color: #333333;")
        return item

    def row(self):
        row = QHBoxLayout()
        row.setSpacing(8)
        self.box.addLayout(row)
        return row

    def button(self, text, handler, primary=False, width=84):
        btn = QPushButton(text)
        btn.setFixedSize(width, 28)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setStyleSheet(_primary_btn() if primary else _secondary_btn())
        btn.clicked.connect(handler)
        return btn

    def combo(self, items, width=140):
        box = QComboBox()
        box.addItems(list(items))
        box.setFixedWidth(width)
        box.setStyleSheet(_combo_style())
        return box

    def line(self, placeholder=""):
        edit = QLineEdit()
        edit.setStyleSheet(_lineedit_style())
        if placeholder:
            edit.setPlaceholderText(placeholder)
        return edit

    def area(self, height, placeholder=""):
        edit = QPlainTextEdit()
        edit.setFixedHeight(height)
        edit.setStyleSheet(_plain_style())
        if placeholder:
            edit.setPlaceholderText(placeholder)
        return edit

    def output(self):
        view = QTextEdit()
        view.setReadOnly(True)
        view.setStyleSheet(_output_style())
        return view

    def add_status(self):
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.box.addWidget(self.status_label)
        self._set_status("")

    def _set_status(self, text, ok=True):
        color = "#188038" if ok is True else ("#9AA0A6" if ok is None else "#D93025")
        self.status_label.setText(text)
        self.status_label.setStyleSheet("color: %s; font-family: 'PingFang SC'; font-size: 11px;" % color)

    def copy_text(self, text, empty="没有可复制的内容。"):
        if not text:
            self._set_status(empty, ok=False)
            return
        QApplication.clipboard().setText(text.strip())
        self._set_status("已复制到剪贴板。")


class _JwtPage(_CryptoPage):
    """JWT 只看内容不安全，所以顺手把 HS*/RS*/PS*/ES* 的签名也验了。"""

    def __init__(self):
        super().__init__()
        self.box.addWidget(self.label("Token"))
        self.token_edit = self.area(110, "粘贴 eyJ... 开头的 JWT")
        self.box.addWidget(self.token_edit)
        self.box.addWidget(self.label("密钥 / 公钥"))
        self.key_edit = self.area(64, "HS* 填共享密钥；RS*/PS*/ES* 填 PEM 公钥")
        self.box.addWidget(self.key_edit)
        row = self.row()
        row.addWidget(self.button("解析", self.do_parse, True, 72))
        row.addWidget(self.button("复制载荷", self.copy_payload))
        row.addWidget(self.button("清空", self.do_clear, width=64))
        row.addStretch()
        self.result_text = self.output()
        self.box.addWidget(self.result_text, 1)
        self.add_status()
        self._payload = ""

    def do_parse(self):
        token = self.token_edit.toPlainText().strip()
        if not token:
            self.result_text.setPlainText("")
            self._set_status("先粘贴一段 JWT。", ok=False)
            return
        try:
            header, payload, signature, signing_input = jwt_parts(token)
        except ValueError as e:
            self.result_text.setPlainText("")
            self._set_status("解析失败：%s" % e, ok=False)
            return
        self._payload = json.dumps(payload, ensure_ascii=False, indent=2)
        head_text = json.dumps(header, ensure_ascii=False, indent=2)
        blocks = ["头部", head_text, "", "载荷", self._payload]
        notes = jwt_claim_notes(payload)
        if notes:
            blocks += ["", "时间声明"] + notes
        verdict, note = jwt_verify(str(header.get("alg", "")), signing_input, signature,
                                  self.key_edit.toPlainText())
        blocks += ["", "签名 " + (b64url_encode(signature) if signature else "（无）"),
                   "验签：" + note]
        self.result_text.setPlainText("\n".join(blocks))
        self._set_status(note, ok=verdict)

    def copy_payload(self):
        self.copy_text(self._payload, "先解析一段 JWT。")

    def do_clear(self):
        self.token_edit.clear()
        self.key_edit.clear()
        self.result_text.setPlainText("")
        self._payload = ""
        self._set_status("")


class _AesPage(_CryptoPage):
    """口令派生的 AES 密文自带模式和盐，解密时不用再猜参数。"""

    def __init__(self):
        super().__init__()
        row = self.row()
        row.addWidget(QLabel("模式"))
        self.mode_combo = self.combo(AES_MODES, 140)
        row.addWidget(self.mode_combo)
        row.addWidget(QLabel("密钥"))
        self.src_combo = self.combo(AES_KEY_SOURCES, 150)
        row.addWidget(self.src_combo)
        row.addWidget(QLabel("输出"))
        self.out_combo = self.combo(("Base64", "Hex"), 90)
        row.addWidget(self.out_combo)
        row.addStretch()
        self.key_line = self.line("口令，或 16/32 字节 Hex 密钥")
        self.box.addWidget(self.key_line)
        self.box.addWidget(self.label("内容"))
        self.input_edit = self.area(90, "加密前放明文，解密时把密文整段粘进来")
        self.box.addWidget(self.input_edit)
        row = self.row()
        row.addWidget(self.button("加密", self.do_encrypt, True, 72))
        row.addWidget(self.button("解密", self.do_decrypt, True, 72))
        row.addWidget(self.button("复制结果", self.copy_result))
        row.addWidget(self.button("清空", self.do_clear, width=64))
        row.addStretch()
        self.result_text = self.output()
        self.box.addWidget(self.result_text, 1)
        self.add_status()
        self.mode_combo.currentTextChanged.connect(self._hint)
        self.src_combo.currentIndexChanged.connect(self._key_placeholder)
        self._key_placeholder()
        self._hint(self.mode_combo.currentText())

    def _key_placeholder(self):
        derived = self.src_combo.currentIndex() == 0
        self.key_line.setPlaceholderText("口令（PBKDF2-SHA256 %d 次派生，每次加密随机盐）" % AES_PBKDF2_ROUNDS
                                        if derived else "原始密钥 Hex，长度要匹配模式")

    def _hint(self, mode):
        if mode.endswith("GCM"):
            self._set_status("%s 自带完整性校验，推荐用这个；密文头已写入模式和盐，解密不用再选。" % mode)
        elif mode.endswith("CBC"):
            self._set_status("%s 没有完整性校验，只用来和别的系统互通；自己的数据选 GCM。" % mode, ok=False)
        else:
            self._set_status("%s 不校验完整性，且同一个密钥下 IV 绝不能复用。" % mode, ok=False)

    def _derive_key(self):
        text = self.key_line.text()
        if self.src_combo.currentIndex() == 0:
            if not text:
                raise ValueError("请输入口令")
            return text, None
        raw = bytes.fromhex("".join(text.split()))
        size = AES_KEY_BYTES[self.mode_combo.currentText()]
        if len(raw) != size:
            raise ValueError("这个模式需要 %d 字节（%d 个 Hex 字符）密钥，当前 %d 字节"
                            % (size, size * 2, len(raw)))
        return None, raw

    def do_encrypt(self):
        data = self.input_edit.toPlainText().encode("utf-8")
        if not data:
            self._set_status("先输入要加密的明文。", ok=False)
            return
        try:
            passphrase, raw_key = self._derive_key()
            blob = aes_encrypt(data, self.mode_combo.currentText(), passphrase, raw_key)
        except ValueError as e:
            self._set_status("加密失败：%s" % e, ok=False)
            return
        self.result_text.setPlainText(encode_blob(blob, self.out_combo.currentText()))
        self._set_status("已加密：%s，密文 %d 字节。" % (self.mode_combo.currentText(), len(blob)))

    def do_decrypt(self):
        try:
            blob = decode_blob(self.input_edit.toPlainText(), self.out_combo.currentText())
            passphrase, raw_key = self._derive_key()
            plain = aes_decrypt(blob, passphrase, raw_key)
        except InvalidTag:
            self._set_status("解密失败：口令/密钥不对，或密文被改过（GCM 校验不通过）。", ok=False)
            return
        except ValueError as e:
            self._set_status("解密失败：%s" % e, ok=False)
            return
        try:
            text = plain.decode("utf-8")
        except UnicodeDecodeError:
            text = encode_blob(plain, self.out_combo.currentText())
            self._set_status("解出来的不是 UTF-8 文本，已按原样给出字节。", ok=False)
        else:
            self._set_status("解密成功：%d 字符。" % len(text))
        self.result_text.setPlainText(text)

    def copy_result(self):
        self.copy_text(self.result_text.toPlainText(), "还没有结果。")

    def do_clear(self):
        self.key_line.clear()
        self.input_edit.clear()
        self.result_text.setPlainText("")
        self._set_status("")


AES_MODES = ("AES-256-GCM", "AES-128-GCM", "AES-256-CBC", "AES-256-CTR")
AES_KEY_SOURCES = ("口令派生（推荐）", "Hex 原始密钥")
AES_KEY_BYTES = {"AES-256-GCM": 32, "AES-128-GCM": 16, "AES-256-CBC": 32, "AES-256-CTR": 32}
AES_IV_BYTES = {"AES-256-GCM": 12, "AES-128-GCM": 12, "AES-256-CBC": 16, "AES-256-CTR": 16}
AES_MAGIC = b"TBX1"
AES_PBKDF2_ROUNDS = 210000
AES_SALT_BYTES = 16


def encode_blob(data, encoding):
    return data.hex() if encoding == "Hex" else base64.b64encode(data).decode()


def decode_blob(text, encoding):
    text = text.strip()
    if not text:
        raise ValueError("先输入密文")
    if encoding == "Hex":
        return bytes.fromhex("".join(text.split()))
    return base64.b64decode("".join(text.split()), validate=True)


def pbkdf2_key(passphrase, salt, length, rounds=AES_PBKDF2_ROUNDS):
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=length, salt=salt,
                      iterations=rounds).derive(passphrase.encode("utf-8"))


def aes_run(key, iv, mode_name, data, encrypt, aad):
    if mode_name.endswith("GCM"):
        box = AESGCM(key)
        return box.encrypt(iv, data, aad) if encrypt else box.decrypt(iv, data, aad)
    if mode_name.endswith("CBC"):
        if encrypt:
            padder = sym_padding.PKCS7(128).padder()
            data = padder.update(data) + padder.finalize()
    cipher = Cipher(algorithms.AES(key),
                    modes.CBC(iv) if mode_name.endswith("CBC") else modes.CTR(iv))
    engine = cipher.encryptor() if encrypt else cipher.decryptor()
    out = engine.update(data) + engine.finalize()
    if mode_name.endswith("CBC") and not encrypt:
        unpadder = sym_padding.PKCS7(128).unpadder()
        out = unpadder.update(out) + unpadder.finalize()
    return out


def aes_encrypt(data, mode_name, passphrase=None, raw_key=None):
    """TBX1 | 模式 | 密钥来源 | salt | IV | 密文；头部当作 GCM 的附加认证数据。"""
    idx = AES_MODES.index(mode_name)
    size = AES_KEY_BYTES[mode_name]
    iv = os.urandom(AES_IV_BYTES[mode_name])
    if passphrase is None:
        salt, key, flag = b"", raw_key, 1
    else:
        salt = os.urandom(AES_SALT_BYTES)
        key = pbkdf2_key(passphrase, salt, size)
        flag = 0
    head = AES_MAGIC + bytes([idx, flag]) + salt + iv
    return head + aes_run(key, iv, mode_name, data, True, head)


def aes_decrypt(blob, passphrase=None, raw_key=None):
    if not blob.startswith(AES_MAGIC):
        raise ValueError("密文没有 TBX1 头，不是本工具加密的；确认一下输出编码选对了吗")
    idx, flag = blob[4], blob[5]
    if idx >= len(AES_MODES) or flag > 1:
        raise ValueError("密文头部编号不认识")
    mode_name = AES_MODES[idx]
    size = AES_KEY_BYTES[mode_name]
    pos = len(AES_MAGIC) + 2
    salt = b""
    if flag == 0:
        salt = blob[pos:pos + AES_SALT_BYTES]
        pos += AES_SALT_BYTES
    iv = blob[pos:pos + AES_IV_BYTES[mode_name]]
    pos += AES_IV_BYTES[mode_name]
    key = pbkdf2_key(passphrase, salt, size) if passphrase is not None else raw_key
    return aes_run(key, iv, mode_name, blob[pos:], False, blob[:pos])


class _RsaKeygenWorker(QThread):
    done = pyqtSignal(str, str, str)

    def __init__(self, bits):
        super().__init__()
        self.bits = bits

    def run(self):
        try:
            key = rsa.generate_private_key(public_exponent=65537, key_size=self.bits)
            priv = key.private_bytes(serialization.Encoding.PEM,
                                    serialization.PrivateFormat.PKCS8,
                                    serialization.NoEncryption()).decode()
            pub = key.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo).decode()
            self.done.emit(priv, pub, "")
        except Exception as e:
            self.done.emit("", "", "生成失败：%s" % e)


class _RsaPage(_CryptoPage):
    """RSA 用来加密小东西（AES 密钥、签名）；大段内容请回到 AES 页。"""

    def __init__(self):
        super().__init__()
        row = self.row()
        row.addWidget(QLabel("位数"))
        self.bits_combo = self.combo(("2048", "3072", "4096"), 90)
        row.addWidget(self.bits_combo)
        self.gen_btn = self.button("生成密钥对", self.do_keygen, True, 100)
        row.addWidget(self.gen_btn)
        row.addWidget(self.button("清空密钥", self.clear_keys, width=88))
        row.addStretch()
        self.box.addWidget(self.label("私钥（PKCS#8 PEM）"))
        self.priv_edit = self.area(96, "-----BEGIN PRIVATE KEY-----")
        self.box.addWidget(self.priv_edit)
        self.box.addWidget(self.label("公钥（SPKI PEM）"))
        self.pub_edit = self.area(64, "-----BEGIN PUBLIC KEY-----")
        self.box.addWidget(self.pub_edit)
        row = self.row()
        row.addWidget(self.button("复制私钥", lambda: self.copy_text(self.priv_edit.toPlainText())))
        row.addWidget(self.button("复制公钥", lambda: self.copy_text(self.pub_edit.toPlainText())))
        row.addStretch()
        self.box.addWidget(self.label("内容 / 密文"))
        self.input_edit = self.area(64, "加密放明文；解密粘 base64 密文；签名/验签放原文")
        self.box.addWidget(self.input_edit)
        self.sig_line = self.line("验签时把 base64 签名粘到这里")
        self.box.addWidget(self.sig_line)
        row = self.row()
        row.addWidget(self.button("加密", self.do_encrypt, True, 72))
        row.addWidget(self.button("解密", self.do_decrypt, True, 72))
        row.addWidget(self.button("签名", self.do_sign, True, 72))
        row.addWidget(self.button("验签", self.do_verify, True, 72))
        row.addWidget(self.button("复制结果", self.copy_result))
        row.addStretch()
        self.result_text = self.output()
        self.box.addWidget(self.result_text, 1)
        self.add_status()
        self._worker = None
        self._set_status("2048 位 OAEP-SHA256 单次最多加密 %d 字节，更大的内容用 AES。" % rsa_plain_limit(2048))

    def _fail(self, text):
        self._set_status(text, ok=False)

    def do_keygen(self):
        if self._worker is not None and self._worker.isRunning():
            return
        bits = int(self.bits_combo.currentText())
        self.gen_btn.setText("生成中…")
        self.gen_btn.setEnabled(False)
        self._worker = _RsaKeygenWorker(bits)
        self._worker.done.connect(self._keygen_done)
        self._worker.start()

    def _keygen_done(self, priv, pub, error):
        self.gen_btn.setText("生成密钥对")
        self.gen_btn.setEnabled(True)
        if error or not priv:
            self._fail(error or "生成失败：没有取到私钥")
            return
        self.priv_edit.setPlainText(priv)
        self.pub_edit.setPlainText(pub)
        self._set_status("已生成 %d 位密钥对，OAEP-SHA256 单次最多加密 %d 字节。"
                         % (self._worker.bits, rsa_plain_limit(self._worker.bits)))

    def clear_keys(self):
        self.priv_edit.clear()
        self.pub_edit.clear()
        self.result_text.setPlainText("")
        self._set_status("")

    def _key(self, which):
        text = (self.priv_edit if which == "priv" else self.pub_edit).toPlainText()
        if not text.strip():
            raise ValueError("先生成或粘贴%s" % ("私钥" if which == "priv" else "公钥"))
        key = load_pem_key(text)
        return key if which == "priv" else as_public(key)

    def do_encrypt(self):
        try:
            key = self._key("pub")
            data = self.input_edit.toPlainText().encode("utf-8")
            if not data:
                raise ValueError("先输入要加密的明文")
            limit = rsa_plain_limit(key.key_size)
            if len(data) > limit:
                raise ValueError("明文 %d 字节，超过这个密钥的上限 %d 字节；大段数据请用 AES"
                                % (len(data), limit))
            blob = key.encrypt(data, rsa_oaep())
        except (ValueError, TypeError) as e:
            self._fail("加密失败：%s" % e)
            return
        except Exception as e:
            self._fail("加密失败：公钥读不出来（%s）" % e)
            return
        self.result_text.setPlainText(base64.b64encode(blob).decode())
        self._set_status("已加密：%d 字节明文 → %d 字节密文（base64）。" % (len(data), len(blob)))

    def do_decrypt(self):
        try:
            key = self._key("priv")
            blob = base64.b64decode(self.input_edit.toPlainText().strip(), validate=True)
            plain = key.decrypt(blob, rsa_oaep())
        except ValueError as e:
            self._fail("解密失败：密文不是合法 base64 或密钥不对（%s）" % e)
            return
        except Exception as e:
            self._fail("解密失败：%s" % e)
            return
        self.result_text.setPlainText(decode_maybe_text(plain))
        self._set_status("解密完成。")

    def do_sign(self):
        try:
            key = self._key("priv")
            data = self.input_edit.toPlainText().encode("utf-8")
            if not data:
                raise ValueError("先输入要签名的内容")
            sig = key.sign(data, asym_padding.PKCS1v15(), hashes.SHA256())
        except (ValueError, TypeError) as e:
            self._fail("签名失败：%s" % e)
            return
        except Exception as e:
            self._fail("签名失败：私钥读不出来（%s）" % e)
            return
        text = base64.b64encode(sig).decode()
        self.result_text.setPlainText(text)
        self.sig_line.setText(text)
        self._set_status("已用 PKCS1v15 + SHA-256 签名，签名值同时填到了验签框。")

    def do_verify(self):
        try:
            key = self._key("pub")
            data = self.input_edit.toPlainText().encode("utf-8")
            sig = base64.b64decode(self.sig_line.text().strip(), validate=True)
            key.verify(sig, data, asym_padding.PKCS1v15(), hashes.SHA256())
        except InvalidSignature:
            self._fail("验签失败：签名与内容/公钥不匹配")
            return
        except ValueError as e:
            self._fail("验签失败：签名不是合法 base64（%s）" % e)
            return
        except Exception as e:
            self._fail("验签失败：%s" % e)
            return
        self._set_status("验签通过：内容确实由配对的私钥签名。")

    def copy_result(self):
        self.copy_text(self.result_text.toPlainText(), "还没有结果。")


def rsa_oaep():
    return asym_padding.OAEP(mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                            algorithm=hashes.SHA256(), label=None)


def rsa_plain_limit(bits):
    """OAEP-SHA256 的明文上限：key_size - 2*digest - 2。"""
    return bits // 8 - 2 * 32 - 2


def decode_maybe_text(data):
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return base64.b64encode(data).decode()


class _HmacPage(_CryptoPage):
    """给一段内容 + 密钥算消息认证码，结果随输入实时刷新。"""

    def __init__(self):
        super().__init__()
        self.box.addWidget(self.label("内容"))
        self.msg_edit = self.area(100, "要签名的消息")
        self.box.addWidget(self.msg_edit)
        row = self.row()
        row.addWidget(QLabel("密钥"))
        self.key_line = self.line("共享密钥")
        row.addWidget(self.key_line, 1)
        row.addWidget(QLabel("算法"))
        self.alg_combo = self.combo(HMAC_ALGS, 120)
        row.addWidget(self.alg_combo)
        row.addWidget(QLabel("输出"))
        self.out_combo = self.combo(("Hex", "Base64"), 90)
        row.addWidget(self.out_combo)
        row2 = self.row()
        row2.addWidget(self.button("复制结果", self.copy_result))
        row2.addWidget(self.button("清空", self.do_clear, width=64))
        row2.addStretch()
        self.result_text = self.output()
        self.box.addWidget(self.result_text, 1)
        self.add_status()
        for widget in (self.msg_edit, self.key_line):
            widget.textChanged.connect(self.do_compute)
        self.alg_combo.currentIndexChanged.connect(self.do_compute)
        self.out_combo.currentIndexChanged.connect(self.do_compute)

    def do_compute(self):
        key = self.key_line.text().encode("utf-8")
        if not self.msg_edit.toPlainText():
            self.result_text.setPlainText("")
            self._set_status("输入内容后自动计算。")
            return
        name = self.alg_combo.currentText()
        digest = hmac.new(key, self.msg_edit.toPlainText().encode("utf-8"),
                          HMAC_ALGS[name]).digest()
        text = encode_blob(digest, self.out_combo.currentText())
        self.result_text.setPlainText(text)
        self._set_status("%s · %d 字节认证码。" % (name, len(digest)))

    def copy_result(self):
        self.copy_text(self.result_text.toPlainText(), "还没有结果。")

    def do_clear(self):
        self.msg_edit.clear()
        self.key_line.clear()
        self.result_text.setPlainText("")
        self._set_status("")


HMAC_ALGS = {"SHA-1": hashlib.sha1, "SHA-256": hashlib.sha256,
             "SHA-384": hashlib.sha384, "SHA-512": hashlib.sha512}


PASS_ALGS = ("PBKDF2-SHA256", "scrypt")
PASS_ROUNDS = 210000
PASS_SCRYPT_N = 16384
PASS_SCRYPT_R = 8
PASS_SCRYPT_P = 1
PASS_HASH_BYTES = 32
PASS_SALT_BYTES = 16


def passhash_derive(tag, passphrase, salt, params=None):
    """不带 params 用默认值；PBKDF2 传次数，scrypt 传 (N, r, p)。"""
    if tag == "pbkdf2-sha256":
        return pbkdf2_key(passphrase, salt, PASS_HASH_BYTES,
                          int(params) if params else PASS_ROUNDS)
    n, r, p = params or (PASS_SCRYPT_N, PASS_SCRYPT_R, PASS_SCRYPT_P)
    n, r, p = int(n), int(r), int(p)
    if n < 2 or n & (n - 1):
        raise ValueError("scrypt 的 N 必须是 2 的整数次幂，串里写的是 %d" % n)
    return hashlib.scrypt(passphrase.encode("utf-8"), salt=salt, n=n, r=r, p=p,
                          dklen=PASS_HASH_BYTES, maxmem=128 * n * r * p + (1 << 20))


def passhash_make(alg, passphrase):
    """自带盐和参数的字符串，回头可以直接校验，不用记参数。"""
    if not passphrase:
        raise ValueError("口令不能为空")
    salt = os.urandom(PASS_SALT_BYTES)
    digest = passhash_derive(alg_tag(alg), passphrase, salt)
    if alg_tag(alg) == "pbkdf2-sha256":
        return "$pbkdf2-sha256$%d$%s$%s" % (PASS_ROUNDS, base64.b64encode(salt).decode(),
                                           base64.b64encode(digest).decode())
    return "$scrypt$%d$%d$%d$%s$%s" % (PASS_SCRYPT_N, PASS_SCRYPT_R, PASS_SCRYPT_P,
                                      base64.b64encode(salt).decode(),
                                      base64.b64encode(digest).decode())


def alg_tag(name):
    return "pbkdf2-sha256" if name == "PBKDF2-SHA256" else "scrypt"


def passhash_parse(text):
    """解析成 (算法, 参数, salt, 哈希)，格式不对就报错。"""
    parts = text.strip().split("$")
    if parts and not parts[0]:
        parts = parts[1:]
    if not parts or not parts[0]:
        raise ValueError("应是 $pbkdf2-sha256$次数$salt$hash 或 $scrypt$N$r$p$salt$hash")
    tag = parts[0]
    if tag == "pbkdf2-sha256":
        if len(parts) != 4:
            raise ValueError("PBKDF2 串应是 $pbkdf2-sha256$次数$salt$hash")
        return tag, int(parts[1]), base64.b64decode(parts[2]), base64.b64decode(parts[3])
    if tag == "scrypt":
        if len(parts) != 6:
            raise ValueError("scrypt 串应是 $scrypt$N$r$p$salt$hash")
        return (tag, (int(parts[1]), int(parts[2]), int(parts[3])),
                base64.b64decode(parts[4]), base64.b64decode(parts[5]))
    raise ValueError("不认识的算法：%s" % tag)


def passhash_verify(stored, passphrase):
    tag, params, salt, digest = passhash_parse(stored)
    if passphrase == "":
        raise ValueError("先输入口令")
    mine = passhash_derive(tag, passphrase, salt, params)
    return hmac.compare_digest(mine, digest)


class _PassHashPage(_CryptoPage):
    """存口令用：加盐的 PBKDF2/scrypt，外加一把校验。"""

    def __init__(self):
        super().__init__()
        row = self.row()
        row.addWidget(QLabel("口令"))
        self.pass_line = self.line("要哈希的口令")
        row.addWidget(self.pass_line, 1)
        row.addWidget(QLabel("算法"))
        self.alg_combo = self.combo(PASS_ALGS, 150)
        row.addWidget(self.alg_combo)
        row = self.row()
        row.addWidget(self.button("生成哈希", self.do_hash, True, 92))
        row.addWidget(self.button("复制哈希", self.copy_result))
        row.addWidget(self.button("清空", self.do_clear, width=64))
        row.addStretch()
        self.result_text = self.output()
        self.result_text.setFixedHeight(72)
        self.box.addWidget(self.result_text)
        self.box.addWidget(self.label("校验已有哈希"))
        self.stored_edit = self.area(56, "$pbkdf2-sha256$210000$...$... 或 $scrypt$...")
        self.box.addWidget(self.stored_edit)
        row = self.row()
        row.addWidget(self.button("校验", self.do_verify, True, 72))
        row.addWidget(self.button("取上方结果", self.use_result, width=110))
        row.addStretch()
        self.add_status()
        self._set_status("PBKDF2 用 SHA-256 %d 次；scrypt 用 N=%d, r=%d, p=%d。"
                        % (PASS_ROUNDS, PASS_SCRYPT_N, PASS_SCRYPT_R, PASS_SCRYPT_P))

    def do_hash(self):
        try:
            stored = passhash_make(self.alg_combo.currentText(), self.pass_line.text())
        except ValueError as e:
            self._set_status("生成失败：%s" % e, ok=False)
            return
        self.result_text.setPlainText(stored)
        self._set_status("已生成（salt 随机，每次结果都不同是正常的）。")

    def use_result(self):
        text = self.result_text.toPlainText().strip()
        if not text:
            self._set_status("先生成一个哈希。", ok=False)
            return
        self.stored_edit.setPlainText(text)
        self._set_status("已填入待校验框。")

    def do_verify(self):
        stored = self.stored_edit.toPlainText().strip()
        if not stored:
            self._set_status("先粘贴待校验的哈希。", ok=False)
            return
        try:
            ok = passhash_verify(stored, self.pass_line.text())
        except (ValueError, TypeError) as e:
            self._set_status("校验失败：%s" % e, ok=False)
            return
        self._set_status("口令匹配。" if ok else "口令不匹配。", ok=ok)

    def copy_result(self):
        self.copy_text(self.result_text.toPlainText(), "还没有结果。")

    def do_clear(self):
        self.pass_line.clear()
        self.stored_edit.clear()
        self.result_text.setPlainText("")
        self._set_status("")


class _SecretPage(_CryptoPage):
    """用 secrets 取系统熵，生成密钥、令牌和口令。"""

    TYPES = ("Hex", "Base64", "URL 令牌", "可读密码")
    CONFUSING = "0O1lI|"

    def __init__(self):
        super().__init__()
        row = self.row()
        row.addWidget(QLabel("类型"))
        self.type_combo = self.combo(self.TYPES, 120)
        row.addWidget(self.type_combo)
        row.addWidget(QLabel("长度"))
        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 256)
        self.size_spin.setValue(32)
        self.size_spin.setStyleSheet(_combo_style())
        row.addWidget(self.size_spin)
        row.addWidget(QLabel("条数"))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 50)
        self.count_spin.setValue(5)
        self.count_spin.setStyleSheet(_combo_style())
        row.addWidget(self.count_spin)
        row.addStretch()
        self.avoid_check = QCheckBox("排除易混字符 0 O 1 l I |")
        self.avoid_check.setStyleSheet("QCheckBox { font-family: 'PingFang SC'; font-size: 12px; }")
        self.avoid_check.setChecked(True)
        self.box.addWidget(self.avoid_check)
        row = self.row()
        row.addWidget(self.button("生成", self.do_generate, True, 72))
        row.addWidget(self.button("复制全部", self.copy_all))
        row.addWidget(self.button("清空", self.do_clear, width=64))
        row.addStretch()
        self.result_text = self.output()
        self.box.addWidget(self.result_text, 1)
        self.add_status()
        self.type_combo.currentIndexChanged.connect(self._hint)
        self._hint()

    def _hint(self):
        password = self.type_combo.currentText() == "可读密码"
        self.size_spin.setSuffix(" 字符" if password else " 字节")
        self._set_status("「可读密码」保证大小写、数字和符号都有；其他类型按字节取随机。"
                        if password else "Hex/Base64/URL 令牌都是系统随机字节，可直接当密钥用。")

    def _one(self):
        kind = self.type_combo.currentText()
        size = self.size_spin.value()
        if kind == "Hex":
            return os.urandom(size).hex()
        if kind == "Base64":
            return base64.b64encode(os.urandom(size)).decode().rstrip("=")
        if kind == "URL 令牌":
            return b64url_encode(os.urandom(size))
        alphabet = "".join(c for c in (string.ascii_letters + string.digits + "!@#$%^&*-_=+")
                          if not (self.avoid_check.isChecked() and c in self.CONFUSING))
        while True:
            text = "".join(secrets.choice(alphabet) for _ in range(size))
            if (any(c.islower() for c in text) and any(c.isupper() for c in text)
                    and any(c.isdigit() for c in text)
                    and any(c in "!@#$%^&*-_=+" for c in text)):
                return text

    def do_generate(self):
        if self.type_combo.currentText() == "可读密码" and self.size_spin.value() < 10:
            self._set_status("可读密码至少要 10 个字符才凑得齐四类字符。", ok=False)
            return
        lines = [self._one() for _ in range(self.count_spin.value())]
        self.result_text.setPlainText("\n".join(lines))
        self._set_status("已生成 %d 条 %s。" % (len(lines), self.type_combo.currentText()))

    def copy_all(self):
        self.copy_text(self.result_text.toPlainText(), "先点生成。")

    def do_clear(self):
        self.result_text.setPlainText("")
        self._set_status("")


class CryptoWindow(QMainWindow):
    """加解密工具箱。页面本身是 widget，所以不走 TabbedToolWindow 的窗口转换。"""

    PAGES = ((_JwtPage, "JWT"), (_AesPage, "AES"), (_RsaPage, "RSA"),
             (_HmacPage, "HMAC"), (_PassHashPage, "口令哈希"), (_SecretPage, "随机密钥"))

    def __init__(self):
        super().__init__()
        self.setWindowTitle("加解密")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        tabs = QTabWidget()
        tabs.setStyleSheet(_tab_style())
        for cls, name in self.PAGES:
            tabs.addTab(cls(), name)
        self.setCentralWidget(tabs)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class UuidWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UUID 生成")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        opt_layout = QHBoxLayout()
        opt_layout.addWidget(QLabel("版本:"))
        self.version_combo = QComboBox()
        self.version_combo.addItems(["v4 (随机)", "v1 (时间)"])
        self.version_combo.setFixedWidth(120)
        self.version_combo.setStyleSheet(_combo_style())
        opt_layout.addWidget(self.version_combo)

        opt_layout.addWidget(QLabel("数量:"))
        self.count_input = QLineEdit("5")
        self.count_input.setFixedWidth(60)
        self.count_input.setStyleSheet("""
            QLineEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 4px 8px; font-size: 12px; }
            QLineEdit:focus { border-color: #1A73E8; }
        """)
        self.count_input.returnPressed.connect(self.do_generate)
        opt_layout.addWidget(self.count_input)

        gen_btn = QPushButton("生成")
        gen_btn.setFixedSize(60, 28)
        gen_btn.setCursor(QCursor(Qt.PointingHandCursor))
        gen_btn.setStyleSheet("""
            QPushButton { color: #FFFFFF; background: #1A73E8; border: none; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #1557B0; }
        """)
        gen_btn.clicked.connect(self.do_generate)
        opt_layout.addWidget(gen_btn)

        copy_btn = QPushButton("复制全部")
        copy_btn.setFixedSize(80, 28)
        copy_btn.setCursor(QCursor(Qt.PointingHandCursor))
        copy_btn.setStyleSheet("""
            QPushButton { color: #1A73E8; background: #FFFFFF; border: 1px solid #1A73E8; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #F0F6FF; }
        """)
        copy_btn.clicked.connect(self.copy_all)
        opt_layout.addWidget(copy_btn)
        opt_layout.addStretch()
        layout.addLayout(opt_layout)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("""
            QTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; background: #FAFAFA; }
        """)
        layout.addWidget(self.result_text)

        self.do_generate()

    def do_generate(self):
        try:
            count = int(self.count_input.text().strip())
            count = max(1, min(count, 1000))
        except ValueError:
            count = 5
            self.count_input.setText("5")
        use_v1 = self.version_combo.currentIndex() == 1
        lines = []
        for _ in range(count):
            u = uuid.uuid1() if use_v1 else uuid.uuid4()
            lines.append(str(u))
        self.result_text.setPlainText('\n'.join(lines))

    def copy_all(self):
        text = self.result_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self.result_text.setToolTip("已复制")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class QrCodeWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("二维码生成")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        input_label = QLabel("内容")
        input_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        input_label.setStyleSheet("color: #333333;")
        layout.addWidget(input_label)

        self.text_input = QPlainTextEdit()
        self.text_input.setFixedHeight(90)
        self.text_input.setPlaceholderText("输入文字或链接，点击“生成”输出二维码")
        self.text_input.setStyleSheet("""
            QPlainTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; }
        """)
        layout.addWidget(self.text_input)

        btn_layout = QHBoxLayout()
        gen_btn = QPushButton("生成")
        gen_btn.setFixedSize(90, 30)
        gen_btn.setCursor(QCursor(Qt.PointingHandCursor))
        gen_btn.setStyleSheet("""
            QPushButton { color: #FFFFFF; background: #1A73E8; border: none; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #1557B0; }
        """)
        gen_btn.clicked.connect(self.do_generate)
        btn_layout.addWidget(gen_btn)

        paste_btn = QPushButton("粘贴")
        paste_btn.setFixedSize(90, 30)
        paste_btn.setCursor(QCursor(Qt.PointingHandCursor))
        paste_btn.setStyleSheet("""
            QPushButton { color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #E4E4E4; }
        """)
        paste_btn.clicked.connect(self.do_paste)
        btn_layout.addWidget(paste_btn)

        save_btn = QPushButton("保存图片")
        save_btn.setFixedSize(90, 30)
        save_btn.setCursor(QCursor(Qt.PointingHandCursor))
        save_btn.setStyleSheet("""
            QPushButton { color: #1A73E8; background: #FFFFFF; border: 1px solid #1A73E8; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #F0F6FF; }
        """)
        save_btn.clicked.connect(self.save_image)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setMinimumHeight(300)
        self.qr_label.setStyleSheet("color: #999999; font-size: 13px;")
        self.qr_label.setText("请输入内容")
        layout.addWidget(self.qr_label, 1)

        self._current_img = None

    def do_paste(self):
        text = QApplication.clipboard().text().strip()
        if text:
            self.text_input.setPlainText(text)
        self.text_input.setFocus()

    def do_generate(self):
        text = self.text_input.toPlainText().strip()
        if not text:
            self.qr_label.setText("请输入内容")
            self._current_img = None
            return
        try:
            qr = qrcode.QRCode(box_size=8, border=2)
            qr.add_data(text)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            pixmap = QPixmap()
            pixmap.loadFromData(buf.getvalue())
            scaled = pixmap.scaled(self.qr_label.width() or 320, 320,
                                   Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.qr_label.setPixmap(scaled)
            self._current_img = img
        except Exception as e:
            self.qr_label.setText(f"生成失败: {e}")

    def save_image(self):
        if self._current_img is None:
            QMessageBox.warning(self, "提示", "请先生成二维码", QMessageBox.Ok)
            return
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "保存二维码", "qrcode.png", "PNG 图片 (*.png)")
        if path:
            try:
                self._current_img.save(path)
                QMessageBox.information(self, "提示", "已保存", QMessageBox.Ok)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"保存失败: {e}", QMessageBox.Ok)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


# Code 128 条形码，自实现（不引入条码库）。表按 symbol 值索引：0..105 是六位
# “条-空”宽度（每位和=11 模块），106 是结束符（七位，和=13）。错位不会报错，
# 只会生成扫不出来的码，改动后需按值校验。
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


def _code128_values(text):
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


def _code128_widths(text):
    """返回交替的条/空宽度序列（首个为条），供逐段绘制。"""
    widths = []
    for v in _code128_values(text):
        widths.extend(int(d) for d in _CODE128_PATTERNS[v])
    widths.extend(int(d) for d in _CODE128_STOP)
    return widths


def render_code128(text, module=3, height=130):
    """用 QPainter 绘制 Code 128 位图（含底部可读文字），返回 QPixmap 原始分辨率。"""
    widths = _code128_widths(text)
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


class BarcodeWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("条形码生成")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        input_label = QLabel("内容")
        input_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        input_label.setStyleSheet("color: #333333;")
        layout.addWidget(input_label)

        self.text_input = QPlainTextEdit()
        self.text_input.setFixedHeight(90)
        self.text_input.setPlaceholderText("输入文字/链接（Code 128，可打印 ASCII）")
        self.text_input.setStyleSheet("""
            QPlainTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; }
        """)
        layout.addWidget(self.text_input)

        btn_layout = QHBoxLayout()
        gen_btn = QPushButton("生成")
        gen_btn.setFixedSize(90, 30)
        gen_btn.setCursor(QCursor(Qt.PointingHandCursor))
        gen_btn.setStyleSheet("""
            QPushButton { color: #FFFFFF; background: #1A73E8; border: none; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #1557B0; }
        """)
        gen_btn.clicked.connect(self.do_generate)
        btn_layout.addWidget(gen_btn)

        paste_btn = QPushButton("粘贴")
        paste_btn.setFixedSize(90, 30)
        paste_btn.setCursor(QCursor(Qt.PointingHandCursor))
        paste_btn.setStyleSheet("""
            QPushButton { color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #E4E4E4; }
        """)
        paste_btn.clicked.connect(self.do_paste)
        btn_layout.addWidget(paste_btn)

        save_btn = QPushButton("保存图片")
        save_btn.setFixedSize(90, 30)
        save_btn.setCursor(QCursor(Qt.PointingHandCursor))
        save_btn.setStyleSheet("""
            QPushButton { color: #1A73E8; background: #FFFFFF; border: 1px solid #1A73E8; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #F0F6FF; }
        """)
        save_btn.clicked.connect(self.save_image)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.bar_label = QLabel()
        self.bar_label.setAlignment(Qt.AlignCenter)
        self.bar_label.setMinimumHeight(240)
        self.bar_label.setStyleSheet("color: #999999; font-size: 13px;")
        self.bar_label.setText("请输入内容")
        layout.addWidget(self.bar_label, 1)

        self._current_pix = None

    def do_paste(self):
        text = QApplication.clipboard().text().strip()
        if text:
            self.text_input.setPlainText(text)
        self.text_input.setFocus()

    def do_generate(self):
        text = self.text_input.toPlainText().strip()
        if not text:
            self.bar_label.setText("请输入内容")
            self._current_pix = None
            return
        try:
            pix = render_code128(text)
        except ValueError as e:
            self.bar_label.setText(str(e))
            self._current_pix = None
            return
        self._current_pix = pix
        avail_w = self.bar_label.width() or 600
        avail_h = self.bar_label.height() or 240
        scaled = pix.scaled(max(1, avail_w - 8), max(1, avail_h - 8),
                           Qt.KeepAspectRatio, Qt.FastTransformation)
        self.bar_label.setPixmap(scaled)

    def save_image(self):
        if self._current_pix is None:
            QMessageBox.warning(self, "提示", "请先生成条形码", QMessageBox.Ok)
            return
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "保存条形码", "barcode.png", "PNG 图片 (*.png)")
        if path:
            try:
                self._current_pix.save(path, "PNG")
                QMessageBox.information(self, "提示", "已保存", QMessageBox.Ok)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"保存失败: {e}", QMessageBox.Ok)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class RegexWindow(QMainWindow):
    COMMON_PATTERNS = [
        ("常用正则...", ""),
        ("手机号", r"1[3-9]\d{9}"),
        ("邮箱", r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
        ("IP 地址", r"(\d{1,3}\.){3}\d{1,3}"),
        ("URL", r"https?://[\w\-\.]+(:\d+)?(/[^\s]*)?"),
        ("身份证号", r"\d{17}[\dXx]|\d{15}"),
        ("中文字符", r"[\u4e00-\u9fa5]+"),
        ("日期", r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"),
        ("邮政编码", r"[1-9]\d{5}"),
        ("金额", r"\d+\.\d{2}"),
        ("纯数字", r"\d+"),
        ("字母", r"[a-zA-Z]+"),
        ("空白行", r"\n\s*\n"),
        ("HTML 标签", r"<[^>]+>"),
        ("Markdown 链接", r"\[([^\]]+)\]\(([^)]+)\)"),
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("正则测试")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("常用:"))
        self.preset_combo = QComboBox()
        for label, pattern in self.COMMON_PATTERNS:
            self.preset_combo.addItem(label)
        self.preset_combo.setFixedWidth(160)
        self.preset_combo.setStyleSheet(_combo_style())
        self.preset_combo.currentIndexChanged.connect(self.on_preset_selected)
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addStretch()
        layout.addLayout(preset_layout)

        regex_layout = QHBoxLayout()
        regex_layout.addWidget(QLabel("正则:"))
        self.regex_input = QLineEdit()
        self.regex_input.setPlaceholderText("如: \\d+")
        self.regex_input.setStyleSheet("""
            QLineEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 4px 8px; font-size: 12px; }
            QLineEdit:focus { border-color: #1A73E8; }
        """)
        self.regex_input.returnPressed.connect(self.do_test)
        regex_layout.addWidget(self.regex_input)

        self.test_btn = QPushButton("测试")
        self.test_btn.setFixedSize(60, 28)
        self.test_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.test_btn.setStyleSheet("""
            QPushButton { color: #FFFFFF; background: #1A73E8; border: none; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #1557B0; }
            QPushButton:disabled { background: #CCCCCC; }
        """)
        self.test_btn.clicked.connect(self.do_test)
        regex_layout.addWidget(self.test_btn)
        layout.addLayout(regex_layout)

        text_label = QLabel("测试文本")
        text_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        text_label.setStyleSheet("color: #333333;")
        layout.addWidget(text_label)

        self.text_input = QPlainTextEdit()
        self.text_input.setStyleSheet("""
            QPlainTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; }
        """)
        layout.addWidget(self.text_input)

        result_label = QLabel("匹配结果")
        result_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        result_label.setStyleSheet("color: #333333;")
        layout.addWidget(result_label)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("""
            QTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; background: #FAFAFA; }
        """)
        layout.addWidget(self.result_text)

    def on_preset_selected(self, index):
        if index > 0:
            _, pattern = self.COMMON_PATTERNS[index]
            self.regex_input.setText(pattern)
            self.do_test()

    def do_test(self):
        pattern = self.regex_input.text().strip()
        text = self.text_input.toPlainText()
        if not pattern or not text:
            self.result_text.setPlainText("")
            return
        try:
            matches = re.findall(pattern, text)
            if matches:
                self.result_text.setPlainText(f"找到 {len(matches)} 个匹配:\n" + '\n'.join(str(m) for m in matches))
            else:
                self.result_text.setPlainText("未找到匹配")
        except re.error as e:
            self.result_text.setPlainText(f"正则错误:\n{e}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class PingWorker(QThread):
    result_ready = pyqtSignal(str)

    def __init__(self, target):
        super().__init__()
        self.target = target

    def run(self):
        system = platform.system()
        try:
            if system == "Windows":
                output = subprocess.check_output(["ping", "-n", "4", self.target], text=True, encoding="gbk", errors="ignore")
            else:
                output = subprocess.check_output(["ping", "-c", "4", self.target], text=True, errors="ignore")
            self.result_ready.emit(output)
        except subprocess.CalledProcessError as e:
            self.result_ready.emit(f"Ping 失败:\n{e.output}")
        except Exception as e:
            self.result_ready.emit(f"错误:\n{e}")


class PingWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.setWindowTitle("Ping 测试")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("目标:"))
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("如: baidu.com 或 192.168.1.1")
        self.target_input.setStyleSheet("""
            QLineEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 4px 8px; font-size: 12px; }
            QLineEdit:focus { border-color: #1A73E8; }
        """)
        self.target_input.returnPressed.connect(self.do_ping)
        input_layout.addWidget(self.target_input)

        self.ping_btn = QPushButton("Ping")
        self.ping_btn.setFixedSize(60, 28)
        self.ping_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.ping_btn.setStyleSheet("""
            QPushButton { color: #FFFFFF; background: #1A73E8; border: none; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #1557B0; }
            QPushButton:disabled { background: #CCCCCC; }
        """)
        self.ping_btn.clicked.connect(self.do_ping)
        input_layout.addWidget(self.ping_btn)
        layout.addLayout(input_layout)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("""
            QTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; background: #FAFAFA; }
        """)
        layout.addWidget(self.result_text)

    def do_ping(self):
        if not self.ping_btn.isEnabled():
            return
        target = self.target_input.text().strip()
        if not target:
            QMessageBox.warning(self, "提示", "请输入目标地址", QMessageBox.Ok)
            return
        self.result_text.setPlainText("正在 Ping...")
        self.ping_btn.setEnabled(False)
        self.worker = PingWorker(target)
        self.worker.result_ready.connect(self.on_ping_done)
        self.worker.start()

    def on_ping_done(self, output):
        self.result_text.setPlainText(output)
        self.ping_btn.setEnabled(True)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class DNSWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DNS 查询")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("域名:"))
        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText("如: baidu.com")
        self.domain_input.setStyleSheet("""
            QLineEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 4px 8px; font-size: 12px; }
            QLineEdit:focus { border-color: #1A73E8; }
        """)
        self.domain_input.returnPressed.connect(self.do_query)
        input_layout.addWidget(self.domain_input)

        self.query_btn = QPushButton("查询")
        self.query_btn.setFixedSize(60, 28)
        self.query_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.query_btn.setStyleSheet("""
            QPushButton { color: #FFFFFF; background: #1A73E8; border: none; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #1557B0; }
            QPushButton:disabled { background: #CCCCCC; }
        """)
        self.query_btn.clicked.connect(self.do_query)
        input_layout.addWidget(self.query_btn)
        layout.addLayout(input_layout)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("""
            QTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; background: #FAFAFA; }
        """)
        layout.addWidget(self.result_text)

    def do_query(self):
        if not self.query_btn.isEnabled():
            return
        domain = self.domain_input.text().strip()
        if not domain:
            QMessageBox.warning(self, "提示", "请输入域名", QMessageBox.Ok)
            return
        self.query_btn.setEnabled(False)
        try:
            results = socket.getaddrinfo(domain, None)
            output = f"域名: {domain}\n\n解析结果:\n"
            ips = set()
            for r in results:
                ip = r[4][0]
                if ip not in ips:
                    ips.add(ip)
                    output += f"  {ip}\n"
            self.result_text.setPlainText(output)
        except socket.gaierror as e:
            self.result_text.setPlainText(f"DNS 查询失败:\n{e}")
        except Exception as e:
            self.result_text.setPlainText(f"错误:\n{e}")
        finally:
            self.query_btn.setEnabled(True)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class TracerouteWorker(QThread):
    line_ready = pyqtSignal(str)
    result_ready = pyqtSignal()

    def __init__(self, target):
        super().__init__()
        self.target = target

    def run(self):
        system = platform.system()
        try:
            if system == "Windows":
                cmd = ["tracert", "-d", "-w", "2000", "-h", "20", self.target]
            else:
                cmd = ["traceroute", "-I", "-q", "1", "-w", "2", "-m", "20", self.target]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, errors="ignore")
            for line in iter(proc.stdout.readline, ''):
                if line:
                    self.line_ready.emit(line.rstrip())
            proc.wait()
            self.result_ready.emit()
        except Exception as e:
            self.line_ready.emit(f"错误:\n{e}")
            self.result_ready.emit()


class TracerouteWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.setWindowTitle("路由追踪")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("目标:"))
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("如: baidu.com")
        self.target_input.setStyleSheet("""
            QLineEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 4px 8px; font-size: 12px; }
            QLineEdit:focus { border-color: #1A73E8; }
        """)
        self.target_input.returnPressed.connect(self.do_trace)
        input_layout.addWidget(self.target_input)

        self.trace_btn = QPushButton("追踪")
        self.trace_btn.setFixedSize(60, 28)
        self.trace_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.trace_btn.setStyleSheet("""
            QPushButton { color: #FFFFFF; background: #1A73E8; border: none; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #1557B0; }
            QPushButton:disabled { background: #CCCCCC; }
        """)
        self.trace_btn.clicked.connect(self.do_trace)
        input_layout.addWidget(self.trace_btn)
        layout.addLayout(input_layout)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("""
            QTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; background: #FAFAFA; }
        """)
        layout.addWidget(self.result_text)

    def do_trace(self):
        if not self.trace_btn.isEnabled():
            return
        target = self.target_input.text().strip()
        if not target:
            QMessageBox.warning(self, "提示", "请输入目标地址", QMessageBox.Ok)
            return
        self.result_text.setPlainText("正在追踪路由...")
        self.trace_btn.setEnabled(False)
        self.worker = TracerouteWorker(target)
        self.worker.line_ready.connect(self.append_line)
        self.worker.result_ready.connect(self.on_trace_done)
        self.first_line = True
        self.worker.start()

    def append_line(self, line):
        if self.first_line:
            self.result_text.setPlainText(line)
            self.first_line = False
        else:
            self.result_text.append(line)

    def on_trace_done(self):
        self.trace_btn.setEnabled(True)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class PortScanWorker(QThread):
    scan_done = pyqtSignal(list)

    def __init__(self, target, start_port, end_port):
        super().__init__()
        self.target = target
        self.start_port = start_port
        self.end_port = end_port

    def run(self):
        open_ports = []
        for port in range(self.start_port, self.end_port + 1):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex((self.target, port))
                if result == 0:
                    open_ports.append(port)
                sock.close()
            except Exception:
                pass
        self.scan_done.emit(open_ports)


class PortScanWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.setWindowTitle("端口扫描")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("目标:"))
        self.target_input = QLineEdit()
        self.target_input.setPlaceholderText("如: 192.168.1.1")
        self.target_input.setStyleSheet("""
            QLineEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 4px 8px; font-size: 12px; }
            QLineEdit:focus { border-color: #1A73E8; }
        """)
        self.target_input.returnPressed.connect(self.do_scan)
        input_layout.addWidget(self.target_input)

        input_layout.addWidget(QLabel("端口范围:"))
        self.port_range = QLineEdit()
        self.port_range.setPlaceholderText("如: 1-1024")
        self.port_range.setFixedWidth(100)
        self.port_range.setStyleSheet("""
            QLineEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 4px 8px; font-size: 12px; }
            QLineEdit:focus { border-color: #1A73E8; }
        """)
        self.port_range.returnPressed.connect(self.do_scan)
        input_layout.addWidget(self.port_range)

        self.scan_btn = QPushButton("扫描")
        self.scan_btn.setFixedSize(60, 28)
        self.scan_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.scan_btn.setStyleSheet("""
            QPushButton { color: #FFFFFF; background: #1A73E8; border: none; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #1557B0; }
            QPushButton:disabled { background: #CCCCCC; }
        """)
        self.scan_btn.clicked.connect(self.do_scan)
        input_layout.addWidget(self.scan_btn)
        layout.addLayout(input_layout)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("""
            QTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; background: #FAFAFA; }
        """)
        layout.addWidget(self.result_text)

    def do_scan(self):
        if not self.scan_btn.isEnabled():
            return
        target = self.target_input.text().strip()
        port_range = self.port_range.text().strip()
        if not target:
            QMessageBox.warning(self, "提示", "请输入目标地址", QMessageBox.Ok)
            return
        if not port_range:
            port_range = "1-1024"
        try:
            start, end = map(int, port_range.split('-'))
        except ValueError:
            QMessageBox.warning(self, "提示", "端口范围格式错误，如: 1-1024", QMessageBox.Ok)
            return
        self.result_text.setPlainText(f"正在扫描 {target} 的端口 {start}-{end}...")
        self.scan_btn.setEnabled(False)
        self.worker = PortScanWorker(target, start, end)
        self.worker.scan_done.connect(lambda ports: self.show_scan_result(target, ports))
        self.worker.start()

    def show_scan_result(self, target, open_ports):
        if open_ports:
            output = f"目标: {target}\n开放端口:\n" + '\n'.join(f"  {p}" for p in open_ports)
        else:
            output = f"目标: {target}\n未发现开放端口"
        self.result_text.setPlainText(output)
        self.scan_btn.setEnabled(True)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class SpeedTestWorker(QThread):
    speed_done = pyqtSignal(str, str)
    progress = pyqtSignal(str)

    SAMPLE_BYTES = 8 * 1024 * 1024
    TIME_BUDGET = 20
    SOCKET_TIMEOUT = 10

    def __init__(self):
        super().__init__()
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        urls = [
            "https://speed.cloudflare.com/__down?bytes=%d" % self.SAMPLE_BYTES,
            "https://speed.hetzner.de/100MB.bin",
        ]
        last_err = None
        for url in urls:
            if self._cancelled:
                self.speed_done.emit("已取消", "")
                return
            try:
                result = self._measure(url)
                if result is None:
                    self.speed_done.emit("已取消", "")
                    return
                self.speed_done.emit("测速完成", result)
                return
            except Exception as e:
                last_err = e
        self.speed_done.emit("测速失败", "错误: %s" % last_err)

    def _measure(self, url):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        response = urllib.request.urlopen(req, timeout=self.SOCKET_TIMEOUT)
        total = 0
        start = time.perf_counter()
        last_report = start
        try:
            while total < self.SAMPLE_BYTES:
                if self._cancelled:
                    return None
                chunk = response.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                now = time.perf_counter()
                elapsed = now - start
                if now - last_report >= 0.5:
                    self.progress.emit("%s Mbps（已下载 %.1f MB）" % (
                        self._mbps(total, elapsed), total / 1048576.0))
                    last_report = now
                if elapsed >= self.TIME_BUDGET:
                    break
        finally:
            response.close()
        duration = time.perf_counter() - start
        if total == 0 or duration <= 0:
            raise RuntimeError("未收到数据")
        return "下载速度: %s Mbps\n(%.1f MB / %.1f 秒)" % (
            self._mbps(total, duration), total / 1048576.0, duration)

    @staticmethod
    def _mbps(total_bytes, seconds):
        return "%.1f" % ((total_bytes / 1048576.0 * 8) / seconds) if seconds > 0 else "0.0"


class SpeedTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.setWindowTitle("网络测速")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 10)
        layout.setSpacing(15)

        title = QLabel("网络测速")
        title.setFont(QFont("PingFang SC", 16, QFont.Bold))
        title.setStyleSheet("color: #333333;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(20)

        self.status_label = QLabel("点击开始测速")
        self.status_label.setFont(QFont("PingFang SC", 12))
        self.status_label.setStyleSheet("color: #666666;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.result_label = QLabel("")
        self.result_label.setFont(QFont("PingFang SC", 14, QFont.Bold))
        self.result_label.setStyleSheet("color: #1A73E8;")
        self.result_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.result_label)

        layout.addStretch()

        self.test_btn = QPushButton("开始测速")
        self.test_btn.setFixedSize(120, 40)
        self.test_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.test_btn.setStyleSheet("""
            QPushButton { color: #FFFFFF; background: #1A73E8; border: none; border-radius: 6px; font-size: 14px; }
            QPushButton:hover { background: #1557B0; }
            QPushButton:pressed { background: #0D47A1; }
            QPushButton:disabled { background: #CCCCCC; }
        """)
        self.test_btn.clicked.connect(self.do_test)
        layout.addWidget(self.test_btn, alignment=Qt.AlignCenter)

        layout.addStretch()

    def do_test(self):
        if self.worker is not None and self.worker.isRunning():
            self.worker.cancel()
            self.status_label.setText("正在取消...")
            return
        self.status_label.setText("正在连接测速节点...")
        self.result_label.setText("")
        self.test_btn.setText("取消")
        self.worker = SpeedTestWorker()
        self.worker.speed_done.connect(self.show_speed_result)
        self.worker.progress.connect(self.status_label.setText)
        self.worker.start()

    def show_speed_result(self, status, result):
        self.status_label.setText(status)
        self.result_label.setText(result)
        self.test_btn.setText("开始测速")

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(3000)
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class BaseConvertWindow(QMainWindow):
    BASES = [
        ("十进制", 10),
        ("二进制", 2),
        ("八进制", 8),
        ("十六进制", 16),
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("进制转换")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(12)

        combo_layout = QHBoxLayout()
        combo_layout.addWidget(QLabel("源格式:"))
        self.src_combo = QComboBox()
        for label, _ in self.BASES:
            self.src_combo.addItem(label)
        self.src_combo.currentIndexChanged.connect(self.do_convert)
        self.src_combo.setStyleSheet(_combo_style())
        combo_layout.addWidget(self.src_combo)

        self.swap_btn = QPushButton("⇄ 交换格式")
        self.swap_btn.setFixedHeight(28)
        self.swap_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.swap_btn.setStyleSheet(self._btn_style("#F0F0F0", "#333333", "#E0E0E0"))
        self.swap_btn.clicked.connect(self.do_swap)
        combo_layout.addWidget(self.swap_btn)

        combo_layout.addWidget(QLabel("目标格式:"))
        self.dst_combo = QComboBox()
        for label, _ in self.BASES:
            self.dst_combo.addItem(label)
        self.dst_combo.setCurrentText("二进制")
        self.dst_combo.currentIndexChanged.connect(self.do_convert)
        self.dst_combo.setStyleSheet(_combo_style())
        combo_layout.addWidget(self.dst_combo)
        layout.addLayout(combo_layout)

        self.input_text = QLineEdit()
        self.input_text.setPlaceholderText("输入数值...")
        self.input_text.setStyleSheet(self._input_style())
        self.input_text.textChanged.connect(self.do_convert)
        layout.addWidget(self.input_text)

        btn_layout = QHBoxLayout()
        clear_btn = QPushButton("清空")
        clear_btn.setFixedSize(80, 30)
        clear_btn.setCursor(QCursor(Qt.PointingHandCursor))
        clear_btn.setStyleSheet(self._btn_style("#F0F0F0", "#333333", "#E0E0E0"))
        clear_btn.clicked.connect(self.do_clear)
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        out_label = QLabel("转换结果")
        out_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        out_label.setStyleSheet("color: #333333;")
        layout.addWidget(out_label)

        self.output_text = QLineEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet(self._input_style() + "QLineEdit { background: #FAFAFA; }")
        layout.addWidget(self.output_text)

    def _input_style(self):
        return """
            QLineEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 6px 8px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; }
            QLineEdit:focus { border-color: #1A73E8; }
        """

    def _btn_style(self, bg, color, hover):
        return f"""
            QPushButton {{ color: {color}; background: {bg}; border: none;
                border-radius: 4px; font-size: 12px; padding: 0 10px; }}
            QPushButton:hover {{ background: {hover}; }}
        """

    def do_convert(self):
        raw = self.input_text.text().strip()
        if not raw:
            self.output_text.setText("")
            return
        src_base = self.BASES[self.src_combo.currentIndex()][1]
        dst_base = self.BASES[self.dst_combo.currentIndex()][1]
        cleaned = raw.replace("0x", "").replace("0X", "").replace(" ", "")
        try:
            value = int(cleaned, src_base)
        except ValueError:
            self.output_text.setText(f"输入不是合法的{self.BASES[self.src_combo.currentIndex()][0]}数值")
            return
        if dst_base == 10:
            result = str(value)
        elif dst_base == 2:
            result = bin(value).replace("0b", "")
        elif dst_base == 8:
            result = oct(value).replace("0o", "")
        elif dst_base == 16:
            result = hex(value).replace("0x", "").upper()
        else:
            result = str(value)
        self.output_text.setText(result)

    def do_swap(self):
        src_idx = self.src_combo.currentIndex()
        dst_idx = self.dst_combo.currentIndex()
        self.src_combo.setCurrentIndex(dst_idx)
        self.dst_combo.setCurrentIndex(src_idx)
        out_text = self.output_text.text()
        if out_text:
            self.input_text.setText(out_text)
            self.output_text.setText("")

    def do_clear(self):
        self.input_text.setText("")
        self.output_text.setText("")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class DivModWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("商余计算")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(12)

        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("被除数:"))
        self.dividend_input = QLineEdit()
        self.dividend_input.setPlaceholderText("如: 17")
        self.dividend_input.setStyleSheet(self._input_style())
        self.dividend_input.returnPressed.connect(self.do_calc)
        input_layout.addWidget(self.dividend_input)

        input_layout.addWidget(QLabel("除数:"))
        self.divisor_input = QLineEdit()
        self.divisor_input.setPlaceholderText("如: 5")
        self.divisor_input.setStyleSheet(self._input_style())
        self.divisor_input.returnPressed.connect(self.do_calc)
        input_layout.addWidget(self.divisor_input)
        layout.addLayout(input_layout)

        btn_layout = QHBoxLayout()
        calc_btn = QPushButton("计算")
        calc_btn.setFixedSize(80, 30)
        calc_btn.setCursor(QCursor(Qt.PointingHandCursor))
        calc_btn.setStyleSheet("""
            QPushButton { color: #FFFFFF; background: #1A73E8; border: none;
                border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #1557B0; }
        """)
        calc_btn.clicked.connect(self.do_calc)
        btn_layout.addWidget(calc_btn)

        clear_btn = QPushButton("清除")
        clear_btn.setFixedSize(80, 30)
        clear_btn.setCursor(QCursor(Qt.PointingHandCursor))
        clear_btn.setStyleSheet("""
            QPushButton { color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0;
                border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #E0E0E0; }
        """)
        clear_btn.clicked.connect(self.do_clear)
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        result_label = QLabel("计算结果")
        result_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        result_label.setStyleSheet("color: #333333;")
        layout.addWidget(result_label)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("""
            QTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; background: #FAFAFA; }
        """)
        layout.addWidget(self.result_text)

    def _input_style(self):
        return """
            QLineEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 6px 8px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; }
            QLineEdit:focus { border-color: #1A73E8; }
        """

    def do_calc(self):
        try:
            dividend = int(self.dividend_input.text().strip())
            divisor = int(self.divisor_input.text().strip())
        except ValueError:
            self.result_text.setPlainText("请输入整数")
            return
        if divisor == 0:
            self.result_text.setPlainText("除数不能为 0")
            return
        quotient, remainder = divmod(dividend, divisor)
        self.result_text.setPlainText(
            f"商: {quotient}\n余数: {remainder}\n\n{dividend} ÷ {divisor} = {quotient} ... {remainder}")

    def do_clear(self):
        self.dividend_input.setText("")
        self.divisor_input.setText("")
        self.result_text.setPlainText("")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class JsonYamlWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JSON ↔ YAML")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        tool_layout = QHBoxLayout()
        tool_layout.setSpacing(8)
        tools = [
            ("JSON → YAML", self.json_to_yaml),
            ("YAML → JSON", self.yaml_to_json),
            ("清空", self.do_clear),
        ]
        for text, handler in tools:
            b = QPushButton(text)
            b.setFixedHeight(28)
            b.setCursor(QCursor(Qt.PointingHandCursor))
            b.setStyleSheet("""
                QPushButton { color: #FFFFFF; background: #1A73E8; border: none;
                    border-radius: 4px; font-size: 12px; padding: 0 12px; }
                QPushButton:hover { background: #1557B0; }
            """)
            b.clicked.connect(handler)
            tool_layout.addWidget(b)
        tool_layout.addStretch()
        layout.addLayout(tool_layout)

        edit_layout = QHBoxLayout()
        left_col = QVBoxLayout()
        left_col.addWidget(QLabel("输入"))
        self.input_text = QPlainTextEdit()
        self.input_text.setStyleSheet(_plain_style())
        left_col.addWidget(self.input_text)
        edit_layout.addLayout(left_col)

        right_col = QVBoxLayout()
        right_col.addWidget(QLabel("输出"))
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet(_output_style())
        right_col.addWidget(self.output_text)
        edit_layout.addLayout(right_col)
        layout.addLayout(edit_layout)

    def json_to_yaml(self):
        raw = self.input_text.toPlainText().strip()
        if not raw:
            self.output_text.setPlainText("")
            return
        try:
            data = json.loads(raw)
            self.output_text.setPlainText(yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False))
        except Exception as e:
            self.output_text.setPlainText(f"JSON 解析错误:\n{e}")

    def yaml_to_json(self):
        raw = self.input_text.toPlainText().strip()
        if not raw:
            self.output_text.setPlainText("")
            return
        try:
            data = yaml.safe_load(raw)
            self.output_text.setPlainText(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception as e:
            self.output_text.setPlainText(f"YAML 解析错误:\n{e}")

    def do_clear(self):
        self.input_text.setPlainText("")
        self.output_text.setPlainText("")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


POSIX_ENV_FILE = os.path.join(os.path.expanduser("~"), ".personal_toolbox", "env.sh")
POSIX_RC_MARKER = "# personal_toolbox env"
SHELL_RC_FILES = (".zshrc", ".bashrc")
WIN_ENV_SUBKEY = "Environment"
ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def user_env_location():
    return r"HKCU\Environment" if os.name == "nt" else POSIX_ENV_FILE


def load_user_env():
    return _win_load_env() if os.name == "nt" else _posix_load_env()


def save_user_env(name, value):
    if os.name == "nt":
        _win_save_env(name, value)
        _win_broadcast_env()
    else:
        items = _posix_load_env()
        items[name] = value
        _posix_write_env(items)
    os.environ[name] = value


def remove_user_env(name):
    if os.name == "nt":
        _win_remove_env(name)
        _win_broadcast_env()
    else:
        items = _posix_load_env()
        items.pop(name, None)
        _posix_write_env(items)
    os.environ.pop(name, None)


def _win_load_env():
    import winreg
    items = {}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WIN_ENV_SUBKEY) as key:
            for i in range(winreg.QueryInfoKey(key)[1]):
                name, value, _type = winreg.EnumValue(key, i)
                items[name] = value
    except OSError:
        pass
    return items


def _win_save_env(name, value):
    import winreg
    # %VAR% references only survive as REG_EXPAND_SZ; REG_SZ would freeze them literally.
    vtype = winreg.REG_EXPAND_SZ if "%" in value else winreg.REG_SZ
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, WIN_ENV_SUBKEY) as key:
        winreg.SetValueEx(key, name, 0, vtype, value)


def _win_remove_env(name):
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WIN_ENV_SUBKEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.DeleteValue(key, name)


def _win_broadcast_env():
    """Tell running shells/Explorer to reload the environment; best effort."""
    _win_broadcast_setting("Environment")


def _posix_load_env():
    items = {}
    try:
        with open(POSIX_ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line.startswith("export "):
                    continue
                name, sep, raw = line[len("export "):].partition("=")
                if not sep or not ENV_NAME_RE.match(name):
                    continue
                try:
                    # shlex does not treat "=" as a separator, so unquote the value alone.
                    parts = shlex.split(raw)
                except ValueError:
                    continue
                items[name] = parts[0] if parts else ""
    except OSError:
        pass
    return items


def _posix_write_env(items):
    try:
        os.makedirs(os.path.dirname(POSIX_ENV_FILE), exist_ok=True)
        with open(POSIX_ENV_FILE, "w", encoding="utf-8") as f:
            for name in sorted(items):
                f.write("export %s=%s\n" % (name, shlex.quote(items[name])))
    except OSError as e:
        raise RuntimeError("无法写入 %s: %s" % (POSIX_ENV_FILE, e))
    _posix_ensure_rc()


def _posix_ensure_rc():
    """Source the env file from interactive shells, once per rc file."""
    for rc in SHELL_RC_FILES:
        path = os.path.join(os.path.expanduser("~"), rc)
        try:
            existing = ""
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    existing = f.read()
            if POSIX_RC_MARKER in existing:
                continue
            with open(path, "a", encoding="utf-8") as f:
                f.write("\n%s\n. %s\n" % (POSIX_RC_MARKER, shlex.quote(POSIX_ENV_FILE)))
        except OSError:
            continue


class _ProcessEnvPage(QWidget):
    """当前进程看到的环境变量快照，只读。"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索变量名或值...")
        self.search_input.setStyleSheet(_lineedit_style())
        self.search_input.textChanged.connect(self.filter_vars)
        layout.addWidget(self.search_input)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet(_output_style())
        layout.addWidget(self.result_text)

        self._all_vars = dict(os.environ)
        self.filter_vars()

    def filter_vars(self):
        keyword = self.search_input.text().strip().lower()
        lines = []
        for k in sorted(self._all_vars.keys()):
            v = self._all_vars[k]
            if not keyword or keyword in k.lower() or keyword in v.lower():
                lines.append(f"{k} = {v}")
        self.result_text.setPlainText('\n'.join(lines) if lines else "无匹配变量")


class _UserEnvPage(QWidget):
    """增删改用户级环境变量：Windows 落到注册表，macOS/Linux 写入 env.sh 并由 shell 加载。"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        row = QHBoxLayout()
        for text, slot, primary in (("添加", self.do_add, True), ("修改", self.do_edit, False),
                                    ("删除", self.do_delete, False), ("终端查看", self.open_terminal, False),
                                    ("刷新", self.refresh, False)):
            btn = QPushButton(text)
            btn.setFixedSize(72, 30)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setStyleSheet(_primary_btn() if primary else _secondary_btn())
            btn.clicked.connect(slot)
            row.addWidget(btn)
        row.addStretch()
        location = QLabel("保存位置: " + user_env_location())
        location.setStyleSheet("color: #999999; font-family: 'PingFang SC'; font-size: 11px;")
        row.addWidget(location)
        layout.addLayout(row)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索变量名或值...")
        self.search_input.setStyleSheet(_lineedit_style())
        self.search_input.textChanged.connect(self.refresh)
        layout.addWidget(self.search_input)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget { border: 1px solid #D0D0D0; border-radius: 6px; background: #FAFAFA;
                font-family: "Menlo", "Consolas", monospace; font-size: 12px; color: #333333; }
            QListWidget::item { padding: 4px 8px; }
            QListWidget::item:selected { background: #E8F0FE; color: #1A73E8; }
        """)
        layout.addWidget(self.list_widget)

        self.status_label = QLabel("双击条目可直接修改。")
        self.status_label.setStyleSheet("color: #999999; font-family: 'PingFang SC'; font-size: 12px;")
        layout.addWidget(self.status_label)

        self._items = {}
        self.list_widget.itemDoubleClicked.connect(lambda _i: self.do_edit())
        self.refresh()

    def _set_status(self, text, color):
        self.status_label.setText(text)
        self.status_label.setStyleSheet("color: %s; font-family: 'PingFang SC'; font-size: 12px;" % color)

    def refresh(self):
        self._items = load_user_env()
        keyword = self.search_input.text().strip().lower()
        self.list_widget.clear()
        for name in sorted(self._items, key=str.upper):
            value = self._items[name]
            if keyword and keyword not in name.lower() and keyword not in value.lower():
                continue
            item = QListWidgetItem("%s = %s" % (name, value))
            item.setData(Qt.UserRole, name)
            self.list_widget.addItem(item)
        if not self.list_widget.count():
            self.list_widget.addItem(QListWidgetItem("无匹配变量"))

    def _selected_name(self):
        item = self.list_widget.currentItem()
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def do_add(self):
        name, ok = QInputDialog.getText(self, "添加环境变量", "变量名 (如 MY_TOOL):")
        name = name.strip()
        if not ok or not self._check_name(name):
            return
        if name in self._items:
            answer = QMessageBox.question(
                self, "已存在", "%s 已存在，覆盖其值？" % name,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                return
        value = self._ask_value(name, self._items.get(name, ""))
        if value is None:
            return
        self._apply(name, value, "已保存")

    def do_edit(self):
        name = self._selected_name()
        if not name:
            self._set_status("请先选中一个变量。", "#D93025")
            return
        value = self._ask_value(name, self._items.get(name, ""))
        if value is None:
            return
        self._apply(name, value, "已更新")

    def do_delete(self):
        name = self._selected_name()
        if not name:
            self._set_status("请先选中一个变量。", "#D93025")
            return
        answer = QMessageBox.question(
            self, "删除确认",
            "从用户环境变量中删除 %s？\n已打开的程序不会立即感知，需要重启。" % name,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        try:
            remove_user_env(name)
        except Exception as e:
            self._fail("删除失败", e)
            return
        self.refresh()
        self._set_status("已删除 %s。" % name, "#188038")

    def open_terminal(self):
        name, ok = QInputDialog.getText(
            self, "在终端中查看", "变量名:", QLineEdit.Normal, self._selected_name() or "")
        name = name.strip()
        if not ok or not name:
            return
        if not ENV_NAME_RE.match(name):
            self._set_status("变量名不合法，无法传给终端。", "#D93025")
            return
        try:
            self._launch_terminal(name)
        except OSError as e:
            self._set_status("打开终端失败: %s" % e, "#D93025")
            QMessageBox.warning(self, "打开终端失败", str(e), QMessageBox.Ok)
        else:
            self._set_status("已在新终端中展示 %s。" % name, "#188038")

    def _launch_terminal(self, name):
        if os.name == "nt":
            # The new console inherits this process's snapshot, so pull the
            # persistent values in first; otherwise vars set elsewhere look unset.
            os.environ.update(load_user_env())
            return subprocess.Popen(["cmd.exe", "/k", self._cmd_show(name)],
                                    creationflags=subprocess.CREATE_NEW_CONSOLE)
        command = '%s; exec "${SHELL:-bash}" -i' % self._shell_show(name)
        if sys.platform == "darwin":
            script = command.replace("\\", "\\\\").replace('"', '\\"')
            return subprocess.Popen(["osascript", "-e",
                                     'tell application "Terminal" to do script "%s"' % script,
                                     "-e", 'tell application "Terminal" to activate'])
        for term in ("x-terminal-emulator", "gnome-terminal", "konsole", "xterm"):
            if shutil.which(term):
                flag = "--" if term == "gnome-terminal" else "-e"
                return subprocess.Popen([term, flag, "sh", "-c", command])
        raise OSError("未找到可用的终端程序，请手动执行: %s" % command)

    @staticmethod
    def _cmd_show(name):
        # "if %NAME%==""" cannot detect an undefined variable here: on cmd's command
        # line an undefined %NAME% stays literal instead of expanding to empty.
        return ('@echo off & title 环境变量 %s & '
                'if defined %s (echo %s = %%%s%%) else (echo %s 未在此终端的环境中)'
                % (name, name, name, name, name))

    @staticmethod
    def _shell_show(name):
        return ('. %s 2>/dev/null; echo "%s = $%s"'
                % (shlex.quote(POSIX_ENV_FILE), name, name))

    def _path_mode(self):
        box = QMessageBox(self)
        box.setWindowTitle("PATH 处理")
        box.setText("已有用户级 PATH。\n追加＝把新值拼到末尾；整条覆盖＝用新值替换整个 PATH。")
        append_btn = box.addButton("追加到末尾", QMessageBox.AcceptRole)
        overwrite_btn = box.addButton("整条覆盖", QMessageBox.DestructiveRole)
        box.addButton("取消", QMessageBox.RejectRole)
        box.setDefaultButton(append_btn)
        box.exec_()
        clicked = box.clickedButton()
        if clicked is append_btn:
            return "append"
        if clicked is overwrite_btn:
            return "overwrite"
        return None

    def _ask_value(self, name, current):
        mode = "set"
        prefill = current
        if name.upper() == "PATH" and current:
            mode = self._path_mode()
            if mode is None:
                return None
            if mode == "append":
                prefill = ""
        text, ok = QInputDialog.getText(self, "变量值", "%s 的值:" % name, QLineEdit.Normal, prefill)
        if not ok:
            return None
        if mode == "append":
            if not text.strip():
                return current
            return current.rstrip(os.pathsep) + os.pathsep + text.strip().strip(os.pathsep)
        return text

    def _apply(self, name, value, verb):
        if "\n" in value:
            self._set_status("变量值不能包含换行。", "#D93025")
            return
        try:
            save_user_env(name, value)
        except Exception as e:
            self._fail("保存失败", e)
            return
        self.refresh()
        self._set_status("%s %s = %s（%s）" % (verb, name, value, user_env_location()), "#188038")

    def _check_name(self, name):
        if not name:
            return False
        if not ENV_NAME_RE.match(name):
            self._set_status("变量名只能由字母、数字、下划线组成，且不能以数字开头。", "#D93025")
            return False
        return True

    def _fail(self, title, error):
        self._set_status("%s: %s" % (title, error), "#D93025")
        QMessageBox.warning(self, title, str(error), QMessageBox.Ok)


def git_global_path():
    override = os.environ.get("GIT_CONFIG_GLOBAL")
    if override:
        return override
    return os.path.join(os.path.expanduser("~"), ".gitconfig")


def _refresh_path_from_system():
    """Windows 上从注册表重新读取 PATH，识别新安装的工具（如 git）。"""
    if os.name != "nt":
        return
    try:
        import winreg
        # 系统 PATH
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                           r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as key:
            sys_path, _ = winreg.QueryValueEx(key, "Path")
        # 用户 PATH
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            usr_path, _ = winreg.QueryValueEx(key, "Path")
        # 合并并更新当前进程的环境变量
        os.environ["PATH"] = sys_path + ";" + usr_path
    except Exception:
        pass


def _run_git(args):
    try:
        return subprocess.run(["git", "config"] + args, capture_output=True,
                              encoding="utf-8", errors="replace", **win_no_console())
    except OSError:
        raise RuntimeError("未找到 git 命令，请确认已安装 Git 并在 PATH 中")


def _git_error(result):
    return (result.stderr or "").strip() or "git config 执行失败"


def git_global_list():
    _refresh_path_from_system()
    if shutil.which("git") is None:
        raise RuntimeError("未找到 git 命令，请确认已安装 Git 并在 PATH 中")
    # git exits 128 on a missing file and 1 on an empty one; neither is an error here.
    if not os.path.exists(git_global_path()):
        return []
    result = _run_git(["--global", "--list"])
    if result.returncode not in (0, 1):
        raise RuntimeError(_git_error(result))
    pairs = []
    for line in (result.stdout or "").splitlines():
        key, sep, value = line.partition("=")
        if sep:
            pairs.append((key, value))
    return pairs


def git_global_set(key, value):
    _refresh_path_from_system()
    result = _run_git(["--global", key, value])
    if result.returncode != 0:
        raise RuntimeError(_git_error(result))


def git_global_unset(key):
    _refresh_path_from_system()
    # rc 1 = no entries left in the file, rc 5 = that key was not set. Both are no-ops.
    result = _run_git(["--global", "--unset-all", key])
    if result.returncode not in (0, 1, 5):
        raise RuntimeError(_git_error(result))


GIT_KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]*(\.[A-Za-z0-9._-]+)*$")


class _GitConfigPage(QWidget):
    """全局 Git 配置：查看、设置、删除写进 ~/.gitconfig 的键值。"""

    def __init__(self):
        super().__init__()
        self.init_ui()
        self.refresh()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        row = QHBoxLayout()
        for text, slot, primary in (
                ("设置身份", self.set_identity, True),
                ("添加配置项", self.do_add, False),
                ("删除选中", self.do_delete, False),
                ("刷新", self.refresh, False),
                ("下载 Git", self.open_git_download, False)):
            btn = QPushButton(text)
            btn.setFixedHeight(30)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setStyleSheet(_primary_btn() if primary else _secondary_btn())
            btn.clicked.connect(slot)
            row.addWidget(btn)
        row.addStretch()
        location = QLabel("保存位置: " + git_global_path())
        location.setStyleSheet("color: #999999; font-family: 'PingFang SC'; font-size: 11px;")
        row.addWidget(location)
        layout.addLayout(row)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索配置项或值...")
        self.search_input.setStyleSheet(_lineedit_style())
        self.search_input.textChanged.connect(self.refresh)
        layout.addWidget(self.search_input)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget { border: 1px solid #D0D0D0; border-radius: 6px; background: #FAFAFA;
                font-family: "Menlo", "Consolas", monospace; font-size: 12px; color: #333333; }
            QListWidget::item { padding: 4px 8px; }
            QListWidget::item:selected { background: #E8F0FE; color: #1A73E8; }
        """)
        layout.addWidget(self.list_widget)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #999999; font-family: 'PingFang SC'; font-size: 12px;")
        layout.addWidget(self.status_label)

        self.list_widget.itemDoubleClicked.connect(lambda _i: self.do_edit())

    def _set_status(self, text, color):
        self.status_label.setText(text)
        self.status_label.setStyleSheet("color: %s; font-family: 'PingFang SC'; font-size: 12px;" % color)

    def open_git_download(self):
        QDesktopServices.openUrl(QUrl("https://git-scm.com/downloads"))

    def refresh(self):
        try:
            entries = git_global_list()
        except RuntimeError as e:
            self._entries = []
            self.list_widget.clear()
            self.list_widget.addItem(QListWidgetItem(str(e)))
            self._set_status(str(e), "#D93025")
            return
        self._entries = entries
        keyword = self.search_input.text().strip().lower()
        self.list_widget.clear()
        for key, value in entries:
            if keyword and keyword not in key.lower() and keyword not in value.lower():
                continue
            item = QListWidgetItem("%s = %s" % (key, value))
            item.setData(Qt.UserRole, key)
            self.list_widget.addItem(item)
        if not self.list_widget.count():
            self.list_widget.addItem(QListWidgetItem("全局配置中没有匹配项"))
        self._set_status("共 %d 项配置。双击条目可直接修改。" % len(entries), "#999999")

    def _current_of(self, key):
        value = ""
        for name, raw in self._entries:
            if name == key:
                value = raw
        return value

    def _selected_key(self):
        item = self.list_widget.currentItem()
        return None if item is None else item.data(Qt.UserRole)

    def set_key(self, key):
        current = self._current_of(key)
        value, ok = QInputDialog.getText(self, "设置 %s" % key, "%s 的值:" % key,
                                        QLineEdit.Normal, current)
        if not ok:
            return
        if not value.strip():
            self._set_status("%s 不能为空。" % key, "#D93025")
            return
        if key == "user.email" and "@" not in value:
            answer = QMessageBox.question(
                self, "确认邮箱", "%s 不含 @，看起来不像邮箱地址。\n仍要保存吗？" % value,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                return
        self._write(key, value)

    def set_identity(self):
        """一次性设置 user.name 和 user.email。"""
        dlg = QDialog(self)
        dlg.setWindowTitle("设置 Git 身份")
        dlg.setFixedWidth(360)
        form = QFormLayout(dlg)
        form.setContentsMargins(16, 16, 16, 12)
        form.setSpacing(10)

        name_edit = QLineEdit(self._current_of("user.name"))
        name_edit.setPlaceholderText("如 Zhang San")
        name_edit.setStyleSheet(_lineedit_style())
        form.addRow("用户名 (user.name)", name_edit)

        email_edit = QLineEdit(self._current_of("user.email"))
        email_edit.setPlaceholderText("如 zhangsan@example.com")
        email_edit.setStyleSheet(_lineedit_style())
        form.addRow("邮箱 (user.email)", email_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)

        if dlg.exec_() != QDialog.Accepted:
            return

        name = name_edit.text().strip()
        email = email_edit.text().strip()

        if not name:
            self._set_status("用户名不能为空。", "#D93025")
            return
        if not email:
            self._set_status("邮箱不能为空。", "#D93025")
            return
        if "@" not in email:
            answer = QMessageBox.question(
                self, "确认邮箱", "%s 不含 @，看起来不像邮箱地址。\n仍要保存吗？" % email,
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                return

        try:
            git_global_set("user.name", name)
            git_global_set("user.email", email)
        except RuntimeError as e:
            self._fail("保存失败", e)
            return
        self.refresh()
        self._set_status("已保存 user.name = %s，user.email = %s（%s）"
                         % (name, email, git_global_path()), "#188038")

    def do_add(self):
        key, ok = QInputDialog.getText(self, "添加配置项", "配置项 (如 core.editor):")
        key = key.strip()
        if not ok or not key:
            return
        if not GIT_KEY_RE.match(key):
            self._set_status("配置项格式不对，应形如 core.editor 或 url.<base>.insteadOf。", "#D93025")
            return
        self.set_key(key)

    def do_edit(self):
        key = self._selected_key()
        if not key:
            self._set_status("请先选中一个配置项。", "#D93025")
            return
        self.set_key(key)

    def do_delete(self):
        key = self._selected_key()
        if not key:
            self._set_status("请先选中要删除的配置项。", "#D93025")
            return
        answer = QMessageBox.question(
            self, "删除确认", "从全局配置中删除 %s？\n该文件里所有同名条目都会被移除。" % key,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        try:
            git_global_unset(key)
        except RuntimeError as e:
            self._fail("删除失败", e)
            return
        self.refresh()
        self._set_status("已删除 %s。" % key, "#188038")

    def _write(self, key, value):
        if "\n" in value:
            self._set_status("配置值不能包含换行。", "#D93025")
            return
        try:
            git_global_set(key, value)
        except RuntimeError as e:
            self._fail("保存失败", e)
            return
        self.refresh()
        self._set_status("已保存 %s = %s（%s）" % (key, value, git_global_path()), "#188038")

    def _fail(self, title, error):
        self._set_status("%s: %s" % (title, error), "#D93025")
        QMessageBox.warning(self, title, str(error), QMessageBox.Ok)


# 每类：标签、单位列表、折算到基准单位的因子、默认选中的单位
UNIT_CATEGORIES = (
    ("字节", ("B", "KB", "MB", "GB", "TB", "PB"),
     tuple(1024 ** i for i in range(6)), "B"),
    ("时间", ("纳秒", "微秒", "毫秒", "秒", "分钟", "小时", "天"),
     (1, 1000, 1000000, 1000000000, 60000000000, 3600000000000, 86400000000000), "秒"),
    ("长度", ("微米", "毫米", "厘米", "米", "千米", "英寸", "英尺", "码", "英里"),
     (1e-6, 0.001, 0.01, 1, 1000, 0.0254, 0.3048, 0.9144, 1609.344), "米"),
    ("重量", ("毫克", "克", "千克", "吨", "斤", "盎司", "磅"),
     (1e-6, 0.001, 1, 1000, 0.5, 0.028349523125, 0.45359237), "克"),
    ("面积", ("平方厘米", "平方米", "平方千米", "亩", "公顷", "平方英寸", "平方英尺", "英亩"),
     (0.0001, 1, 1000000, 2000.0 / 3.0, 10000, 0.00064516, 0.09290304, 4046.8564224), "平方米"),
    ("体积", ("毫升", "升", "立方米", "立方英寸", "立方英尺", "加仑(美)", "液量盎司(美)"),
     (0.001, 1, 1000, 0.016387064, 28.316846592, 3.785411784, 0.0295735295625), "升"),
    ("速度", ("米/秒", "千米/时", "英里/时", "节", "英尺/秒"),
     (1, 1000.0 / 3600.0, 0.44704, 1852.0 / 3600.0, 0.3048), "千米/时"),
)

TEMP_UNITS = ("℃", "℉", "K")


def _ratio_converters(factors):
    """乘数类单位：先折算到该类的基准单位，再从基准单位摊回每个目标单位。"""
    return ([lambda v, f=f: v * f for f in factors],
            [lambda t, f=f: t / f for f in factors])


def _temp_converters():
    """温度有偏移量，套不进乘数：℉ 和 K 都先折回 ℃（℃ 就是这类的基准）。"""
    return ([lambda v: v,
             lambda v: (v - 32) * 5.0 / 9.0,
             lambda v: v - 273.15],
            [lambda c: c,
             lambda c: c * 9.0 / 5.0 + 32,
             lambda c: c + 273.15])


class _UnitConvertPage(QWidget):
    """一个换算类别：输入数值和源单位，一次列出该类别下所有单位的结果。"""

    def __init__(self, units, to_base, from_base, default_unit=None):
        super().__init__()
        self._units = units
        self._to_base = to_base
        self._from_base = from_base

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        row = QHBoxLayout()
        row.addWidget(QLabel("数值:"))
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("输入数值...")
        self.value_input.setStyleSheet(_lineedit_style())
        self.value_input.textChanged.connect(self.do_convert)
        row.addWidget(self.value_input, 1)
        self.src_combo = QComboBox()
        self.src_combo.addItems(units)
        if default_unit in units:
            self.src_combo.setCurrentIndex(units.index(default_unit))
        self.src_combo.setStyleSheet(_combo_style())
        self.src_combo.currentIndexChanged.connect(self.do_convert)
        row.addWidget(self.src_combo)
        layout.addLayout(row)

        result_label = QLabel("换算结果")
        result_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        result_label.setStyleSheet("color: #333333;")
        layout.addWidget(result_label)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet(_output_style())
        layout.addWidget(self.result_text)

        clear_btn = QPushButton("清空")
        clear_btn.setFixedSize(80, 30)
        clear_btn.setCursor(QCursor(Qt.PointingHandCursor))
        clear_btn.setStyleSheet(_secondary_btn())
        clear_btn.clicked.connect(self.do_clear)
        layout.addWidget(clear_btn)

    def do_convert(self):
        raw = self.value_input.text().strip()
        if not raw:
            self.result_text.setPlainText("")
            return
        try:
            val = float(raw)
        except ValueError:
            self.result_text.setPlainText("请输入有效数字")
            return
        total = self._to_base[self.src_combo.currentIndex()](val)
        lines = ["%s %s" % (self._fmt(self._from_base[i](total)), unit)
                 for i, unit in enumerate(self._units)]
        self.result_text.setPlainText("\n".join(lines))

    def do_clear(self):
        self.value_input.clear()
        self.result_text.setPlainText("")

    @staticmethod
    def _fmt(v):
        if abs(v) < 1e15 and v == int(v):
            return str(int(v))
        return "%.6g" % v


class UnitConvertWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("单位转换")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        tabs = QTabWidget()
        tabs.setStyleSheet(_tab_style())
        for name, units, factors, default_unit in UNIT_CATEGORIES:
            tabs.addTab(_UnitConvertPage(units, *_ratio_converters(factors), default_unit), name)
        tabs.addTab(_UnitConvertPage(TEMP_UNITS, *_temp_converters()), "温度")
        self.setCentralWidget(tabs)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class RandomWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("随机数生成")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(12)

        range_layout = QHBoxLayout()
        range_layout.addWidget(QLabel("最小:"))
        self.min_input = QLineEdit("1")
        self.min_input.setStyleSheet(_lineedit_style())
        range_layout.addWidget(self.min_input)
        range_layout.addWidget(QLabel("最大:"))
        self.max_input = QLineEdit("100")
        self.max_input.setStyleSheet(_lineedit_style())
        range_layout.addWidget(self.max_input)
        range_layout.addWidget(QLabel("个数:"))
        self.count_input = QLineEdit("5")
        self.count_input.setStyleSheet(_lineedit_style())
        range_layout.addWidget(self.count_input)
        layout.addLayout(range_layout)

        opt_layout = QHBoxLayout()
        self.repeat_check = QCheckBox("可重复")
        self.repeat_check.setStyleSheet("QCheckBox { font-size: 12px; }")
        opt_layout.addWidget(self.repeat_check)
        opt_layout.addStretch()
        layout.addLayout(opt_layout)

        btn_layout = QHBoxLayout()
        gen_btn = QPushButton("生成")
        gen_btn.setFixedHeight(30)
        gen_btn.setCursor(QCursor(Qt.PointingHandCursor))
        gen_btn.setStyleSheet(_primary_btn())
        gen_btn.clicked.connect(self.do_generate)
        btn_layout.addWidget(gen_btn)
        copy_btn = QPushButton("复制")
        copy_btn.setFixedHeight(30)
        copy_btn.setCursor(QCursor(Qt.PointingHandCursor))
        copy_btn.setStyleSheet(_secondary_btn())
        copy_btn.clicked.connect(self.copy_all)
        btn_layout.addWidget(copy_btn)
        clear_btn = QPushButton("清空")
        clear_btn.setFixedHeight(30)
        clear_btn.setCursor(QCursor(Qt.PointingHandCursor))
        clear_btn.setStyleSheet(_secondary_btn())
        clear_btn.clicked.connect(self.do_clear)
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet(_output_style())
        layout.addWidget(self.result_text)

    def do_generate(self):
        try:
            lo = int(self.min_input.text().strip())
            hi = int(self.max_input.text().strip())
            count = int(self.count_input.text().strip())
        except ValueError:
            self.result_text.setPlainText("请输入有效整数")
            return
        if lo > hi:
            lo, hi = hi, lo
        if count < 1:
            count = 1
        count = min(count, 10000)
        if self.repeat_check.isChecked():
            nums = [random.randint(lo, hi) for _ in range(count)]
        else:
            span = hi - lo + 1
            if count > span:
                self.result_text.setPlainText(f"不重复个数超出范围（最多 {span} 个）")
                return
            nums = random.sample(range(lo, hi + 1), count)
        self.result_text.setPlainText(', '.join(str(n) for n in nums))

    def copy_all(self):
        text = self.result_text.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def do_clear(self):
        self.result_text.setPlainText("")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


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


def _mac_cover_menu_bar(widget):
    """把原生 NSWindow 抬到菜单栏之上（屏幕保护程序用的 window level），
    并让它覆盖所有 Space。纯 Qt 无法盖住 macOS 系统菜单栏，必须走 AppKit。"""
    import ctypes
    import ctypes.util
    objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
    objc.sel_registerName.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]
    objc.objc_msgSend.restype = ctypes.c_void_p
    objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

    def sel(name):
        return objc.sel_registerName(name.encode())

    view_ptr = int(widget.winId())
    window = objc.objc_msgSend(view_ptr, sel("window"))
    if not window:
        return False

    cg = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreGraphics"))
    cg.CGShieldingWindowLevel.restype = ctypes.c_int
    level = cg.CGShieldingWindowLevel()

    objc.objc_msgSend.restype = ctypes.c_void_p
    objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_longlong]
    # NSWindowCollectionBehavior: CanJoinAllSpaces(1<<0) | Stationary(1<<2) | FullScreenAuxiliary(1<<7)
    behavior = (1 << 0) | (1 << 2) | (1 << 7)
    objc.objc_msgSend(window, sel("setCollectionBehavior:"), behavior)
    objc.objc_msgSend(window, sel("setLevel:"), level)

    objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
    objc.objc_msgSend(window, sel("setHidesOnDeactivate:"), 0)
    return True


def _mac_picker_nonactivating(widget):
    """把取色罩抬到菜单栏之上并覆盖所有 Space，但只 orderFront、不 makeKey、不 activate：
    被取色的应用保持原样停在最前，不会退到后台。键盘退出靠 HID 键态轮询。"""
    import ctypes
    import ctypes.util
    objc = _mac_objc_runtime()
    send = objc.objc_msgSend
    send.restype = ctypes.c_void_p
    send.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    view = int(widget.winId())
    window = send(view, objc.sel_registerName(b"window"))
    if not window:
        return False
    cg = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreGraphics"))
    cg.CGShieldingWindowLevel.restype = ctypes.c_int
    send.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_longlong]
    send(window, objc.sel_registerName(b"setLevel:"), cg.CGShieldingWindowLevel())
    send(window, objc.sel_registerName(b"setCollectionBehavior:"),
         (1 << 0) | (1 << 2) | (1 << 7))
    send.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
    send(window, objc.sel_registerName(b"setHidesOnDeactivate:"), 0)
    # 关掉原生投影：否则首帧 loupe 的阴影会缓存成糊在初始位置的"影子"
    send(window, objc.sel_registerName(b"setHasShadow:"), 0)
    send.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    send(window, objc.sel_registerName(b"orderFront:"), None)
    return True


def _mac_objc_runtime():
    import ctypes
    import ctypes.util
    objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
    objc.sel_registerName.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]
    objc.objc_getClass.restype = ctypes.c_void_p
    objc.objc_getClass.argtypes = [ctypes.c_char_p]
    return objc


def _mac_is_cocoa():
    return platform.system() == "Darwin" and QApplication.platformName() == "cocoa"


def _mac_frontmost_pid():
    """提醒弹出时用户正在用的 app 的 PID；本进程或取不到时返回 None。"""
    if not _mac_is_cocoa():
        return None
    import ctypes
    try:
        objc = _mac_objc_runtime()
        send = objc.objc_msgSend
        send.restype = ctypes.c_void_p
        send.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        workspace = send(objc.objc_getClass(b"NSWorkspace"),
                         objc.sel_registerName(b"sharedWorkspace"))
        app = send(workspace, objc.sel_registerName(b"frontmostApplication"))
        if not app:
            return None
        send.restype = ctypes.c_int
        pid = send(app, objc.sel_registerName(b"processIdentifier"))
    except Exception:
        return None
    return pid if pid > 0 and pid != os.getpid() else None


def _mac_reactivate(pid):
    """把前台交还给指定 PID 的 app：点掉提醒卡片不该顺手把工具箱吊起来。"""
    if not pid or pid <= 0 or not _mac_is_cocoa():
        return False
    import ctypes
    try:
        objc = _mac_objc_runtime()
        send = objc.objc_msgSend
        send.restype = ctypes.c_void_p
        send.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
        app = send(objc.objc_getClass(b"NSRunningApplication"),
                   objc.sel_registerName(b"runningApplicationWithProcessIdentifier:"), int(pid))
        if not app:
            return False

        # macOS 14 起 activateWithOptions: 换成 activate；探测后再调，
        # 命中不存在的 selector 是 doesNotRecognizeSelector，Python 抓不到直接 abort。
        send.restype = ctypes.c_bool
        send.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        probe = objc.sel_registerName(b"respondsToSelector:")
        if send(app, probe, objc.sel_registerName(b"activate")):
            send.restype = ctypes.c_bool
            send.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
            return bool(send(app, objc.sel_registerName(b"activate")))
        if send(app, probe, objc.sel_registerName(b"activateWithOptions:")):
            send.restype = ctypes.c_bool
            send.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
            # NSApplicationActivateIgnoringOtherApps
            return bool(send(app, objc.sel_registerName(b"activateWithOptions:"), 1 << 1))
    except Exception:
        return False
    return False


class MatrixRainOverlay(QWidget):
    """全屏黑客帝国代码雨覆盖层，置顶并覆盖菜单栏；ESC 或双击任意处关闭。"""

    def __init__(self, on_close=None):
        super().__init__()
        self._on_close = on_close
        self._canvas = None
        self._drops = []
        self._cols = 0
        self._rows = 0
        self._cw = 18
        self._ch = 22
        self._chars = ["0", "1"]
        self._font = QFont("Menlo", 15)
        self._font.setStyleHint(QFont.Monospace)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setFocusPolicy(Qt.StrongFocus)
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._step)

    def start(self):
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self._rebuild_canvas()
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()
        if platform.system() == "Darwin" and QApplication.platformName() == "cocoa":
            try:
                _mac_cover_menu_bar(self)
            except Exception:
                pass
        self._timer.start()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _rebuild_canvas(self):
        w = max(self.width(), 1)
        h = max(self.height(), 1)
        self._canvas = QPixmap(w, h)
        p = QPainter(self._canvas)
        p.fillRect(self._canvas.rect(), QColor(0, 0, 0))
        p.end()
        self._cols = w // self._cw + 1
        self._rows = h // self._ch + 1
        self._drops = [random.randint(0, self._rows) for _ in range(self._cols)]

    def resizeEvent(self, e):
        if self._canvas is not None:
            self._rebuild_canvas()

    def _step(self):
        if self._canvas is None:
            return
        p = QPainter(self._canvas)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 40))
        p.drawRect(self._canvas.rect())
        p.setFont(self._font)
        for i in range(self._cols):
            ch = random.choice(self._chars)
            x = i * self._cw
            y = self._drops[i] * self._ch
            p.setPen(QColor(180, 255, 180))
            p.drawText(x, y, ch)
            self._drops[i] += 1
            if y > self.height() and random.random() > 0.975:
                self._drops[i] = random.randint(0, 2)
        p.end()
        self.update()

    def paintEvent(self, e):
        if self._canvas is None:
            return
        p = QPainter(self)
        p.drawPixmap(0, 0, self._canvas)
        p.end()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self._dismiss()
        else:
            super().keyPressEvent(e)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._dismiss()

    def _dismiss(self):
        self._timer.stop()
        if self._on_close:
            self._on_close()
        self.hide()


COMMAND_ITEMS = [
    # ---------- Docker ----------
    ("docker login", "登录 Docker Hub / 私有仓库", "Docker"),
    ("docker login -u 用户名 registry.example.com", "登录指定私有仓库", "Docker"),
    ("docker logout", "退出仓库登录并清除凭据", "Docker"),
    ("docker search nginx", "在 Docker Hub 搜索镜像", "Docker"),
    ("docker info", "查看引擎信息（含已登录仓库地址）", "Docker"),
    ("docker version", "查看客户端与服务端版本", "Docker"),
    ("docker ps", "查看运行中的容器", "Docker"),
    ("docker ps -a", "查看所有容器（含已停止）", "Docker"),
    ("docker images", "列出本地镜像", "Docker"),
    ("docker pull nginx", "拉取镜像", "Docker"),
    ("docker run -d --name web -p 8080:80 nginx", "后台启动容器并映射端口", "Docker"),
    ("docker exec -it 容器ID bash", "进入容器交互式 shell", "Docker"),
    ("docker logs -f 容器ID", "实时查看容器日志", "Docker"),
    ("docker stop 容器ID", "停止容器", "Docker"),
    ("docker rm 容器ID", "删除容器", "Docker"),
    ("docker rmi 镜像名", "删除镜像", "Docker"),
    ("docker build -t myimage .", "用当前目录 Dockerfile 构建镜像", "Docker"),
    ("docker compose up -d", "后台启动 compose 编排的服务", "Docker"),
    ("docker compose down", "停止并移除 compose 服务", "Docker"),
    ("docker compose ps", "查看 compose 服务状态", "Docker"),
    ("docker inspect 容器ID", "查看容器详细配置（JSON）", "Docker"),
    ("docker network ls", "列出 Docker 网络", "Docker"),
    ("docker volume ls", "列出数据卷", "Docker"),
    ("docker system df", "查看 Docker 磁盘占用", "Docker"),
    ("docker system prune -a", "清理未使用的镜像/容器/网络", "Docker"),
    ("docker cp 容器ID:/path ./local", "从容器复制文件到主机", "Docker"),
    ("docker run -v /data:/data -e KEY=val 镜像", "挂载卷并传入环境变量启动", "Docker"),
    ("docker stats", "实时查看各容器 CPU/内存", "Docker"),
    ("docker stats 容器ID", "查看指定容器资源占用", "Docker"),
    ("docker compose logs -f", "跟踪 compose 服务日志", "Docker"),
    ("docker compose build", "重新构建 compose 服务镜像", "Docker"),
    ("docker start 容器ID", "启动已停止的容器", "Docker"),
    ("docker restart 容器ID", "重启容器", "Docker"),
    ("docker tag 镜像 仓库/名:tag", "给镜像打标签准备推送", "Docker"),
    ("docker push 仓库/名:tag", "推送镜像到远程仓库", "Docker"),
    ("docker save -o a.tar 镜像", "把镜像导出为 tar 包", "Docker"),
    ("docker load -i a.tar", "从 tar 包导入镜像", "Docker"),
    ("docker commit 容器ID 新镜像", "把容器当前状态保存为镜像", "Docker"),
    ("docker history 镜像", "查看镜像各层构建历史", "Docker"),
    ("docker attach 容器ID", "附着到容器主进程终端", "Docker"),
    # ---------- Linux ----------
    ("ls -lh", "以易读大小列出文件", "Linux"),
    ("cd /var/log", "切换目录", "Linux"),
    ("pwd", "显示当前工作目录", "Linux"),
    ("cp -r src dst", "递归复制目录", "Linux"),
    ("mv old new", "移动 / 重命名", "Linux"),
    ("rm -rf dir", "递归强制删除（危险）", "Linux"),
    ("mkdir -p a/b/c", "递归创建多级目录", "Linux"),
    ("cat file", "查看文件内容", "Linux"),
    ("less file", "分页查看文件", "Linux"),
    ("tail -f app.log", "实时跟踪日志末尾", "Linux"),
    ("head -n 20 file", "查看文件前 20 行", "Linux"),
    ("grep -rn \"text\" .", "递归搜索文本并显示行号", "Linux"),
    ("find . -name \"*.log\"", "按名称查找文件", "Linux"),
    ("chmod +x script.sh", "赋予执行权限", "Linux"),
    ("chown user:group file", "修改属主属组", "Linux"),
    ("sudo -i", "以 root 身份进入登录 shell", "Linux"),
    ("sudo -s", "切到 root 但沿用当前环境变量", "Linux"),
    ("su -", "切到 root 并加载 root 的环境", "Linux"),
    ("su - 用户名", "切换到其他用户并加载其环境", "Linux"),
    ("sudo !!", "用 sudo 重新执行上一条命令", "Linux"),
    ("sudo -u 用户名 命令", "以指定用户身份执行一条命令", "Linux"),
    ("sudo -l", "查看当前用户能 sudo 哪些命令", "Linux"),
    ("visudo", "安全地编辑 sudoers 授权文件", "Linux"),
    ("whoami", "查看当前是哪个用户", "Linux"),
    ("id", "查看当前用户的 UID/GID 和所属组", "Linux"),
    ("passwd", "改当前用户密码（root 下可改任何人）", "Linux"),
    ("exit 或 Ctrl+D", "退出 root / 当前 shell", "Linux"),
    ("ps aux | grep nginx", "查找指定进程", "Linux"),
    ("top", "实时查看进程与资源占用", "Linux"),
    ("df -h", "查看磁盘空间使用", "Linux"),
    ("du -sh dir", "查看目录总大小", "Linux"),
    ("free -h", "查看内存使用", "Linux"),
    ("systemctl status nginx", "查看服务状态", "Linux"),
    ("systemctl restart nginx", "重启服务", "Linux"),
    ("journalctl -u nginx -f", "跟踪某服务日志", "Linux"),
    ("ss -tulpn", "查看监听端口与进程", "Linux"),
    ("sudo ufw status verbose", "查看 ufw 防火墙规则", "Linux"),
    ("sudo ufw status numbered", "带编号查看，方便按编号删", "Linux"),
    ("sudo ufw allow 8080/tcp", "开放 8080 端口", "Linux"),
    ("sudo ufw allow from 192.168.1.0/24 to any port 22 proto tcp", "只给某网段开放 22", "Linux"),
    ("sudo ufw delete allow 8080/tcp", "删除对应的放行规则", "Linux"),
    ("sudo ufw delete 3", "按编号删除规则（先 status numbered）", "Linux"),
    ("sudo ufw enable", "启用 ufw（开机自启）", "Linux"),
    ("sudo ufw disable", "临时关闭 ufw", "Linux"),
    ("sudo ufw reload", "改完规则后重载", "Linux"),
    ("sudo firewall-cmd --add-port=8080/tcp --permanent", "firewalld 永久开放端口", "Linux"),
    ("sudo firewall-cmd --remove-port=8080/tcp --permanent", "firewalld 永久关闭端口", "Linux"),
    ("sudo firewall-cmd --reload", "firewalld 重载，--permanent 才生效", "Linux"),
    ("sudo firewall-cmd --list-all", "查看当前区域的规则", "Linux"),
    ("sudo iptables -L -n -v", "查看 iptables 规则和包计数", "Linux"),
    ("sudo iptables -A INPUT -p tcp --dport 8080 -j ACCEPT", "放行 8080 入站", "Linux"),
    ("sudo iptables -D INPUT -p tcp --dport 8080 -j ACCEPT", "删除那条放行规则", "Linux"),
    ("sudo iptables-save | sudo tee /etc/iptables/rules.v4", "保存 iptables 规则，重启不丢", "Linux"),
    ("sudo nft list ruleset", "查看 nftables 规则（新版默认后端）", "Linux"),
    ("nc -zv host 8080", "测试目标端口通不通", "Linux"),
    ("nc -l 8080", "本地监听端口，做连通性测试", "Linux"),
    ("tar -czf a.tar.gz dir/", "打包压缩目录", "Linux"),
    ("tar -xzf a.tar.gz", "解压 tar.gz", "Linux"),
    ("kill -9 PID", "强制结束进程", "Linux"),
    ("nohup cmd &", "后台运行且退出终端不中断", "Linux"),
    ("rm 文件.txt", "删除单个文件", "Linux"),
    ("rm -f 文件.txt", "强制删除文件，不存在也不报错", "Linux"),
    ("rm -i 文件.txt", "删除前逐个确认", "Linux"),
    ("rm *.log", "删除当前目录所有 .log 文件", "Linux"),
    ("rm -r 目录/", "递归删除目录及其内容", "Linux"),
    ("rm -rf ./目录/*", "清空目录内容但保留目录本身（危险）", "Linux"),
    ("rmdir 空目录", "删除空目录", "Linux"),
    ("find . -name \"*.tmp\" -delete", "按名称批量删除匹配文件", "Linux"),
    ("unlink 文件.txt", "删除单个文件（底层系统调用）", "Linux"),
    ("nano 文件.txt", "用 nano 打开 / 新建文件", "Linux"),
    ("nano +65 文件.txt", "打开并跳转到第 65 行", "Linux"),
    ("nano -m 文件.txt", "保存时不自动折行", "Linux"),
    ("nano -B 文件.txt", "保存时生成 .bak 备份", "Linux"),
    ("Ctrl+O 回车", "nano 保存（写入）文件", "Linux"),
    ("Ctrl+X", "nano 退出", "Linux"),
    ("Ctrl+K", "nano 剪切（删除）当前行", "Linux"),
    ("Ctrl+U", "nano 粘贴刚剪切的内容", "Linux"),
    ("Ctrl+W", "nano 搜索文本", "Linux"),
    ("Ctrl+\\ (或 Ctrl+R)", "nano 查找并替换", "Linux"),
    ("Ctrl+A / Ctrl+E", "nano 跳到行首 / 行尾", "Linux"),
    ("Ctrl+D", "nano 删除光标处字符", "Linux"),
    ("Ctrl+_ (或 Ctrl+3)", "nano 跳转到指定行号", "Linux"),
    ("Ctrl+J", "nano 切换自动换行", "Linux"),
    ("Ctrl+G", "nano 查看帮助", "Linux"),
    ("Alt+U / Alt+E", "nano 撤销 / 重做", "Linux"),
    ("pkill -f nginx", "按名称结束进程", "Linux"),
    ("killall 进程名", "结束同名所有进程", "Linux"),
    ("lsof -i :8080", "查看占用 8080 端口的进程", "Linux"),
    ("fuser -k 8080/tcp", "结束占用该端口的进程", "Linux"),
    ("ln -s 目标路径 链接名", "创建软链接", "Linux"),
    ("crontab -l", "列出当前用户的定时任务", "Linux"),
    ("crontab -e", "编辑当前用户的定时任务", "Linux"),
    ("sed -i 's/foo/bar/g' f.txt", "原地批量替换文本", "Linux"),
    ("awk '{print $1}' f.txt", "按列提取文本", "Linux"),
    ("sort f.txt | uniq -c", "排序并统计每行出现次数", "Linux"),
    ("cut -d: -f1 /etc/passwd", "按分隔符取字段", "Linux"),
    ("zip -r a.zip 目录/", "递归压缩为 zip", "Linux"),
    ("unzip a.zip -d 目标目录", "解压 zip 到指定目录", "Linux"),
    ("source ~/.bashrc", "重新加载 shell 配置", "Linux"),
    ("uname -a", "查看内核与系统信息", "Linux"),
    ("env | grep PATH", "查看环境变量", "Linux"),
    ("chmod 755 目录/", "设置目录权限 rwxr-xr-x", "Linux"),
    ("history", "查看命令历史", "Linux"),
    ("which python3", "查看命令所在路径", "Linux"),
    ("echo \"文本\" >> f.txt", "追加内容到文件末尾", "Linux"),
    ("touch f.txt", "新建空文件 / 更新修改时间", "Linux"),
    ("stat f.txt", "查看大小、权限和三个时间戳", "Linux"),
    ("file f.txt", "查看文件真实类型", "Linux"),
    ("wc -l f.txt", "统计行数（-w 词数 / -c 字节）", "Linux"),
    ("tree -L 2", "树形查看两层目录结构", "Linux"),
    ("diff a.txt b.txt", "比较两个文件的差异", "Linux"),
    ("cp -a src/ dst/", "递归复制并保留权限与时间", "Linux"),
    ("readlink -f 链接名", "查看软链接指向的真实路径", "Linux"),
    ("split -l 1000 big.log part_", "按行数切分大文件", "Linux"),
    ("cmd | tee f.log", "输出到屏幕的同时写入文件", "Linux"),
    ("rsync -av src/ user@host:/path/", "增量同步目录，只传改动部分", "Linux"),
    ("find . -name \"*.log\" -print0 | xargs -0 rm", "按名称查找并批量删除", "Linux"),
    # ---------- SSH ----------
    ("ssh user@host", "远程登录", "SSH"),
    ("ssh root@host", "以 root 直接登录（多数发行版默认禁止）", "SSH"),
    ("ssh -p 2222 user@host", "指定端口登录", "SSH"),
    ("ssh user@host \"命令\"", "远程执行一条命令后退出", "SSH"),
    ("ssh-keygen -t ed25519 -C \"邮箱\"", "生成 ed25519 密钥对", "SSH"),
    ("ssh-copy-id user@host", "把公钥装到远程，之后免密登录", "SSH"),
    ("ssh-add ~/.ssh/id_ed25519", "把私钥交给 ssh-agent 管理", "SSH"),
    ("ssh -v user@host", "打印握手过程，排查连不上", "SSH"),
    ("ssh -L 8080:localhost:80 user@host", "本地端口转发（本地 8080 → 远端 80）", "SSH"),
    ("ssh -R 8080:localhost:80 user@host", "远程端口转发（远端 8080 → 本地 80）", "SSH"),
    ("ssh -D 1080 user@host", "开一个 SOCKS5 代理", "SSH"),
    ("ssh -J 跳板机 user@内网主机", "经跳板机连内网机器", "SSH"),
    ("scp file user@host:/path", "远程复制文件", "SSH"),
    ("scp -r 目录/ user@host:/path", "递归复制整个目录", "SSH"),
    ("sftp user@host", "交互式传输文件（get / put）", "SSH"),
    ("cat ~/.ssh/known_hosts", "查看已信任的主机指纹", "SSH"),
    ("ssh-keygen -R host", "删掉某主机的旧指纹（重装后报错时用）", "SSH"),
    # ---------- Vim ----------
    ("vim f.txt", "打开或新建文件", "Vim"),
    ("vim +65 f.txt", "打开并跳到第 65 行", "Vim"),
    ("vim -R f.txt", "只读方式打开", "Vim"),
    ("i", "在光标前插入", "Vim"),
    ("a", "在光标后插入", "Vim"),
    ("o / O", "在下方 / 上方新开一行插入", "Vim"),
    ("Esc", "回到普通模式", "Vim"),
    ("v / V / Ctrl+V", "选字符 / 选整行 / 列块选择", "Vim"),
    (":w", "保存", "Vim"),
    (":wq 或 ZZ", "保存并退出", "Vim"),
    (":q", "退出（没改动时）", "Vim"),
    (":q!", "放弃改动强制退出", "Vim"),
    (":w !sudo tee %", "没权限时用 sudo 保存", "Vim"),
    ("gg / G", "跳到文件开头 / 末尾", "Vim"),
    ("65G 或 :65", "跳到第 65 行", "Vim"),
    ("0 / $", "跳到行首 / 行尾", "Vim"),
    ("w / b", "按词向前 / 向后跳", "Vim"),
    ("Ctrl+f / Ctrl+b", "向下一页 / 上一页", "Vim"),
    ("%", "在成对括号间跳转", "Vim"),
    ("dd", "删除当前行", "Vim"),
    ("5dd", "删除 5 行", "Vim"),
    ("yy / 5yy", "复制当前行 / 5 行", "Vim"),
    ("p / P", "粘贴到下一行 / 上一行", "Vim"),
    ("x / r", "删除光标字符 / 替换为另一个字符", "Vim"),
    ("u / Ctrl+r", "撤销 / 重做", "Vim"),
    (">> / <<", "当前行缩进 / 反缩进", "Vim"),
    ("J", "把下一行接到当前行末尾", "Vim"),
    ("/关键字", "向下搜索", "Vim"),
    ("?关键字", "向上搜索", "Vim"),
    ("n / N", "跳到下一个 / 上一个匹配", "Vim"),
    (":%s/旧/新/g", "全文替换", "Vim"),
    (":%s/旧/新/gc", "全文替换并逐个确认", "Vim"),
    (":noh", "取消搜索高亮", "Vim"),
    (":set nu / :set nonu", "显示 / 关闭行号", "Vim"),
    (":set paste", "粘贴前关闭自动缩进，避免阶梯", "Vim"),
    (":sp 文件", "上下分屏打开另一个文件", "Vim"),
    (":vsp 文件", "左右分屏打开另一个文件", "Vim"),
    ("Ctrl+w w", "在分屏窗口之间切换", "Vim"),
    (":e 文件", "在当前窗口编辑另一个文件", "Vim"),
    # ---------- Windows ----------
    ("ipconfig /all", "查看完整网络配置", "Windows"),
    ("ping 8.8.8.8", "测试网络连通", "Windows"),
    ("tracert baidu.com", "路由追踪", "Windows"),
    ("netstat -ano", "查看所有连接与监听端口（含 PID）", "Windows"),
    ("netstat -ano | findstr :8080", "查 8080 端口被哪个 PID 占用", "Windows"),
    ("netsh advfirewall show allprofiles state", "查看防火墙是否开启", "Windows"),
    ("netsh advfirewall set allprofiles state on", "打开所有配置文件的防火墙（管理员）", "Windows"),
    ("netsh advfirewall firewall add rule name=\"开放8080\" dir=in action=allow protocol=TCP localport=8080", "放行入站端口（管理员）", "Windows"),
    ("netsh advfirewall firewall delete rule name=\"开放8080\"", "删除这条放行规则（管理员）", "Windows"),
    ("New-NetFirewallRule -DisplayName 开放8080 -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow", "PowerShell 加入站放行（管理员）", "Windows"),
    ("Remove-NetFirewallRule -DisplayName 开放8080", "PowerShell 删除该规则（管理员）", "Windows"),
    ("netsh interface portproxy show all", "查看已有的端口转发规则", "Windows"),
    ("netsh interface portproxy add v4tov4 listenport=8080 connectport=80 connectaddress=127.0.0.1", "把 8080 转发到本机 80（管理员）", "Windows"),
    ("tasklist", "列出运行中的进程", "Windows"),
    ("taskkill /PID 1234 /F", "强制结束指定进程", "Windows"),
    ("systeminfo", "查看系统详细信息", "Windows"),
    ("sfc /scannow", "扫描并修复系统文件（管理员）", "Windows"),
    ("chkdsk C: /f", "检查并修复磁盘（管理员）", "Windows"),
    ("shutdown /s /t 0", "立即关机", "Windows"),
    ("shutdown /r /t 0", "立即重启", "Windows"),
    ("nslookup baidu.com", "DNS 查询", "Windows"),
    ("route print", "查看路由表", "Windows"),
    ("dir", "列出目录内容（cmd）", "Windows"),
    ("Get-Process", "查看进程（PowerShell）", "Windows"),
    ("Get-Service", "查看服务（PowerShell）", "Windows"),
    ("Get-NetIPAddress", "查看 IP 地址（PowerShell）", "Windows"),
    ("Get-CimInstance Win32_OperatingSystem", "查看操作系统信息（PowerShell）", "Windows"),
    ("Set-ExecutionPolicy RemoteSigned", "允许运行脚本（管理员，PowerShell）", "Windows"),
    ("winget install 包名", "用 winget 安装软件", "Windows"),
    ("Get-ChildItem", "列出目录内容（PowerShell 版 dir）", "Windows"),
    ("New-Item -ItemType Directory 名", "新建文件夹（PowerShell）", "Windows"),
    ("Remove-Item -Recurse -Force 路径", "递归强制删除（PowerShell，危险）", "Windows"),
    ("Select-String \"text\" *.log", "在文件中搜索文本（PowerShell 版 grep）", "Windows"),
    ("Stop-Process -Name firefox -Force", "按名称强制结束进程（PowerShell）", "Windows"),
    ("Test-NetConnection 1.1.1.1 -Port 443", "测试主机端口连通（PowerShell）", "Windows"),
    ("Resolve-DnsName baidu.com", "DNS 解析（PowerShell）", "Windows"),
    ("Get-Service | Where Status -eq 'Running'", "列出正在运行的服务（PowerShell）", "Windows"),
    ("DISM /Online /Cleanup-Image /RestoreHealth", "修复系统镜像（管理员）", "Windows"),
    ("schtasks /create /tn 任务 /tr cmd /sc daily /st 09:00", "创建每日计划任务", "Windows"),
    ("reg query HKCU\\Software", "查询注册表项", "Windows"),
    ("gpupdate /force", "强制刷新组策略", "Windows"),
    ("wsl --install", "安装 Windows Subsystem for Linux", "Windows"),
    ("powercfg /batteryreport", "生成电池健康报告", "Windows"),
    ("net user", "查看本机用户列表", "Windows"),
    # ---------- Git ----------
    ("git config --global user.name \"你的名字\"", "设置全局提交名字", "Git"),
    ("git config --global user.email \"you@example.com\"", "设置全局提交邮箱", "Git"),
    ("git config --global --list", "查看全部全局配置", "Git"),
    ("git config --global user.name", "只看全局提交名字", "Git"),
    ("git init", "初始化仓库", "Git"),
    ("git clone <url>", "克隆远程仓库", "Git"),
    ("git status", "查看工作区状态", "Git"),
    ("git add .", "暂存所有改动", "Git"),
    ("git commit -m \"msg\"", "提交改动", "Git"),
    ("git log --oneline --graph", "简洁查看提交历史", "Git"),
    ("git diff", "查看未暂存的差异", "Git"),
    ("git branch", "列出本地分支", "Git"),
    ("git checkout -b feature", "新建并切换到分支", "Git"),
    ("git switch main", "切换分支（新语法）", "Git"),
    ("git merge feature", "合并分支到当前分支", "Git"),
    ("git pull", "拉取并合并远程更新", "Git"),
    ("git push origin main", "推送到远程", "Git"),
    ("git stash", "暂存当前未提交改动", "Git"),
    ("git stash pop", "恢复最近一次暂存", "Git"),
    ("git reset --soft HEAD~1", "撤销上次提交但保留改动", "Git"),
    ("git reset --hard HEAD", "丢弃工作区改动（危险）", "Git"),
    ("git revert <commitID>", "生成一次反做提交", "Git"),
    ("git remote -v", "查看远程仓库地址", "Git"),
    ("git tag -a v1.0 -m \"note\"", "打一个带说明的标签", "Git"),
    ("git rebase -i HEAD~3", "交互式改写最近 3 次提交", "Git"),
    ("git commit --amend -m \"新信息\"", "修改上一次提交", "Git"),
    ("git add -p", "分块（逐段）暂存改动", "Git"),
    ("git cherry-pick <commitID>", "把某次提交应用到当前分支", "Git"),
    ("git restore 文件", "丢弃工作区某文件的改动", "Git"),
    ("git restore --staged 文件", "把已暂存文件退回工作区", "Git"),
    ("git clean -fd", "删除未跟踪的文件和目录（危险）", "Git"),
    ("git push -u origin 分支", "首次推送并设置上游跟踪", "Git"),
    ("git push --force-with-lease", "较安全的强制推送", "Git"),
    ("git branch -d 分支", "删除已合并的分支", "Git"),
    ("git branch -D 分支", "强制删除分支", "Git"),
    ("git fetch --all", "拉取所有远程的更新（不合并）", "Git"),
    ("git blame 文件", "逐行查看代码最后修改者", "Git"),
    ("git shortlog -sn", "统计各作者提交数", "Git"),
    ("git stash list", "查看暂存记录列表", "Git"),
    ("git push origin --delete 分支", "删除远程分支", "Git"),
]

COMMAND_CAT_COLORS = {
    "Docker": "#1D63ED",
    "Linux": "#E8590C",
    "Windows": "#1A7F37",
    "Git": "#D81E06",
}


class CommandRow(QWidget):
    def __init__(self, cmd, desc, cat, on_copy):
        super().__init__()
        self._cmd = cmd
        self._on_copy = on_copy
        self.setObjectName("cmdRow")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setMinimumHeight(46)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(12, 6, 12, 6)
        outer.setSpacing(10)

        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        cmd_label = QLabel(cmd)
        mono = QFont("Menlo", 13)
        mono.setStyleHint(QFont.TypeWriter)
        cmd_label.setFont(mono)
        cmd_label.setStyleSheet("color: #1A73E8; background: transparent;")
        cmd_label.setTextInteractionFlags(Qt.NoTextInteraction)
        desc_label = QLabel(desc)
        desc_label.setFont(QFont("PingFang SC", 12))
        desc_label.setStyleSheet("color: #555555; background: transparent;")
        desc_label.setWordWrap(True)
        text_box.addWidget(cmd_label)
        text_box.addWidget(desc_label)
        outer.addLayout(text_box, 1)

        cat_label = QLabel(cat)
        cat_label.setFont(QFont("PingFang SC", 11, QFont.Bold))
        cat_label.setStyleSheet(
            "color: %s; background: transparent;" % COMMAND_CAT_COLORS.get(cat, "#999999"))
        outer.addWidget(cat_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._on_copy(self._cmd)


class DeveloperReferenceWindow(QMainWindow):
    CATEGORIES = ["全部", "Docker", "Linux", "SSH", "Vim", "Windows", "Git", "HTTP"]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("开发速查")
        self._items = COMMAND_ITEMS + [(f"{code} {en}", f"{zh} · {desc}", "HTTP")
                                       for code, en, zh, desc in HTTP_STATUS_CODES]
        self.setGeometry(*tool_win_geometry())
        self._current_cat = "全部"
        self.setStyleSheet("""
            QMainWindow { background: #FFFFFF; }
            #cmdRow { background: transparent; border-radius: 6px; }
            #cmdRow:hover { background: #F3F8FF; }
        """)
        self.init_ui()
        self.apply_filter()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        self.search_edit = QLineEdit()
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setPlaceholderText("搜索命令、HTTP 状态码或说明，例如 容器、分支、404、超时…")
        self.search_edit.setStyleSheet("""
            QLineEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 7px 10px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; }
            QLineEdit:focus { border-color: #1A73E8; }
        """)
        self.search_edit.textChanged.connect(self.apply_filter)
        layout.addWidget(self.search_edit)

        cat_bar = QHBoxLayout()
        cat_bar.setSpacing(8)
        self._cat_buttons = []
        for cat in self.CATEGORIES:
            btn = QPushButton(cat)
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setChecked(cat == "全部")
            btn.setStyleSheet("""
                QPushButton { color: #222; background: #FFFFFF; border: 1px solid #CFCFCF;
                    border-radius: 4px; padding: 6px 12px; font-size: 12px; font-weight: 500;
                    font-family: "PingFang SC", "Microsoft YaHei", sans-serif; }
                QPushButton:hover { border-color: #1A73E8; color: #1A73E8; }
                QPushButton:checked { color: #FFFFFF; background: #1A73E8; border-color: #1A73E8; }
            """)
            btn.clicked.connect(lambda checked, c=cat: self.select_category(c))
            cat_bar.addWidget(btn)
            self._cat_buttons.append(btn)
        cat_bar.addStretch()
        layout.addLayout(cat_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._results = QWidget()
        self._results_layout = QVBoxLayout(self._results)
        self._results_layout.setContentsMargins(0, 4, 8, 4)
        self._results_layout.setSpacing(4)
        self._results_layout.addStretch()
        scroll.setWidget(self._results)
        layout.addWidget(scroll, 1)

        self.status_label = QLabel("")
        self.status_label.setFont(QFont("PingFang SC", 11))
        self.status_label.setStyleSheet("color: #999999;")
        layout.addWidget(self.status_label)

    def select_category(self, cat):
        self._current_cat = cat
        for btn in self._cat_buttons:
            btn.setChecked(btn.text() == cat)
        self.apply_filter()

    def _clear_results(self):
        while self._results_layout.count():
            item = self._results_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def apply_filter(self):
        query = self.search_edit.text().strip().lower()
        self._clear_results()
        count = 0
        for cmd, desc, cat in self._items:
            if self._current_cat != "全部" and cat != self._current_cat:
                continue
            if query and query not in cmd.lower() and query not in desc.lower() and query not in cat.lower():
                continue
            row = CommandRow(cmd, desc, cat, self.copy_command)
            self._results_layout.addWidget(row)
            count += 1
        if count == 0:
            empty = QLabel("没有匹配的速查条目")
            empty.setFont(QFont("PingFang SC", 12))
            empty.setStyleSheet("color: #999999; padding: 30px;")
            empty.setAlignment(Qt.AlignCenter)
            self._results_layout.addWidget(empty)
        self._results_layout.addStretch()
        self.status_label.setText("共 %d 条 · 点击条目复制命令或状态码" % count)

    def copy_command(self, cmd):
        QApplication.clipboard().setText(cmd)
        self.status_label.setText("已复制：%s" % cmd)
        self.status_label.setStyleSheet("color: #1A73E8;")
        QTimer.singleShot(1500, self._reset_status)

    def _reset_status(self):
        self.status_label.setStyleSheet("color: #999999;")
        self.apply_filter()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


SSH_KEY_NAMES = ["id_ed25519", "id_rsa", "id_ecdsa", "id_dsa"]


def find_ssh_pubkey():
    ssh_dir = os.path.join(os.path.expanduser("~"), ".ssh")
    for name in SSH_KEY_NAMES:
        pub = os.path.join(ssh_dir, name + ".pub")
        if os.path.isfile(pub):
            try:
                with open(pub, "r", encoding="utf-8", errors="ignore") as f:
                    return pub, f.read().strip()
            except OSError:
                continue
    return None, None


def create_ssh_keypair(email, algorithm="ed25519"):
    ssh_dir = os.path.join(os.path.expanduser("~"), ".ssh")
    os.makedirs(ssh_dir, exist_ok=True)
    priv = os.path.join(ssh_dir, "id_" + algorithm)
    if os.path.exists(priv):
        priv = os.path.join(ssh_dir, "id_%s_%s" % (algorithm, str(int(time.time()))[-6:]))
    if not shutil.which("ssh-keygen"):
        raise RuntimeError("未找到 ssh-keygen，请安装 OpenSSH（Windows：设置 → 可选功能 → 添加 OpenSSH 客户端）")
    cmd = ["ssh-keygen", "-t", algorithm, "-f", priv, "-N", "", "-C", email]
    if platform.system() == "Windows":
        cmd = subprocess.list2cmdline(cmd)
    proc = subprocess.run(cmd, shell=False, capture_output=True, text=True,
                          errors="ignore", **win_no_console())
    if proc.returncode != 0:
        raise RuntimeError("生成失败: %s" % (proc.stderr or "").strip())
    return priv + ".pub"


def win_no_console():
    """Windows: keep console from flashing when spawning child processes."""
    if platform.system() == "Windows":
        return {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)}
    return {}


class _SshPubkeyPage(QWidget):
    def __init__(self):
        super().__init__()
        self.pub_path = None
        self.pub_text = None
        self.init_ui()
        self.refresh()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(8)

        gen_btn = QPushButton("生成密钥")
        gen_btn.setFixedSize(70, 28)
        gen_btn.setCursor(QCursor(Qt.PointingHandCursor))
        gen_btn.setStyleSheet("""
            QPushButton { color: #FFFFFF; background: #1A73E8; border: none; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #1557B0; }
        """)
        gen_btn.clicked.connect(self.do_generate)
        header.addWidget(gen_btn)

        open_btn = QPushButton("打开目录")
        open_btn.setFixedSize(70, 28)
        open_btn.setCursor(QCursor(Qt.PointingHandCursor))
        open_btn.setStyleSheet("""
            QPushButton { color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #E0E0E0; }
        """)
        open_btn.clicked.connect(self.open_ssh_dir)
        header.addWidget(open_btn)

        refresh_btn = QPushButton("刷新")
        refresh_btn.setFixedSize(60, 28)
        refresh_btn.setCursor(QCursor(Qt.PointingHandCursor))
        refresh_btn.setStyleSheet("""
            QPushButton { color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #E0E0E0; }
        """)
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)

        copy_btn = QPushButton("复制")
        copy_btn.setFixedSize(60, 28)
        copy_btn.setCursor(QCursor(Qt.PointingHandCursor))
        copy_btn.setStyleSheet("""
            QPushButton { color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #E0E0E0; }
        """)
        copy_btn.clicked.connect(self.do_copy)
        header.addWidget(copy_btn)
        layout.addLayout(header)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("""
            QTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
                font-family: "Consolas", "Menlo", monospace; font-size: 12px; background: #FAFAFA; }
        """)
        layout.addWidget(self.result_text)

        self.status_label = QLabel()
        self.status_label.setFont(QFont("PingFang SC", 11))
        self.status_label.setStyleSheet("color: #999999; font-size: 11px;")
        layout.addWidget(self.status_label)

    def set_status(self, text, ok=True):
        self.status_label.setText(text)
        self.status_label.setStyleSheet("color: %s; font-size: 11px;" % ("#188038" if ok else "#D93025"))

    def refresh(self):
        self.pub_path, self.pub_text = find_ssh_pubkey()
        if self.pub_text:
            self.result_text.setPlainText(self.pub_text)
            self.set_status("公钥文件：%s" % self.pub_path, ok=True)
        else:
            self.result_text.clear()
            self.set_status("未找到公钥，点击「生成密钥」创建", ok=False)

    def do_copy(self):
        if not self.pub_text:
            self.set_status("没有可复制的公钥", ok=False)
            return
        QApplication.clipboard().setText(self.pub_text)
        self.set_status("已复制到剪贴板", ok=True)

    def open_ssh_dir(self):
        try:
            reveal_in_folder(user_path(".ssh"))
        except (RuntimeError, OSError) as e:
            self.set_status(str(e), ok=False)
            return
        self.set_status("已打开目录：%s" % user_path(".ssh"), ok=True)

    def do_generate(self):
        existing_path, existing_text = find_ssh_pubkey()
        if existing_text:
            self.result_text.setPlainText(existing_text)
            self.set_status("已存在公钥：%s" % existing_path, ok=True)
            return
        email, ok = QInputDialog.getText(self, "生成 SSH 密钥", "邮箱（用作密钥备注，可留空）:",
                                         QLineEdit.Normal, "")
        if not ok:
            return
        email = email.strip()
        if not email:
            email = "%s@%s" % (os.path.expanduser("~").split(os.sep)[-1], platform.node())
        try:
            pub = create_ssh_keypair(email)
            with open(pub, "r", encoding="utf-8", errors="ignore") as f:
                self.pub_path, self.pub_text = pub, f.read().strip()
        except Exception as e:
            self.result_text.setPlainText(str(e))
            self.set_status("生成失败", ok=False)
            return
        self.result_text.setPlainText(self.pub_text)
        self.set_status("已生成密钥：%s" % pub, ok=True)


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


def reveal_in_folder(path):
    """Reveal a config file by opening the folder that should already hold it."""
    target = path if os.path.isdir(path) else os.path.dirname(path)
    if not os.path.isdir(target):
        raise RuntimeError("目录不存在：%s（先生成或手动创建）" % target)
    system = platform.system()
    if system == "Windows":
        os.startfile(target)
    elif system == "Darwin":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen(["xdg-open", target])


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


def npm_config_path():
    return user_path(".npmrc")


def pip_config_path():
    return _app_config_dir("pip", "pip.ini" if platform.system() == "Windows" else "pip.conf")


def go_env_path():
    return _app_config_dir("go", "env")


def docker_daemon_path():
    return user_path(".docker", "daemon.json")


def maven_settings_path():
    return user_path(".m2", "settings.xml")


MAVEN_NOTE = "<!-- 这一段由 系统工具箱 的「镜像源」标签维护 -->"
MAVEN_OUR_ID = "toolbox-mirror"
MAVEN_MIRROR_RE = re.compile(r"<mirror\b[^>]*>.*?</mirror>", re.S | re.I)
MAVEN_OURS_RE = re.compile(
    r"<mirror\b[^>]*>(?:(?!</mirror>).)*?<id>\s*" + MAVEN_OUR_ID + r"\s*</id>(?:(?!</mirror>).)*?</mirror>",
    re.S | re.I)
MAVEN_MIRROR_OF_RE = re.compile(r"<mirrorOf\b[^>]*>([^<]*)</mirrorOf>", re.I)
MAVEN_URL_RE = re.compile(r"<url\b[^>]*>([^<]*)</url>", re.I)


def _xml_escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def maven_central_url():
    text = _read_text(maven_settings_path())
    if not text:
        return None
    for block in MAVEN_MIRROR_RE.finditer(text):
        of = MAVEN_MIRROR_OF_RE.search(block.group(0))
        if of and "central" in [p.strip().lower() for p in of.group(1).split(",")]:
            url = MAVEN_URL_RE.search(block.group(0))
            if url:
                return url.group(1).strip()
    return None


def _maven_mirror_block(url, label):
    return ('<mirror>\n      <id>%s</id>\n      <mirrorOf>central</mirrorOf>\n'
            '      <name>%s</name>\n      <url>%s</url>\n    </mirror>'
            % (MAVEN_OUR_ID, _xml_escape(label), _xml_escape(url)))


def _maven_document(mirror):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n%s\n<settings>\n  <mirrors>\n    %s\n'
            '  </mirrors>\n</settings>\n' % (MAVEN_NOTE, mirror))


def maven_set_central(url, label):
    """Only ever touch the mirror block we own, so a hand-written settings.xml survives."""
    path = maven_settings_path()
    text = _read_text(path)
    mirror = _maven_mirror_block(url, label) if url else None
    if text is None:
        if url is None:
            return
        _write_text(path, _maven_document(mirror))
        return
    ours = MAVEN_OURS_RE.search(text)
    if ours:
        if url:
            _write_text(path, text[:ours.start()] + mirror + text[ours.end():])
            return
        start = text.rfind("\n", 0, ours.start()) + 1
        end = text.find("\n", ours.end())
        end = len(text) if end < 0 else end + 1
        _write_text(path, text[:start] + text[end:])
        return
    if MAVEN_MIRROR_RE.search(text):
        raise RuntimeError("settings.xml 里已有别人写的 mirrors，工具不覆盖，请手动编辑：\n%s" % path)
    if url is None:
        return
    lowered = text.lower()
    if "<mirrors" in lowered:
        close = lowered.find("</mirrors>", lowered.index("<mirrors"))
        if close < 0:
            raise RuntimeError("settings.xml 的 <mirrors> 没有闭合，请手动修正：%s" % path)
        _write_text(path, text[:close].rstrip() + "\n    " + mirror + "\n  " + text[close:].lstrip())
        return
    if "<settings" not in lowered:
        raise RuntimeError("settings.xml 缺少 <settings> 根节点，请手动修正：%s" % path)
    close = lowered.rindex("</settings>")
    _write_text(path, text[:close] + "  <mirrors>\n    %s\n  </mirrors>\n" % mirror + text[close:])


def docker_read_mirror():
    text = _read_text(docker_daemon_path())
    if not text:
        return None
    data = json.loads(text)
    mirrors = data.get("registry-mirrors") if isinstance(data, dict) else None
    return mirrors[0] if isinstance(mirrors, list) and mirrors else None


def docker_write_mirror(url):
    path = docker_daemon_path()
    text = _read_text(path)
    data = {}
    if text:
        try:
            data = json.loads(text)
        except ValueError:
            raise RuntimeError("daemon.json 不是合法 JSON，请手动修正：\n%s" % path)
        if not isinstance(data, dict):
            raise RuntimeError("daemon.json 顶层应为对象，请手动修正：\n%s" % path)
        if url is None:
            if "registry-mirrors" not in data:
                return
            data.pop("registry-mirrors")
        else:
            data["registry-mirrors"] = [url]
        _write_text(path, json.dumps(data, indent=4, ensure_ascii=False))
        return
    if url is None:
        return
    _write_text(path, json.dumps({"registry-mirrors": [url]}, indent=4, ensure_ascii=False))


class _MirrorTarget:
    def __init__(self, name, read, write, path_of, options, note=""):
        self.name, self.read, self.write, self.path_of = name, read, write, path_of
        self.options, self.note = options, note


CUSTOM_MIRROR = "__custom__"


def mirror_targets():
    npm = [
        ("官方", "https://registry.npmjs.org/"),
        ("淘宝 npmmirror", "https://registry.npmmirror.com"),
        ("腾讯云", "https://mirrors.cloud.tencent.com/npm/"),
    ]
    pip = [
        ("官方默认", None),
        ("清华", "https://pypi.tuna.tsinghua.edu.cn/simple"),
        ("阿里云", "https://mirrors.aliyun.com/pypi/simple/"),
        ("腾讯云", "https://mirrors.cloud.tencent.com/pypi/simple"),
    ]
    go = [
        ("官方", "https://proxy.golang.org,direct"),
        ("goproxy.cn", "https://goproxy.cn,direct"),
        ("阿里云", "https://mirrors.aliyun.com/goproxy/,direct"),
    ]
    maven = [
        ("官方（不设镜像）", None),
        ("阿里云", "https://maven.aliyun.com/repository/public"),
        ("华为云", "https://repo.huaweicloud.com/repository/maven/"),
    ]
    docker = [
        ("官方（不设镜像）", None),
        ("DaoCloud 公共加速", "https://docker.m.daocloud.io"),
        ("清华", "https://docker.mirrors.tuna.tsinghua.edu.cn"),
    ]
    return [
        _MirrorTarget("npm / yarn",
                      lambda: _ini_get(npm_config_path(), None, "registry"),
                      lambda url: _ini_set(npm_config_path(), None, "registry", url, tight=True),
                      npm_config_path, npm,
                      "yarn 也读这个 .npmrc"),
        _MirrorTarget("pip",
                      lambda: _ini_get(pip_config_path(), "global", "index-url"),
                      lambda url: _ini_set(pip_config_path(), "global", "index-url", url),
                      pip_config_path, pip,
                      "等价于 pip config set global.index-url"),
        _MirrorTarget("Go modules",
                      lambda: _ini_get(go_env_path(), None, "GOPROXY"),
                      lambda url: _ini_set(go_env_path(), None, "GOPROXY", url, tight=True),
                      go_env_path, go,
                      "等价于 go env -w GOPROXY，新开的终端立刻生效"),
        _MirrorTarget("Maven central",
                      maven_central_url,
                      lambda url: maven_set_central(url, "personal_toolbox mirror"),
                      maven_settings_path, maven,
                      "只改 central 的镜像；已有自定义 mirrors 时不覆盖"),
        _MirrorTarget("Docker Hub",
                      docker_read_mirror,
                      docker_write_mirror,
                      docker_daemon_path, docker,
                      "改完需要重启 Docker 才生效"),
    ]


class _MirrorPage(QWidget):
    """一键切换各包管理器的国内镜像；写入前把原文件备份成 .bak。"""

    def __init__(self):
        super().__init__()
        self._targets = mirror_targets()
        self._combos = []
        self._values = []
        self.init_ui()
        self.refresh()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        top = QHBoxLayout()
        refresh_btn = QPushButton("刷新")
        refresh_btn.setFixedSize(64, 28)
        refresh_btn.setCursor(QCursor(Qt.PointingHandCursor))
        refresh_btn.setStyleSheet(_secondary_btn())
        refresh_btn.clicked.connect(self.refresh)
        top.addWidget(refresh_btn)
        hint = QLabel("选择即写入对应配置文件，原文件备份为同名 .bak")
        hint.setStyleSheet("color: #999999; font-size: 11px;")
        top.addWidget(hint)
        top.addStretch()
        layout.addLayout(top)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        for row, target in enumerate(self._targets):
            name = QLabel(target.name)
            name.setFont(QFont("PingFang SC", 12, QFont.Bold))
            name.setFixedWidth(96)
            grid.addWidget(name, row, 0)

            combo = QComboBox()
            combo.setFixedWidth(230)
            combo.setStyleSheet(_combo_style())
            for label, url in target.options:
                combo.addItem(label, url)
            combo.addItem("自定义…", CUSTOM_MIRROR)
            combo.activated.connect(lambda index, t=target: self.apply_choice(t, index))
            grid.addWidget(combo, row, 1)
            self._combos.append(combo)

            value = QLabel("")
            value.setStyleSheet("color: #666666; font-family: 'Menlo', 'Consolas', monospace; font-size: 11px;")
            value.setTextInteractionFlags(Qt.TextSelectableByMouse)
            grid.addWidget(value, row, 2)
            self._values.append(value)

            open_btn = QPushButton("打开")
            open_btn.setFixedSize(52, 26)
            open_btn.setCursor(QCursor(Qt.PointingHandCursor))
            open_btn.setStyleSheet(_secondary_btn())
            open_btn.clicked.connect(lambda _c, t=target: self.reveal(t))
            grid.addWidget(open_btn, row, 3)

            note = QLabel(target.note)
            note.setStyleSheet("color: #AAAAAA; font-size: 10px;")
            grid.addWidget(note, row, 4)
        grid.setColumnStretch(2, 1)
        grid.setColumnStretch(4, 1)
        layout.addLayout(grid)

        layout.addStretch()
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #999999; font-size: 12px; font-family: 'PingFang SC';")
        layout.addWidget(self.status_label)

    def _set_status(self, text, color="#999999"):
        self.status_label.setText(text)
        self.status_label.setStyleSheet("color: %s; font-size: 12px; font-family: 'PingFang SC';" % color)

    def refresh(self):
        for target, combo, value in zip(self._targets, self._combos, self._values):
            path = target.path_of()
            try:
                current = target.read()
            except (ValueError, RuntimeError, OSError) as e:
                current = None
                value.setText("读取失败：%s" % e)
                value.setStyleSheet("color: #D93025; font-size: 11px;")
            else:
                shown = current if current else "未设置（用官方默认）"
                value.setText("%s  ·  %s" % (shown, path))
                value.setStyleSheet("color: #666666; font-family: 'Menlo', 'Consolas', monospace; font-size: 11px;")
            index = combo.findData(current)
            if index < 0:
                index = combo.findData(CUSTOM_MIRROR) if current else 0
            combo.setCurrentIndex(index)

    def apply_choice(self, target, index):
        combo = self._combos[self._targets.index(target)]
        choice = combo.itemData(index)
        if choice == CUSTOM_MIRROR:
            try:
                current = target.read() or ""
            except (ValueError, RuntimeError, OSError):
                current = ""
            text, ok = QInputDialog.getText(self, "自定义镜像地址",
                                           "%s 的镜像 URL（留空＝去掉覆盖）:" % target.name,
                                           QLineEdit.Normal, current)
            if not ok:
                self.refresh()
                return
            choice = text.strip() or None
        try:
            target.write(choice)
        except (RuntimeError, OSError, ValueError) as e:
            self._set_status("%s: %s" % (target.name, e), "#D93025")
            QMessageBox.warning(self, "写入失败", "%s\n\n%s" % (target.name, e), QMessageBox.Ok)
            self.refresh()
            return
        self.refresh()
        if choice:
            self._set_status("已切换 %s → %s" % (target.name, choice), "#188038")
        else:
            self._set_status("已清除 %s 的镜像覆盖，恢复官方默认" % target.name, "#188038")

    def reveal(self, target):
        path = target.path_of()
        try:
            reveal_in_folder(path)
        except (RuntimeError, OSError) as e:
            self._set_status("%s（%s）" % (e, path), "#D93025")
            return
        self._set_status("已打开 %s" % os.path.dirname(path), "#188038")


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


class _SshConfigPage(QWidget):
    """~/.ssh/config 的图形化编辑：别名、跳转、密钥路径，不用再手抠缩进。"""

    def __init__(self):
        super().__init__()
        self._preamble = []
        self._blocks = []
        self._locked = False
        self._index = None
        self.init_ui()
        self.refresh()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(8)

        top = QHBoxLayout()
        for text, slot, primary in (("添加主机", self.new_entry, True), ("保存", self.save, True),
                                    ("删除", self.delete_entry, False), ("复制 ssh 命令", self.copy_command, False),
                                    ("打开目录", self.reveal, False), ("刷新", self.refresh, False)):
            btn = QPushButton(text)
            btn.setFixedHeight(28)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setStyleSheet(_primary_btn() if primary else _secondary_btn())
            btn.clicked.connect(slot)
            top.addWidget(btn)
        top.addStretch()
        layout.addLayout(top)

        self.path_label = QLabel(ssh_config_path())
        self.path_label.setStyleSheet("color: #999999; font-size: 11px; font-family: 'Menlo', 'Consolas', monospace;")
        layout.addWidget(self.path_label)

        body = QHBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.setFixedWidth(210)
        self.list_widget.setStyleSheet("""
            QListWidget { border: 1px solid #D0D0D0; border-radius: 6px; background: #FAFAFA;
                font-family: "Menlo", "Consolas", monospace; font-size: 12px; }
            QListWidget::item { padding: 6px 8px; }
            QListWidget::item:selected { background: #E8F0FE; color: #1A73E8; }
        """)
        self.list_widget.currentRowChanged.connect(self.load_form)
        body.addWidget(self.list_widget)

        form = QGridLayout()
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(8)
        self.field_edits = {}
        fields = (("别名", "Host", "prod，可空格写多个别名"),
                  ("主机地址", "HostName", "10.0.0.8 或 example.com"),
                  ("用户名", "User", "deploy"),
                  ("端口", "Port", "22"),
                  ("密钥文件", "IdentityFile", "~/.ssh/id_ed25519"),
                  ("跳转主机", "ProxyJump", "prod"))
        for row, (label, key, placeholder) in enumerate(fields):
            name = QLabel(label + ":")
            name.setStyleSheet("font-family: 'PingFang SC'; font-size: 12px; color: #333333;")
            form.addWidget(name, row, 0)
            edit = QLineEdit()
            edit.setPlaceholderText(placeholder)
            edit.setStyleSheet(_lineedit_style())
            form.addWidget(edit, row, 1)
            self.field_edits[key] = edit
            if key == "IdentityFile":
                browse = QPushButton("浏览…")
                browse.setFixedWidth(56)
                browse.setCursor(QCursor(Qt.PointingHandCursor))
                browse.setStyleSheet(_secondary_btn())
                browse.clicked.connect(self.browse_key)
                form.addWidget(browse, row, 2)
        extras = QLabel("其他选项:")
        extras.setStyleSheet("font-family: 'PingFang SC'; font-size: 12px; color: #333333;")
        form.addWidget(extras, len(fields), 0)
        self.extras_edit = QPlainTextEdit()
        self.extras_edit.setPlaceholderText("每行一条，如 ForwardAgent yes")
        self.extras_edit.setStyleSheet(_plain_style())
        self.extras_edit.setFixedHeight(70)
        form.addWidget(self.extras_edit, len(fields), 1, 2, 2)
        form.setColumnStretch(1, 1)
        body.addLayout(form, 2)
        layout.addLayout(body, 1)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #999999; font-size: 12px; font-family: 'PingFang SC';")
        layout.addWidget(self.status_label)

    def _set_status(self, text, color="#999999"):
        self.status_label.setText(text)
        self.status_label.setStyleSheet("color: %s; font-size: 12px; font-family: 'PingFang SC';" % color)

    def refresh(self):
        text = _read_text(ssh_config_path())
        try:
            self._preamble, self._blocks, self._locked = ssh_parse_config(text)
        except Exception as e:
            self._set_status("读取失败: %s" % e, "#D93025")
            return
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for block in self._blocks:
            self.list_widget.addItem("%s\n%s" % (" ".join(block["host"]), ssh_summary(block)))
        self.list_widget.blockSignals(False)
        if self._locked:
            self._set_status("文件里有 Match 配置，本工具只按 Host 分组，请手动编辑：%s" % ssh_config_path(), "#D93025")
        elif text is None:
            self._set_status("还没有 %s，点「添加主机」创建。" % ssh_config_path(), "#999999")
        else:
            self._set_status("共 %d 个 Host 条目。" % len(self._blocks), "#999999")
        if self._blocks:
            self.list_widget.setCurrentRow(0)
        else:
            self.new_entry()

    def current_block(self):
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self._blocks):
            return None
        return self._blocks[row]

    def load_form(self, row):
        block = self._blocks[row] if 0 <= row < len(self._blocks) else None
        if block is None:
            return
        self._index = row
        opts = {}
        extras = []
        for key, value in block["opts"]:
            if key == "#":
                if value.strip():
                    extras.append(value.strip())
                continue
            canonical = _ssh_canonical(key)
            if canonical in SSH_CONFIG_KEYS:
                opts[canonical] = value
            else:
                extras.append("%s %s" % (key, value))
        for key, edit in self.field_edits.items():
            edit.setText(" ".join(block["host"]) if key == "Host" else opts.get(key, ""))
        self.extras_edit.setPlainText("\n".join(extras))

    def new_entry(self):
        self._index = None
        self.list_widget.clearSelection()
        for edit in self.field_edits.values():
            edit.setText("")
        self.extras_edit.setPlainText("")
        self.field_edits["Host"].setFocus()
        self._set_status("填写别名和地址后点「保存」。", "#1A73E8")

    def _form_values(self):
        return {key: edit.text().strip() for key, edit in self.field_edits.items()}

    def save(self):
        if self._locked:
            self._set_status("检测到 Match 配置，已停止自动写入，请手动编辑。", "#D93025")
            return
        values = self._form_values()
        aliases = values["Host"].split()
        if not aliases:
            self._set_status("别名不能为空，例如 prod。", "#D93025")
            return
        bad = [a for a in aliases if not SSH_ALIAS_RE.match(a)]
        if bad:
            self._set_status("别名含有非法字符：%s" % " ".join(bad), "#D93025")
            return
        if not values["HostName"] and not any("." in a or "*" in a for a in aliases):
            self._set_status("别名不是域名或通配符时必须填 HostName。", "#D93025")
            return
        clash = [b for i, b in enumerate(self._blocks)
                 if i != self._index and set(b["host"]) & set(aliases)]
        if clash:
            self._set_status("别名 %s 已存在，ssh 只会用第一条，请换个名字。"
                             % " ".join(clash[0]["host"]), "#D93025")
            return
        if values["Port"] and not values["Port"].isdigit():
            self._set_status("端口只能是数字。", "#D93025")
            return
        extras = self._parse_extras(self.extras_edit.toPlainText())
        if isinstance(extras, tuple):
            self._set_status(extras[0], "#D93025")
            return
        managed = {k: v for k, v in values.items() if k != "Host"}
        if self._index is None:
            block = {"host": aliases,
                     "opts": [(k, v) for k, v in managed.items() if v] + extras}
            self._blocks.append(block)
        else:
            block = self._blocks[self._index]
            block["host"] = aliases
            block["opts"] = _ssh_merge_opts(block["opts"], managed, extras)
        self._write()

    @staticmethod
    def _parse_extras(text):
        extras = []
        for line in text.splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                if s:
                    extras.append(("#", s))
                continue
            match = re.match(r"^(\S+?)\s*=\s*(.*)$", s) or re.match(r"^(\S+)\s+(.*)$", s)
            if not match:
                return "其他选项每行应是「键 值」或「键=值」：%s" % s
            extras.append((match.group(1), match.group(2).strip()))
        return extras

    def _write(self):
        path = ssh_config_path()
        try:
            _write_text(path, ssh_dump(self._preamble, self._blocks), key_file=True)
        except OSError as e:
            self._set_status("写入失败: %s" % e, "#D93025")
            return
        self.refresh()
        self._set_status("已写入 %d 个 Host 条目到 %s" % (len(self._blocks), path), "#188038")

    def delete_entry(self):
        if self._locked:
            self._set_status("检测到 Match 配置，已停止自动写入，请手动编辑。", "#D93025")
            return
        block = self.current_block()
        if block is None:
            self._set_status("请先选中要删除的主机。", "#D93025")
            return
        answer = QMessageBox.question(
            self, "删除确认", "从 %s 中删除 Host %s？" % (ssh_config_path(), " ".join(block["host"])),
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        self._blocks.remove(block)
        self._write()

    def copy_command(self):
        block = self.current_block()
        if block is None:
            self._set_status("请先选中一个主机。", "#D93025")
            return
        QApplication.clipboard().setText("ssh %s" % block["host"][0])
        self._set_status("已复制：ssh %s" % block["host"][0], "#188038")

    def browse_key(self):
        path, _selected = QFileDialog.getOpenFileName(self, "选择私钥/公钥文件",
                                                     user_path(".ssh"), "All files (*)")
        if path:
            self.field_edits["IdentityFile"].setText(path)

    def reveal(self):
        try:
            reveal_in_folder(ssh_config_path())
        except (RuntimeError, OSError) as e:
            self._set_status(str(e), "#D93025")


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


WIN_ADVANCED_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"

VISIBILITY_ROWS = (
    {"id": "hidden", "label": "显示隐藏文件",
     "win": ("Hidden", 1, 2), "mac": ("com.apple.finder", "AppleShowAllFiles"),
     "note": "Windows 存注册表 HKCU\\%s\\Hidden；macOS 是 Finder 的 AppleShowAllFiles" % WIN_ADVANCED_SUBKEY},
    {"id": "ext", "label": "显示文件扩展名",
     "win": ("HideFileExt", 0, 1), "mac": ("NSGlobalDomain", "AppleShowAllExtensions"),
     "note": "扩展名打开后一眼看出 report.pdf.exe"},
    {"id": "super", "label": "显示受保护的系统文件",
     "win": ("ShowSuperHidden", 1, 0), "mac": None,
     "note": "仅 Windows：bootmgr、pagefile.sys 这类"},
)


def _win_dword_get(name):
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WIN_ADVANCED_SUBKEY) as key:
            return int(winreg.QueryValueEx(key, name)[0])
    except OSError:
        return None


def _win_dword_set(name, value):
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, WIN_ADVANCED_SUBKEY) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, int(value))


def _win_broadcast_setting(message):
    """WM_SETTINGCHANGE so open Explorer windows and shells can reload."""
    try:
        import ctypes
        HWND_BROADCAST, WM_SETTINGCHANGE, SMTO_ABORTIFHUNG = 0xFFFF, 0x1A, 0x0002
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST, WM_SETTINGCHANGE, 0, message, SMTO_ABORTIFHUNG, 5000, None)
    except Exception:
        pass


def _macos_default_read(domain, key):
    result = subprocess.run(["defaults", "read", domain, key], capture_output=True,
                            encoding="utf-8", errors="replace", **win_no_console())
    if result.returncode != 0:
        return None
    return (result.stdout or "").strip()


def _macos_default_write(domain, key, on):
    subprocess.run(["defaults", "write", domain, key, "-bool", "true" if on else "false"],
                   capture_output=True, **win_no_console())


def _macos_restart_finder():
    subprocess.run(["killall", "Finder"], capture_output=True, **win_no_console())


def visibility_read(row):
    """True/False for the current state, or None when the value was never written."""
    if platform.system() == "Windows":
        name, on, _off = row["win"]
        value = _win_dword_get(name)
        return None if value is None else value == on
    if platform.system() == "Darwin" and row["mac"]:
        raw = _macos_default_read(*row["mac"])
        if raw is None:
            return None
        return raw in ("1", "true", "YES")
    return None


def visibility_write(row, on):
    if platform.system() == "Windows":
        name, win_on, win_off = row["win"]
        _win_dword_set(name, win_on if on else win_off)
        _win_broadcast_setting("Probe")
        return "已写入注册表，资源管理器若没立刻变化，重开一个窗口即可。"
    if platform.system() == "Darwin" and row["mac"]:
        _macos_default_write(row["mac"][0], row["mac"][1], on)
        _macos_restart_finder()
        return "已写入 defaults，访达已重启。"
    raise RuntimeError("当前系统没有对应的开关。")


class _VisibilityPage(QWidget):
    """文件夹显示开关：隐藏文件、扩展名、受保护的系统文件。"""

    def __init__(self):
        super().__init__()
        self._rows = []
        self._loading = False
        self.init_ui()
        self.refresh()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        if platform.system() not in ("Windows", "Darwin"):
            hint = QLabel("Linux 的显示开关在各文件管理器的首选项里，本工具只提供 Windows 和 macOS。")
            hint.setFont(QFont("PingFang SC", 12))
            hint.setStyleSheet("color: #999999;")
            layout.addWidget(hint)
            layout.addStretch()
            return

        for row in VISIBILITY_ROWS:
            if platform.system() == "Darwin" and not row["mac"]:
                continue
            box = QCheckBox(row["label"])
            box.setFont(QFont("PingFang SC", 12))
            box.setStyleSheet("QCheckBox { color: #333333; }")
            box.toggled.connect(lambda checked, r=row, b=box: self.apply(r, b, checked))
            layout.addWidget(box)
            detail = QLabel("")
            detail.setStyleSheet("color: #AAAAAA; font-size: 11px; font-family: 'PingFang SC';")
            layout.addWidget(detail)
            self._rows.append((row, box, detail))
        layout.addStretch()

        self.status_label = QLabel("勾选即生效，写入的都是当前用户的设置，不需要管理员权限。")
        self.status_label.setStyleSheet("color: #999999; font-size: 12px; font-family: 'PingFang SC';")
        layout.addWidget(self.status_label)

    def _set_status(self, text, color="#999999"):
        self.status_label.setText(text)
        self.status_label.setStyleSheet("color: %s; font-size: 12px; font-family: 'PingFang SC';" % color)

    def refresh(self):
        self._loading = True
        for row, box, detail in self._rows:
            state = visibility_read(row)
            box.setChecked(bool(state))
            stored = "未设置（用系统默认）" if state is None else ("已显示" if state else "已隐藏")
            detail.setText("%s · %s" % (stored, row["note"]))
        self._loading = False

    def apply(self, row, box, checked):
        if self._loading:
            return
        if platform.system() == "Darwin" and checked:
            answer = QMessageBox.question(
                self, "重启访达", "macOS 需要重启访达（Finder）才能看到变化，现在重启？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if answer != QMessageBox.Yes:
                self._loading = True
                box.setChecked(False)
                self._loading = False
                self._set_status("已取消，未改动设置。", "#999999")
                return
        try:
            message = visibility_write(row, checked)
        except (RuntimeError, OSError) as e:
            self._set_status("%s" % e, "#D93025")
            self.refresh()
            return
        self.refresh()
        self._set_status("%s：%s（%s）" % (row["label"], "显示" if checked else "隐藏", message), "#188038")


class ConfigWindow(QMainWindow):
    """环境变量、Git、镜像源、SSH、显示开关合成一个入口，每类配置一个标签。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("配置")
        x, y, w, h = tool_win_geometry()
        self.setGeometry(x, y, min(w + 180, 1000), min(h + 40, 700))
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        tabs = QTabWidget()
        tabs.setStyleSheet(_tab_style())
        tabs.addTab(_UserEnvPage(), "环境变量")
        tabs.addTab(_ProcessEnvPage(), "进程内变量")
        tabs.addTab(_GitConfigPage(), "Git 配置")
        tabs.addTab(_MirrorPage(), "镜像源")
        tabs.addTab(_SshPubkeyPage(), "SSH 密钥")
        tabs.addTab(_SshConfigPage(), "SSH 主机")
        tabs.addTab(_VisibilityPage(), "显示开关")
        self.setCentralWidget(tabs)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class MortgageWindow(QMainWindow):
    """房贷计算：等额本息 / 等额本金。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("房贷计算器")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        form = QGridLayout()
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(10)
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("如: 100")
        self.rate_input = QLineEdit()
        self.rate_input.setPlaceholderText("如: 3.6")
        self.years_input = QLineEdit()
        self.years_input.setPlaceholderText("如: 30")
        for edit in (self.amount_input, self.rate_input, self.years_input):
            edit.setStyleSheet(_lineedit_style())
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["等额本息", "等额本金"])
        self.mode_combo.setStyleSheet(_combo_style())

        rows = [("贷款金额(万元)", self.amount_input),
                ("年利率(%)", self.rate_input),
                ("贷款年限(年)", self.years_input),
                ("还款方式", self.mode_combo)]
        for i, (label, widget) in enumerate(rows):
            form.addWidget(QLabel(label), i, 0)
            form.addWidget(widget, i, 1)
        form.setColumnStretch(1, 1)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        calc_btn = QPushButton("计算")
        calc_btn.setFixedSize(70, 30)
        calc_btn.setCursor(QCursor(Qt.PointingHandCursor))
        calc_btn.setStyleSheet(_primary_btn())
        calc_btn.clicked.connect(self.do_calc)
        btn_row.addWidget(calc_btn)

        clear_btn = QPushButton("清空")
        clear_btn.setFixedSize(70, 30)
        clear_btn.setCursor(QCursor(Qt.PointingHandCursor))
        clear_btn.setStyleSheet(_secondary_btn())
        clear_btn.clicked.connect(self.do_clear)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        result_label = QLabel("计算结果")
        result_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        result_label.setStyleSheet("color: #333333;")
        layout.addWidget(result_label)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet(_output_style())
        layout.addWidget(self.result_text)

    def do_calc(self):
        try:
            principal = float(self.amount_input.text().strip()) * 10000
            rate = float(self.rate_input.text().strip()) / 100
            years = float(self.years_input.text().strip())
        except ValueError:
            self.result_text.setPlainText("请输入有效数字")
            return
        if principal <= 0 or years <= 0 or rate < 0:
            self.result_text.setPlainText("贷款金额和年限需大于 0，年利率不能为负")
            return

        n = int(round(years * 12))
        monthly_rate = rate / 12
        base_monthly = principal / n
        lines = ["贷款本金: %s 元" % format(principal, ",.2f"),
                 "年利率: %s%%   期数: %d 期" % (format(rate * 100, ".4g"), n)]

        if self.mode_combo.currentIndex() == 0:
            if monthly_rate == 0:
                monthly = base_monthly
            else:
                factor = (1 + monthly_rate) ** n
                monthly = principal * monthly_rate * factor / (factor - 1)
            total = monthly * n
            lines += ["每月还款: %s 元" % format(monthly, ",.2f"),
                      "还款总额: %s 元" % format(total, ",.2f"),
                      "利息总额: %s 元" % format(total - principal, ",.2f")]
        else:
            if monthly_rate == 0:
                first = last = base_monthly
                interest = 0.0
            else:
                first = base_monthly + principal * monthly_rate
                last = base_monthly * (1 + monthly_rate)
                interest = principal * monthly_rate * (n + 1) / 2
            lines += ["首月还款: %s 元（每月递减 %s 元）" % (
                          format(first, ",.2f"), format(base_monthly * monthly_rate, ",.2f")),
                      "末月还款: %s 元" % format(last, ",.2f"),
                      "还款总额: %s 元" % format(principal + interest, ",.2f"),
                      "利息总额: %s 元" % format(interest, ",.2f")]

        self.result_text.setPlainText("\n".join(lines))

    def do_clear(self):
        for edit in (self.amount_input, self.rate_input, self.years_input):
            edit.clear()
        self.result_text.setPlainText("")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


HTTP_STATUS_CODES = [
    (100, "Continue", "继续", "客户端应继续发送请求主体"),
    (101, "Switching Protocols", "切换协议", "服务器同意切换协议，如 WebSocket"),
    (200, "OK", "成功", "请求成功，最常见的成功状态码"),
    (201, "Created", "已创建", "资源创建成功，常用于 POST 后"),
    (202, "Accepted", "已接受", "请求已接受但未处理完成，异步任务"),
    (204, "No Content", "无内容", "请求成功但无返回内容，常用于 DELETE"),
    (301, "Moved Permanently", "永久重定向", "资源已永久移动到新 URL"),
    (302, "Found", "临时重定向", "资源临时移动到新 URL"),
    (304, "Not Modified", "未修改", "缓存有效，可使用本地缓存"),
    (400, "Bad Request", "错误请求", "请求语法错误，服务器无法理解"),
    (401, "Unauthorized", "未授权", "需要身份验证，如登录"),
    (403, "Forbidden", "禁止访问", "已认证但无权限访问资源"),
    (404, "Not Found", "未找到", "请求的资源不存在"),
    (405, "Method Not Allowed", "方法不允许", "请求方法不支持，如用 POST 访问只支持 GET 的接口"),
    (408, "Request Timeout", "请求超时", "服务器等待请求超时"),
    (409, "Conflict", "冲突", "请求与资源状态冲突，如重复创建"),
    (410, "Gone", "已删除", "资源已永久删除"),
    (413, "Payload Too Large", "载荷过大", "请求主体超过服务器限制"),
    (414, "URI Too Long", "URI 过长", "请求 URL 超过服务器限制"),
    (415, "Unsupported Media Type", "不支持的媒体类型", "请求格式不支持"),
    (429, "Too Many Requests", "请求过多", "触发限流，请稍后重试"),
    (500, "Internal Server Error", "服务器内部错误", "服务器遇到未预期的错误"),
    (501, "Not Implemented", "未实现", "服务器不支持请求的功能"),
    (502, "Bad Gateway", "错误网关", "网关或代理服务器收到无效响应"),
    (503, "Service Unavailable", "服务不可用", "服务器过载或维护中"),
    (504, "Gateway Timeout", "网关超时", "网关或代理服务器未及时收到响应"),
]


class ChmodWindow(QMainWindow):
    """chmod 权限计算器：八进制 ↔ 符号表示互转，可视化 9 个权限位。"""

    PERM_BITS = [
        ("所有者", ["读 (r)", "写 (w)", "执行 (x)"]),
        ("用户组", ["读 (r)", "写 (w)", "执行 (x)"]),
        ("其他人", ["读 (r)", "写 (w)", "执行 (x)"]),
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("chmod 权限计算器")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.checkboxes = []
        self.init_ui()
        self.update_from_octal("755")

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(12)

        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("八进制:"))
        self.octal_input = QLineEdit("755")
        self.octal_input.setFixedWidth(80)
        self.octal_input.setStyleSheet(_lineedit_style())
        self.octal_input.textChanged.connect(self.on_octal_changed)
        input_layout.addWidget(self.octal_input)
        input_layout.addSpacing(20)
        input_layout.addWidget(QLabel("符号:"))
        self.symbolic_label = QLabel("rwxr-xr-x")
        self.symbolic_label.setFont(QFont("Menlo", 14))
        self.symbolic_label.setStyleSheet("color: #1A73E8; padding: 4px 8px; background: #F0F7FF; border-radius: 4px;")
        input_layout.addWidget(self.symbolic_label)
        input_layout.addStretch()
        layout.addLayout(input_layout)

        grid = QGridLayout()
        grid.setSpacing(10)
        for group_idx, (group_name, perms) in enumerate(self.PERM_BITS):
            group_label = QLabel(group_name)
            group_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
            group_label.setStyleSheet("color: #333333;")
            grid.addWidget(group_label, group_idx, 0)
            for perm_idx, perm_name in enumerate(perms):
                cb = QCheckBox(perm_name)
                cb.setStyleSheet("QCheckBox { font-size: 12px; }")
                cb.stateChanged.connect(self.on_checkbox_changed)
                grid.addWidget(cb, group_idx, perm_idx + 1)
                self.checkboxes.append(cb)
        layout.addLayout(grid)

        cmd_layout = QHBoxLayout()
        cmd_layout.addWidget(QLabel("chmod 命令:"))
        self.cmd_label = QLabel("chmod 755 file")
        self.cmd_label.setFont(QFont("Menlo", 13))
        self.cmd_label.setStyleSheet("color: #333333; background: #F5F5F5; padding: 6px 10px; border-radius: 4px;")
        self.cmd_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        cmd_layout.addWidget(self.cmd_label, 1)
        copy_btn = QPushButton("复制")
        copy_btn.setFixedSize(60, 28)
        copy_btn.setCursor(QCursor(Qt.PointingHandCursor))
        copy_btn.setStyleSheet(_secondary_btn())
        copy_btn.clicked.connect(self.copy_command)
        cmd_layout.addWidget(copy_btn)
        layout.addLayout(cmd_layout)

        layout.addStretch()

    def on_octal_changed(self, text):
        text = text.strip()
        if not text or not text.isdigit():
            return
        try:
            value = int(text)
            if value < 0 or value > 777:
                return
            self.update_from_octal(text)
        except ValueError:
            pass

    def on_checkbox_changed(self):
        octal = self.compute_octal()
        self.octal_input.blockSignals(True)
        self.octal_input.setText(octal)
        self.octal_input.blockSignals(False)
        self.update_display(octal)

    def update_from_octal(self, octal_str):
        value = int(octal_str, 8)
        bits = []
        for i in range(8, -1, -1):
            bits.append(bool(value & (1 << i)))
        for cb, bit in zip(self.checkboxes, bits):
            cb.blockSignals(True)
            cb.setChecked(bit)
            cb.blockSignals(False)
        self.update_display(octal_str)

    def compute_octal(self):
        value = 0
        for i, cb in enumerate(self.checkboxes):
            if cb.isChecked():
                value |= (1 << (8 - i))
        return oct(value)[2:].zfill(3)

    def update_display(self, octal_str):
        value = int(octal_str, 8)
        symbolic = ""
        for i in range(8, -1, -1):
            bit = value & (1 << i)
            pos = 8 - i
            if pos % 3 == 0:
                symbolic += "r" if bit else "-"
            elif pos % 3 == 1:
                symbolic += "w" if bit else "-"
            else:
                symbolic += "x" if bit else "-"
        self.symbolic_label.setText(symbolic)
        self.cmd_label.setText(f"chmod {octal_str} file")

    def copy_command(self):
        QApplication.clipboard().setText(self.cmd_label.text())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


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


class DateTimeWindow(QMainWindow):
    """日期时间：时间戳转换、日期计算、时区转换。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("日期时间")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self._ns = None
        self._clock = QTimer(self)
        self._clock.timeout.connect(self._tick)
        tabs = QTabWidget()
        tabs.setStyleSheet(_tab_style())
        tabs.addTab(self._build_convert_tab(), "时间戳转换")
        tabs.addTab(self._build_calc_tab(), "日期计算")
        tabs.addTab(self._build_zone_tab(), "时区转换")
        container = QWidget()
        outer = QVBoxLayout(container)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.addWidget(tabs)
        self.setCentralWidget(container)
        self.input_edit.setText(str(int(time.time())))
        self._tick()

    # ---------- 通用 ----------
    def _small_btn(self, text, slot, primary=False):
        btn = QPushButton(text)
        btn.setFixedHeight(26)
        btn.setCursor(QCursor(Qt.PointingHandCursor))
        btn.setStyleSheet(_primary_btn() if primary else _secondary_btn())
        btn.clicked.connect(slot)
        return btn

    def _copy(self, btn, text):
        if not text:
            return
        QApplication.clipboard().setText(text)
        if btn is not None:
            old = btn.text()
            btn.setText("已复制")
            QTimer.singleShot(900, lambda: btn.setText(old))

    def _value_field(self):
        field = QLineEdit()
        field.setReadOnly(True)
        field.setFont(_dt_mono())
        field.setStyleSheet("QLineEdit { border: 1px solid #E3E6EA; border-radius: 4px;"
                            " padding: 3px 6px; background: #FAFBFC; color: #202124; }")
        return field

    def _zone_combo(self, default_index=0):
        combo = QComboBox()
        for i in range(len(DT_ZONES)):
            combo.addItem(_dt_zone_label(i))
        combo.setCurrentIndex(default_index)
        combo.setStyleSheet(_combo_style())
        return combo

    def _dt_edit(self):
        edit = QDateTimeEdit(QDateTime.currentDateTime())
        edit.setCalendarPopup(True)
        edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        edit.setStyleSheet("QDateTimeEdit { border: 1px solid #D0D0D0; border-radius: 4px;"
                           " padding: 4px 6px; font-size: 13px; }")
        return edit

    @staticmethod
    def _scroll_grid():
        host = QWidget()
        host.setObjectName("dtGrid")
        host.setStyleSheet("#dtGrid { background: #FFFFFF; }")
        grid = QGridLayout(host)
        grid.setContentsMargins(0, 0, 6, 0)
        grid.setAlignment(Qt.AlignTop)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: #FFFFFF; }")
        scroll.setWidget(host)
        return host, grid, scroll

    @staticmethod
    def _section_title(text):
        label = QLabel(text)
        label.setStyleSheet("color: #5F6368; font-size: 12px; font-weight: bold;")
        return label

    def showEvent(self, event):
        super().showEvent(event)
        self._tick()
        self._clock.start(1000)

    def hideEvent(self, event):
        super().hideEvent(event)
        self._clock.stop()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    # ---------- 时间戳转换 ----------
    def _build_convert_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(8)

        now_row = QHBoxLayout()
        now_row.addWidget(self._section_title("当前"))
        self.now_label = QLabel("")
        self.now_label.setFont(_dt_mono())
        self.now_label.setStyleSheet("color: #1A73E8;")
        self.now_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        now_row.addWidget(self.now_label, 1)
        self.copy_now_s = self._small_btn("复制秒", lambda: self._copy(self.copy_now_s, str(time.time_ns() // 10 ** 9)))
        self.copy_now_ms = self._small_btn("复制毫秒", lambda: self._copy(self.copy_now_ms, str(time.time_ns() // 10 ** 6)))
        now_row.addWidget(self.copy_now_s)
        now_row.addWidget(self.copy_now_ms)
        now_row.addWidget(self._small_btn("填入", lambda: self.input_edit.setText(str(int(time.time())))))
        layout.addLayout(now_row)

        in_row = QHBoxLayout()
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("时间戳或日期，如 1731552000 / 1731552000123 / 2026-11-14 12:00:00 / 2026-11-14T04:00:00Z")
        self.input_edit.setStyleSheet(_lineedit_style())
        self.input_edit.setFont(_dt_mono())
        self.input_edit.setClearButtonEnabled(True)
        self.input_edit.textChanged.connect(self._convert)
        in_row.addWidget(self.input_edit, 1)
        self.unit_combo = QComboBox()
        for name, _ in DT_UNITS:
            self.unit_combo.addItem(name)
        self.unit_combo.setStyleSheet(_combo_style())
        self.unit_combo.setToolTip("时间戳单位：自动识别按数值大小判断秒 / 毫秒 / 微秒 / 纳秒")
        self.unit_combo.currentIndexChanged.connect(self._convert)
        in_row.addWidget(self.unit_combo)
        self.zone_combo = self._zone_combo()
        self.zone_combo.setToolTip("无时区的输入按此时区解析，结果也按此时区显示")
        self.zone_combo.currentIndexChanged.connect(self._convert)
        in_row.addWidget(self.zone_combo)
        layout.addLayout(in_row)

        self.hint_label = QLabel("")
        self.hint_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.hint_label)

        grid_host, grid, scroll = self._scroll_grid()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(5)
        grid.setColumnStretch(1, 1)
        self.out_fields = {}
        rows = ["Unix 秒", "Unix 毫秒", "日期时间", "ISO 8601", "UTC", "自定义", "相对时间",
                "日历", "RFC 2822", "HTTP Date", "Unix 微秒", "Unix 纳秒"]
        for r, key in enumerate(rows):
            if key == "自定义":
                self.pattern_combo = QComboBox()
                self.pattern_combo.setEditable(True)
                self.pattern_combo.addItems(DT_PRESET_PATTERNS)
                self.pattern_combo.setStyleSheet(_combo_style())
                self.pattern_combo.setFixedWidth(150)
                self.pattern_combo.setToolTip("yyyy 年 MM 月 dd 日 HH 时 mm 分 ss 秒 SSS 毫秒 "
                                              "EEE 星期 a 上下午 Z/XXX 时区，'文字' 原样输出")
                self.pattern_combo.currentTextChanged.connect(self._convert)
                grid.addWidget(self.pattern_combo, r, 0)
            else:
                label = QLabel(key)
                label.setStyleSheet("color: #5F6368; font-size: 12px;")
                grid.addWidget(label, r, 0)
            field = self._value_field()
            grid.addWidget(field, r, 1)
            btn = QPushButton("复制")
            btn.setFixedSize(52, 24)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setStyleSheet(_secondary_btn())
            btn.clicked.connect(lambda _=False, f=field, b=btn: self._copy(b, f.text()))
            grid.addWidget(btn, r, 2)
            self.out_fields[key] = field
        layout.addWidget(scroll, 1)
        return page

    def _tick(self):
        ns = time.time_ns()
        local = dt_in_zone(dt_from_ns(ns), dt_zone(self.zone_combo.currentIndex()))
        self.now_label.setText(f"{ns // 10 ** 9}   {ns // 10 ** 6}   {dt_format(local, 'yyyy-MM-dd HH:mm:ss')}")
        if self._ns is not None:
            self.out_fields["相对时间"].setText(dt_relative(self._ns, ns))

    def _convert(self):
        text = self.input_edit.text().strip()
        tz = dt_zone(self.zone_combo.currentIndex())
        if not text:
            self._show_result(None, "", tz)
            return
        try:
            ns, label = dt_parse(text, tz, DT_UNITS[self.unit_combo.currentIndex()][1])
            self._show_result(ns, label, tz)
        except (ValueError, ArithmeticError) as e:
            self._show_result(None, str(e) or "无法识别", tz, error=True)

    def _show_result(self, ns, label, tz, error=False):
        self._ns = ns
        color = "#D93025" if error else "#188038"
        self.hint_label.setStyleSheet(f"color: {color}; font-size: 12px;")
        self.hint_label.setText(("✗ " if error else "✓ 识别为 ") + label if label else "")
        if ns is None:
            for field in self.out_fields.values():
                field.clear()
            return
        utc = dt_from_ns(ns)
        local = dt_in_zone(utc, tz)
        iso_frac = "" if ns % 10 ** 9 == 0 else ".SSS"
        year = local.year
        leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
        iso_year, iso_week, _ = local.isocalendar()
        try:
            rfc = email.utils.format_datetime(local)
            http = email.utils.format_datetime(utc, usegmt=True)
        except (ValueError, OverflowError):
            rfc = http = ""
        values = {
            "Unix 秒": str(ns // 10 ** 9),
            "Unix 毫秒": str(ns // 10 ** 6),
            "Unix 微秒": str(ns // 10 ** 3),
            "Unix 纳秒": str(ns),
            "日期时间": dt_format(local, "yyyy-MM-dd HH:mm:ss" + iso_frac),
            "ISO 8601": dt_format(local, f"yyyy-MM-dd'T'HH:mm:ss{iso_frac}XXX"),
            "UTC": dt_format(utc, f"yyyy-MM-dd'T'HH:mm:ss{iso_frac}'Z'"),
            "RFC 2822": rfc,
            "HTTP Date": http,
            "自定义": dt_format(local, self.pattern_combo.currentText()),
            "相对时间": dt_relative(ns),
            "日历": (f"星期{DT_WEEKDAYS[local.weekday()]} · 第 {local.timetuple().tm_yday} 天"
                     f" · ISO {iso_year}-W{iso_week:02d} · 第 {(local.month - 1) // 3 + 1} 季度"
                     f" · {'闰年' if leap else '平年'}"),
        }
        for key, value in values.items():
            self.out_fields[key].setText(value)
            self.out_fields[key].setCursorPosition(0)

    # ---------- 日期计算 ----------
    def _build_calc_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(8)

        layout.addWidget(self._section_title("时间间隔"))
        row = QHBoxLayout()
        self.span_start = self._dt_edit()
        self.span_end = self._dt_edit()
        self.span_end.setDateTime(QDateTime.currentDateTime().addDays(30))
        row.addWidget(QLabel("从"))
        row.addWidget(self.span_start, 1)
        row.addWidget(self._small_btn("⇄", self._swap_span))
        row.addWidget(QLabel("到"))
        row.addWidget(self.span_end, 1)
        row.addWidget(self._small_btn("现在", lambda: self.span_start.setDateTime(QDateTime.currentDateTime())))
        layout.addLayout(row)
        self.span_result = QLabel("")
        self.span_result.setFont(ui_font(14, 16, bold=True))
        self.span_result.setStyleSheet("color: #1A73E8;")
        self.span_result.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.span_result)
        self.span_detail = QLabel("")
        self.span_detail.setStyleSheet("color: #5F6368; font-size: 12px;")
        self.span_detail.setWordWrap(True)
        self.span_detail.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.span_detail)
        self.span_start.dateTimeChanged.connect(self._calc_span)
        self.span_end.dateTimeChanged.connect(self._calc_span)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #E0E0E0;")
        layout.addWidget(sep)

        layout.addWidget(self._section_title("时间加减"))
        row2 = QHBoxLayout()
        self.shift_base = self._dt_edit()
        row2.addWidget(self.shift_base, 1)
        row2.addWidget(self._small_btn("现在", lambda: self.shift_base.setDateTime(QDateTime.currentDateTime())))
        self.shift_amount = QSpinBox()
        self.shift_amount.setRange(-999999, 999999)
        self.shift_amount.setValue(7)
        self.shift_amount.setPrefix("+ ")
        self.shift_amount.setFixedWidth(110)
        self.shift_amount.setStyleSheet("QSpinBox { border: 1px solid #D0D0D0; border-radius: 4px;"
                                        " padding: 4px 6px; font-size: 13px; }")
        self.shift_amount.valueChanged.connect(
            lambda v: self.shift_amount.setPrefix("+ " if v >= 0 else ""))
        row2.addWidget(self.shift_amount)
        self.shift_unit = QComboBox()
        self.shift_unit.addItems(["秒", "分钟", "小时", "天", "周", "月", "年"])
        self.shift_unit.setCurrentText("天")
        self.shift_unit.setStyleSheet(_combo_style())
        row2.addWidget(self.shift_unit)
        layout.addLayout(row2)
        res_row = QHBoxLayout()
        self.shift_result = self._value_field()
        res_row.addWidget(self.shift_result, 1)
        self.shift_copy = self._small_btn("复制", lambda: self._copy(self.shift_copy, self.shift_result.text()))
        res_row.addWidget(self.shift_copy)
        layout.addLayout(res_row)
        self.shift_detail = QLabel("")
        self.shift_detail.setStyleSheet("color: #5F6368; font-size: 12px;")
        self.shift_detail.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.shift_detail)
        self.shift_base.dateTimeChanged.connect(self._calc_shift)
        self.shift_amount.valueChanged.connect(self._calc_shift)
        self.shift_unit.currentIndexChanged.connect(self._calc_shift)
        layout.addStretch()

        self._calc_span()
        self._calc_shift()
        return page

    def _swap_span(self):
        a, b = self.span_start.dateTime(), self.span_end.dateTime()
        self.span_start.setDateTime(b)
        self.span_end.setDateTime(a)

    def _calc_span(self):
        start = self.span_start.dateTime().toPyDateTime().replace(microsecond=0)
        end = self.span_end.dateTime().toPyDateTime().replace(microsecond=0)
        total = int((end - start).total_seconds())
        lo, hi = (start, end) if total >= 0 else (end, start)
        secs = abs(total)
        d, rest = divmod(secs, 86400)
        h, rest = divmod(rest, 3600)
        m, s = divmod(rest, 60)
        parts = [f"{v} {u}" for v, u in ((d, "天"), (h, "小时"), (m, "分"), (s, "秒")) if v]
        text = "相差 " + (" ".join(parts) if parts else "0 秒")
        if total < 0:
            text += "（结束早于开始）"
        self.span_result.setText(text)
        y, mo, dd = dt_calendar_diff(lo.date(), hi.date())
        cal = " ".join(f"{v} {u}" for v, u in ((y, "年"), (mo, "个月"), (dd, "天")) if v) or "0 天"
        self.span_detail.setText(
            f"按日历：{cal}  ·  共 {secs / 86400:,.2f} 天 / {secs / 3600:,.2f} 小时 / "
            f"{secs // 60:,} 分钟 / {secs:,} 秒  ·  {secs / 604800:,.2f} 周  ·  "
            f"工作日（周一至周五）{dt_workdays(lo.date(), hi.date())} 天")

    def _calc_shift(self):
        base = self.shift_base.dateTime()
        n = self.shift_amount.value()
        unit = self.shift_unit.currentText()
        if unit == "月":
            result = base.addMonths(n)
        elif unit == "年":
            result = base.addYears(n)
        elif unit in ("天", "周"):
            result = base.addDays(n * (7 if unit == "周" else 1))
        else:
            result = base.addSecs(n * {"秒": 1, "分钟": 60, "小时": 3600}[unit])
        if not result.isValid():
            self.shift_result.setText("超出范围")
            self.shift_detail.setText("")
            return
        py = result.toPyDateTime()
        self.shift_result.setText(result.toString("yyyy-MM-dd HH:mm:ss"))
        ts = result.toSecsSinceEpoch()
        self.shift_detail.setText(f"星期{DT_WEEKDAYS[py.weekday()]}  ·  Unix 秒 {ts}  ·  毫秒 {ts * 1000}"
                                  f"  ·  {dt_relative(ts * 10 ** 9)}")

    # ---------- 时区转换 ----------
    def _build_zone_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(8)

        row = QHBoxLayout()
        self.zone_time = self._dt_edit()
        row.addWidget(self.zone_time, 1)
        row.addWidget(self._small_btn("现在", lambda: self.zone_time.setDateTime(QDateTime.currentDateTime())))
        row.addWidget(QLabel("所在时区"))
        self.zone_src = self._zone_combo(2)
        row.addWidget(self.zone_src)
        layout.addLayout(row)
        note = QLabel("按真实时区规则换算，自动处理夏令时；“+1 天”表示与源时区不在同一天")
        note.setStyleSheet("color: #9AA0A6; font-size: 11px;")
        layout.addWidget(note)

        grid_host, grid, scroll = self._scroll_grid()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(4)
        grid.setColumnStretch(4, 1)
        self.zone_rows = []
        for i, (name, _, _) in enumerate(DT_ZONES):
            cells = [QLabel(name), QLabel(""), QLabel(""), QLabel("")]
            for c, cell in enumerate(cells):
                cell.setTextInteractionFlags(Qt.TextSelectableByMouse)
                if c in (1, 2):
                    cell.setFont(_dt_mono())
                grid.addWidget(cell, i, c)
            self.zone_rows.append(cells)
        layout.addWidget(scroll, 1)

        self.zone_time.dateTimeChanged.connect(self._calc_zones)
        self.zone_src.currentIndexChanged.connect(self._calc_zones)
        self._calc_zones()
        return page

    def _calc_zones(self):
        src_index = self.zone_src.currentIndex()
        naive = self.zone_time.dateTime().toPyDateTime().replace(microsecond=0)
        src = dt_localize(naive, dt_zone(src_index))
        for i, cells in enumerate(self.zone_rows):
            dt = dt_in_zone(src, dt_zone(i))
            day_diff = (dt.date() - src.date()).days
            cells[1].setText(dt_format(dt, "yyyy-MM-dd HH:mm:ss") + f"  周{DT_WEEKDAYS[dt.weekday()]}")
            cells[2].setText("UTC" + _dt_offset(dt))
            cells[3].setText(f"{day_diff:+d} 天" if day_diff else "")
            style = "color: #1A73E8; font-weight: bold;" if i == src_index else "color: #202124;"
            for cell in cells[:3]:
                cell.setStyleSheet(style)
            cells[3].setStyleSheet("color: #E37400; font-size: 12px;")


# 首页按钮的悬停说明：直接列出工具内部的页签或主要功能，省得一个个点开找。
TOOL_TIPS = {
    "网络诊断": "页签：Ping 测试 / 路由追踪 / DNS 查询 / 端口扫描 / 网络测速 · 目标地址跨页签同步",
    "进程管理": "功能：进程列表 · 按名称/PID/窗口标题搜索 · 按端口过滤 · 结束进程",
    "配置": "页签：环境变量 / 进程内变量 / Git 配置 / 镜像源 / SSH 密钥 / SSH 主机 / 显示开关",
    "数据格式": "页签：JSON / XML / JSON ↔ YAML · 格式化 · 校验 · 转换",
    "编解码": "页签：Base64 / URL / Unicode 转义",
    "加解密": "页签：JWT / AES / RSA / HMAC / 口令哈希 / 随机密钥",
    "正则测试": "功能：常用正则预设 · 实时匹配与高亮",
    "生成器": "页签：二维码 / 条形码 / UUID / 随机数",
    "颜色": "功能：颜色选择器 · HEX / RGB / HSL 互转",
    "取色器": "功能：屏幕取色 · 全屏放大镜 · C 复制并退出 · X 切换 HEX/RGB · 左键/ESC 退出",
    "截图贴图": "功能：区域截屏 · OCR 文字识别 · 本地识别 · 旁窗查看文字 · 选中复制 · 像素放大镜 · HEX / RGB 取色 · 复制颜色 · 调整选区 · 矩形 / 箭头 / 画笔 / 文字标注 · 截图自动复制 · 自定义截屏 · 剪贴板贴图 · 桌面置顶 · 缩放 / 透明度 · 隐藏显示全部贴图",
    "文本工具": "页签：处理与统计（排序 · 去重 · uniq -c · 命名风格 · 合并拆分 · SQL IN · 选区实时统计 · 编码字节 · 不可见字符）/ 文本对比（行内高亮 · 忽略空白/大小写 · 差异跳转 · unified diff）",
    "Cron 表达式": "页签：执行计划 / 书写规范",
    "哈希计算": "页签：文本哈希 / 文件哈希（MD5 / SHA1 / SHA256 / SHA512）",
    "开发速查": "分类：Docker / Linux / SSH / Vim / Windows / Git 命令速查 / HTTP 状态码 · 统一搜索 · 点击复制",
    "chmod 权限": "功能：八进制 ↔ 符号表示互转，可视化 9 个权限位",
    "日期时间": "页签：时间戳转换（秒/毫秒/微秒/纳秒自动识别 · ISO 8601 / RFC 2822 / 自定义格式）/ 日期计算（间隔 · 工作日 · 加减）/ 时区转换（夏令时）",
    "提醒事项": "功能：定时弹框提醒（如上下班打卡）· 每天/工作日/仅一次 · 稍后再提醒 · 提示音",
    "房贷计算器": "功能：等额本息 / 等额本金",
    "图片处理": "页签：转 Base64 / 格式转换 / 缩放压缩",
    "文字雨": "功能：桌面字符雨特效，开启时自动防黑屏（开关）",
    "防黑屏": "功能：阻止系统休眠与屏幕关闭（开关）",
    "数字转换": "页签：进制转换（二进制 / 八进制 / 十进制 / 十六进制）/ 罗马数字 / 金额大写",
    "商余计算": "功能：求整除的商和余数",
    "单位转换": "页签：字节 / 时间 / 长度 / 重量 / 面积 / 体积 / 速度 / 温度",
}

# 拼音搜索映射：支持输入拼音匹配工具（不增加依赖的轻量方案）
PINYIN_MAP = {
    "jincheng": ["进程管理"],
    "duankou": ["网络诊断"],
    "ping": ["网络诊断"],
    "dns": ["网络诊断"],
    "luyou": ["网络诊断"],
    "wangluo": ["网络诊断"],
    "zhenduan": ["网络诊断"],
    "cesu": ["网络诊断"],
    "peizhi": ["配置"],
    "huanjing": ["配置"],
    "bianma": ["编解码"],
    "base64": ["编解码"],
    "url": ["编解码"],
    "unicode": ["编解码"],
    "jiami": ["加解密"],
    "jwt": ["加解密"],
    "aes": ["加解密"],
    "rsa": ["加解密"],
    "hmac": ["加解密"],
    "zhengze": ["正则测试"],
    "regex": ["正则测试"],
    "shengcheng": ["生成器"],
    "erweima": ["生成器"],
    "tiaoxingma": ["生成器"],
    "uuid": ["生成器"],
    "geshi": ["数据格式"],
    "shuju": ["数据格式"],
    "yanse": ["颜色"],
    "quse": ["取色器", "截图贴图"],
    "quseqi": ["取色器", "截图贴图"],
    "fangdajing": ["取色器", "截图贴图"],
    "xiangsu": ["截图贴图"],
    "wenzishibie": ["截图贴图"],
    "shibie": ["截图贴图"],
    "pingmu": ["取色器", "截图贴图"],
    "jietu": ["截图贴图"],
    "jieping": ["截图贴图"],
    "tietu": ["截图贴图"],
    "jietutietu": ["截图贴图"],
    "shijianchuo": ["日期时间"],
    "timestamp": ["日期时间"],
    "unix": ["日期时间"],
    "json": ["数据格式"],
    "xml": ["数据格式"],
    "yaml": ["数据格式"],
    "wenben": ["文本工具"],
    "tongji": ["文本工具"],
    "duibi": ["文本工具"],
    "diff": ["文本工具"],
    "paixu": ["文本工具"],
    "quchong": ["文本工具"],
    "zishu": ["文本工具"],
    "cron": ["Cron 表达式"],
    "hash": ["哈希计算"],
    "md5": ["哈希计算"],
    "sha": ["哈希计算"],
    "mingling": ["开发速查"],
    "kaifa": ["开发速查"],
    "sucha": ["开发速查"],
    "docker": ["开发速查"],
    "linux": ["开发速查"],
    "ssh": ["开发速查", "配置"],
    "vim": ["开发速查"],
    "windows": ["开发速查"],
    "git": ["开发速查", "配置"],
    "http": ["开发速查"],
    "zhuangtai": ["开发速查"],
    "chmod": ["chmod 权限"],
    "quanxian": ["chmod 权限"],
    "riqi": ["日期时间"],
    "shijian": ["日期时间"],
    "shiqu": ["日期时间"],
    "shizhong": ["日期时间"],
    "tixing": ["提醒事项"],
    "tixingshixiang": ["提醒事项"],
    "shixiang": ["提醒事项"],
    "daka": ["提醒事项"],
    "shangban": ["提醒事项"],
    "xiaban": ["提醒事项"],
    "fangdai": ["房贷计算器"],
    "tupian": ["图片处理"],
    "wenziyu": ["文字雨"],
    "yu": ["文字雨"],
    "fangheiping": ["防黑屏"],
    "heiping": ["防黑屏"],
    "xiuxi": ["防黑屏"],
    "jinzhi": ["数字转换"],
    "shuzi": ["数字转换"],
    "eryuan": ["商余计算"],
    "shangyu": ["商余计算"],
    "danwei": ["单位转换"],
    "wendu": ["单位转换"],
    "changdu": ["单位转换"],
    "zhongliang": ["单位转换"],
    "suijishu": ["生成器"],
    "suiji": ["生成器"],
    "jine": ["数字转换"],
    "daxie": ["数字转换"],
    "renminbi": ["数字转换"],
    "luoma": ["数字转换"],
}


# ---- 提醒事项 -------------------------------------------------------------
REMINDERS_PATH = os.path.join(os.path.expanduser("~"), ".personal_toolbox", "reminders.json")
REPEAT_DAILY = "每天"
REPEAT_WEEKDAY = "工作日"
REPEAT_ONCE = "仅一次"
REPEAT_CHOICES = (REPEAT_DAILY, REPEAT_WEEKDAY, REPEAT_ONCE)
WEEKDAY_NAMES = ("", "周一", "周二", "周三", "周四", "周五", "周六", "周日")
SNOOZE_MINUTES = 10
# 错过太久就不再弹，避免开机时把昨天的提醒一次性补出来；只登记为已触发。
MISSED_QUIET_SECONDS = 3 * 3600
LAUNCH_AGENT_PATH = os.path.join(os.path.expanduser("~"), "Library",
                                 "LaunchAgents", "com.personal.toolbox.plist")
LAUNCH_AGENT_LABEL = "com.personal.toolbox"
WIN_RUN_KEY = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run"
WIN_RUN_NAME = "PersonalToolbox"


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


def play_alert_sound():
    """用系统自带能力发声，不引入依赖；环境不配合时静默。"""
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.Popen(["afplay", "/System/Library/Sounds/Glass.aiff"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif system == "Windows":
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    except (OSError, ImportError):
        pass


def app_launch_path():
    """自启指向的目标：打包后是 .app/exe，源码运行是 python + 脚本。"""
    if getattr(sys, "frozen", False):
        exe = sys.executable
        if platform.system() == "Darwin" and "/Contents/MacOS/" in exe:
            return exe[:exe.index("/Contents/MacOS/")]
        return exe
    return os.path.abspath(__file__)


def autostart_programs():
    if getattr(sys, "frozen", False) and platform.system() == "Darwin":
        return ["/usr/bin/open", "-a", app_launch_path()]
    if getattr(sys, "frozen", False):
        return [app_launch_path()]
    return [sys.executable, app_launch_path()]


def autostart_status():
    if platform.system() == "Darwin":
        return os.path.exists(LAUNCH_AGENT_PATH)
    if platform.system() == "Windows":
        result = subprocess.run(["reg", "query", WIN_RUN_KEY, "/v", WIN_RUN_NAME],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return result.returncode == 0
    return False


def set_autostart(enable):
    """写入或移除开机自启项，返回给用户核对的说明文字。"""
    system = platform.system()
    if system == "Darwin":
        import plistlib
        if enable:
            payload = {"Label": LAUNCH_AGENT_LABEL,
                       "ProgramArguments": autostart_programs(),
                       "RunAtLoad": True,
                       "KeepAlive": False}
            os.makedirs(os.path.dirname(LAUNCH_AGENT_PATH), exist_ok=True)
            with open(LAUNCH_AGENT_PATH, "wb") as f:
                plistlib.dump(payload, f)
            os.chmod(LAUNCH_AGENT_PATH, 0o600)
            uid = os.getuid()
            # 只卸载旧任务、不 bootstrap：bootstrap 会按 RunAtLoad 立刻拉起一个新实例，
            # 而新实例撞上单实例守卫，等于给用户自己弹一次"重复打开"。plist 留着，下次登录生效。
            subprocess.run(["launchctl", "bootout", "gui/%d/%s" % (uid, LAUNCH_AGENT_LABEL)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return "已开启：%s\n下次登录生效，启动命令：%s" % (
                LAUNCH_AGENT_PATH, " ".join(autostart_programs()))
        uid = os.getuid()
        subprocess.run(["launchctl", "bootout", "gui/%d/%s" % (uid, LAUNCH_AGENT_LABEL)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            os.remove(LAUNCH_AGENT_PATH)
        except OSError:
            pass
        return "已关闭：删除 %s" % LAUNCH_AGENT_PATH

    if system == "Windows":
        if enable:
            subprocess.run(["reg", "add", WIN_RUN_KEY, "/v", WIN_RUN_NAME,
                            "/t", "REG_SZ", "/d", '"%s"' % app_launch_path(), "/f"],
                           check=True)
            return "已开启：HKCU 启动项 %s = %s" % (WIN_RUN_NAME, app_launch_path())
        subprocess.run(["reg", "delete", WIN_RUN_KEY, "/v", WIN_RUN_NAME, "/f"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return "已关闭：删除启动项 %s" % WIN_RUN_NAME

    return "当前平台不支持开机自启，请保持应用运行（含最小化到托盘）"


class ReminderCard(QWidget):
    """屏幕正中的置顶提醒卡片。

    外层窗口透明，只为阴影留出空间；白底圆角画在内层 body 上。裸 QWidget 不加
    WA_StyledBackground 时样式表的 background 不会被绘制，整张卡片就是透明的。
    """

    snoozed = pyqtSignal()
    dismissed = pyqtSignal()

    CARD_W = 420
    CARD_H = 190
    SHADOW_MARGIN = 22

    def __init__(self, title, subtitle, note):
        # 不用 Qt.Tool/Qt.Dialog：这类面板在 macOS 上会随应用失焦被收起，
        # 用户就只有"切回工具箱"时才能看到提醒。普通窗口 + AppKit 抬层级才常驻最上层。
        super().__init__(None, Qt.Window | Qt.FramelessWindowHint |
                         Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(self.CARD_W + 2 * self.SHADOW_MARGIN,
                          self.CARD_H + 2 * self.SHADOW_MARGIN)
        # 卡片出现时用户正在用的 app；关闭后把前台还给它（必须在 show 之前记录）
        self._prev_pid = _mac_frontmost_pid()

        body = QWidget(self)
        body.setObjectName("reminderCardBody")
        body.setAttribute(Qt.WA_StyledBackground, True)
        body.setFixedSize(self.CARD_W, self.CARD_H)
        body.move(self.SHADOW_MARGIN, self.SHADOW_MARGIN)
        body.setStyleSheet("""
            QWidget#reminderCardBody { background: #FFFFFF; border: 1px solid #D0D0D0;
                border-radius: 10px; }
        """)
        shadow = QGraphicsDropShadowEffect(body)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 70))
        body.setGraphicsEffect(shadow)

        layout = QVBoxLayout(body)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setFont(QFont("PingFang SC", 20, QFont.Bold))
        title_label.setStyleSheet("color: #1F2328; border: none;")
        layout.addWidget(title_label)

        sub_label = QLabel(subtitle)
        sub_label.setStyleSheet("color: #57606A; font-size: 13px; border: none;")
        layout.addWidget(sub_label)

        if note:
            note_label = QLabel(note)
            note_label.setStyleSheet("color: #CF222E; font-size: 12px; border: none;")
            layout.addWidget(note_label)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        done_btn = QPushButton("完成")
        done_btn.setFixedSize(110, 34)
        done_btn.setCursor(QCursor(Qt.PointingHandCursor))
        done_btn.setStyleSheet(_primary_btn() + "QPushButton { font-size: 13px; }")
        done_btn.clicked.connect(self.close)
        btn_row.addWidget(done_btn)

        snooze_btn = QPushButton("稍后 %d 分钟" % SNOOZE_MINUTES)
        snooze_btn.setFixedSize(130, 34)
        snooze_btn.setCursor(QCursor(Qt.PointingHandCursor))
        snooze_btn.setStyleSheet(_secondary_btn() + "QPushButton { font-size: 13px; }")
        snooze_btn.clicked.connect(self._do_snooze)
        btn_row.addWidget(snooze_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._center_on_screen()

    def _do_snooze(self):
        self.snoozed.emit()
        self.close()

    def _center_on_screen(self):
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        geo = screen.availableGeometry()
        self.move(geo.x() + (geo.width() - self.width()) // 2,
                  geo.y() + (geo.height() - self.height()) // 2)

    def showEvent(self, event):
        super().showEvent(event)
        self.raise_()
        self.activateWindow()
        self.setFocus()
        # 抬到菜单栏之上并关掉 hidesOnDeactivate：这样切在别的应用里也能弹出来
        if _mac_is_cocoa():
            try:
                _mac_cover_menu_bar(self)
            except Exception:
                pass

    def closeEvent(self, event):
        self.dismissed.emit()
        super().closeEvent(event)
        # 点按钮会让 macOS 顺手激活工具箱，这里立刻把前台还给提醒弹出时用户在用的 app
        if self._prev_pid:
            _mac_reactivate(self._prev_pid)
            self._prev_pid = None

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)


class ReminderEngine(QObject):
    """20 秒轮询一次：到点弹框，顺带覆盖睡眠唤醒后错过的提醒。"""

    changed = pyqtSignal()

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.card = None
        self.card_rule = None
        self.snoozes = []
        self._timer = QTimer(self)
        self._timer.setInterval(20000)
        self._timer.timeout.connect(self.tick)
        self._timer.start()
        self.tick()

    def rules(self):
        return self.state["rules"]

    def forget(self, rule):
        # 稍后再提醒的队列持有规则对象本身，删除或停用规则时必须一起清掉，否则仍会再弹
        self.snoozes = [s for s in self.snoozes if s[1] is not rule]
        if self.card is not None and self.card_rule is rule:
            self.card.close()

    def remove_rule(self, rule):
        self.forget(rule)
        self.state["rules"] = [r for r in self.rules() if r is not rule]
        save_reminders(self.state)
        self.changed.emit()

    def tick(self):
        if self.card is not None:
            return
        now = QDateTime.currentDateTime()

        due = [s for s in self.snoozes if s[0] <= now]
        if due:
            due.sort(key=lambda s: s[0])
            when, rule, key = due[0]
            self.snoozes.remove(due[0])
            self._popup(rule, key, now, again=True)
            return

        for rule in self.rules():
            if not rule.get("enabled", True):
                continue
            occ = reminder_occurrence(rule, now)
            if occ is None:
                continue
            key = occ.toString("yyyy-MM-dd HH:mm")
            if rule.get("last_fired") == key:
                continue
            elapsed = occ.secsTo(now)
            if elapsed > MISSED_QUIET_SECONDS:
                # 太久以前：不打扰，也不写"上次触发"；仅一次的规则顺手停用，避免悬着
                if rule.get("repeat") == REPEAT_ONCE:
                    rule["enabled"] = False
                    save_reminders(self.state)
                    self.changed.emit()
                continue
            rule["last_fired"] = key
            if rule.get("repeat") == REPEAT_ONCE:
                rule["enabled"] = False
            save_reminders(self.state)
            self.changed.emit()
            self._popup(rule, key, now, missed=elapsed > 120)
            return

    def _popup(self, rule, key, now, missed=False, again=False):
        subtitle = "%s · %s" % (rule.get("time", ""), rule.get("repeat", REPEAT_DAILY))
        note = ""
        if missed:
            note = "已错过 %s（现在 %s）" % (key.split(" ")[1], now.toString("HH:mm"))
        elif again:
            note = "上次提醒后你选择了稍后再提醒"
        self.card = ReminderCard(rule.get("name", "提醒"), subtitle, note)
        self.card_rule = rule
        self.card.snoozed.connect(lambda: self._add_snooze(rule, key))
        self.card.dismissed.connect(self._clear_card)
        if self.state.get("sound", True):
            play_alert_sound()
        self.card.show()

    def _add_snooze(self, rule, key):
        when = QDateTime.currentDateTime().addSecs(SNOOZE_MINUTES * 60)
        self.snoozes.append((when, rule, key))

    def _clear_card(self):
        if self.card is not None:
            self.card.deleteLater()
            self.card = None
            self.card_rule = None


class _EventHotKeyID(ctypes.Structure):
    _fields_ = [("signature", ctypes.c_uint32), ("id", ctypes.c_uint32)]


class _EventTypeSpec(ctypes.Structure):
    _fields_ = [("eventClass", ctypes.c_uint32), ("eventKind", ctypes.c_uint32)]


_CARBON_HANDLER = ctypes.CFUNCTYPE(ctypes.c_int32, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)


SHORTCUT_ACTIONS = {"rain": "文字雨", "picker": "取色器", "capture": "截屏",
                    "capture_copy": "截屏并自动复制", "custom_capture": "自定义截屏",
                    "paste_image": "贴图", "toggle_pins": "隐藏 / 显示所有贴图"}


def default_shortcuts():
    modifier = "Meta+Alt+" if platform.system() == "Darwin" else "Ctrl+Alt+"
    return {"rain": modifier + "O", "picker": modifier + "C", "capture": modifier + "S",
            "capture_copy": modifier + "Shift+S", "custom_capture": modifier + "A",
            "paste_image": modifier + "V", "toggle_pins": modifier + "H"}


def shortcut_native(sequence, system=None):
    system = system or platform.system()
    seq = QKeySequence(sequence, QKeySequence.PortableText)
    if seq.count() != 1:
        raise ValueError("请设置单组快捷键，不支持连续多组按键")
    chord = seq[0]
    mods = chord & int(Qt.KeyboardModifierMask)
    key = chord & ~int(Qt.KeyboardModifierMask)
    allowed = int(Qt.ControlModifier | Qt.AltModifier | Qt.ShiftModifier | Qt.MetaModifier)
    if mods & ~allowed or (not mods and not Qt.Key_F1 <= key <= Qt.Key_F12):
        raise ValueError("F1～F12 可单独使用，其他按键请搭配修饰键（Ctrl、Alt、Shift 或 Win / Command）")
    if system == "Windows":
        keys = {Qt.Key_Space: 0x20, Qt.Key_Return: 0x0D, Qt.Key_Tab: 0x09,
                Qt.Key_Backspace: 0x08, Qt.Key_Delete: 0x2E, Qt.Key_Insert: 0x2D,
                Qt.Key_Home: 0x24, Qt.Key_End: 0x23, Qt.Key_PageUp: 0x21,
                Qt.Key_PageDown: 0x22, Qt.Key_Left: 0x25, Qt.Key_Up: 0x26,
                Qt.Key_Right: 0x27, Qt.Key_Down: 0x28}
        keys.update({k: k for k in range(Qt.Key_A, Qt.Key_Z + 1)})
        keys.update({k: k for k in range(Qt.Key_0, Qt.Key_9 + 1)})
        keys.update({Qt.Key_F1 + i: 0x70 + i for i in range(12)})
        flags = ((0x02 if mods & Qt.ControlModifier else 0) |
                 (0x01 if mods & Qt.AltModifier else 0) |
                 (0x04 if mods & Qt.ShiftModifier else 0) |
                 (0x08 if mods & Qt.MetaModifier else 0))
    elif system == "Darwin":
        letters = [0, 11, 8, 2, 14, 3, 5, 4, 34, 38, 40, 37, 46,
                   45, 31, 35, 12, 15, 1, 17, 32, 9, 13, 7, 16, 6]
        digits = [29, 18, 19, 20, 21, 23, 22, 26, 28, 25]
        functions = [122, 120, 99, 118, 96, 97, 98, 100, 101, 109, 103, 111]
        keys = {Qt.Key_Space: 49, Qt.Key_Return: 36, Qt.Key_Tab: 48,
                Qt.Key_Backspace: 51, Qt.Key_Delete: 117, Qt.Key_Home: 115,
                Qt.Key_End: 119, Qt.Key_PageUp: 116, Qt.Key_PageDown: 121,
                Qt.Key_Left: 123, Qt.Key_Up: 126, Qt.Key_Right: 124, Qt.Key_Down: 125}
        keys.update({Qt.Key_A + i: k for i, k in enumerate(letters)})
        keys.update({Qt.Key_0 + i: k for i, k in enumerate(digits)})
        keys.update({Qt.Key_F1 + i: k for i, k in enumerate(functions)})
        # Qt 在 macOS 上把 Control 映射为 Command、Meta 映射为物理 Control。
        flags = ((0x0100 if mods & Qt.ControlModifier else 0) |
                 (0x0800 if mods & Qt.AltModifier else 0) |
                 (0x0200 if mods & Qt.ShiftModifier else 0) |
                 (0x1000 if mods & Qt.MetaModifier else 0))
    else:
        raise ValueError("当前系统暂不支持全局快捷键")
    if key not in keys:
        raise ValueError("支持字母、数字、F1–F12、空格、回车及方向 / 编辑键")
    return flags, keys[key]


def load_shortcuts():
    result = default_shortcuts()
    try:
        with open(SHORTCUTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        saved = data.get(platform.system(), {}) if isinstance(data, dict) else {}
        for action in result:
            value = saved.get(action) if isinstance(saved, dict) else None
            if isinstance(value, str):
                try:
                    if value:
                        shortcut_native(value)
                    result[action] = value
                except ValueError:
                    continue
    except (OSError, ValueError):
        pass
    return result


def save_shortcuts(bindings):
    try:
        with open(SHORTCUTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data[platform.system()] = bindings
    os.makedirs(os.path.dirname(SHORTCUTS_PATH), exist_ok=True)
    temporary = SHORTCUTS_PATH + ".tmp"
    try:
        with open(temporary, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(temporary, SHORTCUTS_PATH)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


class _WindowsHotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    def nativeEventFilter(self, event_type, message):
        from ctypes import wintypes
        if event_type in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            msg = wintypes.MSG.from_address(int(message))
            action = self.owner._ids.get(msg.wParam)
            if msg.message == 0x0312 and action is not None:
                self.owner.triggered.emit(action)
                return True, 0
        return False, 0


class GlobalHotkey(QObject):
    triggered = pyqtSignal(str)
    status_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.bindings = load_shortcuts()
        self.errors = {}
        self.error = ""
        self.suspended = False
        self._ids = {}
        self._refs = {}
        self._filter = None
        self._carbon = None
        self._handler_ref = None
        self._handler_cb = None
        self._pump = None

    def start(self):
        if self.suspended or self._filter is not None or self._handler_ref is not None:
            return
        self.errors = {}
        try:
            if platform.system() == "Windows":
                self._filter = _WindowsHotkeyFilter(self)
                QApplication.instance().installNativeEventFilter(self._filter)
            elif platform.system() == "Darwin":
                self._start_mac()
            for index, (action, value) in enumerate(self.bindings.items(), 1):
                if not value:
                    continue
                try:
                    mods, key = shortcut_native(value)
                    hotkey_id = 0xB000 + index
                    if platform.system() == "Windows":
                        if not ctypes.windll.user32.RegisterHotKey(None, hotkey_id, mods | 0x4000, key):
                            raise ValueError("被系统或其他程序占用，请换一个组合")
                    else:
                        ref = ctypes.c_void_p()
                        status = self._carbon.RegisterEventHotKey(
                            key, mods, _EventHotKeyID(0x68746B31, hotkey_id),
                            self._carbon.GetApplicationEventTarget(), 0, ctypes.byref(ref))
                        if status != 0:
                            raise ValueError("注册失败（%s），可能被系统或其他程序占用" % status)
                        self._refs[hotkey_id] = ref
                    self._ids[hotkey_id] = action
                except ValueError as exc:
                    self.errors[action] = str(exc)
        except (OSError, ValueError) as exc:
            self.errors = {a: str(exc) for a, v in self.bindings.items() if v}
            self.stop()
        self.error = "；".join("%s：%s" % (SHORTCUT_ACTIONS[a], e) for a, e in self.errors.items())
        self.status_changed.emit()

    def _start_mac(self):
        carbon = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/Carbon.framework/Carbon")
        carbon.GetApplicationEventTarget.restype = ctypes.c_void_p
        carbon.RegisterEventHotKey.argtypes = [
            ctypes.c_uint32, ctypes.c_uint32, _EventHotKeyID,
            ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p)]
        carbon.RegisterEventHotKey.restype = ctypes.c_int32
        carbon.InstallEventHandler.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32,
            ctypes.POINTER(_EventTypeSpec), ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
        carbon.InstallEventHandler.restype = ctypes.c_int32
        carbon.RunCurrentEventLoop.argtypes = [ctypes.c_double]
        carbon.UnregisterEventHotKey.argtypes = [ctypes.c_void_p]
        carbon.RemoveEventHandler.argtypes = [ctypes.c_void_p]
        carbon.GetEventParameter.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32,
                                             ctypes.c_void_p, ctypes.c_uint32,
                                             ctypes.c_void_p, ctypes.c_void_p]
        carbon.GetEventParameter.restype = ctypes.c_int32
        self._carbon = carbon
        spec = _EventTypeSpec(0x6B657962, 5)
        self._handler_cb = _CARBON_HANDLER(self._on_carbon_hotkey)
        href = ctypes.c_void_p()
        status = carbon.InstallEventHandler(
            carbon.GetApplicationEventTarget(), ctypes.cast(self._handler_cb, ctypes.c_void_p),
            1, ctypes.byref(spec), None, ctypes.byref(href))
        if status != 0:
            raise ValueError("macOS 快捷键监听失败（%s）" % status)
        self._handler_ref = href
        if self._pump is None:
            self._pump = QTimer(self)
            self._pump.timeout.connect(lambda: carbon.RunCurrentEventLoop(0.0))
        self._pump.start(50)

    def _on_carbon_hotkey(self, next_handler, event, user_data):
        hotkey = _EventHotKeyID()
        status = self._carbon.GetEventParameter(
            event, 0x2D2D2D2D, 0x686B6964, None, ctypes.sizeof(hotkey), None, ctypes.byref(hotkey))
        action = self._ids.get(hotkey.id)
        if status == 0 and hotkey.signature == 0x68746B31 and action is not None:
            self.triggered.emit(action)
        return 0

    def stop(self):
        if self._filter is not None:
            QApplication.instance().removeNativeEventFilter(self._filter)
            for hotkey_id in self._ids:
                ctypes.windll.user32.UnregisterHotKey(None, hotkey_id)
            self._filter = None
        if self._pump is not None:
            self._pump.stop()
        if self._carbon is not None:
            for ref in self._refs.values():
                self._carbon.UnregisterEventHotKey(ref)
            if self._handler_ref is not None:
                self._carbon.RemoveEventHandler(self._handler_ref)
                self._handler_ref = None
        self._ids.clear()
        self._refs.clear()

    def set_suspended(self, suspended):
        if suspended == self.suspended:
            return
        self.suspended = suspended
        if suspended:
            self.stop()
        else:
            self.start()

    def apply(self, bindings):
        normalized = {}
        seen = {}
        for action in SHORTCUT_ACTIONS:
            value = bindings[action]
            if value:
                native = shortcut_native(value)
                if native in seen:
                    raise ValueError("%s与%s不能使用相同的快捷键" % (SHORTCUT_ACTIONS[seen[native]], SHORTCUT_ACTIONS[action]))
                seen[native] = action
                value = QKeySequence(value, QKeySequence.PortableText).toString(QKeySequence.PortableText)
            normalized[action] = value
        previous = self.bindings
        suspended = self.suspended
        self.stop()
        self.bindings = normalized
        self.suspended = False
        self.start()
        try:
            if self.errors:
                raise ValueError(self.error)
            save_shortcuts(normalized)
        except (OSError, ValueError):
            self.stop()
            self.bindings = previous
            self.start()
            raise
        finally:
            self.set_suspended(suspended)


class ReminderWindow(QMainWindow):
    """提醒事项：新建、启用/停用、删除提醒，提示音开关。"""

    PRESETS = (("上班打卡", 9, 0), ("午休", 12, 0), ("下班打卡", 18, 0))

    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.setWindowTitle("提醒事项")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }"
                           ' QWidget { font-family: "PingFang SC", "Microsoft YaHei", sans-serif; }')
        self._loading = False
        self.init_ui()
        self.engine.changed.connect(self.refresh)
        self.refresh()

    def _title(self, text):
        label = QLabel(text)
        label.setFont(ui_font(13, 14, bold=True))
        label.setStyleSheet("color: #222222;")
        return label

    def _field_label(self, text):
        label = QLabel(text)
        label.setStyleSheet("color: #57606A; font-size: 12px;")
        return label

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(18, 16, 18, 12)
        layout.setSpacing(12)

        form_card = QFrame()
        form_card.setObjectName("reminderForm")
        form_card.setStyleSheet("QFrame#reminderForm { background: #F8FAFC; border: 1px solid #E8EDF3; border-radius: 8px; }")
        form = QVBoxLayout(form_card)
        form.setContentsMargins(14, 12, 14, 12)
        form.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(6)
        head.addWidget(self._title("新建提醒"))
        head.addStretch()
        head.addWidget(self._field_label("快速填写"))
        chip_style = """
            QPushButton { color: #1A73E8; background: #FFFFFF; border: 1px solid #D6E4FA;
                border-radius: 13px; font-size: 12px; padding: 0 10px; }
            QPushButton:hover { background: #EEF4FE; }
        """
        for name, hour, minute in self.PRESETS:
            chip = QPushButton("%s %02d:%02d" % (name, hour, minute))
            chip.setFixedHeight(26)
            chip.setCursor(QCursor(Qt.PointingHandCursor))
            chip.setStyleSheet(chip_style)
            chip.clicked.connect(lambda _=False, n=name, h=hour, m=minute: self.fill_preset(n, h, m))
            head.addWidget(chip)
        form.addLayout(head)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("提醒内容，如 上班打卡、喝水、开会")
        self.name_input.setMaxLength(40)
        self.name_input.setStyleSheet(_lineedit_style())
        self.name_input.returnPressed.connect(self.add_rule)
        self.name_input.textChanged.connect(lambda _: self.form_message.hide())
        form.addWidget(self.name_input)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(self._field_label("时间"))
        self.time_input = QTimeEdit(QTime(9, 0))
        self.time_input.setDisplayFormat("HH:mm")
        self.time_input.setFixedSize(84, 32)
        self.time_input.setStyleSheet(_lineedit_style().replace("QLineEdit", "QTimeEdit"))
        row.addWidget(self.time_input)
        row.addSpacing(8)
        row.addWidget(self._field_label("重复"))
        self.repeat_input = QComboBox()
        self.repeat_input.addItems(REPEAT_CHOICES)
        self.repeat_input.setCurrentText(REPEAT_WEEKDAY)
        self.repeat_input.setFixedSize(96, 32)
        self.repeat_input.setStyleSheet(_combo_style())
        row.addWidget(self.repeat_input)
        row.addSpacing(8)
        self.date_label = self._field_label("日期")
        row.addWidget(self.date_label)
        self.date_input = QDateEdit(QDate.currentDate())
        self.date_input.setDisplayFormat("yyyy-MM-dd")
        self.date_input.setCalendarPopup(True)
        self.date_input.setMinimumDate(QDate.currentDate())
        self.date_input.setFixedSize(124, 32)
        self.date_input.setStyleSheet(_lineedit_style().replace("QLineEdit", "QDateEdit"))
        row.addWidget(self.date_input)
        row.addStretch()
        add_btn = QPushButton("添加提醒")
        add_btn.setFixedSize(96, 32)
        add_btn.setCursor(QCursor(Qt.PointingHandCursor))
        add_btn.setStyleSheet(_primary_btn() + "QPushButton { font-size: 13px; }")
        add_btn.clicked.connect(self.add_rule)
        row.addWidget(add_btn)
        form.addLayout(row)
        self.repeat_input.currentTextChanged.connect(self._sync_date_field)
        self._sync_date_field(self.repeat_input.currentText())

        self.form_message = QLabel("")
        self.form_message.setStyleSheet("color: #CF222E; font-size: 12px;")
        self.form_message.hide()
        form.addWidget(self.form_message)
        layout.addWidget(form_card)

        list_head = QHBoxLayout()
        list_head.setSpacing(8)
        list_head.addWidget(self._title("我的提醒"))
        self.count_label = self._field_label("")
        list_head.addWidget(self.count_label)
        list_head.addStretch()
        self.delete_btn = QPushButton("删除")
        self.delete_btn.setFixedSize(72, 28)
        self.delete_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.delete_btn.setToolTip("删除选中的提醒（Delete 键）")
        self.delete_btn.setStyleSheet(_secondary_btn() + """
            QPushButton:disabled { color: #A0A8B4; background: #F6F8FA; border-color: #E4E8EE; }
        """)
        self.delete_btn.clicked.connect(self.delete_rule)
        list_head.addWidget(self.delete_btn)
        layout.addLayout(list_head)

        self.table = QTreeWidget()
        self.table.setHeaderLabels(["提醒", "时间", "重复", "下次提醒"])
        self.table.setRootIsDecorated(False)
        self.table.setUniformRowHeights(True)
        self.table.setSelectionMode(QTreeWidget.SingleSelection)
        self.table.setStyleSheet("""
            QTreeWidget { border: 1px solid #E4EAF2; border-radius: 6px; outline: none;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; }
            QTreeWidget::item { height: 34px; }
            QTreeWidget::item:selected { background: #E8F0FE; color: #1F2328; }
            QHeaderView::section { background: #FAFBFC; color: #697386; border: none;
                border-bottom: 1px solid #E4EAF2; padding: 6px 8px; font-size: 12px; }
        """)
        header = self.table.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for column, width in ((1, 80), (2, 130), (3, 140)):
            header.setSectionResizeMode(column, QHeaderView.Fixed)
            self.table.setColumnWidth(column, width)
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.itemSelectionChanged.connect(self._sync_delete_btn)
        layout.addWidget(self.table, 1)

        self.empty_label = QLabel("还没有提醒\n在上方填写内容和时间，点击“添加提醒”")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #8290A5; font-size: 13px; background: #FBFCFD;"
                                       " border: 1px dashed #D6DEE8; border-radius: 6px;")
        layout.addWidget(self.empty_label, 1)

        footer = QHBoxLayout()
        self.sound_check = QCheckBox("提醒时播放提示音")
        self.sound_check.setChecked(bool(self.engine.state.get("sound", True)))
        self.sound_check.toggled.connect(self.on_sound_toggled)
        footer.addWidget(self.sound_check)
        footer.addStretch()
        self.next_label = QLabel("")
        self.next_label.setStyleSheet("color: #1F2328; font-size: 12px;")
        footer.addWidget(self.next_label)
        layout.addLayout(footer)

        hint = QLabel("工具箱运行时（包括最小化到托盘）才会提醒，错过的提醒在 3 小时内补弹；"
                      "提醒删除或停用后不会再弹出。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #8290A5; font-size: 11px;")
        layout.addWidget(hint)

    def _sync_date_field(self, repeat):
        once = repeat == REPEAT_ONCE
        self.date_label.setVisible(once)
        self.date_input.setVisible(once)
        if once and QDateTime(self.date_input.date(), self.time_input.time()) <= QDateTime.currentDateTime():
            self.date_input.setDate(QDate.currentDate().addDays(1))

    def _form_error(self, text):
        self.form_message.setText(text)
        self.form_message.show()

    def fill_preset(self, name, hour, minute):
        self.name_input.setText(name)
        self.time_input.setTime(QTime(hour, minute))
        self.repeat_input.setCurrentText(REPEAT_WEEKDAY)
        self.form_message.hide()
        self.name_input.setFocus()

    def add_rule(self):
        name = self.name_input.text().strip()
        if not name:
            self._form_error("请填写提醒内容")
            self.name_input.setFocus()
            return
        rule = {"name": name,
                "time": self.time_input.time().toString("HH:mm"),
                "repeat": self.repeat_input.currentText(),
                "enabled": True}
        if rule["repeat"] == REPEAT_ONCE:
            rule["date"] = self.date_input.date().toString("yyyy-MM-dd")
            if reminder_upcoming(rule, QDateTime.currentDateTime()) is None:
                self._form_error("这个时间已经过去了，请选择之后的日期或时间")
                return
        same = ("name", "time", "repeat", "date")
        if any(all(r.get(k) == rule.get(k) for k in same) for r in self.engine.rules()):
            self._form_error("已经有一条相同的提醒")
            return
        self.engine.rules().append(rule)
        save_reminders(self.engine.state)
        self.name_input.clear()
        self.form_message.hide()
        self.refresh()
        self.table.scrollToItem(self.table.topLevelItem(self.table.topLevelItemCount() - 1))

    def delete_rule(self):
        items = self.table.selectedItems()
        if not items:
            return
        index = self.table.indexOfTopLevelItem(items[0])
        rules = self.engine.rules()
        if 0 <= index < len(rules):
            self.table.clearSelection()
            self.engine.remove_rule(rules[index])

    def _repeat_text(self, rule):
        repeat = rule.get("repeat", REPEAT_DAILY)
        if repeat == REPEAT_ONCE:
            day = QDate.fromString(rule.get("date", ""), "yyyy-MM-dd")
            if day.isValid():
                return "%s · %s" % (repeat, day.toString("MM-dd"))
        return repeat

    def _next_text(self, rule, now):
        if not rule.get("enabled", True):
            if rule.get("repeat") == REPEAT_ONCE and rule.get("last_fired"):
                return "已提醒"
            return "已停用"
        when = reminder_upcoming(rule, now)
        return reminder_when_text(when, now) if when else "已过期"

    def _fill_item(self, item, rule, now):
        enabled = rule.get("enabled", True)
        item.setText(0, rule.get("name", ""))
        item.setCheckState(0, Qt.Checked if enabled else Qt.Unchecked)
        item.setToolTip(0, "勾选启用，取消勾选停用")
        item.setText(1, rule.get("time", ""))
        item.setText(2, self._repeat_text(rule))
        item.setText(3, self._next_text(rule, now))
        color = QColor("#1F2328") if enabled else QColor("#9AA4B2")
        for column in range(4):
            item.setForeground(column, QBrush(color))

    def refresh(self):
        now = QDateTime.currentDateTime()
        selected = self.table.selectedItems()
        selected_index = self.table.indexOfTopLevelItem(selected[0]) if selected else -1
        rules = self.engine.rules()
        self._loading = True
        self.table.clear()
        for rule in rules:
            item = QTreeWidgetItem()
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            self._fill_item(item, rule, now)
            self.table.addTopLevelItem(item)
        if 0 <= selected_index < len(rules):
            self.table.topLevelItem(selected_index).setSelected(True)
        self._loading = False
        self.table.setVisible(bool(rules))
        self.empty_label.setVisible(not rules)
        self._update_summary(now)

    def _update_summary(self, now):
        rules = self.engine.rules()
        enabled = sum(1 for r in rules if r.get("enabled", True))
        self.count_label.setText("共 %d 条 · 启用 %d 条" % (len(rules), enabled) if rules else "")
        name, when = next_reminder(rules, now)
        self.next_label.setText("下一条：%s · %s" % (name, reminder_when_text(when, now))
                                if when else "暂无待提醒的事项")
        self._sync_delete_btn()

    def _sync_delete_btn(self):
        self.delete_btn.setEnabled(bool(self.table.selectedItems()))

    def on_item_changed(self, item, column):
        if self._loading or column != 0:
            return
        index = self.table.indexOfTopLevelItem(item)
        if not (0 <= index < len(self.engine.rules())):
            return
        rule = self.engine.rules()[index]
        enabled = item.checkState(0) == Qt.Checked
        if rule.get("enabled", True) == enabled:
            return
        rule["enabled"] = enabled
        if not enabled:
            self.engine.forget(rule)
        save_reminders(self.engine.state)
        now = QDateTime.currentDateTime()
        self._loading = True
        self._fill_item(item, rule, now)
        self._loading = False
        self._update_summary(now)

    def on_sound_toggled(self, checked):
        self.engine.state["sound"] = checked
        save_reminders(self.engine.state)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() in (Qt.Key_Delete, Qt.Key_Backspace) and self.table.hasFocus():
            self.delete_rule()
        else:
            super().keyPressEvent(event)


class SectionOrderWindow(QMainWindow):
    """大类/工具排序：拖动大类调整顺序，拖动工具在类内排序或换到别的大类。"""

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.setWindowTitle("大类排序")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(8)

        hint = QLabel("拖动大类调整顺序；展开大类后拖动工具可在类内排序，或拖到别的大类上换类；也可选中后用右侧上移 / 下移微调。调整后立即生效并保存。")
        hint.setStyleSheet("color: #57606A; font-size: 12px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        mid = QHBoxLayout()
        mid.setSpacing(8)
        self.tree = _DragTree()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(20)
        self.tree.setDragDropMode(QAbstractItemView.InternalMove)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setDefaultDropAction(Qt.MoveAction)
        self.tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tree.setStyleSheet("""
            QTreeWidget { border: 1px solid #E5E7EB; border-radius: 8px; background: #FFFFFF; outline: 0; }
            QTreeWidget::item { height: 30px; color: #1F2328; font-size: 13px; }
            QTreeWidget::item:selected { background: transparent; color: #1F2328; }
            QTreeWidget::item:hover { background: #F5F8FC; }
        """)
        pal = self.tree.palette()
        pal.setColor(QPalette.Highlight, Qt.transparent)
        pal.setColor(QPalette.HighlightedText, QColor("#1F2328"))
        self.tree.setPalette(pal)
        self.tree.orderChanged.connect(self._sync_from_tree)
        self.tree.currentItemChanged.connect(self._update_move_buttons)
        mid.addWidget(self.tree, 1)

        side = QVBoxLayout()
        side.setSpacing(6)
        self.up_btn = QPushButton("上移")
        self.down_btn = QPushButton("下移")
        for b in (self.up_btn, self.down_btn):
            b.setFixedSize(56, 30)
            b.setCursor(QCursor(Qt.PointingHandCursor))
            b.setStyleSheet(_secondary_btn() + "QPushButton { font-size: 12px; }")
        self.up_btn.clicked.connect(lambda: self._move(-1))
        self.down_btn.clicked.connect(lambda: self._move(1))
        side.addWidget(self.up_btn)
        side.addWidget(self.down_btn)
        side.addStretch()
        mid.addLayout(side)
        layout.addLayout(mid, 1)

        btn_row = QHBoxLayout()
        reset_btn = QPushButton("恢复默认")
        reset_btn.setFixedSize(90, 30)
        reset_btn.setCursor(QCursor(Qt.PointingHandCursor))
        reset_btn.setStyleSheet(_secondary_btn() + "QPushButton { font-size: 12px; }")
        reset_btn.clicked.connect(self._reset)
        btn_row.addWidget(reset_btn)
        btn_row.addStretch()
        done_btn = QPushButton("完成")
        done_btn.setFixedSize(80, 30)
        done_btn.setCursor(QCursor(Qt.PointingHandCursor))
        done_btn.setStyleSheet(_primary_btn() + "QPushButton { font-size: 12px; }")
        done_btn.clicked.connect(self.close)
        btn_row.addWidget(done_btn)
        layout.addLayout(btn_row)

        self.refresh()

    def refresh(self):
        self.tree.clear()
        for cat in self.main.section_order:
            ci = QTreeWidgetItem([cat])
            self.tree.addTopLevelItem(ci)
            for name in self.main.tool_order.get(cat, []):
                ci.addChild(QTreeWidgetItem([name]))
            ci.setExpanded(False)
        self._update_move_buttons()

    def _sync_from_tree(self):
        root = self.tree.invisibleRootItem()
        cat_set = set(self.main.section_order)
        all_tools = set(self.main.all_buttons.keys())
        cats, tools, seen = [], {}, set()
        valid = True
        for i in range(root.childCount()):
            ci = root.child(i)
            cat = ci.text(0)
            if cat not in cat_set or cat in cats:
                valid = False
                break
            cats.append(cat)
            lst = []
            for j in range(ci.childCount()):
                ti = ci.child(j)
                name = ti.text(0)
                if ti.childCount() or name not in all_tools or name in seen:
                    valid = False
                    break
                seen.add(name)
                lst.append(name)
            if not valid:
                break
            tools[cat] = lst
        if valid and set(cats) == cat_set and seen == all_tools:
            self.main.section_order = cats
            self.main.tool_order = tools
            self.main.apply_section_order()
            self.main.apply_tool_order()
        else:
            # 非法落点（工具变成顶层 / 大类嵌套等）回退到当前生效顺序
            self.refresh()
        self._update_move_buttons()

    def _move(self, delta):
        item = self.tree.currentItem()
        if item is None:
            return
        parent = item.parent() or self.tree.invisibleRootItem()
        idx = parent.indexOfChild(item)
        target = idx + delta
        if not 0 <= target < parent.childCount():
            return
        parent.takeChild(idx)
        parent.insertChild(target, item)
        self.tree.setCurrentItem(item)
        self._sync_from_tree()

    def _update_move_buttons(self, *args):
        item = self.tree.currentItem()
        if item is None:
            self.up_btn.setEnabled(False)
            self.down_btn.setEnabled(False)
            return
        parent = item.parent() or self.tree.invisibleRootItem()
        idx = parent.indexOfChild(item)
        self.up_btn.setEnabled(idx > 0)
        self.down_btn.setEnabled(idx < parent.childCount() - 1)

    def _reset(self):
        self.main.reset_section_order()
        self.refresh()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)


class SettingsWindow(QMainWindow):

    REPO_URL = "https://github.com/FantasyEngineer/personal_tool"

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.setWindowTitle("设置")
        self.setGeometry(*tool_win_geometry())
        self.resize(660, 590)
        self.setMinimumSize(590, 540)
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(20, 18, 20, 16)
        outer.setSpacing(14)
        title = QLabel("设置")
        title.setFont(ui_font(19, 22, bold=True))
        title.setStyleSheet("color: #202124;")
        outer.addWidget(title)
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; border-top: 1px solid #E8EAED; }
            QTabBar::tab { padding: 10px 22px; color: #697386; font-size: 13px;
                background: transparent; border-bottom: 2px solid transparent; }
            QTabBar::tab:selected { color: #1A73E8; border-bottom: 2px solid #1A73E8; }
            QTabBar::tab:hover { color: #1A73E8; }
        """)
        outer.addWidget(self.tabs, 1)
        general = QWidget()
        self.tabs.addTab(general, "通用")
        layout = QVBoxLayout(general)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(10)

        layout.addWidget(self._group_title("开机自启"))
        self.autostart_check = QCheckBox("开机自动启动工具箱")
        self.autostart_check.setChecked(autostart_status())
        self.autostart_check.toggled.connect(self.on_autostart_toggled)
        layout.addWidget(self.autostart_check)
        self.autostart_status = QLabel("已开启，下次登录生效" if autostart_status() else "未开启")
        self.autostart_status.setWordWrap(True)
        self.autostart_status.setStyleSheet("color: #57606A; font-size: 12px;")
        layout.addWidget(self.autostart_status)

        layout.addWidget(self._group_title("首页排序"))
        sort_row = QHBoxLayout()
        sort_row.setSpacing(8)
        sort_hint = QLabel("调整大类与工具在首页的展示顺序")
        sort_hint.setStyleSheet("color: #57606A; font-size: 12px;")
        sort_row.addWidget(sort_hint, 1)
        open_sort = QPushButton("打开")
        open_sort.setFixedSize(70, 28)
        open_sort.setCursor(QCursor(Qt.PointingHandCursor))
        open_sort.setStyleSheet(_secondary_btn() + "QPushButton { font-size: 12px; }")
        open_sort.clicked.connect(self.main.show_section_order)
        sort_row.addWidget(open_sort)
        layout.addLayout(sort_row)

        layout.addWidget(self._group_title("缓存目录"))
        cache_row = QHBoxLayout()
        cache_row.setSpacing(8)
        cache_path = QLabel(os.path.join(os.path.expanduser("~"), ".personal_toolbox"))
        cache_path.setStyleSheet("color: #57606A; font-size: 12px;")
        cache_row.addWidget(cache_path, 1)
        open_cache = QPushButton("打开")
        open_cache.setFixedSize(70, 28)
        open_cache.setCursor(QCursor(Qt.PointingHandCursor))
        open_cache.setStyleSheet(_secondary_btn() + "QPushButton { font-size: 12px; }")
        open_cache.clicked.connect(self.main._open_cache_dir)
        cache_row.addWidget(open_cache)
        layout.addLayout(cache_row)

        layout.addWidget(self._group_title("源码仓库"))
        repo_row = QHBoxLayout()
        repo_row.setSpacing(8)
        repo_label = QLabel(self.REPO_URL)
        repo_label.setStyleSheet("color: #57606A; font-size: 12px;")
        repo_row.addWidget(repo_label, 1)
        open_repo = QPushButton("打开")
        open_repo.setFixedSize(70, 28)
        open_repo.setCursor(QCursor(Qt.PointingHandCursor))
        open_repo.setStyleSheet(_secondary_btn() + "QPushButton { font-size: 12px; }")
        open_repo.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.REPO_URL)))
        repo_row.addWidget(open_repo)
        layout.addLayout(repo_row)

        layout.addWidget(self._group_title("检查更新"))
        upd_row = QHBoxLayout()
        upd_row.setSpacing(8)
        upd_hint = QLabel("当前版本 v%s" % APP_VERSION)
        upd_hint.setStyleSheet("color: #57606A; font-size: 12px;")
        upd_row.addWidget(upd_hint, 1)
        upd_row.addWidget(self.main.update_btn)
        layout.addLayout(upd_row)

        layout.addStretch()
        self._build_shortcuts_page()
        self.tabs.currentChanged.connect(self._sync_hotkeys)
        self.main.hotkey.status_changed.connect(self._refresh_shortcut_status)

    def _build_shortcuts_page(self):
        page = QWidget()
        self.tabs.addTab(page, "快捷键")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 18, 0, 0)
        layout.setSpacing(14)
        heading = self._group_title("全局快捷键")
        layout.addWidget(heading)
        hint = QLabel("工具箱运行时，在其他应用中也可使用。点击输入框，直接按下新的组合键。")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #697386; font-size: 12px;")
        layout.addWidget(hint)
        self.shortcut_edits = {}
        self.shortcut_states = {}
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 8, 8)
        body_layout.setSpacing(12)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.viewport().setObjectName("shortcutViewport")
        scroll.viewport().setStyleSheet("QWidget#shortcutViewport { background: #FFFFFF; }")
        scroll.setWidget(body)
        body.setAutoFillBackground(False)
        layout.addWidget(scroll, 1)
        descriptions = {"rain": "开启 / 关闭桌面文字雨，自动联动防黑屏",
                        "picker": "启动 / 关闭屏幕放大镜，快速获取颜色",
                        "capture": "像素取色与本地 OCR，框选后调整与标注，直接复制、保存或贴图",
                        "capture_copy": "框选完成后直接复制，不弹出预览",
                        "custom_capture": "按屏幕、坐标及尺寸截取指定区域",
                        "paste_image": "把剪贴板中的图片固定到桌面",
                        "toggle_pins": "统一隐藏或显示全部桌面贴图"}
        for action, name in SHORTCUT_ACTIONS.items():
            card = QFrame()
            card.setObjectName("shortcutCard")
            card.setStyleSheet("QFrame#shortcutCard { background: #F8FAFC; border: 1px solid #E8EDF3; border-radius: 8px; }")
            row = QHBoxLayout(card)
            row.setContentsMargins(14, 12, 14, 12)
            row.setSpacing(10)
            text = QVBoxLayout()
            text.setSpacing(4)
            text.addWidget(self._group_title(name))
            description = QLabel(descriptions[action])
            description.setWordWrap(True)
            description.setStyleSheet("color: #697386; font-size: 11px;")
            text.addWidget(description)
            state = QLabel()
            state.setWordWrap(True)
            text.addWidget(state)
            self.shortcut_states[action] = state
            row.addLayout(text, 1)
            edit = QKeySequenceEdit(QKeySequence(self.main.hotkey.bindings[action]))
            edit.setFixedSize(180, 36)
            edit.setStyleSheet("""
                QLineEdit { background: white; border: 1px solid #D6DEE8; border-radius: 6px;
                    padding: 6px 8px; font-size: 13px; }
                QLineEdit:focus { border: 1px solid #1A73E8; }
            """)
            edit.findChild(QLineEdit).setPlaceholderText("未设置")
            edit.setToolTip("F1～F12 可单独使用；字母、数字等需搭配修饰键")
            edit.keySequenceChanged.connect(lambda seq, a=action: self._shortcut_edited(a, seq))
            self.shortcut_edits[action] = edit
            row.addWidget(edit)
            clear = QPushButton("清除")
            clear.setFixedSize(48, 30)
            clear.setCursor(QCursor(Qt.PointingHandCursor))
            clear.setStyleSheet("QPushButton { color: #697386; background: transparent; border: none; font-size: 12px; } QPushButton:hover { color: #1A73E8; }")
            clear.clicked.connect(edit.clear)
            row.addWidget(clear)
            body_layout.addWidget(card)
        explanation = ("macOS：⌘ Command · ⌃ Control · ⌥ Option · ⇧ Shift。"
                       if platform.system() == "Darwin" else "Windows：Meta 表示 Win 键；可搭配 Ctrl、Alt、Shift。")
        note = QLabel(explanation + "\nF1～F12 可单独设置，其他按键需使用组合键。\n清除并保存可停用；编辑本页时暂停全局快捷键，切换到其他窗口后恢复。")
        note.setWordWrap(True)
        note.setStyleSheet("color: #697386; font-size: 11px; line-height: 1.5;")
        body_layout.addWidget(note)
        body_layout.addWidget(self._group_title("取色器内置按键"))
        local = QLabel("C  复制并退出     X  切换 HEX / RGB     Esc / 左键 / 右键  退出")
        local.setWordWrap(True)
        local.setStyleSheet("color: #57606A; background: #F8FAFC; border-radius: 6px; padding: 10px; font-size: 12px;")
        body_layout.addWidget(local)
        capture_hint = QLabel("截屏取色：像素放大镜 · C 复制颜色并退出 · X 切换 HEX / RGB\n截屏：框选后调整 / 标注 · Enter / Ctrl+C 复制截图 · Ctrl+T 贴图 · Esc 退出 · 右键重选\n文字识别：框选后点击识别按钮 / Ctrl+O，识别后在旁窗查看 / 编辑 / 选中复制，不自动复制或退出；无文字或失败可调整选区重试\n贴图：拖动移动 · 滚轮缩放 · Ctrl+滚轮调透明度 · 双击 / Esc 隐藏 · 全局显隐快捷键恢复")
        capture_hint.setWordWrap(True)
        capture_hint.setStyleSheet("color: #697386; font-size: 11px;")
        body_layout.addWidget(capture_hint)
        body_layout.addStretch()
        self.shortcut_feedback = QLabel()
        self.shortcut_feedback.setWordWrap(True)
        self.shortcut_feedback.setStyleSheet("color: #697386; font-size: 12px;")
        layout.addWidget(self.shortcut_feedback)
        buttons = QHBoxLayout()
        reset = QPushButton("恢复默认")
        reset.setFixedSize(94, 32)
        reset.setStyleSheet(_secondary_btn())
        reset.setCursor(QCursor(Qt.PointingHandCursor))
        reset.clicked.connect(self._reset_shortcuts)
        buttons.addWidget(reset)
        buttons.addStretch()
        self.save_shortcuts_btn = QPushButton("保存快捷键")
        self.save_shortcuts_btn.setFixedSize(106, 32)
        self.save_shortcuts_btn.setStyleSheet(_primary_btn())
        self.save_shortcuts_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.save_shortcuts_btn.clicked.connect(self._save_shortcuts)
        buttons.addWidget(self.save_shortcuts_btn)
        layout.addLayout(buttons)
        self._refresh_shortcut_status()

    def _shortcut_edited(self, action, sequence):
        if sequence.count() > 1:
            self.shortcut_edits[action].setKeySequence(QKeySequence(sequence[0]))
            return
        self.shortcut_feedback.setText("修改尚未保存，点击“保存快捷键”后生效。")
        self.shortcut_feedback.setStyleSheet("color: #697386; font-size: 12px;")
        self._refresh_shortcut_status()

    def _refresh_shortcut_status(self):
        for action, state in self.shortcut_states.items():
            value = self.shortcut_edits[action].keySequence().toString(QKeySequence.PortableText)
            error = self.main.hotkey.errors.get(action)
            if value != self.main.hotkey.bindings[action]:
                text, color = "待保存" if value else "待停用", "#B26A00"
            elif error:
                text, color = error, "#C62828"
            else:
                text, color = ("已设置 · 全局" if value else "未设置 · 已停用"), "#188038" if value else "#697386"
            state.setText(text)
            state.setStyleSheet("color: %s; font-size: 11px;" % color)

    def _reset_shortcuts(self):
        for action, value in default_shortcuts().items():
            self.shortcut_edits[action].setKeySequence(QKeySequence(value))
        self.shortcut_feedback.setText("已填入默认组合，保存后生效。")

    def _save_shortcuts(self):
        bindings = {a: edit.keySequence().toString(QKeySequence.PortableText)
                    for a, edit in self.shortcut_edits.items()}
        try:
            self.main.hotkey.apply(bindings)
        except (OSError, ValueError) as exc:
            self.shortcut_feedback.setText("保存失败：%s。原快捷键保持不变。" % exc)
            self.shortcut_feedback.setStyleSheet("color: #C62828; font-size: 12px;")
            return
        self.shortcut_feedback.setText("已保存；切换到其他窗口即可使用，重启后仍然有效。")
        self.shortcut_feedback.setStyleSheet("color: #188038; font-size: 12px;")
        self._refresh_shortcut_status()

    def _sync_hotkeys(self, *_):
        self.main.hotkey.set_suspended(self.isVisible() and self.isActiveWindow() and self.tabs.currentIndex() == 1)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.ActivationChange and hasattr(self, "tabs"):
            self._sync_hotkeys()

    def hideEvent(self, event):
        self.main.hotkey.set_suspended(False)
        super().hideEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        for action, value in self.main.hotkey.bindings.items():
            edit = self.shortcut_edits[action]
            edit.blockSignals(True)
            edit.setKeySequence(QKeySequence(value))
            edit.blockSignals(False)
        self.shortcut_feedback.clear()
        self._refresh_shortcut_status()
        self._sync_hotkeys()

    def _group_title(self, text):
        lb = QLabel(text)
        lb.setFont(ui_font(13, 14, bold=True))
        lb.setStyleSheet("color: #222222;")
        return lb

    def on_autostart_toggled(self, checked):
        try:
            self.autostart_status.setText(set_autostart(checked))
        except Exception as exc:
            self.autostart_check.blockSignals(True)
            self.autostart_check.setChecked(autostart_status())
            self.autostart_check.blockSignals(False)
            self.autostart_status.setText("设置失败：%s" % exc)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)


class ToolboxWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"系统工具箱 v{APP_VERSION}")
        screen = QApplication.primaryScreen().availableGeometry()
        w, h = 700, int(screen.height() * 0.68)
        self.setGeometry(screen.x() + (screen.width() - w) // 2,
                         screen.y() + (screen.height() - h) // 2, w, h)
        self.setStyleSheet("QMainWindow { background: #F6F8FC; }")
        self.ip, self.mac, self.adapter = get_effective_ip()
        self.popup = None
        self.data_format_window = None
        self.codec_window = None
        self.hash_window = None
        self.crypto_window = None
        self.regex_window = None
        self.text_tool_window = None
        self.generator_window = None
        self.number_convert_window = None
        self.divmod_window = None
        self.color_window = None
        self.screenshot_tool = None
        self._screen_pick_overlay = None
        self._screen_pick_prev_pid = None
        self._screen_pick_silent_exit = False
        self.config_window = None
        self.unit_window = None
        self.cron_window = None
        self.image_window = None
        self.network_window = None
        self.dev_reference_window = None
        self.mortgage_window = None
        self.chmod_window = None
        self.datetime_window = None
        self.reminder_window = None
        self.section_order_window = None
        self.settings_window = None
        self.tray_icon = None
        self.init_ui()
        self.init_tray()
        # 引擎挂在主窗口上：窗口关掉、最小化到托盘后照样按点弹框
        self.reminder_engine = ReminderEngine(load_reminders(), self)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(18, 14, 18, 10)
        main_layout.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(12)
        title = QLabel("工具箱")
        title.setFont(ui_font(18, 21, bold=True))
        title.setStyleSheet("color: #202B3D;")
        header.addWidget(title)
        subtitle = QLabel("系统 · 开发 · 日常")
        subtitle.setFont(ui_font(10, 12))
        subtitle.setStyleSheet("color: #8290A5;")
        header.addWidget(subtitle)
        header.addStretch()
        self.tool_count_label = QLabel()
        self.tool_count_label.setFont(ui_font(10, 12))
        self.tool_count_label.setStyleSheet("color: #69788F;")
        header.addWidget(self.tool_count_label)
        main_layout.addLayout(header)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索工具、功能或拼音 · 唯一结果按 Enter 打开")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedHeight(40)
        self.search_input.setStyleSheet("""
            QLineEdit { background: #FFFFFF; color: #263449; font-size: 13px;
                border: 1px solid #DAE2ED; border-radius: 8px; padding: 0 12px; }
            QLineEdit:hover { border-color: #BCCBE0; }
            QLineEdit:focus { border-color: #1A73E8; }
        """)
        self.search_input.textChanged.connect(self.filter_tools)
        self.search_input.returnPressed.connect(self.open_single_match)
        self.search_input.setFocusPolicy(Qt.ClickFocus)
        main_layout.addWidget(self.search_input)

        self.history_mode = "recent"
        self.usage_history = []
        self.search_history = []
        self.max_history = 12
        self.history_widget = QWidget()
        self.history_widget.setFixedHeight(64)
        self.history_widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        history_layout = QVBoxLayout(self.history_widget)
        history_layout.setContentsMargins(0, 0, 0, 4)
        history_layout.setSpacing(6)

        history_header = QHBoxLayout()
        history_header.setSpacing(14)
        self.history_tabs = {}
        for mode, label in (("recent", "最近使用"), ("search", "搜索记录")):
            btn = QPushButton(label)
            btn.setFixedHeight(22)
            btn.setCheckable(True)
            btn.setChecked(mode == self.history_mode)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton { color: #8290A5; background: transparent; border: none;
                    border-bottom: 2px solid transparent; padding: 0 0 3px; font-size: 12px; }
                QPushButton:hover { color: #1A73E8; }
                QPushButton:checked { color: #1A73E8; border-bottom-color: #1A73E8; }
            """)
            btn.clicked.connect(lambda _checked, m=mode: self._set_history_mode(m))
            history_header.addWidget(btn)
            self.history_tabs[mode] = btn
        history_header.addStretch()
        self.history_more = QPushButton("全部")
        self.history_more.setFixedHeight(22)
        self.history_more.setCursor(Qt.PointingHandCursor)
        self.history_more.setStyleSheet("""
            QPushButton { color: #69788F; border: none; background: transparent;
                padding: 0 16px 0 6px; font-size: 11px; }
            QPushButton:hover { color: #1A73E8; }
            QPushButton:disabled { color: #AAB4C1; }
        """)
        self.history_menu = QMenu(self.history_more)
        self.history_menu.setStyleSheet("""
            QMenu { background: #FFFFFF; color: #33435A; border: 1px solid #DAE2ED;
                padding: 4px; font-size: 12px; }
            QMenu::item { padding: 7px 28px 7px 14px; }
            QMenu::item:selected { background: #EDF3FC; color: #1A73E8; }
            QMenu::separator { height: 1px; background: #E4EAF2; margin: 4px 6px; }
        """)
        self.history_menu.aboutToShow.connect(self._populate_history_menu)
        self.history_more.setMenu(self.history_menu)
        history_header.addWidget(self.history_more)
        history_layout.addLayout(history_header)

        self.history_row = QHBoxLayout()
        self.history_row.setContentsMargins(0, 0, 0, 0)
        self.history_row.setSpacing(6)
        history_layout.addLayout(self.history_row)
        history_layout.addStretch()
        self.history_widget.installEventFilter(self)
        main_layout.addWidget(self.history_widget)

        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        self.toggle_buttons = {}
        self._caffeinate = None
        self._rain_overlay = None
        self._rain_saved_awake = None
        self.all_buttons = {}  # 存储按钮引用用于搜索过滤
        self.sections = []  # 存储 (section_widget, [button_texts]) 用于搜索时隐藏空分类
        self._tool_callbacks = {}

        self.create_section("系统与桌面", [
            "网络诊断", "进程管理", "配置", "截图贴图", "取色器", "图片处理", "防黑屏", "文字雨"
        ], {
            "网络诊断": self.show_network,
            "进程管理": self.show_process_search,
            "配置": self.show_config,
            "截图贴图": self.show_screenshots,
            "取色器": self.show_screen_pick,
            "图片处理": self.show_image_tool
        }, {
            "防黑屏": self.set_awake,
            "文字雨": self.set_matrix_rain
        })

        self.create_section("编码与安全", ["编解码", "加解密", "哈希计算"], {
            "编解码": self.show_codec,
            "加解密": self.show_crypto,
            "哈希计算": self.show_hash
        })

        self.create_section("文本与数据", ["数据格式", "文本工具", "正则测试"], {
            "数据格式": self.show_data_format,
            "文本工具": self.show_text_tool,
            "正则测试": self.show_regex
        })

        self.create_section("时间与日程", ["日期时间", "Cron 表达式", "提醒事项"], {
            "日期时间": self.show_datetime,
            "Cron 表达式": self.show_cron,
            "提醒事项": self.show_reminder
        })

        self.create_section("数值计算", ["数字转换", "单位转换", "商余计算", "房贷计算器"], {
            "数字转换": self.show_number_convert,
            "单位转换": self.show_unit_convert,
            "商余计算": self.show_divmod,
            "房贷计算器": self.show_mortgage
        })

        self.create_section("开发辅助", ["开发速查", "chmod 权限", "颜色", "生成器"], {
            "开发速查": self.show_dev_reference,
            "chmod 权限": self.show_chmod,
            "颜色": self.show_color,
            "生成器": self.show_generator
        })

        self.usage_history = self._load_usage_history()
        self.search_history = self._load_search_history()
        self._refresh_history_display()

        self.content_layout = content_layout
        default_order = [s[1].text() for s in self.sections]
        saved = load_section_order()
        # 保存过的顺序优先；新增的大类追加到末尾，删掉的大类自动忽略
        self.section_order = ([t for t in saved if t in default_order] +
                              [t for t in default_order if t not in saved])
        self.apply_section_order()

        # 工具顺序/归属：保存过的优先（含跨大类），没保存过的新工具回落到默认大类
        self.default_tool_order = {s[1].text(): list(s[2]) for s in self.sections}
        saved_tools = load_tool_order()
        all_names = set(n for lst in self.default_tool_order.values() for n in lst)
        assigned = set()
        self.tool_order = {cat: [] for cat in self.section_order}
        for cat in self.section_order:
            for n in saved_tools.get(cat, []):
                if n in all_names and n not in assigned:
                    assigned.add(n)
                    self.tool_order[cat].append(n)
        for cat in self.section_order:
            for n in self.default_tool_order[cat]:
                if n not in assigned:
                    assigned.add(n)
                    self.tool_order[cat].append(n)
        self.apply_tool_order()

        self.empty_search_label = QLabel("没有找到匹配的工具\n试试功能名称、拼音，或清除搜索。")
        self.empty_search_label.setAlignment(Qt.AlignCenter)
        self.empty_search_label.setStyleSheet("color: #8290A5; font-size: 13px; padding: 40px 16px;")
        self.empty_search_label.hide()
        content_layout.addWidget(self.empty_search_label)
        content_layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }
            QScrollBar::handle:vertical { background: #CFD9E6; border-radius: 4px; min-height: 32px; }
            QScrollBar::handle:vertical:hover { background: #AEBED3; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
        """)
        scroll.viewport().setObjectName("launcherViewport")
        scroll.viewport().setStyleSheet("QWidget#launcherViewport { background: #F6F8FC; }")
        scroll.setWidget(content_area)
        content_area.setAutoFillBackground(False)
        self.tool_count_label.setText("%s 个工具" % len(self.all_buttons))
        # 顶部渐隐：仅当内容真正向上滚动时才淡出顶端，静止时标题完全可见
        self._top_fade = QGraphicsOpacityEffect(scroll.viewport())
        self._top_fade.setOpacity(1.0)
        scroll.viewport().setGraphicsEffect(self._top_fade)

        def update_top_fade(value):
            grad = QLinearGradient(0, 0, 0, 28)
            if value <= 0:
                grad.setColorAt(0.0, QColor(255, 255, 255, 255))
                grad.setColorAt(1.0, QColor(255, 255, 255, 255))
            else:
                grad.setColorAt(0.0, QColor(255, 255, 255, 0))
                grad.setColorAt(1.0, QColor(255, 255, 255, 255))
            self._top_fade.setOpacityMask(QBrush(grad))

        scroll.verticalScrollBar().valueChanged.connect(update_top_fade)
        update_top_fade(0)
        main_layout.addWidget(scroll, 1)

        bottom_bar = QFrame()
        bottom_bar.setObjectName("launcherFooter")
        bottom_bar.setStyleSheet("QFrame#launcherFooter { border-top: 1px solid #E1E7F0; }")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(0, 10, 0, 0)
        bottom_layout.setSpacing(12)

        self.cpu_label = QLabel("CPU: --")
        self.cpu_label.setFont(ui_font(10, 11))
        self.cpu_label.setStyleSheet("color: #8290A5;")
        bottom_layout.addWidget(self.cpu_label)

        self.mem_label = QLabel("内存: --")
        self.mem_label.setFont(ui_font(10, 11))
        self.mem_label.setStyleSheet("color: #8290A5;")
        bottom_layout.addWidget(self.mem_label)
        bottom_layout.addStretch()

        info_label = QLabel(f"IP: {self.ip}")
        info_label.setFont(ui_font(10, 11))
        info_label.setStyleSheet("color: #69788F;")
        info_label.setCursor(QCursor(Qt.PointingHandCursor))
        info_label.setToolTip("点击复制 IP\nMAC: %s\n网卡: %s" % (self.mac or "--", self.adapter))
        info_label.mousePressEvent = lambda e: self.copy_to_clipboard(self.ip)
        bottom_layout.addWidget(info_label)

        settings_btn = QPushButton("设置")
        settings_btn.setFont(ui_font(10, 12))
        settings_btn.setFixedSize(56, 30)
        settings_btn.setCursor(QCursor(Qt.PointingHandCursor))
        settings_btn.setToolTip("快捷键 / 开机自启 / 首页排序 / 缓存目录 / 源码仓库 / 检查更新")
        settings_btn.setStyleSheet("""
            QPushButton { color: #53657E; background: #FFFFFF; border: 1px solid #DAE2ED; border-radius: 6px; }
            QPushButton:hover { color: #1A73E8; background: #EDF4FF; border-color: #AAC8F4; }
        """)
        settings_btn.clicked.connect(self.show_settings)
        bottom_layout.addWidget(settings_btn)

        self._update_dialog = None
        self.check_thread = None
        QApplication.instance().aboutToQuit.connect(self._stop_update_check)
        self.update_btn = QPushButton("检查更新")
        self.update_btn.setFixedSize(90, 28)
        self.update_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.update_btn.setStyleSheet(_secondary_btn() + "QPushButton { font-size: 12px; }")
        self.update_btn.clicked.connect(self.check_for_updates)

        exit_btn = QPushButton("退出")
        exit_btn.setFont(ui_font(10, 12))
        exit_btn.setFixedSize(56, 30)
        exit_btn.setCursor(QCursor(Qt.PointingHandCursor))
        exit_btn.setStyleSheet("""
            QPushButton { color: #BA5555; background: transparent; border: 1px solid transparent; border-radius: 6px; }
            QPushButton:hover { color: #B3261E; background: #FFF0EF; border-color: #F2D2D0; }
        """)
        exit_btn.clicked.connect(QApplication.instance().quit)
        bottom_layout.addWidget(exit_btn)

        main_layout.addWidget(bottom_bar)

        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self.refresh_stats)
        self.stats_timer.start(3000)
        self.refresh_stats()

        self.hotkey = GlobalHotkey()
        self.hotkey.triggered.connect(self._on_global_hotkey)
        self.hotkey.start()
        QApplication.instance().aboutToQuit.connect(self.hotkey.stop)

    def _on_global_hotkey(self, action):
        if action == "rain":
            btn = self.toggle_buttons.get("文字雨")
            if btn is not None:
                btn.setChecked(not btn.isChecked())
        elif action == "picker":
            if self._screen_pick_overlay is not None:
                self._screen_pick_overlay.close()
            else:
                self._record_usage_and_call(self.show_screen_pick)
        elif action in ("capture", "capture_copy", "custom_capture", "paste_image", "toggle_pins"):
            self._add_to_history("截图贴图")
            tool = self._get_screenshot_tool()
            callbacks = {"capture": tool.capture, "capture_copy": tool.capture_copy,
                         "custom_capture": tool.custom_capture, "paste_image": tool.paste,
                         "toggle_pins": tool.toggle_pins}
            callbacks[action]()

    def _get_screenshot_tool(self):
        if self.screenshot_tool is None:
            self.screenshot_tool = ScreenshotTool(self)
        return self.screenshot_tool

    def show_screenshots(self):
        self._get_screenshot_tool().capture()

    def refresh_stats(self):
        cpu_pct, mem_pct, used_gb, total_gb = get_system_stats()
        if cpu_pct is not None:
            self.cpu_label.setText(f"CPU: {cpu_pct:.0f}%")
        if mem_pct is not None:
            self.mem_label.setText(f"内存: {used_gb:.1f}G / {total_gb:.0f}G ({mem_pct:.0f}%)")

    def create_section(self, title, buttons, callbacks=None, toggle_callbacks=None):
        toggle_callbacks = toggle_callbacks or {}
        section = QFrame()
        section.setObjectName("toolSection")
        section.setStyleSheet("QFrame#toolSection { background: #FFFFFF; border: 1px solid #E4EAF2; border-radius: 10px; }")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setFont(ui_font(12, 13, bold=True))
        title_label.setStyleSheet("color: #53657E;")
        layout.addWidget(title_label)

        from PyQt5.QtWidgets import QGridLayout
        btn_layout = QGridLayout()
        btn_layout.setSpacing(8)

        section_buttons = []  # 记录这个分类包含哪些按钮
        for i, btn_text in enumerate(buttons):
            btn = QPushButton(btn_text)
            btn.setFixedHeight(36)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            tip = TOOL_TIPS.get(btn_text)
            if tip:
                btn.setToolTip(tip)
            btn.setStyleSheet("""
                QPushButton {
                    color: #33435A;
                    background: #F8FAFD;
                    border: 1px solid #E8EDF5;
                    border-radius: 6px;
                    font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
                    font-size: __FS__px;
                    font-weight: normal;
                    padding: 0 8px;
                }
                QPushButton:hover {
                    background: #F0F6FF;
                    border-color: #1A73E8;
                    color: #1A73E8;
                }
                QPushButton:pressed {
                    background: #E3EDFC;
                }
            """.replace("__FS__", "13" if platform.system() == "Windows" else "12")
            )
            if btn_text in toggle_callbacks:
                btn.setCheckable(True)
                btn.setStyleSheet(btn.styleSheet() + """
                QPushButton:checked {
                    color: #FFFFFF;
                    background: #1A73E8;
                    border-color: #1A73E8;
                }
                QPushButton:checked:hover {
                    background: #1666CE;
                }
                """)
                btn.toggled.connect(lambda checked, t=btn_text: self._record_usage_and_call(toggle_callbacks[t], checked))
                btn.clicked.connect(self._remember_search)
                self.toggle_buttons[btn_text] = btn
            elif callbacks and btn_text in callbacks:
                self._tool_callbacks[btn_text] = callbacks[btn_text]
                btn.clicked.connect(lambda _, t=btn_text: self._activate_tool(t))
            self.all_buttons[btn_text] = btn  # 存储按钮引用用于搜索
            section_buttons.append(btn_text)  # 记录到分类按钮列表
            row = i // 6
            col = i % 6
            btn_layout.addWidget(btn, row, col)

        for col in range(6):
            btn_layout.setColumnStretch(col, 1)
        layout.addLayout(btn_layout)

        # 存储分类信息：(section_widget, title_label, [button_texts], btn_layout)
        self.sections.append((section, title_label, section_buttons, btn_layout))
        return section

    def set_awake(self, active):
        try:
            if platform.system() == "Darwin":
                if active:
                    if self._caffeinate is None or self._caffeinate.poll() is not None:
                        self._caffeinate = subprocess.Popen(
                            ["caffeinate", "-d", "-i", "-u"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                        )
                else:
                    if self._caffeinate is not None and self._caffeinate.poll() is None:
                        self._caffeinate.terminate()
                    self._caffeinate = None
            elif platform.system() == "Windows":
                import ctypes
                ES_CONTINUOUS = 0x80000000
                ES_SYSTEM_REQUIRED = 0x00000001
                ES_DISPLAY_REQUIRED = 0x00000002
                state = ES_CONTINUOUS
                if active:
                    state |= ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
                ctypes.windll.kernel32.SetThreadExecutionState(state)
        except Exception as e:
            if active:
                self.toggle_buttons["防黑屏"].setChecked(False)
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "防黑屏", f"无法启动防休眠: {e}")

    def set_matrix_rain(self, active):
        awake_btn = self.toggle_buttons.get("防黑屏")
        if active:
            if self._rain_overlay is None:
                self._rain_overlay = MatrixRainOverlay(
                    on_close=lambda: self.toggle_buttons["文字雨"].setChecked(False)
                )
            self._rain_overlay.start()
            # 文字雨自带防黑屏：记录开启前的状态，便于关闭时还原
            if awake_btn is not None and not awake_btn.isChecked():
                self._rain_saved_awake = False
                awake_btn.setChecked(True)
            else:
                self._rain_saved_awake = True
        else:
            if self._rain_overlay is not None:
                self._rain_overlay.stop()
            # 仅当防黑屏是文字雨带起来的（用户没主动开），才关回去
            if self._rain_saved_awake is False and awake_btn is not None:
                awake_btn.setChecked(False)
            self._rain_saved_awake = None

    def _tray_icon(self):
        """托盘图标：Mac 菜单栏用单色模板图（黑色+透明，自动适配深浅色栏）。"""
        base = app_icon()
        if platform.system() != "Darwin":
            return base
        src = base.pixmap(44, 44)
        if src.isNull():
            return base
        # 保留 alpha 形状、RGB 全设为黑，作为 macOS 模板图（SourceIn 一次性合成）
        img = QImage(src.size(), QImage.Format_ARGB32_Premultiplied)
        img.fill(QColor(0, 0, 0, 0))
        painter = QPainter(img)
        painter.drawPixmap(0, 0, src)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(img.rect(), QColor(0, 0, 0, 255))
        painter.end()
        pm = QPixmap.fromImage(img)
        pm.setDevicePixelRatio(2.0)  # 约 22pt 逻辑尺寸
        icon = QIcon(pm)
        icon.setIsMask(True)  # 通知 Qt 作为模板渲染
        return icon

    def init_tray(self):
        """系统托盘：点 X 隐藏到托盘而非退出，双击托盘图标恢复窗口。"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray_icon = QSystemTrayIcon(self._tray_icon(), self)
        self.tray_icon.setToolTip("系统工具箱")
        menu = QMenu()
        show_action = QAction("显示主窗口", self)
        show_action.triggered.connect(self.show_from_tray)
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(show_action)
        menu.addAction(quit_action)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def show_from_tray(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def on_tray_activated(self, reason):
        # 双击（Mac 上单击）恢复窗口
        if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger):
            if self.isVisible():
                self.raise_()
                self.activateWindow()
            else:
                self.show_from_tray()

    def quit_app(self):
        """真正退出：清理托盘并结束进程。"""
        self._force_quit = True
        if self.tray_icon:
            self.tray_icon.hide()
        self.close()
        QApplication.quit()

    def closeEvent(self, event):
        # 无论哪种退出路径，都做资源清理
        try:
            self.set_awake(False)
        except Exception:
            pass
        try:
            if self._rain_overlay is not None:
                self._rain_overlay.stop()
        except Exception:
            pass
        if self._screen_pick_overlay is not None:
            ov = self._screen_pick_overlay
            self._screen_pick_overlay = None
            ov.closed.disconnect(self._on_screen_pick_closed)
            ov.close()

        # 托盘可用且非强制退出：隐藏到托盘，保持进程存活
        if self.tray_icon and not getattr(self, "_force_quit", False):
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "系统工具箱", "已最小化到托盘，双击图标恢复。",
                QSystemTrayIcon.Information, 2000)
            return

        super().closeEvent(event)

    def show_process_search(self):
        if self.popup and self.popup.isVisible():
            self.popup.activateWindow()
            return
        self.popup = ProcessManagerWindow(self)
        self.popup.show()

    def show_data_format(self):
        if self.data_format_window is None:
            self.data_format_window = DataFormatWindow()
        self.data_format_window.show()
        self.data_format_window.activateWindow()

    def show_codec(self):
        if self.codec_window is None:
            self.codec_window = CodecWindow()
        self.codec_window.show()
        self.codec_window.activateWindow()

    def show_hash(self):
        if self.hash_window is None:
            self.hash_window = HashWindow()
        self.hash_window.show()
        self.hash_window.activateWindow()

    def show_crypto(self):
        if self.crypto_window is None:
            self.crypto_window = CryptoWindow()
        self.crypto_window.show()
        self.crypto_window.activateWindow()

    def show_regex(self):
        if self.regex_window is None:
            self.regex_window = RegexWindow()
        self.regex_window.show()
        self.regex_window.activateWindow()

    def show_text_tool(self):
        if self.text_tool_window is None:
            self.text_tool_window = TextToolWindow()
        self.text_tool_window.show()
        self.text_tool_window.activateWindow()

    def show_generator(self):
        if self.generator_window is None:
            self.generator_window = GeneratorWindow()
        self.generator_window.show()
        self.generator_window.activateWindow()

    def show_number_convert(self):
        if self.number_convert_window is None:
            self.number_convert_window = NumberConvertWindow()
        self.number_convert_window.show()
        self.number_convert_window.activateWindow()

    def show_divmod(self):
        if self.divmod_window is None:
            self.divmod_window = DivModWindow()
        self.divmod_window.show()
        self.divmod_window.activateWindow()

    def show_color(self):
        if self.color_window is None:
            self.color_window = ColorWindow()
        self.color_window.show()
        self.color_window.activateWindow()

    def show_screen_pick(self):
        if self._screen_pick_overlay is not None:
            self._screen_pick_overlay.close()
        self._screen_pick_prev_pid = _mac_frontmost_pid()
        self.hide()
        ov = ScreenPickOverlay()
        ov.setAttribute(Qt.WA_DeleteOnClose)
        ov.copied.connect(self._on_screen_copied)
        ov.closed.connect(self._on_screen_pick_closed)
        self._screen_pick_overlay = ov
        ov.start()

    def _on_screen_copied(self, color):
        # 复制即退出：静默回填已存在的颜色窗口，不创建/不显示/不激活（复制不弹窗）
        self._screen_pick_silent_exit = True
        if self.color_window is not None:
            hexval = color.name().upper()
            self.color_window.color_edit.setText(hexval)
            self.color_window.set_status(f"取色器 {hexval}，已复制到剪贴板", ok=True)

    def _on_screen_pick_closed(self, *_):
        self._screen_pick_overlay = None
        prev = self._screen_pick_prev_pid
        self._screen_pick_prev_pid = None
        silent = self._screen_pick_silent_exit
        self._screen_pick_silent_exit = False
        if not silent:
            self.show()
        if prev:
            _mac_reactivate(prev)

    def show_config(self):
        if self.config_window is None:
            self.config_window = ConfigWindow()
        self.config_window.show()
        self.config_window.activateWindow()

    def show_dev_reference(self):
        if self.dev_reference_window is None:
            self.dev_reference_window = DeveloperReferenceWindow()
        self.dev_reference_window.show()
        self.dev_reference_window.activateWindow()

    def show_mortgage(self):
        if self.mortgage_window is None:
            self.mortgage_window = MortgageWindow()
        self.mortgage_window.show()
        self.mortgage_window.activateWindow()

    def show_chmod(self):
        if self.chmod_window is None:
            self.chmod_window = ChmodWindow()
        self.chmod_window.show()
        self.chmod_window.activateWindow()

    def show_datetime(self):
        if self.datetime_window is None:
            self.datetime_window = DateTimeWindow()
        self.datetime_window.show()
        self.datetime_window.activateWindow()

    def show_reminder(self):
        if self.reminder_window is None:
            self.reminder_window = ReminderWindow(self.reminder_engine)
        self.reminder_window.refresh()
        self.reminder_window.show()
        self.reminder_window.activateWindow()

    def show_unit_convert(self):
        if self.unit_window is None:
            self.unit_window = UnitConvertWindow()
        self.unit_window.show()
        self.unit_window.activateWindow()


    def show_cron(self):
        if self.cron_window is None:
            self.cron_window = CronWindow()
        self.cron_window.show()
        self.cron_window.activateWindow()

    def show_image_tool(self):
        if self.image_window is None:
            self.image_window = ImageToolWindow()
        self.image_window.show()
        self.image_window.activateWindow()

    def show_network(self):
        if self.network_window is None:
            self.network_window = NetworkDiagnosticsWindow()
        self.network_window.show()
        self.network_window.activateWindow()

    def filter_tools(self):
        """根据搜索框内容过滤工具按钮，匹配工具名称、内部功能和拼音。"""
        keyword = self.search_input.text().strip().lower()
        if not keyword:
            # 无搜索词时显示所有按钮和分类
            for btn in self.all_buttons.values():
                btn.setVisible(True)
                btn._filter_match = True
            for section, title_label, _, _ in self.sections:
                section.setVisible(True)
            self.tool_count_label.setText("%s 个工具" % len(self.all_buttons))
            self.empty_search_label.hide()
            return
        # 模糊匹配：工具名称、提示内容或拼音包含关键词
        for btn_text, btn in self.all_buttons.items():
            tip = TOOL_TIPS.get(btn_text, "").lower()
            # 检查拼音映射
            pinyin_match = any(py.startswith(keyword) or keyword == py 
                             for py, tools in PINYIN_MAP.items() 
                             if btn_text in tools)
            alias_match = any(keyword in old.lower() for old, new in TOOL_RENAMES.items() if new == btn_text)
            match = keyword in btn_text.lower() or keyword in tip or pinyin_match or alias_match
            btn.setVisible(match)
            btn._filter_match = match
        
        # 隐藏没有匹配按钮的分类
        for section, title_label, btn_texts, btn_layout in self.sections:
            has_visible = any(self.all_buttons[text]._filter_match 
                            for text in btn_texts if text in self.all_buttons)
            section.setVisible(has_visible)
        count = sum(btn._filter_match for btn in self.all_buttons.values())
        self.tool_count_label.setText("找到 %s 个工具" % count)
        self.empty_search_label.setVisible(count == 0)

    def open_single_match(self):
        """搜索框按回车时，如果只有一个匹配项，直接打开该工具。"""
        keyword = self.search_input.text().strip().lower()
        if not keyword:
            return
        matches = []
        for btn_text, btn in self.all_buttons.items():
            if not getattr(btn, '_filter_match', False):
                continue
            matches.append(btn_text)
        if matches:
            self._remember_search()
        if len(matches) == 1:
            self.all_buttons[matches[0]].click()
            self.search_input.clear()

    def _activate_tool(self, name, from_search=True):
        if from_search:
            self._remember_search()
        self.search_input.clear()
        self._record_usage_and_call(self._tool_callbacks[name])

    def _record_usage_and_call(self, callback, *args):
        tool_name = next((name for name, cb in self._tool_callbacks.items() if cb == callback), None)
        if tool_name:
            self._add_to_history(tool_name)
        callback(*args)

    def _load_usage_history(self):
        """从文件加载使用历史。"""
        try:
            with open(TOOL_USAGE_HISTORY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    data = list(data)
                if isinstance(data, list):
                    names = []
                    for name in data:
                        if not isinstance(name, str):
                            continue
                        name = TOOL_RENAMES.get(name, name)
                        if name in self._tool_callbacks and name not in names:
                            names.append(name)
                    return names[:self.max_history]
        except (OSError, ValueError):
            pass
        return []

    def _load_search_history(self):
        try:
            with open(SEARCH_HISTORY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return []
        if not isinstance(data, list):
            return []
        terms, seen = [], set()
        for value in data:
            if not isinstance(value, str):
                continue
            term = value.strip()
            if 0 < len(term) <= 80 and term.casefold() not in seen:
                terms.append(term)
                seen.add(term.casefold())
        return terms[:8]

    def _history_items(self, mode):
        return self.usage_history if mode == "recent" else self.search_history

    def _save_launcher_history(self, mode):
        path = TOOL_USAGE_HISTORY_PATH if mode == "recent" else SEARCH_HISTORY_PATH
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._history_items(mode), f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def _remember_search(self):
        term = self.search_input.text().strip()
        if not term or len(term) > 80:
            return
        if not any(getattr(btn, "_filter_match", False) for btn in self.all_buttons.values()):
            return
        if self.search_history and self.search_history[0] == term:
            return
        self.search_history = ([term] + [s for s in self.search_history if s.casefold() != term.casefold()])[:8]
        self._save_launcher_history("search")
        if self.history_mode == "search":
            self._refresh_history_display()

    def _add_to_history(self, tool_name):
        if tool_name not in self._tool_callbacks:
            return
        self.usage_history = ([tool_name] + [name for name in self.usage_history if name != tool_name])[:self.max_history]
        self._save_launcher_history("recent")
        if self.history_mode == "recent":
            self._refresh_history_display()

    def _set_history_mode(self, mode):
        self.history_mode = mode
        for name, btn in self.history_tabs.items():
            btn.setChecked(name == mode)
        self._refresh_history_display()

    def _use_history_entry(self, mode, value):
        if mode == "recent":
            self._activate_tool(value, from_search=False)
        else:
            self.search_input.setText(value)
            self.search_input.setFocus()
            self.search_input.selectAll()

    def _refresh_history_display(self):
        while self.history_row.count():
            widget = self.history_row.takeAt(0).widget()
            if widget:
                widget.hide()
                widget.deleteLater()
        mode = self.history_mode
        items = self._history_items(mode)
        self.history_more.setText("全部 (%d)" % len(items) if items else "全部")
        self.history_more.setEnabled(bool(items))
        if not items:
            text = "打开工具后会出现在这里" if mode == "recent" else "确认搜索后保留记录，不记录输入过程"
            hint = QLabel(text)
            hint.setFixedHeight(28)
            hint.setFont(ui_font(10, 12))
            hint.setStyleSheet("color: #9AA7B8;")
            self.history_row.addWidget(hint)
        available = self.history_widget.contentsRect().width()
        for value in items[:5]:
            btn = QPushButton()
            btn.setFont(ui_font(10, 12))
            width = min(160, btn.fontMetrics().horizontalAdvance(value) + 24)
            if width > available and self.history_row.count():
                btn.deleteLater()
                break
            width = min(width, max(40, available))
            btn.setText(btn.fontMetrics().elidedText(value, Qt.ElideRight, width - 24).replace("&", "&&"))
            btn.setFixedSize(width, 28)
            btn.setProperty("historyValue", value)
            btn.setToolTip(value + "\n" + ("点击打开工具" if mode == "recent" else "点击重新搜索") + " · 右键移除")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton { background: #EDF3FC; border: 1px solid #DDE7F6;
                    border-radius: 14px; padding: 0 10px; color: #526A8C; }
                QPushButton:hover { background: #F0F5FF; border-color: #1A73E8; color: #1A73E8; }
            """)
            btn.clicked.connect(lambda _checked, m=mode, v=value: self._use_history_entry(m, v))
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, b=btn, m=mode, v=value: self._show_history_context(m, v, b.mapToGlobal(pos)))
            self.history_row.addWidget(btn)
            available -= width + self.history_row.spacing()
        self.history_row.addStretch()

    def _populate_history_menu(self):
        self.history_menu.clear()
        self.history_menu.setToolTipsVisible(True)
        mode = self.history_mode
        items = self._history_items(mode)
        title = "最近使用" if mode == "recent" else "搜索记录"
        self.history_menu.addAction(title + " · 最近优先").setEnabled(False)
        for value in items:
            label = self.history_more.fontMetrics().elidedText(value, Qt.ElideRight, 320).replace("&", "&&")
            action = self.history_menu.addAction(label)
            action.setToolTip(value)
            action.setData(value)
            action.triggered.connect(lambda _checked, m=mode, v=value: self._use_history_entry(m, v))
        self.history_menu.addSeparator()
        remove_menu = self.history_menu.addMenu("移除单条记录")
        for value in items:
            label = self.history_more.fontMetrics().elidedText(value, Qt.ElideRight, 320).replace("&", "&&")
            action = remove_menu.addAction(label)
            action.setToolTip(value)
            action.triggered.connect(lambda _checked, m=mode, v=value: self._remove_history_entry(m, v))
        self.history_menu.addAction("清空" + title).triggered.connect(lambda _checked: self._clear_history(mode))

    def _show_history_context(self, mode, value, position):
        menu = QMenu(self)
        menu.setStyleSheet(self.history_menu.styleSheet())
        menu.addAction("从记录中移除").triggered.connect(lambda _checked: self._remove_history_entry(mode, value))
        menu.exec_(position)
        menu.deleteLater()

    def _remove_history_entry(self, mode, value):
        items = self._history_items(mode)
        if value in items:
            items.remove(value)
            self._save_launcher_history(mode)
            self._refresh_history_display()

    def _clear_history(self, mode):
        self._history_items(mode).clear()
        self._save_launcher_history(mode)
        self._refresh_history_display()

    def eventFilter(self, obj, event):
        if obj is self.history_widget and event.type() == QEvent.Resize:
            self._refresh_history_display()
        return super().eventFilter(obj, event)

    def apply_section_order(self):
        """按 self.section_order 重排首页分组，并持久化。"""
        by_title = {s[1].text(): s[0] for s in self.sections}
        for i in reversed(range(self.content_layout.count())):
            if self.content_layout.itemAt(i).widget() is not None:
                self.content_layout.takeAt(i)
        for pos, title in enumerate(self.section_order):
            self.content_layout.insertWidget(pos, by_title[title])
        save_section_order(self.section_order)

    def apply_tool_order(self):
        """按 self.tool_order 重排/跨类移动首页按钮，并持久化。"""
        # 先全部摘下来，再按新归属装回去，避免按钮同时挂在两个网格上
        for section, title_label, texts, grid in self.sections:
            for n in list(texts):
                b = self.all_buttons.get(n)
                if b is not None:
                    grid.removeWidget(b)
        for section, title_label, texts, grid in self.sections:
            names = self.tool_order.get(title_label.text(), list(texts))
            texts[:] = names
            for i, n in enumerate(names):
                b = self.all_buttons.get(n)
                if b is not None:
                    grid.addWidget(b, i // 6, i % 6)
        save_tool_order(self.tool_order)

    def reset_section_order(self):
        self.section_order = [s[1].text() for s in self.sections]
        self.tool_order = {cat: list(names) for cat, names in self.default_tool_order.items()}
        self.apply_section_order()
        self.apply_tool_order()

    def show_section_order(self):
        if self.section_order_window is None:
            self.section_order_window = SectionOrderWindow(self)
        self.section_order_window.show()
        self.section_order_window.raise_()
        self.section_order_window.activateWindow()

    def show_settings(self):
        if self.settings_window is None:
            self.settings_window = SettingsWindow(self)
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def _open_cache_dir(self):
        """打开缓存目录。"""
        import subprocess
        cache_dir = os.path.join(os.path.expanduser("~"), ".personal_toolbox")
        os.makedirs(cache_dir, exist_ok=True)
        
        if sys.platform == "win32":
            os.startfile(cache_dir)
        elif sys.platform == "darwin":
            subprocess.call(["open", cache_dir])
        else:
            subprocess.call(["xdg-open", cache_dir])

    def copy_to_clipboard(self, text):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        QMessageBox.information(self, "已复制", f"已复制到剪贴板:\n{text}", QMessageBox.Ok)

    def check_for_updates(self):
        if self._update_dialog is not None and self._update_dialog.isVisible():
            self._update_dialog.raise_()
            self._update_dialog.activateWindow()
            return
        if self.check_thread is not None and self.check_thread.isRunning():
            return
        self._update_parent = QApplication.activeWindow() or self
        self.update_btn.setEnabled(False)
        self.update_btn.setText("检查中...")
        self.check_thread = CheckUpdateThread(self)
        self.check_thread.result.connect(self._on_check_update_result)
        self.check_thread.finished.connect(self._update_check_finished)
        self.check_thread.start()

    def _update_check_finished(self):
        thread = self.sender()
        if self.check_thread is thread:
            self.check_thread = None
        thread.deleteLater()

    def _stop_update_check(self):
        if self.check_thread is not None:
            self.check_thread.wait()

    def _on_check_update_result(self, success, data, error):
        self.update_btn.setEnabled(True)
        self.update_btn.setText("检查更新")
        parent = self._update_parent if self._update_parent.isVisible() else self
        if not success:
            box = QMessageBox(QMessageBox.Warning, "检查更新", error, QMessageBox.Ok, parent)
            box.setTextFormat(Qt.PlainText)
            box.exec_()
            return
        if not self._is_newer_version(APP_VERSION, data['version']):
            QMessageBox.information(parent, "检查更新", f"当前已是最新版本 v{APP_VERSION}", QMessageBox.Ok)
            return
        self._download_update(data, parent)

    def _is_newer_version(self, current, remote):
        return update_version_parts(remote) > update_version_parts(current)

    def _download_update(self, data, parent):
        try:
            self._update_dialog = AppUpdateDialog(data, parent)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(parent, "下载更新", str(exc), QMessageBox.Ok)
            return
        self._update_dialog.install_ready.connect(QApplication.instance().quit)
        self._update_dialog.show()


def update_version_parts(version):
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]{1,5}(?:\.[0-9]{1,5}){1,3}", version):
        raise ValueError("更新服务器返回了无效的版本号。")
    parts = tuple(int(part) for part in version.split('.'))
    return parts + (0,) * (4 - len(parts))


def validate_update_url(url):
    if not isinstance(url, str) or any(ord(char) < 33 for char in url):
        raise ValueError("更新下载地址无效。")
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password or parts.fragment:
        raise ValueError("更新仅接受不含账号信息的 HTTPS 下载地址。")


class UpdateRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_update_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def update_install_target(system):
    if system == "Windows":
        if getattr(sys, "frozen", False):
            return os.path.abspath(sys.executable)
        return os.path.join(os.environ['LOCALAPPDATA'], "PersonalToolbox", "Toolbox.exe")
    if system == "Darwin":
        return os.path.join(QStandardPaths.writableLocation(QStandardPaths.DownloadLocation), "Toolbox.app")
    raise ValueError("应用内更新仅支持 Windows 和 macOS。")


def extract_update_package(archive_path, directory, system, cancelled):
    with zipfile.ZipFile(archive_path) as archive:
        entries = archive.infolist()
        if len(entries) > 30000 or sum(entry.file_size for entry in entries) > 2 * 1024 ** 3:
            raise ValueError("更新包解压后的大小或文件数超出限制。")
        names = {}
        for entry in entries:
            name = entry.filename.rstrip('/')
            parts = name.split('/')
            mode = entry.external_attr >> 16
            if (entry.orig_filename != entry.filename or not name or '\\' in name
                    or ntpath.splitdrive(name)[0] or any(part in ('', '.', '..') for part in parts)
                    or any(ord(char) < 32 for char in name)
                    or stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK)):
                raise ValueError("更新包包含不安全的路径或文件类型。")
            if system == 'Windows' and (stat.S_ISLNK(mode) or any(
                    ':' in part or part.endswith(('.', ' ')) or re.fullmatch(
                        r'(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', part, re.I)
                    for part in parts)):
                raise ValueError("更新包包含不安全的 Windows 文件名。")
            key = name.casefold()
            if key in names:
                raise ValueError("更新包包含重复的文件路径。")
            names[key] = entry
            if entry.flag_bits & 1:
                raise ValueError("无法安装加密的更新包。")

        files = [entry for entry in entries if not entry.is_dir()
                 and not entry.filename.startswith('__MACOSX/')
                 and posixpath.basename(entry.filename) != '.DS_Store']
        if system == 'Windows':
            candidates = [entry for entry in files if posixpath.basename(entry.filename).casefold()
                          in ('toolbox.exe', 'toolbox-windows.exe')]
            if len(candidates) != 1 or len(files) != 1:
                raise ValueError("Windows 更新包应仅包含单文件 Toolbox.exe。")
            selected = [(candidates[0], 'Toolbox.exe')]
            payload = os.path.join(directory, 'Toolbox.exe')
        elif system == 'Darwin':
            candidates = [entry for entry in files
                          if entry.filename.endswith('Toolbox.app/Contents/Info.plist')]
            if len(candidates) != 1:
                raise ValueError("macOS 更新包中未找到唯一的 Toolbox.app。")
            prefix = candidates[0].filename[:-len('Contents/Info.plist')]
            selected = [(entry, 'Toolbox.app/' + entry.filename[len(prefix):]) for entry in entries
                        if entry.filename.startswith(prefix) and entry.filename != prefix]
            payload = os.path.join(directory, 'Toolbox.app')
        else:
            raise ValueError("不支持的更新平台。")

        links, directories = [], []
        link_names = {relative.rstrip('/') for entry, relative in selected
                      if stat.S_ISLNK(entry.external_attr >> 16)}
        for entry, relative in selected:
            if cancelled.is_set():
                raise InterruptedError("已取消更新。")
            components = relative.rstrip('/').split('/')
            if any('/'.join(components[:index]) in link_names for index in range(1, len(components))):
                raise ValueError("更新包不能通过符号链接写入文件。")
            path = os.path.join(directory, *components)
            mode = (entry.external_attr >> 16) & 0o777
            if entry.is_dir():
                os.makedirs(path, exist_ok=True)
                directories.append((path, mode))
                continue
            os.makedirs(os.path.dirname(path), exist_ok=True)
            if stat.S_ISLNK(entry.external_attr >> 16):
                if entry.file_size > 4096:
                    raise ValueError("更新包的符号链接过长。")
                target = archive.read(entry).decode('utf-8')
                resolved = posixpath.normpath(posixpath.join(posixpath.dirname(relative), target))
                if (not target or '\\' in target or ntpath.splitdrive(target)[0]
                        or target.startswith('/') or resolved == '..' or resolved.startswith('../')
                        or not resolved.startswith('Toolbox.app/')):
                    raise ValueError("更新包的符号链接指向应用目录之外。")
                links.append((path, target))
                continue
            with archive.open(entry) as source, open(path, 'xb') as output:
                while True:
                    if cancelled.is_set():
                        raise InterruptedError("已取消更新。")
                    chunk = source.read(256 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
            if system == 'Darwin' and mode:
                os.chmod(path, mode)
        for path, target in links:
            os.symlink(target, path)
        for path, _ in links:
            resolved = os.path.realpath(path)
            if (os.path.commonpath((os.path.realpath(payload), resolved)) != os.path.realpath(payload)
                    or not os.path.exists(path)):
                raise ValueError("更新包包含越界或失效的符号链接。")
        if system == 'Darwin':
            for path, mode in reversed(directories):
                if mode:
                    os.chmod(path, mode)
            with open(os.path.join(payload, 'Contents', 'Info.plist'), 'rb') as file:
                info = plistlib.load(file)
            if not isinstance(info, dict):
                raise ValueError("更新包的应用信息格式无效。")
            executable = info.get('CFBundleExecutable', '')
            if (info.get('CFBundleIdentifier') != 'com.jimmy.personal_tool'
                    or not isinstance(executable, str) or not executable
                    or executable in ('.', '..') or ntpath.splitdrive(executable)[0]
                    or '/' in executable or '\\' in executable):
                raise ValueError("更新包不是系统工具箱应用。")
            executable_path = os.path.join(payload, 'Contents', 'MacOS', executable)
            with open(executable_path, 'rb') as file:
                magic = file.read(4)
            if magic not in (b'\xfe\xed\xfa\xce', b'\xce\xfa\xed\xfe', b'\xfe\xed\xfa\xcf',
                             b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe', b'\xbe\xba\xfe\xca',
                             b'\xca\xfe\xba\xbf', b'\xbf\xba\xfe\xca'):
                raise ValueError("更新包中缺少有效的 macOS 可执行程序。")
            os.chmod(executable_path, os.stat(executable_path).st_mode | stat.S_IXUSR)
        else:
            with open(payload, 'rb') as file:
                header = file.read(64)
                if len(header) < 64 or header[:2] != b'MZ':
                    raise ValueError("更新包不是有效的 Windows 应用程序。")
                offset = int.from_bytes(header[60:64], 'little')
                if offset < 64 or offset > os.path.getsize(payload) - 24:
                    raise ValueError("更新包的 Windows 可执行文件头损坏。")
                file.seek(offset)
                if file.read(4) != b'PE\x00\x00':
                    raise ValueError("更新包的 Windows 可执行文件头损坏。")
        return payload


class UpdateDownloadWorker(QThread):
    progress = pyqtSignal(int, int)
    unpacking = pyqtSignal()
    ready = pyqtSignal(str, str)
    failed = pyqtSignal(str)

    def __init__(self, url, system, parent):
        super().__init__(parent)
        self.url = url
        self.system = system
        self.cancelled = threading.Event()
        self.directory = None

    def cancel(self):
        self.cancelled.set()

    def run(self):
        directory, delivered = None, False
        try:
            validate_update_url(self.url)
            directory = tempfile.mkdtemp(prefix='toolbox_update_')
            self.directory = directory
            archive_path = os.path.join(directory, 'update.zip')
            request = urllib.request.Request(self.url, headers={
                'User-Agent': 'Mozilla/5.0', 'Accept': 'application/zip, application/octet-stream'})
            opener = urllib.request.build_opener(UpdateRedirectHandler())
            with opener.open(request, timeout=15) as response, open(archive_path, 'wb') as output:
                validate_update_url(response.geturl())
                total = int(response.headers.get('Content-Length', '0'))
                limit = 1024 ** 3
                if total < 0 or total > limit:
                    raise ValueError("更新包大小超出 1 GB 限制。")
                received, last_progress = 0, 0
                self.progress.emit(0, total)
                while True:
                    if self.cancelled.is_set():
                        raise InterruptedError("已取消更新。")
                    chunk = response.read(256 * 1024)
                    if not chunk:
                        break
                    received += len(chunk)
                    if received > limit:
                        raise ValueError("更新包大小超出 1 GB 限制。")
                    output.write(chunk)
                    if time.monotonic() - last_progress >= 0.1:
                        self.progress.emit(received, total)
                        last_progress = time.monotonic()
                if total and received != total:
                    raise ValueError("更新包下载不完整，请重试。")
                self.progress.emit(received, total)
            if self.cancelled.is_set():
                raise InterruptedError("已取消更新。")
            self.unpacking.emit()
            payload = extract_update_package(archive_path, directory, self.system, self.cancelled)
            os.remove(archive_path)
            if self.cancelled.is_set():
                raise InterruptedError("已取消更新。")
            delivered = True
            self.ready.emit(directory, payload)
        except InterruptedError:
            pass
        except Exception as exc:
            if not self.cancelled.is_set():
                self.failed.emit("下载或解压失败：" + str(exc)[:400])
        finally:
            if directory is not None and not delivered:
                shutil.rmtree(directory, ignore_errors=True)


def start_update_installer(directory, payload, target, shortcut, system):
    token = uuid.uuid4().hex
    parent = os.path.dirname(target)
    incoming = os.path.join(parent, '.toolbox-update-' + token + ('.exe' if system == 'Windows' else '.app'))
    backup = os.path.join(parent, '.toolbox-backup-' + token + ('.exe' if system == 'Windows' else '.app'))
    ready = os.path.join(directory, 'installer.ready')
    error = os.path.join(directory, 'installer.error')
    old_command = autostart_programs()
    env = os.environ.copy()
    env['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    if system == 'Windows':
        plan = {'source': payload, 'target': target, 'incoming': incoming, 'backup': backup,
                'shortcut': shortcut, 'process_id': os.getpid(), 'ready': ready, 'error': error,
                'directory': directory, 'old_program': old_command[0],
                'old_arguments': subprocess.list2cmdline(old_command[1:])}
        plan_path = os.path.join(directory, 'install.json')
        with open(plan_path, 'w', encoding='utf-8') as file:
            json.dump(plan, file, ensure_ascii=False)
        env['PERSONAL_TOOLBOX_UPDATE_PLAN'] = plan_path
        script = r'''
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$plan = Get-Content -LiteralPath $env:PERSONAL_TOOLBOX_UPDATE_PLAN -Encoding UTF8 -Raw | ConvertFrom-Json
$prepared = $false
$replaced = $false
$successful = $false
$started = $null
try {
    if ([IO.Directory]::Exists($plan.target)) { throw '安装位置被同名文件夹占用。' }
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($plan.target)) | Out-Null
    [IO.File]::Copy($plan.source, $plan.incoming, $false)
    if ((Get-FileHash -LiteralPath $plan.source -Algorithm SHA256).Hash -ne
        (Get-FileHash -LiteralPath $plan.incoming -Algorithm SHA256).Hash) {
        throw '安装文件复制校验失败。'
    }
    $previousProcess = $null
    try { $previousProcess = [Diagnostics.Process]::GetProcessById([int]$plan.process_id) } catch [ArgumentException] {}
    [IO.File]::WriteAllText($plan.ready, 'ready')
    $prepared = $true
    if ($null -ne $previousProcess -and -not $previousProcess.WaitForExit(60000)) {
        throw '旧版本未能退出，更新已停止。'
    }
    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    while ($true) {
        try {
            if ([IO.File]::Exists($plan.target)) {
                [IO.File]::Replace($plan.incoming, $plan.target, $plan.backup)
            } else {
                [IO.File]::Move($plan.incoming, $plan.target)
            }
            $replaced = $true
            break
        } catch [IO.IOException] {
            $code = $_.Exception.GetBaseException().HResult -band 65535
            if ($code -notin @(32, 33) -or [DateTime]::UtcNow -ge $deadline) { throw }
            Start-Sleep -Milliseconds 200
        }
    }
    $started = Start-Process -FilePath $plan.target -WorkingDirectory ([IO.Path]::GetDirectoryName($plan.target)) -PassThru
    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    $name = [IO.Path]::GetFileNameWithoutExtension($plan.target)
    while ($true) {
        $windows = @(Get-Process -Name $name -ErrorAction SilentlyContinue | Where-Object {
            $_.Path -eq $plan.target -and $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like '系统工具箱*'
        })
        if (@($windows | Where-Object { $_.MainWindowTitle -like '*启动失败*' }).Count -gt 0) {
            throw '新版本报告启动失败。'
        }
        if ($windows.Count -gt 0) { break }
        if ($started.HasExited) { throw '新版本未能启动。' }
        if ([DateTime]::UtcNow -ge $deadline) { throw '新版本未能显示主窗口。' }
        Start-Sleep -Milliseconds 200
    }
    $shortcutWarning = ''
    if ($plan.shortcut) {
        try {
            $shell = New-Object -ComObject WScript.Shell
            $link = $shell.CreateShortcut($plan.shortcut)
            $link.TargetPath = $plan.target
            $link.Arguments = ''
            $link.WindowStyle = 1
            $link.WorkingDirectory = [IO.Path]::GetDirectoryName($plan.target)
            $link.IconLocation = $plan.target + ',0'
            $link.Description = '系统工具箱'
            $link.Save()
        } catch { $shortcutWarning = '新版已安装，但桌面快捷方式创建失败。应用位置：' + $plan.target }
    }
    $successful = $true
    try { if ([IO.File]::Exists($plan.backup)) { [IO.File]::Delete($plan.backup) } } catch {}
    if ($shortcutWarning) {
        Add-Type -AssemblyName System.Windows.Forms
        [Windows.Forms.MessageBox]::Show($shortcutWarning, '工具箱更新') | Out-Null
    }
} catch {
    $message = $_.Exception.Message
    if ($replaced) {
        try {
            if ($null -ne $started -and -not $started.HasExited) {
                $killer = Join-Path $env:SystemRoot 'System32\taskkill.exe'
                & $killer /PID $started.Id /T /F | Out-Null
                $started.WaitForExit(5000) | Out-Null
            }
            $deadline = [DateTime]::UtcNow.AddSeconds(30)
            while ($true) {
                try {
                    if ([IO.File]::Exists($plan.backup)) {
                        [IO.File]::Replace($plan.backup, $plan.target, [NullString]::Value)
                    } elseif ([IO.File]::Exists($plan.target)) {
                        [IO.File]::Delete($plan.target)
                    }
                    break
                } catch [IO.IOException] {
                    $code = $_.Exception.GetBaseException().HResult -band 65535
                    if ($code -notin @(32, 33) -or [DateTime]::UtcNow -ge $deadline) { throw }
                    Start-Sleep -Milliseconds 200
                }
            }
        } catch { $message += "`n恢复旧版本失败：" + $_.Exception.Message + "`n请保留备份：" + $plan.backup }
    }
    [IO.File]::WriteAllText($plan.error, $message, [Text.UTF8Encoding]::new($false))
    if ($prepared) {
        Add-Type -AssemblyName System.Windows.Forms
        [Windows.Forms.MessageBox]::Show('更新失败：' + $message, '工具箱更新失败') | Out-Null
        if ($null -ne $previousProcess -and $previousProcess.HasExited) {
            try {
                if ($plan.old_arguments) {
                    Start-Process -FilePath $plan.old_program -ArgumentList $plan.old_arguments | Out-Null
                } else { Start-Process -FilePath $plan.old_program | Out-Null }
            } catch {}
        }
    }
} finally {
    if ([IO.File]::Exists($plan.incoming)) { [IO.File]::Delete($plan.incoming) }
    if ($successful) { Remove-Item -LiteralPath $plan.directory -Recurse -Force }
}
'''
        encoded = base64.b64encode(script.encode('utf-16-le')).decode('ascii')
        command = [os.path.join(os.environ['SystemRoot'], 'System32', 'WindowsPowerShell',
                               'v1.0', 'powershell.exe'), '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded]
        # Windows PowerShell 在 DETACHED_PROCESS 下可能直接退出而不执行命令。
        kwargs = {'creationflags': subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP}
    else:
        values = {'source': payload, 'target': target, 'incoming': incoming, 'backup': backup,
                  'ready': ready, 'error': error, 'directory': directory}
        assignments = '\n'.join(key + '=' + shlex.quote(value) for key, value in values.items())
        script = assignments + '\nold_pid=' + str(os.getpid()) + '\n' + r'''
prepared=0
replaced=0
had_old=0
fail() {
    message="$1"
    if [ "$replaced" = 1 ]; then
        if [ "$had_old" = 1 ]; then
            /bin/rm -rf "$target"
            /bin/mv "$backup" "$target" || message="$message 旧版备份仍在：$backup"
        else
            /bin/rm -rf "$target"
        fi
    fi
    /bin/rm -rf "$incoming"
    printf '%s' "$message" > "$error"
    if [ "$prepared" = 1 ]; then
        /usr/bin/osascript -e 'on run argv
            display alert "工具箱更新失败" message (item 1 of argv)
        end run' "$message"
''' + '        if ! /bin/kill -0 "$old_pid" 2>/dev/null; then\n            ' + ' '.join(shlex.quote(arg) for arg in old_command) + r'''
        fi
    fi
    exit 1
}
/bin/mkdir -p "$(/usr/bin/dirname "$target")" || fail '无法创建安装目录。'
/usr/bin/ditto "$source" "$incoming" || fail '无法复制新版应用，请检查安装目录权限。'
printf '%s' ready > "$ready" || fail '无法通知应用准备完成。'
prepared=1
count=0
while /bin/kill -0 "$old_pid" 2>/dev/null; do
    count=$((count + 1))
    [ "$count" -le 300 ] || fail '旧版本未能退出，更新已停止。'
    /bin/sleep 0.2
done
if [ -e "$target" ]; then
    /bin/mv "$target" "$backup" || fail '无法备份旧版本。'
    had_old=1
fi
replaced=1
/bin/mv "$incoming" "$target" || fail '无法安装新版本。'
/usr/bin/open -n "$target" || fail '新版本未能启动。'
/bin/rm -rf "$backup" "$directory"
'''
        script_path = os.path.join(directory, 'install.sh')
        with open(script_path, 'w', encoding='utf-8', newline='\n') as file:
            file.write(script)
        command, kwargs = ['/bin/sh', script_path], {'start_new_session': True}
    if system == 'Windows' and getattr(sys, 'frozen', False):
        ctypes.windll.kernel32.SetDllDirectoryW(None)
    try:
        process = subprocess.Popen(command, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)
    finally:
        if system == 'Windows' and getattr(sys, 'frozen', False):
            ctypes.windll.kernel32.SetDllDirectoryW(sys._MEIPASS)
    return process, ready, error


class AppUpdateDialog(QDialog):
    install_ready = pyqtSignal()

    def __init__(self, data, parent):
        super().__init__(parent)
        self.system = platform.system()
        self.target = update_install_target(self.system)
        self.url = data.get('win_url' if self.system == 'Windows' else 'mac_url', '')
        validate_update_url(self.url)
        self._phase = 'idle'
        self._worker = None
        self._directory = None
        self._helper = None
        self.setWindowTitle('应用内更新')
        self.setWindowModality(Qt.ApplicationModal)
        self.resize(590, 475)
        self.setStyleSheet('QDialog { background: #F6F8FC; } QLabel { color: #344054; }')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)
        title = QLabel('发现新版本 v' + data['version'])
        title.setFont(ui_font(18, 22, True))
        title.setTextFormat(Qt.PlainText)
        layout.addWidget(title)
        layout.addWidget(QLabel('当前版本 v' + APP_VERSION + ' · 在应用内下载、解压并安装'))
        changelog = QPlainTextEdit()
        changelog.setReadOnly(True)
        changelog.setPlainText(data.get('changelog') or '此版本未提供更新说明。')
        changelog.setMaximumHeight(140)
        changelog.setStyleSheet('QPlainTextEdit { background: white; border: 1px solid #E1E7EF; border-radius: 8px; padding: 10px; }')
        layout.addWidget(changelog)
        layout.addWidget(QLabel('安装位置（下次更新覆盖同一位置）'))
        location_row = QHBoxLayout()
        self.location = QLineEdit(self.target)
        self.location.setReadOnly(True)
        self.location.setToolTip(self.target)
        location_row.addWidget(self.location, 1)
        self.choose_btn = QPushButton('更改位置')
        self.choose_btn.setStyleSheet(_secondary_btn())
        self.choose_btn.clicked.connect(self._choose_location)
        location_row.addWidget(self.choose_btn)
        layout.addLayout(location_row)
        self.shortcut = QCheckBox('创建 / 更新桌面快捷方式')
        self.shortcut.setChecked(True)
        self.shortcut.setVisible(self.system == 'Windows')
        layout.addWidget(self.shortcut)
        note = ('下载完成后自动解压，退出旧版并启动新版；安装失败时保留或恢复旧版本。'
                if getattr(sys, 'frozen', False) else
                '当前为源码运行：发布包可能不含本地未发布功能，Python 和源码不会被覆盖；完成后退出源码运行并启动安装版。')
        if self.system == 'Darwin':
            note += '\n安装的是完整 Toolbox.app，无需手动解压；已有同名工具箱会被替换。'
        hint = QLabel(note)
        hint.setWordWrap(True)
        hint.setStyleSheet('color: #667085; font-size: 12px;')
        layout.addWidget(hint)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        self.progress_bar.setStyleSheet('QProgressBar { border: 1px solid #E1E7EF; border-radius: 5px; background: white; text-align: center; height: 18px; } QProgressBar::chunk { background: #6688D9; border-radius: 4px; }')
        layout.addWidget(self.progress_bar)
        self.status = QLabel('下载过程中可取消，现有应用与个人设置不会受到影响。')
        self.status.setTextFormat(Qt.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        layout.addStretch()
        buttons = QHBoxLayout()
        buttons.addStretch()
        self.cancel_btn = QPushButton('暂不更新')
        self.cancel_btn.setStyleSheet(_secondary_btn())
        self.cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.cancel_btn)
        self.start_btn = QPushButton('下载并更新')
        self.start_btn.setStyleSheet(_primary_btn())
        self.start_btn.clicked.connect(self._start)
        buttons.addWidget(self.start_btn)
        layout.addLayout(buttons)
        self._installer_timer = QTimer(self)
        self._installer_timer.setInterval(80)
        self._installer_timer.timeout.connect(self._poll_installer)
        QApplication.instance().aboutToQuit.connect(self.stop)

    def _choose_location(self):
        directory = QFileDialog.getExistingDirectory(self, '选择应用安装目录', os.path.dirname(self.target))
        if directory:
            self.target = os.path.join(directory, 'Toolbox.exe' if self.system == 'Windows' else 'Toolbox.app')
            self.location.setText(self.target)
            self.location.setToolTip(self.target)

    def _start(self):
        if self._worker is not None or self._phase != 'idle':
            return
        try:
            if self.system == 'Windows':
                if os.path.isdir(self.target):
                    raise ValueError('安装位置被同名文件夹占用，请更改位置。')
                if (not getattr(sys, 'frozen', False) and os.path.normcase(os.path.realpath(self.target))
                        == os.path.normcase(os.path.realpath(sys.executable))):
                    raise ValueError('不能覆盖正在使用的 Python 解释器，请更改位置。')
            elif os.path.lexists(self.target):
                with open(os.path.join(self.target, 'Contents', 'Info.plist'), 'rb') as file:
                    info = plistlib.load(file)
                if not isinstance(info, dict) or info.get('CFBundleIdentifier') != 'com.jimmy.personal_tool':
                    raise ValueError('安装位置已有同名的其他应用，请更改位置。')
        except (OSError, ValueError, plistlib.InvalidFileException) as exc:
            self.status.setText('无法安装：' + str(exc))
            return
        self._phase = 'downloading'
        self.start_btn.setText('下载中…')
        self.start_btn.setEnabled(False)
        self.choose_btn.setEnabled(False)
        self.shortcut.setEnabled(False)
        self.cancel_btn.setText('取消下载')
        self.status.setText('正在连接下载服务器…')
        self.progress_bar.show()
        self.progress_bar.setRange(0, 0)
        self._worker = UpdateDownloadWorker(self.url, self.system, self)
        self._worker.progress.connect(self._download_progress)
        self._worker.unpacking.connect(self._unpacking)
        self._worker.ready.connect(self._download_ready)
        self._worker.failed.connect(self._failed)
        self._worker.finished.connect(self._worker_finished)
        self._worker.start()

    def _download_progress(self, received, total):
        if self._phase != 'downloading':
            return
        self.progress_bar.setRange(0, 100 if total else 0)
        if total:
            self.progress_bar.setValue(received * 100 // total)
        self.status.setText('正在下载：%.1f MB%s' % (received / 1024 ** 2,
                            ' / %.1f MB' % (total / 1024 ** 2) if total else ''))

    def _unpacking(self):
        if self._phase == 'downloading':
            self.progress_bar.setRange(0, 0)
            self.status.setText('正在校验并解压更新包…')

    def _download_ready(self, directory, payload):
        if self._phase == 'cancelling':
            shutil.rmtree(directory, ignore_errors=True)
            return
        self._directory = directory
        self._phase = 'installing'
        self.start_btn.setText('安装中…')
        self.cancel_btn.setEnabled(False)
        self.status.setText('已解压，正在准备替换…完成后自动重启。')
        shortcut = ''
        if self.system == 'Windows' and self.shortcut.isChecked():
            shortcut = os.path.join(QStandardPaths.writableLocation(QStandardPaths.DesktopLocation), '系统工具箱.lnk')
        try:
            self._helper, self._ready_file, self._error_file = start_update_installer(
                directory, payload, self.target, shortcut, self.system)
            self._installer_timer.start()
        except OSError as exc:
            self._failed('无法启动更新程序：' + str(exc))
            self._discard_download()

    def _poll_installer(self):
        if os.path.isfile(self._error_file):
            if self._helper.poll() is None:
                return
            with open(self._error_file, 'r', encoding='utf-8') as file:
                message = file.read(1000)
            self._installer_timer.stop()
            self._failed('安装失败，旧版本未被修改：' + message)
            self._discard_download()
        elif os.path.isfile(self._ready_file):
            self._installer_timer.stop()
            self.status.setText('准备完成，正在退出旧版并启动新版…')
            self.install_ready.emit()
        elif self._helper.poll() is not None:
            self._installer_timer.stop()
            self._failed('更新程序未能启动，旧版本未被修改。请检查系统权限后重试。')
            self._discard_download()

    def _discard_download(self):
        if self._directory is not None:
            shutil.rmtree(self._directory, ignore_errors=True)
            self._directory = None

    def _failed(self, message):
        self._phase = 'idle'
        self.status.setText(message)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setText('关闭')
        self.start_btn.setText('重试更新')
        self.start_btn.setEnabled(self._worker is None)
        self.choose_btn.setEnabled(True)
        self.shortcut.setEnabled(True)

    def _worker_finished(self):
        worker, self._worker = self._worker, None
        worker.deleteLater()
        if self._phase == 'cancelling':
            self._phase = 'idle'
            super().reject()
        elif self._phase == 'idle':
            self.start_btn.setEnabled(True)

    def reject(self):
        if self._phase == 'installing':
            return
        if self._worker is not None:
            self._phase = 'cancelling'
            self._worker.cancel()
            self.cancel_btn.setEnabled(False)
            self.status.setText('正在取消并清理临时文件…')
            return
        super().reject()

    def closeEvent(self, event):
        if self._phase == 'installing' or self._worker is not None:
            event.ignore()
            self.reject()
            return
        super().closeEvent(event)

    def stop(self):
        self._installer_timer.stop()
        if self._worker is not None:
            self._worker.cancel()
            self._worker.wait()
        if self._phase != 'installing':
            self._discard_download()
            if self._worker is not None and self._worker.directory is not None:
                shutil.rmtree(self._worker.directory, ignore_errors=True)


class CheckUpdateThread(QThread):
    """后台检查更新线程"""
    result = pyqtSignal(bool, dict, str)
    
    def run(self):
        try:
            validate_update_url(UPDATE_CHECK_URL)
            req = urllib.request.Request(UPDATE_CHECK_URL, headers={'User-Agent': f'Toolbox/{APP_VERSION}'})
            opener = urllib.request.build_opener(UpdateRedirectHandler())
            with opener.open(req, timeout=10) as response:
                validate_update_url(response.geturl())
                content = response.read(1024 * 1024 + 1)
                if len(content) > 1024 * 1024:
                    raise ValueError('更新信息超出大小限制。')
                envelope = json.loads(content.decode('utf-8'))
                if (not isinstance(envelope, dict) or envelope.get('encoding') != 'base64'
                        or not isinstance(envelope.get('content'), str)):
                    raise ValueError('更新服务器返回的文件信息无效。')
                data = json.loads(base64.b64decode(envelope['content'], validate=True).decode('utf-8'))
            if not isinstance(data, dict):
                raise ValueError('更新服务器返回的内容不是版本信息。')
            update_version_parts(data.get('version'))
            if not isinstance(data.get('changelog', ''), str):
                raise ValueError('更新说明格式无效。')
            self.result.emit(True, data, "")
        except urllib.error.URLError as e:
            print(f"[Update] URLError: {e}")
            self.result.emit(False, {}, f"无法连接到更新服务器：\n{e}")
        except Exception as e:
            import traceback
            print(f"[Update] Error: {type(e).__name__}: {e}")
            traceback.print_exc()
            self.result.emit(False, {}, f"检查更新时出错：\n{e}")


def startup_log_path():
    """启动日志：统一保存到用户缓存目录。"""
    folder = os.path.join(os.path.expanduser("~"), ".personal_toolbox")
    path = os.path.join(folder, "startup.log")
    try:
        os.makedirs(folder, exist_ok=True)
        with open(path, "a", encoding="utf-8"):
            pass
        return path
    except OSError:
        return None


def write_startup_log(text, reset=False):
    path = startup_log_path()
    if not path:
        return
    try:
        with open(path, "w" if reset else "a", encoding="utf-8") as f:
            f.write(text.rstrip() + "\n")
    except OSError:
        pass


def fatal_dialog(text):
    """启动失败时弹出看得见的提示；Qt 建不起来就用 Win32 弹窗兜底。"""
    try:
        # QMessageBox 之前必须有 QApplication，否则 Qt 直接 abort()：那是 C++ 层的崩溃，
        # Python 的 except 抓不到，只会留下一份崩溃报告。引用必须握住，临时对象一析构就又没了。
        _app_keepalive = QApplication.instance() or QApplication(sys.argv[:1])
        QMessageBox.critical(None, "系统工具箱启动失败", text)
        return
    except Exception:
        pass
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, text, "系统工具箱启动失败", 0x10)
    except Exception:
        print(text, file=sys.stderr)


if __name__ == "__main__":
    write_startup_log(
        "[%s] 启动 pid=%d frozen=%s exe=%s cwd=%s"
        % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), os.getpid(),
           getattr(sys, "frozen", False), sys.executable, os.getcwd()),
        reset=True)
    # Qt 初始化失败时是在 C++ 层直接 abort，Python 的 try 捕不到；
    # faulthandler 能把这类原生崩溃的栈写进同一个日志。
    crash_file = None
    log_path = startup_log_path()
    if log_path:
        try:
            crash_file = open(log_path, "a", encoding="utf-8")
            faulthandler.enable(file=crash_file, all_threads=True)
        except OSError:
            crash_file = None
    # 防止多开：用 QLockFile 锁定用户目录下的锁文件，进程退出自动释放。
    lock_dir = os.path.join(os.path.expanduser("~"), ".personal_toolbox")
    os.makedirs(lock_dir, exist_ok=True)
    lock_file = QLockFile(os.path.join(lock_dir, "app.lock"))
    if not lock_file.tryLock(0):
        write_startup_log("检测到已有实例运行，退出")
        fatal_dialog("应用已在运行中，请勿重复打开。")
        sys.exit(1)
    try:
        app = QApplication(sys.argv)
        app.setWindowIcon(app_icon())
        # 下拉框整框可点（挂在 app 上，覆盖之后新建的所有 QComboBox）
        combo_click_filter = _ComboClickFilter(app)
        app.installEventFilter(combo_click_filter)
        # 有托盘时隐藏主窗口不应退出程序（由托盘"退出"显式结束）
        app.setQuitOnLastWindowClosed(not QSystemTrayIcon.isSystemTrayAvailable())
        window = ToolboxWindow()
        window.show()
        write_startup_log("界面已显示")
        exit_code = app.exec_()
    except Exception:
        detail = traceback.format_exc()
        write_startup_log("启动失败：\n" + detail)
        fatal_dialog("启动失败，详细信息已写入同目录的 startup.log：\n\n" + detail[-2000:])
        raise
    sys.exit(exit_code)
