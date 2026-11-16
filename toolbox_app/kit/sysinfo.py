"""系统信息与进程：网卡地址、CPU/内存占用、进程快照与端口归属。

只做数据采集，不涉及界面；全部是平台命令的封装，命令固定不拼接用户输入。
"""
import csv
import io
import os
import platform
import re
import socket
import subprocess
import time

from toolbox_app.natives import win_no_console


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
