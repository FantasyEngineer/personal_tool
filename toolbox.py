import sys
import os
import platform
import subprocess
import traceback
import faulthandler
import re
import socket
import json
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
import colorsys
import decimal
import shutil
import shlex
import csv
import difflib
import hmac
import secrets
import string
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
                              QTreeWidget, QTreeWidgetItem, QHeaderView,
                              QStyledItemDelegate, QStyle)
from PyQt5.QtCore import Qt, QPoint, QPointF, QRectF, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QCursor, QColor, QPen, QPixmap, QPainter, QIcon


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
        self.history_combo.setStyleSheet("""
            QComboBox { border: 1px solid #D0D0D0; border-radius: 4px; padding: 3px 8px;
                font-size: 12px; background: #FFFFFF; color: #333333; }
            QComboBox:focus { border-color: #1A73E8; }
            QComboBox::drop-down { border: none; width: 20px; }
        """)
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


class MarkupWindow(TabbedToolWindow):
    def __init__(self):
        super().__init__("JSON / XML", (
            (JsonFormatterWindow, "JSON"),
            (XmlFormatterWindow, "XML"),
        ))


class GeneratorWindow(TabbedToolWindow):
    def __init__(self):
        super().__init__("UUID/二维码", (
            (UuidWindow, "UUID"),
            (QrCodeWindow, "二维码"),
        ))


class ConvertWindow(TabbedToolWindow):
    def __init__(self):
        super().__init__("格式转换", (
            (ColorWindow, "颜色"),
            (TimestampWindow, "时间戳"),
            (JsonYamlWindow, "JSON-YAML"),
        ))


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
        if self.only_check.isChecked():
            shown = [row for row in rows if row[0] != "equal"]
        else:
            shown = rows
        self.result_tree.clear()
        limit = min(len(shown), DIFF_ROW_LIMIT)
        for kind, l_no, l_text, r_no, r_text in shown[:limit]:
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
        text = ("差异：修改 %d · 新增 %d · 删除 %d · 相同 %d 行"
                % (counts["replace"], counts["insert"], counts["delete"], counts["equal"]))
        if len(shown) > limit:
            text += "（仅显示前 %d 行）" % limit
        if self.only_check.isChecked():
            text += " · 已过滤相同行"
        self.status_label.setText(text)

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


class TextStatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("文本统计")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("输入内容")
        title.setFont(QFont("PingFang SC", 12, QFont.Bold))
        title.setStyleSheet("color: #333333;")
        header.addWidget(title)
        header.addStretch()

        clear_btn = QPushButton("清空")
        clear_btn.setFixedSize(60, 28)
        clear_btn.setCursor(QCursor(Qt.PointingHandCursor))
        clear_btn.setStyleSheet("""
            QPushButton { color: #333333; background: #F0F0F0; border: 1px solid #D0D0D0; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #E0E0E0; }
        """)
        clear_btn.clicked.connect(self.do_clear)
        header.addWidget(clear_btn)
        layout.addLayout(header)

        self.input_text = QPlainTextEdit()
        self.input_text.setStyleSheet("""
            QPlainTextEdit { border: 1px solid #D0D0D0; border-radius: 4px; padding: 8px;
                font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 13px; }
        """)
        self.input_text.textChanged.connect(self.refresh_stats)
        layout.addWidget(self.input_text, 1)

        stats = QGridLayout()
        stats.setHorizontalSpacing(12)
        stats.setVerticalSpacing(8)
        self.stat_labels = {}
        items = [
            ("字符数", "chars"),
            ("行数", "lines"),
            ("词数", "words"),
            ("字节数 (UTF-8)", "bytes"),
            ("字符数 (不含空白)", "chars_ns"),
            ("中文字数", "cjk"),
        ]
        for idx, (label, key) in enumerate(items):
            row = idx // 3
            col = (idx % 3) * 2
            name = QLabel(label)
            name.setFont(QFont("PingFang SC", 11))
            name.setStyleSheet("color: #999999;")
            value = QLabel("0")
            vf = QFont("PingFang SC", 15, QFont.Bold)
            value.setFont(vf)
            value.setStyleSheet("color: #1A73E8;")
            stats.addWidget(name, row, col)
            stats.addWidget(value, row, col + 1)
            self.stat_labels[key] = value
        layout.addLayout(stats)

        self.refresh_stats()

    def do_clear(self):
        self.input_text.setPlainText("")

    def refresh_stats(self):
        text = self.input_text.toPlainText()
        chars = len(text)
        lines = len(text.splitlines()) if text else 0
        words = len(re.findall(r"[A-Za-z0-9]+", text)) + len(re.findall(r"[一-鿿]", text))
        byte_len = len(text.encode("utf-8"))
        chars_no_space = len(re.sub(r"\s", "", text))
        cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
        self.stat_labels["chars"].setText(str(chars))
        self.stat_labels["lines"].setText(str(lines))
        self.stat_labels["words"].setText(str(words))
        self.stat_labels["bytes"].setText(str(byte_len))
        self.stat_labels["chars_ns"].setText(str(chars_no_space))
        self.stat_labels["cjk"].setText(str(cjk))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


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
        self.conv_fmt.setStyleSheet("QComboBox { %s }" % self.FIELD)
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
        self.r_fmt.setStyleSheet("QComboBox { %s }" % self.FIELD)
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
        self.r_preset.setStyleSheet("QComboBox { %s }" % self.FIELD)
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

        pick_btn = QPushButton("取色")
        pick_btn.setFixedSize(70, 30)
        pick_btn.setCursor(QCursor(Qt.PointingHandCursor))
        pick_btn.setStyleSheet("""
            QPushButton { color: #FFFFFF; background: #1A73E8; border: none; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background: #1557B0; }
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
        self.preset_combo.setStyleSheet("""
            QComboBox { border: 1px solid #D0D0D0; border-radius: 4px; padding: 4px 8px;
                font-family: "Menlo", "Consolas", "PingFang SC", monospace; font-size: 13px; background: #FFFFFF; }
            QComboBox:focus { border-color: #1A73E8; }
            QComboBox::drop-down { border: none; width: 20px; }
        """)
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
        self.version_combo.setStyleSheet("""
            QComboBox { border: 1px solid #D0D0D0; border-radius: 4px; padding: 4px 8px; font-size: 12px; background: #FFFFFF; }
            QComboBox::drop-down { border: none; }
        """)
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
        self.text_input.setPlaceholderText("输入文字或链接，实时生成二维码")
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
        self.preset_combo.setStyleSheet("""
            QComboBox { border: 1px solid #D0D0D0; border-radius: 4px; padding: 4px 8px; font-size: 12px; background: #FFFFFF; }
            QComboBox:focus { border-color: #1A73E8; }
            QComboBox::drop-down { border: none; }
        """)
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
                output = subprocess.check_output(f"ping -n 4 {self.target}", shell=True, text=True, encoding="gbk", errors="ignore")
            else:
                output = subprocess.check_output(f"ping -c 4 {self.target}", shell=True, text=True, errors="ignore")
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
        self.src_combo.setStyleSheet(self._combo_style())
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
        self.dst_combo.setStyleSheet(self._combo_style())
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

    def _combo_style(self):
        return """
            QComboBox { border: 1px solid #D0D0D0; border-radius: 4px; padding: 4px 8px;
                font-size: 12px; background: #FFFFFF; }
            QComboBox::drop-down { border: none; }
        """

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


class TimestampWindow(QMainWindow):
    FORMATS = [
        ("yyyy-MM-dd HH:mm:ss", "%Y-%m-%d %H:%M:%S"),
        ("yyyy-MM-dd HH:mm:ss.SSS", "%Y-%m-%d %H:%M:%S.%f"),
        ("yyyy-MM-dd HH:mm", "%Y-%m-%d %H:%M"),
        ("yyyy-MM-dd", "%Y-%m-%d"),
        ("yyyy-MM-dd'T'HH:mm:ss", "%Y-%m-%dT%H:%M:%S"),
        ("yyyy/MM/dd HH:mm:ss", "%Y/%m/%d %H:%M:%S"),
        ("yyyy/MM/dd", "%Y/%m/%d"),
        ("yyyyMMddHHmmss", "%Y%m%d%H%M%S"),
        ("yyyyMMdd", "%Y%m%d"),
        ("MM/dd/yyyy HH:mm:ss", "%m/%d/%Y %H:%M:%S"),
        ("dd-MM-yyyy HH:mm:ss", "%d-%m-%Y %H:%M:%S"),
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("时间戳转换")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        layout.addWidget(QLabel("当前时间戳"))
        cur_layout = QHBoxLayout()
        self.now_label = QLabel("")
        self.now_label.setStyleSheet("color: #1A73E8; font-size: 14px; font-weight: bold;")
        cur_layout.addWidget(self.now_label)
        copy_sec = QPushButton("复制秒级")
        copy_sec.setFixedHeight(28)
        copy_sec.setCursor(QCursor(Qt.PointingHandCursor))
        copy_sec.setStyleSheet(_secondary_btn())
        copy_sec.clicked.connect(lambda: QApplication.clipboard().setText(str(int(time.time()))))
        cur_layout.addWidget(copy_sec)
        copy_ms = QPushButton("复制毫秒级")
        copy_ms.setFixedHeight(28)
        copy_ms.setCursor(QCursor(Qt.PointingHandCursor))
        copy_ms.setStyleSheet(_secondary_btn())
        copy_ms.clicked.connect(lambda: QApplication.clipboard().setText(str(int(time.time() * 1000))))
        cur_layout.addWidget(copy_ms)
        cur_layout.addStretch()
        layout.addLayout(cur_layout)
        self._refresh_now()

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #E0E0E0;")
        layout.addWidget(sep)

        layout.addWidget(QLabel("时间戳 → 日期时间"))
        t2d_layout = QHBoxLayout()
        self.ts_input = QLineEdit()
        self.ts_input.setPlaceholderText("输入秒或毫秒级时间戳")
        self.ts_input.setStyleSheet(_lineedit_style())
        self.ts_input.returnPressed.connect(self.ts_to_date)
        t2d_layout.addWidget(self.ts_input)
        t2d_btn = QPushButton("转换")
        t2d_btn.setFixedHeight(30)
        t2d_btn.setCursor(QCursor(Qt.PointingHandCursor))
        t2d_btn.setStyleSheet(_primary_btn())
        t2d_btn.clicked.connect(self.ts_to_date)
        t2d_layout.addWidget(t2d_btn)
        layout.addLayout(t2d_layout)

        t2d_fmt_layout = QHBoxLayout()
        t2d_fmt_layout.addWidget(QLabel("输出格式:"))
        self.t2d_combo = QComboBox()
        for label, _ in self.FORMATS:
            self.t2d_combo.addItem(label)
        self.t2d_combo.setStyleSheet(_combo_style())
        self.t2d_combo.currentIndexChanged.connect(self.ts_to_date)
        t2d_fmt_layout.addWidget(self.t2d_combo)
        t2d_fmt_layout.addStretch()
        layout.addLayout(t2d_fmt_layout)

        self.ts_result = QLabel("")
        self.ts_result.setStyleSheet("color: #333333; font-size: 13px;")
        self.ts_result.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.ts_result)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("color: #E0E0E0;")
        layout.addWidget(sep2)

        layout.addWidget(QLabel("日期时间 → 时间戳"))
        d2t_layout = QHBoxLayout()
        self.date_input = QLineEdit()
        self.date_input.setPlaceholderText("按所选格式输入日期，如 2026-10-30 12:00:00")
        self.date_input.setStyleSheet(_lineedit_style())
        self.date_input.returnPressed.connect(self.date_to_ts)
        d2t_layout.addWidget(self.date_input)
        d2t_btn = QPushButton("转换")
        d2t_btn.setFixedHeight(30)
        d2t_btn.setCursor(QCursor(Qt.PointingHandCursor))
        d2t_btn.setStyleSheet(_primary_btn())
        d2t_btn.clicked.connect(self.date_to_ts)
        d2t_layout.addWidget(d2t_btn)
        layout.addLayout(d2t_layout)

        d2t_fmt_layout = QHBoxLayout()
        d2t_fmt_layout.addWidget(QLabel("输入格式:"))
        self.d2t_combo = QComboBox()
        self.d2t_combo.addItem("自动识别")
        for label, _ in self.FORMATS:
            self.d2t_combo.addItem(label)
        self.d2t_combo.setStyleSheet(_combo_style())
        self.d2t_combo.currentIndexChanged.connect(self.date_to_ts)
        d2t_fmt_layout.addWidget(self.d2t_combo)
        d2t_fmt_layout.addStretch()
        layout.addLayout(d2t_fmt_layout)

        self.date_result = QLabel("")
        self.date_result.setStyleSheet("color: #333333; font-size: 13px;")
        self.date_result.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.date_result)

        clear_btn = QPushButton("清空")
        clear_btn.setFixedSize(80, 30)
        clear_btn.setCursor(QCursor(Qt.PointingHandCursor))
        clear_btn.setStyleSheet(_secondary_btn())
        clear_btn.clicked.connect(self.do_clear)
        layout.addWidget(clear_btn)
        layout.addStretch()

    def _refresh_now(self):
        now = int(time.time())
        self.now_label.setText(f"秒: {now}    毫秒: {now * 1000}")

    def ts_to_date(self):
        raw = self.ts_input.text().strip()
        if not raw or not raw.isdigit():
            self.ts_result.setText("请输入数字时间戳")
            return
        ts = int(raw)
        if len(raw) >= 13:
            ts = ts / 1000.0
        fmt = self.FORMATS[self.t2d_combo.currentIndex()][1]
        try:
            dt = datetime.datetime.fromtimestamp(ts)
            result = dt.strftime(fmt)
            if 'SSS' in self.FORMATS[self.t2d_combo.currentIndex()][0]:
                result = dt.strftime(fmt)[:-3]
            self.ts_result.setText(result)
        except Exception as e:
            self.ts_result.setText(f"转换失败: {e}")

    def date_to_ts(self):
        raw = self.date_input.text().strip()
        if not raw:
            self.date_result.setText("")
            return
        idx = self.d2t_combo.currentIndex()
        dt = None
        if idx == 0:
            for _, f in self.FORMATS:
                try:
                    dt = datetime.datetime.strptime(raw, f)
                    break
                except ValueError:
                    continue
        else:
            f = self.FORMATS[idx - 1][1]
            try:
                dt = datetime.datetime.strptime(raw, f)
            except ValueError:
                dt = None
        if dt is None:
            self.date_result.setText("日期格式与所选不匹配")
            return
        ts = int(dt.timestamp())
        ms = int(dt.timestamp() * 1000)
        self.date_result.setText(f"秒: {ts}    毫秒: {ms}")

    def do_clear(self):
        self.ts_input.setText("")
        self.date_input.setText("")
        self.ts_result.setText("")
        self.date_result.setText("")

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


def _run_git(args):
    try:
        return subprocess.run(["git", "config"] + args, capture_output=True,
                              encoding="utf-8", errors="replace", **win_no_console())
    except OSError:
        raise RuntimeError("未找到 git 命令，请确认已安装 Git 并在 PATH 中")


def _git_error(result):
    return (result.stderr or "").strip() or "git config 执行失败"


def git_global_list():
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
    result = _run_git(["--global", key, value])
    if result.returncode != 0:
        raise RuntimeError(_git_error(result))


def git_global_unset(key):
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
                ("设置用户名", lambda: self.set_key("user.name"), True),
                ("设置邮箱", lambda: self.set_key("user.email"), True),
                ("添加配置项", self.do_add, False),
                ("删除选中", self.do_delete, False),
                ("刷新", self.refresh, False)):
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


def _combo_style():
    return """
        QComboBox { border: 1px solid #D0D0D0; border-radius: 4px; padding: 4px 8px;
            font-size: 12px; background: #FFFFFF; }
        QComboBox::drop-down { border: none; }
    """


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


class CommandReferenceWindow(QMainWindow):
    CATEGORIES = ["全部", "Docker", "Linux", "SSH", "Vim", "Windows", "Git"]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("命令速查")
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
        self.search_edit.setPlaceholderText("搜索命令或中文说明，例如 容器、端口、分支、log…")
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
                QPushButton { color: #333; background: #FFFFFF; border: 1px solid #D0D0D0;
                    border-radius: 4px; padding: 5px 14px; font-size: 12px; }
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
        for cmd, desc, cat in COMMAND_ITEMS:
            if self._current_cat != "全部" and cat != self._current_cat:
                continue
            if query and query not in cmd.lower() and query not in desc.lower():
                continue
            row = CommandRow(cmd, desc, cat, self.copy_command)
            self._results_layout.addWidget(row)
            count += 1
        if count == 0:
            empty = QLabel("没有匹配的命令")
            empty.setFont(QFont("PingFang SC", 12))
            empty.setStyleSheet("color: #999999; padding: 30px;")
            empty.setAlignment(Qt.AlignCenter)
            self._results_layout.addWidget(empty)
        self._results_layout.addStretch()
        self.status_label.setText("共 %d 条 · 点击任意命令即可复制" % count)

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


# 首页按钮的悬停说明：直接列出工具内部的页签或主要功能，省得一个个点开找。
TOOL_TIPS = {
    "进程管理": "功能：进程列表 · 按名称/PID/窗口标题搜索 · 按端口过滤 · 结束进程",
    "端口扫描": "功能：指定目标与端口范围 · 并发扫描开放端口",
    "Ping 测试": "功能：测试主机连通性与往返延迟",
    "DNS 查询": "功能：查询域名的解析记录",
    "路由追踪": "功能：逐跳查看数据包到达目标的路径",
    "网络测速": "功能：下载速度测试",
    "配置": "页签：环境变量 / 进程内变量 / Git 配置 / 镜像源 / SSH 密钥 / SSH 主机 / 显示开关",
    "JSON/XML": "页签：JSON / XML",
    "编解码": "页签：Base64 / URL / Unicode 转义",
    "加解密": "页签：JWT / AES / RSA / HMAC / 口令哈希 / 随机密钥",
    "正则测试": "功能：常用正则预设 · 实时匹配与高亮",
    "UUID/二维码": "页签：UUID / 二维码",
    "格式转换": "页签：颜色 / 时间戳 / JSON-YAML",
    "文本统计": "功能：字符数 / 行数 / 词数 / 字节数 / 中文字数",
    "文本对比": "功能：逐行 diff · 忽略空白 / 大小写 · 只看差异 · 复制 diff",
    "Cron 表达式": "页签：执行计划 / 书写规范",
    "哈希计算": "页签：文本哈希 / 文件哈希（MD5 / SHA1 / SHA256 / SHA512）",
    "命令速查": "分类：全部 / Docker / Linux / SSH / Vim / Windows / Git",
    "房贷计算器": "功能：等额本息 / 等额本金",
    "图片处理": "页签：转 Base64 / 格式转换 / 缩放压缩",
    "文字雨": "功能：桌面字符雨特效（开关）",
    "防黑屏": "功能：阻止系统休眠与屏幕关闭（开关）",
    "进制转换": "格式：十进制 / 二进制 / 八进制 / 十六进制",
    "商余计算": "功能：求整除的商和余数",
    "单位转换": "页签：字节 / 时间 / 长度 / 重量 / 面积 / 体积 / 速度 / 温度",
    "随机数": "功能：范围内批量生成随机整数 · 可重复",
    "金额大写": "功能：数字金额转人民币中文大写",
    "罗马数字": "功能：阿拉伯数字 ↔ 罗马数字",
}


class ToolboxWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("系统工具箱")
        screen = QApplication.primaryScreen().availableGeometry()
        w, h = 700, min(500, screen.height() - 40)
        self.setGeometry(screen.x() + (screen.width() - w) // 2,
                         screen.y() + (screen.height() - h) // 2, w, h)
        self.setStyleSheet("""
            QMainWindow { background: #FFFFFF; }
        """)
        self.ip, self.mac, self.adapter = get_effective_ip()
        self.popup = None
        self.markup_window = None
        self.codec_window = None
        self.hash_window = None
        self.crypto_window = None
        self.regex_window = None
        self.diff_window = None
        self.generator_window = None
        self.baseconvert_window = None
        self.divmod_window = None
        self.convert_window = None
        self.config_window = None
        self.unit_window = None
        self.random_window = None
        self.textstat_window = None
        self.cron_window = None
        self.image_window = None
        self.rmb_window = None
        self.roman_window = None
        self.ping_window = None
        self.dns_window = None
        self.traceroute_window = None
        self.portscan_window = None
        self.speedtest_window = None
        self.cmdref_window = None
        self.mortgage_window = None
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(20, 20, 20, 5)
        main_layout.setSpacing(15)

        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        self.toggle_buttons = {}
        self._caffeinate = None
        self._rain_overlay = None

        section1 = self.create_section("系统工具", [
            "进程管理", "端口扫描", "Ping 测试", "DNS 查询", "路由追踪",
            "网络测速", "配置"
        ], {
            "进程管理": self.show_process_search,
            "端口扫描": self.show_portscan,
            "Ping 测试": self.show_ping,
            "DNS 查询": self.show_dns,
            "路由追踪": self.show_traceroute,
            "网络测速": self.show_speedtest,
            "配置": self.show_config
        })

        section3 = self.create_section("文本处理", [
            "JSON/XML", "编解码", "加解密",
            "正则测试", "UUID/二维码",
            "格式转换", "文本统计", "文本对比", "Cron 表达式", "哈希计算"
        ], {
            "JSON/XML": self.show_markup,
            "编解码": self.show_codec,
            "哈希计算": self.show_hash,
            "加解密": self.show_crypto,
            "正则测试": self.show_regex,
            "文本对比": self.show_diff,
            "UUID/二维码": self.show_generator,
            "格式转换": self.show_convert,
            "文本统计": self.show_textstat,
            "Cron 表达式": self.show_cron
        })
        content_layout.addWidget(section3)

        section6 = self.create_section("其他", [
            "命令速查", "房贷计算器", "图片处理", "文字雨", "防黑屏"
        ], {
            "命令速查": self.show_command_reference,
            "房贷计算器": self.show_mortgage,
            "图片处理": self.show_image_tool
        }, {
            "文字雨": self.set_matrix_rain,
            "防黑屏": self.set_awake
        })
        content_layout.addWidget(section6)

        section4 = self.create_section("数学工具", [
            "进制转换", "商余计算", "单位转换", "随机数", "金额大写", "罗马数字"
        ], {
            "进制转换": self.show_base_convert,
            "商余计算": self.show_divmod,
            "单位转换": self.show_unit_convert,
            "随机数": self.show_random,
            "金额大写": self.show_rmb,
            "罗马数字": self.show_roman
        })
        content_layout.addWidget(section4)
        content_layout.addWidget(section1)

        content_layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll.viewport().setStyleSheet("background: #FFFFFF;")
        scroll.setWidget(content_area)
        main_layout.addWidget(scroll, 1)

        bottom_bar = QFrame()
        bottom_bar.setStyleSheet("QFrame { background: #FFFFFF; }")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        self.cpu_label = QLabel("CPU: --")
        self.cpu_label.setFont(QFont("PingFang SC", 10))
        self.cpu_label.setStyleSheet("color: #999999;")
        bottom_layout.addWidget(self.cpu_label)

        self.mem_label = QLabel("内存: --")
        self.mem_label.setFont(QFont("PingFang SC", 10))
        self.mem_label.setStyleSheet("color: #999999;")
        bottom_layout.addWidget(self.mem_label)

        bottom_layout.addStretch()

        repo_label = QLabel('<a href="https://github.com/FantasyEngineer/personal_tool">仓库</a>')
        repo_label.setFont(QFont("PingFang SC", 10))
        repo_label.setCursor(QCursor(Qt.PointingHandCursor))
        repo_label.setToolTip("在 GitHub 上查看源码")
        repo_label.setOpenExternalLinks(True)
        bottom_layout.addWidget(repo_label)

        ip_text = f"IP: {self.ip}"
        mac_text = f"MAC: {self.mac}" if self.mac and self.mac != "-" else ""
        info_text = f"{ip_text}  |  {mac_text}" if mac_text else ip_text

        info_label = QLabel(info_text)
        info_label.setFont(QFont("PingFang SC", 10))
        info_label.setStyleSheet("color: #999999;")
        info_label.setCursor(QCursor(Qt.PointingHandCursor))
        info_label.setToolTip("点击复制 IP")
        info_label.mousePressEvent = lambda e: self.copy_to_clipboard(self.ip)
        bottom_layout.addWidget(info_label)

        main_layout.addWidget(bottom_bar)

        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self.refresh_stats)
        self.stats_timer.start(3000)
        self.refresh_stats()

    def refresh_stats(self):
        cpu_pct, mem_pct, used_gb, total_gb = get_system_stats()
        if cpu_pct is not None:
            self.cpu_label.setText(f"CPU: {cpu_pct:.0f}%")
        if mem_pct is not None:
            self.mem_label.setText(f"内存: {used_gb:.1f}G / {total_gb:.0f}G ({mem_pct:.0f}%)")

    def create_section(self, title, buttons, callbacks=None, toggle_callbacks=None):
        toggle_callbacks = toggle_callbacks or {}
        section = QFrame()
        section.setStyleSheet("""
            QFrame {
                background: #FAFAFA;
            }
        """)
        layout = QVBoxLayout(section)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setFont(QFont("PingFang SC", 12, QFont.Bold))
        title_label.setStyleSheet("color: #333333;")
        layout.addWidget(title_label)

        from PyQt5.QtWidgets import QGridLayout
        btn_layout = QGridLayout()
        btn_layout.setSpacing(8)

        for i, btn_text in enumerate(buttons):
            btn = QPushButton(btn_text)
            btn.setFixedHeight(32)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            tip = TOOL_TIPS.get(btn_text)
            if tip:
                btn.setToolTip(tip)
            btn.setStyleSheet("""
                QPushButton {
                    color: #333333;
                    background: #FFFFFF;
                    border: 1px solid #D0D0D0;
                    border-radius: 4px;
                    font-size: 11px;
                    padding: 0 12px;
                }
                QPushButton:hover {
                    background: #F0F0F0;
                    border-color: #1A73E8;
                    color: #1A73E8;
                }
                QPushButton:pressed {
                    background: #E8E8E8;
                }
            """
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
                btn.toggled.connect(toggle_callbacks[btn_text])
                self.toggle_buttons[btn_text] = btn
            elif callbacks and btn_text in callbacks:
                btn.clicked.connect(callbacks[btn_text])
            row = i // 6
            col = i % 6
            btn_layout.addWidget(btn, row, col)

        for col in range(6):
            btn_layout.setColumnStretch(col, 1)
        layout.addLayout(btn_layout)

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
        if active:
            if self._rain_overlay is None:
                self._rain_overlay = MatrixRainOverlay(
                    on_close=lambda: self.toggle_buttons["文字雨"].setChecked(False)
                )
            self._rain_overlay.start()
        else:
            if self._rain_overlay is not None:
                self._rain_overlay.stop()

    def closeEvent(self, event):
        try:
            self.set_awake(False)
        except Exception:
            pass
        try:
            if self._rain_overlay is not None:
                self._rain_overlay.stop()
        except Exception:
            pass
        super().closeEvent(event)

    def show_process_search(self):
        if self.popup and self.popup.isVisible():
            self.popup.activateWindow()
            return
        self.popup = ProcessManagerWindow(self)
        self.popup.show()

    def show_markup(self):
        if self.markup_window is None:
            self.markup_window = MarkupWindow()
        self.markup_window.show()
        self.markup_window.activateWindow()

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

    def show_diff(self):
        if self.diff_window is None:
            self.diff_window = DiffWindow()
        self.diff_window.show()
        self.diff_window.activateWindow()

    def show_generator(self):
        if self.generator_window is None:
            self.generator_window = GeneratorWindow()
        self.generator_window.show()
        self.generator_window.activateWindow()

    def show_base_convert(self):
        if self.baseconvert_window is None:
            self.baseconvert_window = BaseConvertWindow()
        self.baseconvert_window.show()
        self.baseconvert_window.activateWindow()

    def show_divmod(self):
        if self.divmod_window is None:
            self.divmod_window = DivModWindow()
        self.divmod_window.show()
        self.divmod_window.activateWindow()

    def show_convert(self):
        if self.convert_window is None:
            self.convert_window = ConvertWindow()
        self.convert_window.show()
        self.convert_window.activateWindow()

    def show_config(self):
        if self.config_window is None:
            self.config_window = ConfigWindow()
        self.config_window.show()
        self.config_window.activateWindow()

    def show_command_reference(self):
        if self.cmdref_window is None:
            self.cmdref_window = CommandReferenceWindow()
        self.cmdref_window.show()
        self.cmdref_window.activateWindow()

    def show_mortgage(self):
        if self.mortgage_window is None:
            self.mortgage_window = MortgageWindow()
        self.mortgage_window.show()
        self.mortgage_window.activateWindow()

    def show_unit_convert(self):
        if self.unit_window is None:
            self.unit_window = UnitConvertWindow()
        self.unit_window.show()
        self.unit_window.activateWindow()

    def show_random(self):
        if self.random_window is None:
            self.random_window = RandomWindow()
        self.random_window.show()
        self.random_window.activateWindow()

    def show_textstat(self):
        if self.textstat_window is None:
            self.textstat_window = TextStatWindow()
        self.textstat_window.show()
        self.textstat_window.activateWindow()

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

    def show_rmb(self):
        if self.rmb_window is None:
            self.rmb_window = RmbUppercaseWindow()
        self.rmb_window.show()
        self.rmb_window.activateWindow()

    def show_roman(self):
        if self.roman_window is None:
            self.roman_window = RomanNumeralWindow()
        self.roman_window.show()
        self.roman_window.activateWindow()

    def show_ping(self):
        if self.ping_window is None:
            self.ping_window = PingWindow()
        self.ping_window.show()
        self.ping_window.activateWindow()

    def show_dns(self):
        if self.dns_window is None:
            self.dns_window = DNSWindow()
        self.dns_window.show()
        self.dns_window.activateWindow()

    def show_traceroute(self):
        if self.traceroute_window is None:
            self.traceroute_window = TracerouteWindow()
        self.traceroute_window.show()
        self.traceroute_window.activateWindow()

    def show_portscan(self):
        if self.portscan_window is None:
            self.portscan_window = PortScanWindow()
        self.portscan_window.show()
        self.portscan_window.activateWindow()

    def show_speedtest(self):
        if self.speedtest_window is None:
            self.speedtest_window = SpeedTestWindow()
        self.speedtest_window.show()
        self.speedtest_window.activateWindow()

    def copy_to_clipboard(self, text):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        QMessageBox.information(self, "已复制", f"已复制到剪贴板:\n{text}", QMessageBox.Ok)


def startup_log_path():
    """启动日志：打包后放 exe 旁边，开发时放项目目录，不可写再退回用户目录。"""
    if getattr(sys, "frozen", False):
        folders = [os.path.dirname(sys.executable),
                   os.path.join(os.path.expanduser("~"), ".personal_toolbox")]
    else:
        folders = [os.path.dirname(os.path.abspath(__file__)),
                   os.path.join(os.path.expanduser("~"), ".personal_toolbox")]
    for folder in folders:
        path = os.path.join(folder, "startup.log")
        try:
            os.makedirs(folder, exist_ok=True)
            with open(path, "a", encoding="utf-8"):
                pass
            return path
        except OSError:
            continue
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
        QMessageBox.critical(None, "系统工具箱启动失败", text)
        return
    except Exception:
        pass
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, text, "系统工具箱启动失败", 0x10)
    except Exception:
        pass


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
    try:
        app = QApplication(sys.argv)
        app.setWindowIcon(app_icon())
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
