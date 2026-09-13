import os
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
import psutil
import win32gui

logger = logging.getLogger("jarvis")

def check_system_thresholds(disk_threshold_gb: float = 10.0, cpu_threshold: float = 90.0, ram_threshold: float = 90.0) -> List[Dict[str, Any]]:
    """
    Проверяет пороговые значения системы и возвращает список проблем (для проактивных алертов).
    """
    alerts = []
    
    # 1. Проверка дисков
    for part in psutil.disk_partitions(all=False):
        if "cdrom" in part.opts or part.fstype == "":
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            free_gb = usage.free / (1024 ** 3)
            if free_gb < disk_threshold_gb:
                alerts.append({
                    "type": "disk",
                    "key": f"disk_low_{part.mountpoint}",
                    "msg": f"⚠️ На диске `{part.mountpoint}` осталось всего *{free_gb:.1f} ГБ* свободного места (порог: {disk_threshold_gb} ГБ)!"
                })
        except Exception:
            pass

    # 2. Проверка ОЗУ
    ram = psutil.virtual_memory()
    if ram.percent >= ram_threshold:
        alerts.append({
            "type": "ram",
            "key": "ram_high",
            "msg": f"🔥 Загрузка оперативной памяти достигла *{ram.percent}%* ({ram.used // (1024**2)} / {ram.total // (1024**2)} MB)!"
        })

    # 3. Проверка ЦП
    cpu = psutil.cpu_percent(interval=0.5)
    if cpu >= cpu_threshold:
        alerts.append({
            "type": "cpu",
            "key": "cpu_high",
            "msg": f"🔥 Загрузка процессора (CPU) критически высока: *{cpu}%*!"
        })

    return alerts

def find_hung_windows() -> List[Dict[str, Any]]:
    """
    Ищет зависшие приложения Windows с помощью Win32 API IsHungAppWindow.
    Возвращает hwnd, title и pid процесса (для возможности его убить).
    """
    import win32process
    hung_apps = []

    def enum_windows_callback(hwnd, extra):
        try:
            if win32gui.IsWindowVisible(hwnd) and win32gui.IsHungAppWindow(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    try:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    except Exception:
                        pid = None
                    hung_apps.append({
                        "hwnd": hwnd,
                        "title": title,
                        "pid": pid
                    })
        except Exception:
            pass
        return True

    try:
        win32gui.EnumWindows(enum_windows_callback, None)
    except Exception as e:
        logger.debug(f"EnumWindows ended: {e}")

    return hung_apps

def preview_and_cleanup_temp() -> Tuple[int, int]:
    """
    Очищает временные файлы Windows (%TEMP%).
    Возвращает (количество_удаленных_файлов, освобожденных_мегабайт).
    """
    temp_dir = Path(os.environ.get("TEMP", "C:\\Windows\\Temp"))
    deleted_files = 0
    freed_bytes = 0

    if not temp_dir.exists():
        return (0, 0)

    for item in temp_dir.glob("*"):
        try:
            if item.is_file() or item.is_symlink():
                size = item.stat().st_size
                item.unlink(missing_ok=True)
                deleted_files += 1
                freed_bytes += size
            elif item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
                deleted_files += 1
        except Exception:
            continue

    return (deleted_files, freed_bytes // (1024 * 1024))
