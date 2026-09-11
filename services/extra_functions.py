"""
Дополнительные системные функции для Jarvis.
Содержит: сеть, IP, ping, буфер, аккумулятор, яркость, клавиатурная подсветка,
монитор вкл/выкл, очистка корзины, размер папок, поиск файлов, быстрые запуски.
"""
import os
import socket
import subprocess
import ctypes
import logging
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger("jarvis")

# ─────────────────────────────────────────────────────────
# СЕТЬ
# ─────────────────────────────────────────────────────────

def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "Не удалось определить"


def get_public_ip() -> str:
    try:
        import urllib.request
        with urllib.request.urlopen("https://api.ipify.org", timeout=5) as r:
            return r.read().decode().strip()
    except Exception as e:
        return f"Ошибка: {e}"


def ping_host(host: str = "8.8.8.8") -> str:
    try:
        result = subprocess.run(
            ["ping", "-n", "3", host],
            capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.strip().split("\n")
        # Берём строку со статистикой
        for line in lines:
            if "среднее" in line.lower() or "average" in line.lower() or "avg" in line.lower():
                return line.strip()
        # Если не нашли — вернуть последние строки
        return "\n".join(lines[-3:]) if lines else "Нет ответа"
    except Exception as e:
        return f"Ошибка ping: {e}"


def get_network_adapters() -> str:
    try:
        import psutil
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        lines = []
        for iface, addr_list in addrs.items():
            st = stats.get(iface)
            status = "🟢" if (st and st.isup) else "🔴"
            for addr in addr_list:
                if addr.family == socket.AF_INET:
                    lines.append(f"{status} {iface}: {addr.address}")
                    break
        return "\n".join(lines) if lines else "Нет адаптеров"
    except Exception as e:
        return f"Ошибка: {e}"


def get_wifi_networks() -> str:
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "networks"],
            capture_output=True, text=True, encoding="cp1251", timeout=10
        )
        lines = result.stdout.strip().split("\n")
        networks = [l.strip() for l in lines if "SSID" in l and "BSSID" not in l]
        return "\n".join(networks[:10]) if networks else "Wi-Fi сети не найдены"
    except Exception as e:
        return f"Ошибка: {e}"


# ─────────────────────────────────────────────────────────
# БУФЕР ОБМЕНА
# ─────────────────────────────────────────────────────────

def get_clipboard() -> str:
    try:
        import pyperclip
        text = pyperclip.paste()
        if not text:
            return "(Буфер обмена пуст)"
        if len(text) > 500:
            return text[:500] + "...\n_(обрезано)_"
        return text
    except Exception as e:
        return f"Ошибка чтения буфера: {e}"


def set_clipboard(text: str) -> str:
    try:
        import pyperclip
        pyperclip.copy(text)
        return "✅ Текст скопирован в буфер обмена"
    except Exception as e:
        return f"Ошибка: {e}"


# ─────────────────────────────────────────────────────────
# АККУМУЛЯТОР
# ─────────────────────────────────────────────────────────

def get_battery_info() -> str:
    try:
        import psutil
        batt = psutil.sensors_battery()
        if batt is None:
            return "🔌 Аккумулятор не обнаружен (стационарный ПК или не поддерживается)"
        status = "🔌 Заряжается" if batt.power_plugged else "🔋 На батарее"
        secs = batt.secsleft
        if secs == psutil.POWER_TIME_UNLIMITED:
            time_left = "(заряжен)"
        elif secs == psutil.POWER_TIME_UNKNOWN or secs < 0:
            time_left = "(неизвестно)"
        else:
            h, m = divmod(secs // 60, 60)
            time_left = f"{h}ч {m}мин"
        return f"🔋 *Аккумулятор:* {batt.percent:.0f}%\n{status}\n⏱ Осталось: {time_left}"
    except Exception as e:
        return f"Ошибка: {e}"


# ─────────────────────────────────────────────────────────
# МОНИТОР
# ─────────────────────────────────────────────────────────

def turn_off_monitor():
    """Выключает монитор (он включится от движения мыши)."""
    ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)


def get_screen_resolution() -> str:
    try:
        w = ctypes.windll.user32.GetSystemMetrics(0)
        h = ctypes.windll.user32.GetSystemMetrics(1)
        return f"🖥 Разрешение: {w}×{h}"
    except Exception as e:
        return f"Ошибка: {e}"


# ─────────────────────────────────────────────────────────
# КЛАВИАТУРНАЯ ПОДСВЕТКА
# ─────────────────────────────────────────────────────────

def toggle_keyboard_backlight() -> str:
    """Переключает подсветку клавиатуры (через F5/Fn+F5 на ноутбуках — зависит от производителя)."""
    try:
        import pyautogui
        # Большинство ноутбуков: Fn+F5 или Fn+Space
        pyautogui.hotkey("fn", "f5")
        return "💡 Попытка переключения подсветки выполнена (Fn+F5)"
    except Exception:
        # Альтернатива через SetConsoleCP — не работает для всех
        return "⚠️ Управление подсветкой зависит от производителя ноутбука.\nПопробуйте Fn+F5 или Fn+Space вручную."


# ─────────────────────────────────────────────────────────
# ФАЙЛЫ И КОРЗИНА
# ─────────────────────────────────────────────────────────

def empty_recycle_bin() -> str:
    """Очищает корзину Windows."""
    try:
        import winshell
        winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
        return "🗑 Корзина успешно очищена."
    except ImportError:
        # Альтернатива без winshell
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                capture_output=True, text=True, timeout=15
            )
            return "🗑 Корзина очищена (PowerShell)."
        except Exception as e:
            return f"Ошибка очистки корзины: {e}"
    except Exception as e:
        return f"Ошибка: {e}"


def get_desktop_folder_sizes() -> str:
    """Возвращает размеры папок на Рабочем столе."""
    desktop = Path.home() / "Desktop"
    if not desktop.exists():
        return "Рабочий стол не найден"
    lines = []
    try:
        items = sorted(desktop.iterdir())
        for item in items[:15]:
            if item.is_dir():
                try:
                    size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                    lines.append(f"📁 {item.name}: {size / (1024**2):.1f} МБ")
                except Exception:
                    lines.append(f"📁 {item.name}: (нет доступа)")
            else:
                try:
                    size = item.stat().st_size
                    lines.append(f"📄 {item.name}: {size / 1024:.0f} КБ")
                except Exception:
                    pass
    except Exception as e:
        return f"Ошибка: {e}"
    return "\n".join(lines) if lines else "Рабочий стол пуст"


def search_files(query: str, search_dir: Optional[str] = None) -> str:
    """Поиск файлов по имени на Рабочем столе или в указанной папке."""
    base = Path(search_dir) if search_dir else Path.home() / "Desktop"
    results = []
    try:
        for p in base.rglob(f"*{query}*"):
            results.append(str(p))
            if len(results) >= 10:
                break
    except Exception as e:
        return f"Ошибка поиска: {e}"
    if not results:
        return f"🔍 По запросу «{query}» ничего не найдено в {base}"
    return "🔍 Найдено:\n" + "\n".join(results)


def get_downloads_list() -> str:
    """Показывает последние 10 файлов в папке Загрузки."""
    downloads = Path.home() / "Downloads"
    if not downloads.exists():
        return "Папка Загрузки не найдена"
    try:
        files = sorted(downloads.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)
        lines = []
        for f in files[:10]:
            size_kb = f.stat().st_size // 1024
            icon = "📁" if f.is_dir() else "📄"
            lines.append(f"{icon} {f.name} ({size_kb} КБ)")
        return "\n".join(lines) if lines else "Папка Загрузки пуста"
    except Exception as e:
        return f"Ошибка: {e}"


# ─────────────────────────────────────────────────────────
# БЫСТРЫЙ ЗАПУСК ПРИЛОЖЕНИЙ
# ─────────────────────────────────────────────────────────

QUICK_APPS = {
    "chrome":       r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "telegram":     str(Path.home() / "AppData/Roaming/Telegram Desktop/Telegram.exe"),
    "vscode":       str(Path.home() / "AppData/Local/Programs/Microsoft VS Code/Code.exe"),
    "explorer":     "explorer.exe",
    "calc":         "calc.exe",
    "notepad":      "notepad.exe",
    "taskmgr":      "taskmgr.exe",
    "mspaint":      "mspaint.exe",
    "regedit":      "regedit.exe",
    "cmd":          "cmd.exe",
    "powershell":   "powershell.exe",
    "control":      "control.exe",
    "defender":     "windowsdefender://",
    "youtube":      "https://www.youtube.com",
}


def quick_launch(app_key: str) -> str:
    path = QUICK_APPS.get(app_key.lower())
    if not path:
        return f"⚠️ Приложение '{app_key}' не найдено в списке быстрого запуска"
    try:
        if path.startswith("http") or path.startswith("windowsdefender"):
            os.startfile(path)
        elif os.path.exists(path):
            subprocess.Popen([path])
        else:
            # Попробуем как системную команду
            subprocess.Popen(path, shell=True)
        return f"✅ Запущено: {app_key}"
    except Exception as e:
        return f"❌ Ошибка запуска: {e}"


# ─────────────────────────────────────────────────────────
# WINDOWS ИНСТРУМЕНТЫ
# ─────────────────────────────────────────────────────────

def open_task_scheduler() -> str:
    try:
        subprocess.Popen("taskschd.msc", shell=True)
        return "✅ Планировщик задач открыт"
    except Exception as e:
        return f"Ошибка: {e}"


def open_device_manager() -> str:
    try:
        subprocess.Popen("devmgmt.msc", shell=True)
        return "✅ Диспетчер устройств открыт"
    except Exception as e:
        return f"Ошибка: {e}"


def open_event_viewer() -> str:
    try:
        subprocess.Popen("eventvwr.msc", shell=True)
        return "✅ Просмотр событий открыт"
    except Exception as e:
        return f"Ошибка: {e}"


def do_not_disturb_mode() -> str:
    """Включает/выключает режим 'Не беспокоить' через Focus Assist."""
    try:
        # Через реестр меняем режим фокуса
        result = subprocess.run(
            ["powershell", "-Command",
             "$path='HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings'; "
             "$current = (Get-ItemProperty -Path $path -Name NOC_GLOBAL_SETTING_TOASTS_ENABLED -ErrorAction SilentlyContinue).NOC_GLOBAL_SETTING_TOASTS_ENABLED; "
             "if ($current -ne 0) { Set-ItemProperty -Path $path -Name NOC_GLOBAL_SETTING_TOASTS_ENABLED -Value 0; 'disabled' } "
             "else { Set-ItemProperty -Path $path -Name NOC_GLOBAL_SETTING_TOASTS_ENABLED -Value 1; 'enabled' }"],
            capture_output=True, text=True, timeout=10
        )
        state = result.stdout.strip()
        return "🔕 Уведомления ОТКЛЮЧЕНЫ" if state == "disabled" else "🔔 Уведомления ВКЛЮЧЕНЫ"
    except Exception as e:
        return f"Ошибка: {e}"
