import time
import subprocess
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import psutil

def get_cpu_temperature() -> Optional[float]:
    """
    Возвращает актуальную температуру процессора в градусах Цельсия (°C).
    Использует:
    1. psutil.sensors_temperatures (если доступно)
    2. WMI ThermalZoneInformation (HighPrecisionTemperature в десикельвинах)
    3. WMI MSAcpi_ThermalZoneTemperature
    """
    # 1. psutil
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for _, entries in temps.items():
                for e in entries:
                    if e.current and e.current > 0:
                        return round(float(e.current), 1)
    except Exception:
        pass

    # 2. WMI ThermalZoneInformation
    try:
        cmd = [
            "powershell", "-NoProfile", "-Command",
            "(Get-CimInstance -ClassName Win32_PerfFormattedData_Counters_ThermalZoneInformation -ErrorAction SilentlyContinue).HighPrecisionTemperature"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5, creationflags=0x08000000)
        out = res.stdout.strip()
        if out:
            # Преобразование из десикельвинов: (T - 2732) / 10
            # Например 3252 -> (3252 - 2732) / 10 = 52.0 °C
            vals = [float(x) for x in out.split() if x.replace('.', '', 1).isdigit()]
            if vals:
                celsius = (vals[0] - 2732.0) / 10.0
                if 20.0 <= celsius <= 115.0:
                    return round(celsius, 1)
    except Exception:
        pass

    # 3. WMI MSAcpi_ThermalZoneTemperature
    try:
        cmd2 = [
            "powershell", "-NoProfile", "-Command",
            "(Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue).CurrentTemperature"
        ]
        res2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=5, creationflags=0x08000000)
        out2 = res2.stdout.strip()
        if out2:
            vals2 = [float(x) for x in out2.split() if x.replace('.', '', 1).isdigit()]
            if vals2:
                celsius2 = (vals2[0] - 2732.0) / 10.0
                if 20.0 <= celsius2 <= 115.0:
                    return round(celsius2, 1)
    except Exception:
        pass

    return None

def get_system_metrics() -> Dict[str, Any]:
    """
    Возвращает актуальную информацию о загрузке ЦП, температуре, ОЗУ, дисков и времени работы ПК.
    """
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_count_logical = psutil.cpu_count(logical=True)
    cpu_count_physical = psutil.cpu_count(logical=False)
    temp_celsius = get_cpu_temperature()
    
    # RAM
    ram = psutil.virtual_memory()
    
    # Диски (основные разделы)
    disks = []
    for part in psutil.disk_partitions(all=False):
        if "cdrom" in part.opts or part.fstype == "":
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "total_gb": round(usage.total / (1024 ** 3), 1),
                "used_gb": round(usage.used / (1024 ** 3), 1),
                "free_gb": round(usage.free / (1024 ** 3), 1),
                "percent": usage.percent,
            })
        except PermissionError:
            continue

    # Uptime
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime_seconds = int(time.time() - psutil.boot_time())
    uptime_str = str(timedelta(seconds=uptime_seconds))

    return {
        "cpu_percent": cpu_percent,
        "cpu_temp": temp_celsius,
        "cpu_cores": f"{cpu_count_physical} физ. / {cpu_count_logical} лог.",
        "ram_total_mb": ram.total // (1024 ** 2),
        "ram_used_mb": ram.used // (1024 ** 2),
        "ram_percent": ram.percent,
        "disks": disks,
        "uptime": uptime_str,
        "boot_time": boot_time.strftime("%Y-%m-%d %H:%M:%S")
    }

def get_top_processes(limit: int = 10, sort_by: str = "memory") -> List[Dict[str, Any]]:
    """
    Возвращает топ процессов по потреблению памяти или процессора.
    """
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info']):
        try:
            info = proc.info
            mem_mb = (info['memory_info'].rss / (1024 * 1024)) if info.get('memory_info') else 0
            processes.append({
                "pid": info['pid'],
                "name": info['name'] or "Unknown",
                "cpu_percent": info['cpu_percent'] or 0.0,
                "memory_percent": round(info['memory_percent'] or 0.0, 1),
                "memory_mb": round(mem_mb, 1)
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if sort_by == "cpu":
        processes.sort(key=lambda x: x["cpu_percent"], reverse=True)
    else:
        processes.sort(key=lambda x: x["memory_mb"], reverse=True)

    return processes[:limit]

def kill_process_by_pid(pid: int) -> bool:
    """Завершает процесс по PID."""
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        gone, alive = psutil.wait_procs([proc], timeout=3)
        if alive:
            for p in alive:
                p.kill()
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False
