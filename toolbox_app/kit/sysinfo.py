"""系统信息与进程：网卡地址、CPU/内存占用、进程快照与端口归属。

只做数据采集，不涉及界面；全部是平台命令的封装，命令固定不拼接用户输入。
"""
import csv
import io
import os
import platform
import re
import socket
import struct
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


# ------------------------------------------------------------------ 系统详细信息
#
# 首页左下角的 CPU / 内存点击后要看的详情。数据一律来自「当前这台电脑」：
# Windows 走一次 CIM 查询（一个 PowerShell 进程拿全），macOS 走 sysctl +
#
# system_profiler。任何一项取不到就显示 "--"，不让异常把整个窗口拖垮。

INFO_CACHE_SECONDS = 120
_info_cache = {"at": 0.0, "sections": None}

# 只保留便宜的 CIM 查询（合计约 0.3 秒）：Win32_Processor、Get-PhysicalDisk 与
# Get-NetIPConfiguration 实测要 1~3.5 秒，改由注册表 / 轻量网卡类 / ctypes 顶上。
_WINDOWS_INFO_SCRIPT = (
    "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;"
    "$ErrorActionPreference='SilentlyContinue';"
    "$cs=Get-CimInstance Win32_ComputerSystem|Select-Object Manufacturer,Model,SystemType;"
    "$os=Get-CimInstance Win32_OperatingSystem|Select-Object Caption,Version,BuildNumber,OSArchitecture;"
    "$mem=@(Get-CimInstance Win32_PhysicalMemory|Select-Object Capacity,ConfiguredClockSpeed,Speed,"
    "Manufacturer,DeviceLocator);"
    "$disk=@(Get-CimInstance Win32_DiskDrive|Select-Object Model,Size,InterfaceType);"
    "$phys=@(Get-CimInstance -Namespace root\\Microsoft\\Windows\\Storage -ClassName MSFT_PhysicalDisk|"
    "Select-Object FriendlyName,MediaType,BusType,Size);"
    "$vol=@(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3'|Select-Object DeviceID,VolumeName,"
    "Size,FreeSpace);"
    "$gpu=@(Get-CimInstance Win32_VideoController|Select-Object Name,DriverVersion,VideoModeDescription);"
    "$net=@(Get-CimInstance Win32_NetworkAdapterConfiguration -Filter 'IPEnabled=TRUE'|"
    "Select-Object Description,MACAddress,IPAddress,DefaultIPGateway);"
    "@{computer=$cs;os=$os;memory=$mem;disks=$disk;physical=$phys;volumes=$vol;gpu=$gpu;net=$net}|"
    "ConvertTo-Json -Depth 4 -Compress"
)


def _gb_text(value):
    try:
        return "%.1f GB" % (float(value) / (1024 ** 3))
    except (TypeError, ValueError):
        return "--"


def _uptime_text(seconds):
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return "--"
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    if days:
        return "%d 天 %d 小时" % (days, hours)
    if hours:
        return "%d 小时 %d 分" % (hours, rest // 60)
    return "%d 分" % (rest // 60)


def _run_json_powershell(script):
    try:
        raw = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                             capture_output=True, timeout=30, **win_no_console()).stdout
    except Exception:
        return {}
    text = raw.decode("utf-8", "ignore").strip()
    if not text.startswith("{"):
        return {}
    try:
        import json
        return json.loads(text)
    except ValueError:
        return {}


def _as_list(value):
    """CIM 只查回一条时 PowerShell 给对象而不是数组。"""
    if not value:
        return []
    return value if isinstance(value, list) else [value]


def _windows_uptime_seconds():
    try:
        import ctypes
        return ctypes.windll.kernel32.GetTickCount64() // 1000
    except Exception:
        return None


def _windows_reg_value(path, name):
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
            return winreg.QueryValueEx(key, name)[0]
    except (OSError, ValueError, ImportError):
        return None


def _windows_core_counts():
    """物理核 / 逻辑核；Windows 7 以后 GetLogicalProcessorInformationEx 都能用。"""
    threads = os.cpu_count()
    try:
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.windll.kernel32
        length = wintypes.DWORD(0)
        relation_processor_core = 0
        kernel32.GetLogicalProcessorInformationEx(relation_processor_core, None, ctypes.byref(length))
        if not length.value:
            return None, threads
        buffer = (ctypes.c_byte * length.value)()
        if not kernel32.GetLogicalProcessorInformationEx(relation_processor_core, buffer,
                                                        ctypes.byref(length)):
            return None, threads
        cores, offset = 0, 0
        while offset + 8 <= length.value:
            relationship = ctypes.c_uint.from_buffer(buffer, offset).value
            size = ctypes.c_uint.from_buffer(buffer, offset + 4).value
            if size <= 0:
                break
            if relationship == relation_processor_core:
                cores += 1
            offset += size
        return (cores or None), threads
    except Exception:
        return None, threads


def _windows_cpu_info():
    """注册表拿型号与频率，速度远快于 Win32_Processor。"""
    path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
    name = (_windows_reg_value(path, "ProcessorNameString") or "").strip()
    try:
        mhz = int(_windows_reg_value(path, "~MHz"))
    except (TypeError, ValueError):
        mhz = None
    cores, threads = _windows_core_counts()
    return name, cores, threads, mhz


def _windows_vram_sizes():
    """WMI 的 AdapterRAM 超过 4GB 就截断，真实显存在显卡驱动注册表里。"""
    sizes = {}
    base = (r"SYSTEM\CurrentControlSet\Control\Class"
            r"\{4d36e968-e325-11ce-bfc1-08002be10318}")
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as root:
            for index in range(64):
                try:
                    subkey = winreg.EnumKey(root, index)
                except OSError:
                    break
                try:
                    with winreg.OpenKey(root, subkey) as key:
                        desc = str(winreg.QueryValueEx(key, "DriverDesc")[0]).strip().lower()
                        raw = winreg.QueryValueEx(key, "HardwareInformation.qwMemorySize")[0]
                except (OSError, ValueError):
                    continue
                try:
                    sizes[desc] = int(raw)
                except (TypeError, ValueError):
                    continue
    except (OSError, ImportError):
        pass
    return sizes


def _windows_resolution():
    try:
        import ctypes
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        return "%d x %d" % (user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))
    except Exception:
        return "--"


def _first_ip(addresses, ipv6=False):
    """CIM 返回的 IPAddress 里既有 IPv4 也有 fe80 链接本地地址，挑能用的那条。"""
    for address in _as_list(addresses):
        text = str(address or "").strip().split("%")[0]
        if not text:
            continue
        is_v6 = ":" in text
        if is_v6 != ipv6:
            continue
        if ipv6 and text.lower().startswith(("fe80", "fe", "::")):
            continue
        return text
    return ""


_WINDOWS_SYSTEM_TYPE = {
    "x64-based PC": "64 位电脑（x64）",
    "X86-based PC": "32 位电脑（x86）",
}



_MEDIA_TYPE_TEXT = {3: "机械硬盘", 4: "固态硬盘", 5: "存储级内存"}
_BUS_TYPE_TEXT = {
    1: "SCSI", 3: "ATA", 7: "USB", 8: "RAID", 9: "iSCSI", 10: "SAS",
    11: "SATA", 12: "SD", 14: "虚拟", 16: "存储空间", 17: "NVMe",
}


def _resolution_text(text):
    """WMI 的分辨率尾巴带颜色数（"2560 x 1440 x 4294967296 种颜色"），只留尺寸。"""
    match = re.search(r"(\d+)\s*x\s*(\d+)", text or "")
    return "%s x %s" % (match.group(1), match.group(2)) if match else (text or "--")


def _windows_sections():
    data = _run_json_powershell(_WINDOWS_INFO_SCRIPT)
    computer = data.get("computer") or {}
    system = data.get("os") or {}
    modules = _as_list(data.get("memory"))
    disks = _as_list(data.get("disks"))
    volumes = _as_list(data.get("volumes"))
    gpus = _as_list(data.get("gpu"))
    networks = _as_list(data.get("net"))
    ip, mac, adapter = get_effective_ip()
    mem = _windows_memory()
    cpu_name, cores, threads, mhz = _windows_cpu_info()
    vram_sizes = _windows_vram_sizes()

    device_rows = [
        ("电脑名称", _machine_name()),
        ("制造商", computer.get("Manufacturer") or "--"),
        ("设备型号", computer.get("Model") or "--"),
        ("计算机类型", _WINDOWS_SYSTEM_TYPE.get(computer.get("SystemType") or "",
                                          computer.get("SystemType") or "--")),
        ("操作系统", (system.get("Caption") or "").strip() or "--"),
        ("系统版本", "%s（内部版本 %s）" % (system.get("Version") or "--",
                                    system.get("BuildNumber") or "--")),
        ("系统架构", system.get("OSArchitecture") or platform.machine() or "--"),
    ]

    cpu_rows = [
        ("处理器", cpu_name or "--"),
        ("核心 / 线程", "%s 核 / %s 线程" % (cores or "--", threads or "--")),
        ("基准频率", "%s MHz" % mhz if mhz else "--"),
        ("架构", platform.machine() or "--"),
    ]

    memory_rows = []
    if mem is None:
        memory_rows.append(("总容量", "--"))
    else:
        pct, used_gb, total_gb = mem
        memory_rows += [
            ("总容量", "%.1f GB" % total_gb),
            ("已用 / 可用", "%.1f GB / %.1f GB（%.0f%%）" % (used_gb, total_gb - used_gb, pct)),
        ]
    for index, module in enumerate(modules, 1):
        speed = module.get("ConfiguredClockSpeed") or module.get("Speed")
        detail = " · ".join(part for part in (
            _gb_text(module.get("Capacity")), "%s MHz" % speed if speed else "",
            module.get("DeviceLocator") or "", (module.get("Manufacturer") or "").strip()) if part)
        memory_rows.append(("内存条 %d" % index, detail or "--"))

    physical = _as_list(data.get("physical"))

    storage_rows = []
    for disk in physical or disks:
        name = (disk.get("FriendlyName") or disk.get("Model") or "").strip()
        media = _MEDIA_TYPE_TEXT.get(disk.get("MediaType")) or ""
        bus = _BUS_TYPE_TEXT.get(disk.get("BusType")) or (disk.get("InterfaceType") or "")
        detail = " · ".join(part for part in (
            name, _gb_text(disk.get("Size")), media, bus) if part)
        storage_rows.append(("物理磁盘", detail or "--"))
    for volume in volumes:
        try:
            size, free = int(volume.get("Size") or 0), int(volume.get("FreeSpace") or 0)
        except (TypeError, ValueError):
            size = free = 0
        used_pct = (1 - free / size) * 100 if size else 0
        name = volume.get("VolumeName") or "本地磁盘"
        drive = (volume.get("DeviceID") or "").rstrip(":")
        storage_rows.append(("%s 盘" % drive if drive else "分区",
                             "%s · 共 %s · 可用 %s（已用 %.0f%%）" % (
                                 name, _gb_text(size), _gb_text(free), used_pct)))
    if not storage_rows:
        storage_rows.append(("存储", "--"))

    # 远程 / 虚拟显示适配器排到最后，只占一行，别把真显卡挤下去
    real_gpus, virtual_gpus = [], []
    for gpu in gpus:
        name = (gpu.get("Name") or "").strip()
        lowered = name.lower()
        if any(word in lowered for word in ("virtual", "todesk", "remote", "mirror", "基本显示")):
            virtual_gpus.append(name or "未命名")
        else:
            real_gpus.append(gpu)
    gpu_rows = []
    for index, gpu in enumerate(real_gpus, 1):
        suffix = " %d" % index if len(real_gpus) > 1 else ""
        name = (gpu.get("Name") or "").strip()
        vram = vram_sizes.get(name.lower()) or 0
        gpu_rows.append(("显卡" + suffix, name or "--"))
        gpu_rows.append(("显存" + suffix, _gb_text(vram) if vram else "--"))
        gpu_rows.append(("驱动" + suffix, gpu.get("DriverVersion") or "--"))
    if virtual_gpus:
        gpu_rows.append(("虚拟显示", "、".join(virtual_gpus)))
    gpu_rows.append(("当前分辨率", _windows_resolution()))
    if not gpu_rows:
        gpu_rows.append(("显卡", "--"))

    # 主网卡取有默认网关的那块，VMware / Hyper-V 的虚拟网卡归到「其它网卡」
    primary = next((n for n in networks if _first_ip(n.get("DefaultIPGateway"))), None) or \
        (networks[0] if networks else {})
    primary_ip = _first_ip(primary.get("IPAddress"))
    net_rows = [
        ("IPv4 地址", primary_ip or ip),
        ("MAC 地址", (primary.get("MACAddress") or mac or "--").replace("-", ":").upper()),
        ("网卡", primary.get("Description") or adapter or "--"),
    ]
    ipv6 = _first_ip(primary.get("IPAddress"), ipv6=True)
    if ipv6:
        net_rows.append(("IPv6 地址", ipv6))
    gateway = _first_ip(primary.get("DefaultIPGateway"))
    if gateway:
        net_rows.append(("默认网关", gateway))
    others = [n for n in networks if n is not primary]
    if others:
        net_rows.append(("其它网卡", "、".join(
            "%s（%s）" % ((n.get("Description") or "?").split(" - ")[0],
                          _first_ip(n.get("IPAddress")) or "-")
            for n in others)))

    return [
        ("设备与系统", device_rows),
        ("处理器", cpu_rows),
        ("内存", memory_rows),
        ("存储", storage_rows),
        ("显卡", gpu_rows),
        ("网络", net_rows),
    ]


def _mac_sysctl(name):
    try:
        return subprocess.check_output(["sysctl", "-n", name], text=True, timeout=8).strip()
    except Exception:
        return ""


def _mac_profiler(profile):
    try:
        return subprocess.check_output(["system_profiler", profile], text=True,
                                       errors="ignore", timeout=25)
    except Exception:
        return ""


def _mac_display_rows():
    text = _mac_profiler("SPDisplaysDataType")
    rows, name, cores, vram, resolution = [], "", "", "", ""
    for line in text.splitlines():
        item = line.strip()
        if item.startswith("Chipset Model:"):
            name = item.split(":", 1)[1].strip()
        elif item.startswith("Total Number of Cores:"):
            cores = item.split(":", 1)[1].strip()
        elif item.startswith("Resolution:"):
            resolution = item.split(":", 1)[1].strip() or resolution
        elif item.startswith("VRAM"):
            vram = item.split(":", 1)[1].strip()
    if name:
        rows.append(("显卡", name))
    if cores:
        rows.append(("GPU 核心数", cores))
    if vram:
        rows.append(("显存", vram))
    rows.append(("分辨率", resolution or "--"))
    return rows or [("显卡", "--")]


def _mac_storage_rows():
    rows = []
    try:
        output = subprocess.check_output(["df", "-k"], text=True, errors="ignore", timeout=15)
    except Exception:
        output = ""
    for line in output.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 6:
            continue
        mount = parts[-1]
        if mount != "/" and not mount.startswith("/Volumes/"):
            continue
        try:
            total, free = int(parts[1]) * 1024, int(parts[3]) * 1024
        except (ValueError, IndexError):
            continue
        used_pct = (1 - free / total) * 100 if total else 0
        label = "系统盘" if mount == "/" else os.path.basename(mount)
        rows.append((label, "共 %s · 可用 %s（已用 %.0f%%）" % (
            _gb_text(total), _gb_text(free), used_pct)))
    return rows or [("存储", "--")]


def _machine_name():
    """电脑名称：macOS 优先用 scutil 的 ComputerName（就是「关于本机」里那个），
    Windows 用主机名；platform.node() 在 mac 上会带 .local 后缀，去掉更像人话。"""
    if platform.system() == "Darwin":
        try:
            name = subprocess.run(["scutil", "--get", "ComputerName"], capture_output=True,
                                  text=True, timeout=5).stdout.strip()
            if name:
                return name
        except Exception:
            pass
    name = platform.node() or ""
    if name.lower().endswith(".local"):
        name = name[:-6]
    return name or "--"


def _mac_uptime_seconds():
    raw = _mac_sysctl("kern.boottime")
    match = re.search(r"sec\s*=\s*(\d+)", raw)
    if not match:
        return None
    return max(0, int(time.time()) - int(match.group(1)))


def _mac_sections():
    model = _mac_sysctl("hw.model")
    chip = _mac_sysctl("machdep.cpu.brand_string")
    physical = _mac_sysctl("hw.physicalcpu")
    logical = _mac_sysctl("hw.logicalcpu") or (os.cpu_count() or "")
    memory_total = _mac_sysctl("hw.memsize")
    version = platform.mac_ver()[0] or platform.release()
    ip, mac, adapter = get_effective_ip()
    stats = get_system_stats()

    memory_rows = []
    if memory_total:
        memory_rows.append(("总容量", _gb_text(memory_total)))
    if stats[1] is not None:
        memory_rows.append(("已用 / 可用", "%.1f GB / %.1f GB（%.0f%%）" % (
            stats[2], stats[3] - stats[2], stats[1])))
    memory_type = ""
    profiler = _mac_profiler("SPMemoryDataType")
    match = re.search(r"Type:\s*(\S.*)", profiler)
    if match:
        memory_type = match.group(1).strip()
    if memory_type:
        memory_rows.append(("内存类型", memory_type))
    if not memory_rows:
        memory_rows.append(("总容量", "--"))

    return [
        ("设备与系统", [
            ("电脑名称", _machine_name()),
            ("设备型号", model or "--"),
            ("操作系统", "macOS %s" % version),
            ("系统架构", platform.machine() or "--"),
            ("芯片", chip or "--"),
        ]),
        ("处理器", [
            ("处理器", chip or "--"),
            ("核心 / 线程", "%s 核 / %s 线程" % (physical or "--", logical or "--")),
            ("架构", platform.machine() or "--"),
        ]),
        ("内存", memory_rows),
        ("存储", _mac_storage_rows()),
        ("显卡", _mac_display_rows()),
        ("网络", [
            ("IPv4 地址", ip),
            ("MAC 地址", (mac or "--").upper()),
            ("网卡", adapter or "--"),
        ]),
    ]


def _runtime_rows():
    from toolbox_app.constants import APP_VERSION
    uptime = _windows_uptime_seconds() if platform.system() == "Windows" else _mac_uptime_seconds()
    return [
        ("应用版本", "v" + APP_VERSION),
        ("Python", platform.python_version()),
        ("进程位数", "%d 位" % (struct.calcsize("P") * 8)),
        ("已运行", _uptime_text(uptime)),
        ("采集时间", time.strftime("%Y-%m-%d %H:%M:%S")),
    ]


def collect_system_info(force=False):
    """分类系统信息：[(分组标题, [(项目, 值), ...]), ...]，只读当前这台电脑。

    结果缓存两分钟，点「刷新」才重新采；Windows 那次 CIM 查询要一两秒，
    缓存能让同一个窗口里来回切分类不卡。
    """
    now = time.time()
    cached = _info_cache["sections"]
    if not force and cached and now - _info_cache["at"] < INFO_CACHE_SECONDS:
        return cached
    try:
        sections = _windows_sections() if platform.system() == "Windows" else _mac_sections()
    except Exception:
        sections = [("设备与系统", [("电脑名称", _machine_name())])]
    try:
        sections = sections + [("运行环境", _runtime_rows())]
    except Exception:
        pass
    _info_cache["at"] = now
    _info_cache["sections"] = sections
    return sections
