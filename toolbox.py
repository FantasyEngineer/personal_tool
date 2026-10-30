import sys
import os
import platform
import subprocess
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
import yaml
from PIL import Image
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                              QHBoxLayout, QLabel, QPushButton, QFrame,
                              QScrollArea, QMessageBox, QLineEdit,
                              QGraphicsDropShadowEffect, QTextEdit, QSplitter,
                              QPlainTextEdit, QComboBox, QCheckBox, QStackedWidget,
                              QGridLayout, QSpinBox, QTabWidget, QColorDialog,
                              QFileDialog)
from PyQt5.QtCore import Qt, QPoint, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QCursor, QColor, QPixmap, QPainter


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
            cpu_pct = 0.0
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor -Filter \"Name='_Total'\").PercentProcessorTime"],
                text=True, encoding="gbk", errors="ignore")
            for line in out.splitlines():
                line = line.strip()
                if line:
                    try:
                        cpu_pct = float(line)
                    except ValueError:
                        pass
                    break
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command",
                 "$o=Get-CimInstance Win32_OperatingSystem; $o.TotalVisibleMemorySize; $o.FreePhysicalMemory"],
                text=True, encoding="gbk", errors="ignore")
            nums = [l.strip() for l in out.splitlines() if l.strip().isdigit()]
            total_kb = int(nums[0]) if len(nums) >= 1 else 0
            free_kb = int(nums[1]) if len(nums) >= 2 else 0
            used_kb = total_kb - free_kb
            used_gb = used_kb / (1024 ** 2)
            total_gb = total_kb / (1024 ** 2)
            mem_pct = (used_kb / total_kb * 100) if total_kb > 0 else 0
            return cpu_pct, mem_pct, used_gb, total_gb
    except Exception:
        pass
    return None, None, None, None


def search_processes(port="", keyword=""):
    results = []
    system = platform.system()
    try:
        if system == "Windows":
            if port:
                output = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True, text=True, encoding="gbk", errors="ignore")
                pids = set()
                for line in output.splitlines():
                    parts = line.split()
                    if len(parts) >= 4:
                        pids.add(parts[4])
                for pid in pids:
                    try:
                        cmd = subprocess.check_output(f'tasklist /FI "PID eq {pid}" /FO CSV /NH', shell=True, text=True, encoding="gbk", errors="ignore")
                        app_name = cmd.split(",")[0].strip('"')
                        results.append({"pid": pid, "app": app_name, "port": port})
                    except Exception:
                        results.append({"pid": pid, "app": "Unknown", "port": port})
            if keyword:
                output = subprocess.check_output(f'tasklist /FI "IMAGENAME eq {keyword}*" /FO CSV /NH', shell=True, text=True, encoding="gbk", errors="ignore")
                for line in output.strip().splitlines():
                    parts = line.split(",")
                    if len(parts) >= 2:
                        app_name = parts[0].strip('"')
                        pid = parts[1].strip('"')
                        if not any(r["pid"] == pid for r in results):
                            results.append({"pid": pid, "app": app_name, "port": "-"})
        else:
            lsof_output = ""
            try:
                lsof_output = subprocess.check_output(["lsof", "-i", "-P", "-n"], text=True, errors="ignore")
            except Exception:
                pass

            if port:
                for line in lsof_output.splitlines()[1:]:
                    parts = line.split()
                    if len(parts) >= 9:
                        name = parts[0]
                        pid = parts[1]
                        port_col = parts[8]
                        if f":{port}" in port_col and not any(r["pid"] == pid for r in results):
                            results.append({"pid": pid, "app": name, "port": port})

            if keyword:
                ps_output = subprocess.check_output(["ps", "aux"], text=True, errors="ignore")
                for line in ps_output.splitlines():
                    if keyword.lower() in line.lower():
                        parts = line.split()
                        if len(parts) >= 11:
                            pid = parts[1]
                            full_cmd = " ".join(parts[10:])
                            app_name = full_cmd.split("/")[-1].split(" ")[0]
                            port = "-"
                            for pline in lsof_output.splitlines()[1:]:
                                pparts = pline.split()
                                if len(pparts) >= 9 and pparts[1] == pid:
                                    port_col = pparts[8]
                                    if ":" in port_col:
                                        port = port_col.split(":")[-1]
                                        if "(" in port:
                                            port = port.split("(")[0]
                                        break
                            if not any(r["pid"] == pid for r in results):
                                results.append({"pid": pid, "app": app_name, "port": port})
    except Exception:
        pass
    return results


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


TOOL_WIN_W = 900
TOOL_WIN_H = 600


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


class ProcessSearchPopup(QMainWindow):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("进程查询")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("""
            QMainWindow { background: #FFFFFF; }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(8)

        input_layout.addWidget(QLabel("端口:"))
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("如: 8080")
        self.port_input.setFixedWidth(100)
        self.port_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #D0D0D0;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QLineEdit:focus { border-color: #1A73E8; }
        """)
        input_layout.addWidget(self.port_input)

        input_layout.addWidget(QLabel("应用:"))
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("如: python")
        self.keyword_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #D0D0D0;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QLineEdit:focus { border-color: #1A73E8; }
        """)
        input_layout.addWidget(self.keyword_input)

        search_btn = QPushButton("查询")
        search_btn.setFixedSize(60, 28)
        search_btn.setCursor(QCursor(Qt.PointingHandCursor))
        search_btn.setStyleSheet("""
            QPushButton {
                color: #FFFFFF;
                background: #1A73E8;
                border: none;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover { background: #1557B0; }
        """)
        search_btn.clicked.connect(self.do_search)
        input_layout.addWidget(search_btn)

        self.port_input.returnPressed.connect(self.do_search)
        self.keyword_input.returnPressed.connect(self.do_search)

        layout.addLayout(input_layout)

        self.status_label = QLabel("")
        self.status_label.setFont(QFont("PingFang SC", 10))
        self.status_label.setStyleSheet("color: #999999;")
        layout.addWidget(self.status_label)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                border: none;
                background: #F5F5F5;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #CCCCCC;
                border-radius: 4px;
                min-height: 20px;
            }
        """)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 10, 0, 10)
        self.content_layout.setSpacing(8)
        self.content_layout.setAlignment(Qt.AlignTop)

        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll)

        self.show_empty()

    def show_empty(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        no_data = QLabel("请输入端口或应用名称进行查询")
        no_data.setFont(QFont("PingFang SC", 12))
        no_data.setStyleSheet("color: #999999; padding: 30px;")
        no_data.setAlignment(Qt.AlignCenter)
        self.content_layout.addWidget(no_data)

    def do_search(self):
        port = self.port_input.text().strip()
        keyword = self.keyword_input.text().strip()
        if not port and not keyword:
            QMessageBox.warning(self, "提示", "请输入端口或应用名称", QMessageBox.Ok)
            return

        cmds = []
        if platform.system() == "Windows":
            if port:
                cmds.append(f"netstat -ano | findstr :{port}")
            if keyword:
                cmds.append(f'tasklist /FI "IMAGENAME eq {keyword}*"')
        else:
            if port:
                cmds.append(f"lsof -i :{port}")
            if keyword:
                cmds.append(f"ps aux | grep {keyword}")
        self.status_label.setText("执行: " + " && ".join(cmds))

        processes = search_processes(port, keyword)

        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not processes:
            no_data = QLabel("未找到匹配的进程")
            no_data.setFont(QFont("PingFang SC", 12))
            no_data.setStyleSheet("color: #999999; padding: 30px;")
            no_data.setAlignment(Qt.AlignCenter)
            self.content_layout.addWidget(no_data)
            return

        for proc in processes:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 6, 8, 6)

            app_label = QLabel(proc["app"])
            app_label.setFont(QFont("PingFang SC", 11))
            app_label.setStyleSheet("color: #333333;")
            row_layout.addWidget(app_label, 1)

            port_label = QLabel(f"端口: {proc['port']}")
            port_label.setFont(QFont("PingFang SC", 11))
            port_label.setStyleSheet("color: #666666;")
            port_label.setFixedWidth(100)
            row_layout.addWidget(port_label)

            pid_label = QLabel(f"PID: {proc['pid']}")
            pid_label.setFont(QFont("PingFang SC", 11))
            pid_label.setStyleSheet("color: #999999;")
            row_layout.addWidget(pid_label)

            row_layout.addStretch()

            kill_btn = QPushButton("Kill")
            kill_btn.setFixedSize(60, 24)
            kill_btn.setCursor(QCursor(Qt.PointingHandCursor))
            kill_btn.setStyleSheet("""
                QPushButton {
                    color: #FFFFFF;
                    background: #FF5F57;
                    border: none;
                    border-radius: 3px;
                    font-size: 11px;
                }
                QPushButton:hover { background: #E0443E; }
                QPushButton:pressed { background: #C73834; }
            """)
            kill_btn.clicked.connect(lambda checked, p=proc["pid"]: self.kill_and_refresh(p))
            row_layout.addWidget(kill_btn)

            self.content_layout.addWidget(row)

    def kill_and_refresh(self, pid):
        kill_process(pid)
        self.do_search()


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

    def do_format(self):
        raw = self.input_text.toPlainText().strip()
        if not raw:
            self.output_text.setPlainText("")
            return
        try:
            parsed = json.loads(raw)
            formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
            self.output_text.setPlainText(formatted)
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
            resized = self.pil_img.resize((w, h), Image.LANCZOS)
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

    def __init__(self):
        super().__init__()

    def run(self):
        urls = [
            "https://speed.cloudflare.com/__down?bytes=25000000",
            "https://speed.hetzner.de/100MB.bin",
        ]
        last_err = None
        for url in urls:
            try:
                start_time = time.time()
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                response = urllib.request.urlopen(req, timeout=15)
                total = 0
                while True:
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    total += len(chunk)
                duration = time.time() - start_time

                size_mb = total / (1024 * 1024)
                speed_mbps = (size_mb * 8) / duration if duration > 0 else 0
                self.speed_done.emit("测速完成", f"下载速度: {speed_mbps:.1f} Mbps\n({size_mb:.1f} MB / {duration:.1f} 秒)")
                return
            except Exception as e:
                last_err = e
        self.speed_done.emit("测速失败", f"错误: {last_err}")


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
        if not self.test_btn.isEnabled():
            return
        self.status_label.setText("正在下载测试文件...")
        self.result_label.setText("")
        self.test_btn.setEnabled(False)
        self.worker = SpeedTestWorker()
        self.worker.speed_done.connect(self.show_speed_result)
        self.worker.start()

    def show_speed_result(self, status, result):
        self.status_label.setText(status)
        self.result_label.setText(result)
        self.test_btn.setEnabled(True)

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


class EnvVarWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("环境变量")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(10)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索变量名或值...")
        self.search_input.setStyleSheet(_lineedit_style())
        self.search_input.textChanged.connect(self.filter_vars)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

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

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()


class UnitConvertWindow(QMainWindow):
    BYTE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]
    TIME_UNITS = ["纳秒", "微秒", "毫秒", "秒", "分钟", "小时", "天"]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("单位换算")
        self.setGeometry(*tool_win_geometry())
        self.setStyleSheet("QMainWindow { background: #FFFFFF; }")
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 10)
        layout.setSpacing(12)

        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("类别:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(["字节 (B/KB/MB/GB)", "时间 (ms/s/min)"])
        self.type_combo.setStyleSheet(_combo_style())
        self.type_combo.currentIndexChanged.connect(self.on_type_change)
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        layout.addLayout(type_layout)

        val_layout = QHBoxLayout()
        val_layout.addWidget(QLabel("数值:"))
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("输入数值...")
        self.value_input.setStyleSheet(_lineedit_style())
        self.value_input.textChanged.connect(self.do_convert)
        val_layout.addWidget(self.value_input)
        self.src_combo = QComboBox()
        self.src_combo.setStyleSheet(_combo_style())
        self.src_combo.currentIndexChanged.connect(self.do_convert)
        val_layout.addWidget(self.src_combo)
        layout.addLayout(val_layout)

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

        self.on_type_change()

    def on_type_change(self):
        units = self.BYTE_UNITS if self.type_combo.currentIndex() == 0 else self.TIME_UNITS
        self.src_combo.blockSignals(True)
        self.src_combo.clear()
        self.src_combo.addItems(units)
        self.src_combo.blockSignals(False)
        self.do_convert()

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
        idx = self.src_combo.currentIndex()
        lines = []
        if self.type_combo.currentIndex() == 0:
            base_bytes = val * (1024 ** idx)
            for i, unit in enumerate(self.BYTE_UNITS):
                v = base_bytes / (1024 ** i)
                lines.append(f"{self._fmt(v)} {unit}")
        else:
            ns_per = [1, 1000, 1000000, 1000000000, 60000000000, 3600000000000, 86400000000000]
            total_ns = val * ns_per[idx]
            for i, unit in enumerate(self.TIME_UNITS):
                v = total_ns / ns_per[i]
                lines.append(f"{self._fmt(v)} {unit}")
        self.result_text.setPlainText('\n'.join(lines))

    def _fmt(self, v):
        if v == int(v) and abs(v) < 1e15:
            return str(int(v))
        return f"{v:.6g}"

    def do_clear(self):
        self.value_input.setText("")
        self.result_text.setPlainText("")

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
        codes = list(range(0xFF66, 0xFF9D)) + list(range(0x30, 0x3A)) + list(range(0x41, 0x5B))
        self._chars = [chr(c) for c in codes]
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
    ("ps aux | grep nginx", "查找指定进程", "Linux"),
    ("top", "实时查看进程与资源占用", "Linux"),
    ("df -h", "查看磁盘空间使用", "Linux"),
    ("du -sh dir", "查看目录总大小", "Linux"),
    ("free -h", "查看内存使用", "Linux"),
    ("systemctl status nginx", "查看服务状态", "Linux"),
    ("systemctl restart nginx", "重启服务", "Linux"),
    ("journalctl -u nginx -f", "跟踪某服务日志", "Linux"),
    ("ss -tulpn", "查看监听端口与进程", "Linux"),
    ("ssh user@host", "远程登录", "Linux"),
    ("scp file user@host:/path", "远程复制文件", "Linux"),
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
    # ---------- Windows ----------
    ("ipconfig /all", "查看完整网络配置", "Windows"),
    ("ping 8.8.8.8", "测试网络连通", "Windows"),
    ("tracert baidu.com", "路由追踪", "Windows"),
    ("netstat -ano", "查看所有连接与监听端口（含 PID）", "Windows"),
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
    CATEGORIES = ["全部", "Docker", "Linux", "Windows", "Git"]

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


class ToolboxWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("系统工具箱")
        self.setGeometry(200, 200, 700, 500)
        self.setStyleSheet("""
            QMainWindow { background: #FFFFFF; }
        """)
        self.ip, self.mac, self.adapter = get_effective_ip()
        self.popup = None
        self.json_window = None
        self.xml_window = None
        self.base64_window = None
        self.url_window = None
        self.hash_window = None
        self.regex_window = None
        self.uuid_window = None
        self.qrcode_window = None
        self.baseconvert_window = None
        self.divmod_window = None
        self.jsonyaml_window = None
        self.timestamp_window = None
        self.envvar_window = None
        self.unit_window = None
        self.random_window = None
        self.textstat_window = None
        self.unicode_window = None
        self.cron_window = None
        self.color_window = None
        self.image_window = None
        self.rmb_window = None
        self.roman_window = None
        self.ping_window = None
        self.dns_window = None
        self.traceroute_window = None
        self.portscan_window = None
        self.speedtest_window = None
        self.cmdref_window = None
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
        content_layout.setSpacing(15)

        self.toggle_buttons = {}
        self._caffeinate = None
        self._rain_overlay = None

        section1 = self.create_section("系统工具", [
            "获取进程", "端口扫描", "Ping 测试", "DNS 查询", "路由追踪",
            "网络测速", "环境变量", "命令速查", "防黑屏", "文字雨"
        ], {
            "获取进程": self.show_process_search,
            "端口扫描": self.show_portscan,
            "Ping 测试": self.show_ping,
            "DNS 查询": self.show_dns,
            "路由追踪": self.show_traceroute,
            "网络测速": self.show_speedtest,
            "环境变量": self.show_env_vars,
            "命令速查": self.show_command_reference
        }, {
            "防黑屏": self.set_awake,
            "文字雨": self.set_matrix_rain
        })
        content_layout.addWidget(section1)

        section3 = self.create_section("文本处理", [
            "JSON 处理", "XML 格式化", "Base64 编解码", "URL 编解码",
            "哈希计算", "正则测试", "UUID 生成", "二维码生成",
            "JSON-YAML", "时间戳", "Unicode 转义", "文本统计", "Cron 表达式", "颜色转换"
        ], {
            "JSON 处理": self.show_json_formatter,
            "XML 格式化": self.show_xml_formatter,
            "Base64 编解码": self.show_base64,
            "URL 编解码": self.show_url_encode,
            "哈希计算": self.show_hash,
            "正则测试": self.show_regex,
            "UUID 生成": self.show_uuid,
            "二维码生成": self.show_qrcode,
            "JSON-YAML": self.show_json_yaml,
            "时间戳": self.show_timestamp,
            "Unicode 转义": self.show_unicode,
            "文本统计": self.show_textstat,
            "Cron 表达式": self.show_cron,
            "颜色转换": self.show_color
        })
        content_layout.addWidget(section3)

        section4 = self.create_section("数学工具", [
            "进制转换", "商余计算", "单位换算", "随机数", "金额大写", "罗马数字"
        ], {
            "进制转换": self.show_base_convert,
            "商余计算": self.show_divmod,
            "单位换算": self.show_unit_convert,
            "随机数": self.show_random,
            "金额大写": self.show_rmb,
            "罗马数字": self.show_roman
        })
        content_layout.addWidget(section4)

        section5 = self.create_section("图片工具", [
            "图片处理"
        ], {
            "图片处理": self.show_image_tool
        })
        content_layout.addWidget(section5)

        content_layout.addStretch()
        main_layout.addWidget(content_area, 1)

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

        ip_text = f"IP: {self.ip}"
        mac_text = f"MAC: {self.mac}" if self.mac and self.mac != "-" else ""
        info_text = f"{ip_text}  |  {mac_text}" if mac_text else ip_text

        info_label = QLabel(info_text)
        info_label.setFont(QFont("PingFang SC", 10))
        info_label.setStyleSheet("color: #999999;")
        info_label.setCursor(QCursor(Qt.PointingHandCursor))
        info_label.setToolTip("点击复制")
        info_label.mousePressEvent = lambda e: self.copy_to_clipboard(info_text)
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
        self.popup = ProcessSearchPopup(self)
        self.popup.show()

    def show_json_formatter(self):
        if self.json_window is None:
            self.json_window = JsonFormatterWindow()
        self.json_window.show()
        self.json_window.activateWindow()

    def show_xml_formatter(self):
        if self.xml_window is None:
            self.xml_window = XmlFormatterWindow()
        self.xml_window.show()
        self.xml_window.activateWindow()

    def show_base64(self):
        if self.base64_window is None:
            self.base64_window = Base64Window()
        self.base64_window.show()
        self.base64_window.activateWindow()

    def show_url_encode(self):
        if self.url_window is None:
            self.url_window = UrlEncodeWindow()
        self.url_window.show()
        self.url_window.activateWindow()

    def show_hash(self):
        if self.hash_window is None:
            self.hash_window = HashWindow()
        self.hash_window.show()
        self.hash_window.activateWindow()

    def show_regex(self):
        if self.regex_window is None:
            self.regex_window = RegexWindow()
        self.regex_window.show()
        self.regex_window.activateWindow()

    def show_uuid(self):
        if self.uuid_window is None:
            self.uuid_window = UuidWindow()
        self.uuid_window.show()
        self.uuid_window.activateWindow()

    def show_qrcode(self):
        if self.qrcode_window is None:
            self.qrcode_window = QrCodeWindow()
        self.qrcode_window.show()
        self.qrcode_window.activateWindow()

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

    def show_json_yaml(self):
        if self.jsonyaml_window is None:
            self.jsonyaml_window = JsonYamlWindow()
        self.jsonyaml_window.show()
        self.jsonyaml_window.activateWindow()

    def show_timestamp(self):
        if self.timestamp_window is None:
            self.timestamp_window = TimestampWindow()
        self.timestamp_window.show()
        self.timestamp_window.activateWindow()

    def show_env_vars(self):
        if self.envvar_window is None:
            self.envvar_window = EnvVarWindow()
        self.envvar_window.show()
        self.envvar_window.activateWindow()

    def show_command_reference(self):
        if self.cmdref_window is None:
            self.cmdref_window = CommandReferenceWindow()
        self.cmdref_window.show()
        self.cmdref_window.activateWindow()

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

    def show_unicode(self):
        if self.unicode_window is None:
            self.unicode_window = UnicodeEscapeWindow()
        self.unicode_window.show()
        self.unicode_window.activateWindow()

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

    def show_color(self):
        if self.color_window is None:
            self.color_window = ColorWindow()
        self.color_window.show()
        self.color_window.activateWindow()

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ToolboxWindow()
    window.show()
    sys.exit(app.exec_())
