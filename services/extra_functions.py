"""
Расширенный набор рабочих функций Jarvis для Windows.
Каждая функция безопасна к исключениям и возвращает человекочитаемый текст.
"""
from __future__ import annotations

import base64
import ctypes
import hashlib
import io
import json
import logging
import os
import random
import re
import secrets
import shutil
import socket
import string
import subprocess
import tempfile
import time
import urllib.parse
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger("jarvis")

CREATE_NO_WINDOW = 0x08000000


def _run(cmd: list[str] | str, timeout: int = 20, shell: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        timeout=timeout,
        shell=shell,
        creationflags=CREATE_NO_WINDOW,
    )


def _decode(data: bytes) -> str:
    for enc in ("utf-8", "cp866", "cp1251"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", errors="replace")


@dataclass
class ExtraResult:
    success: bool
    text: str
    photo_bytes: Optional[bytes] = None
    photo_name: str = "image.png"
    extra: Dict[str, Any] = field(default_factory=dict)


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
        result = _run(["ping", "-n", "3", host], timeout=12)
        out = _decode(result.stdout)
        times = re.findall(r"(?:среднее|средняя|average|avg)\s*[=:]\s*(\d+)\s*(?:мс|ms)?", out, re.IGNORECASE)
        loss = re.findall(r"(\d+)%\s*(?:потерь|loss)", out, re.IGNORECASE)
        loss_val = f"{loss[0]}% потерь" if loss else "0% потерь"
        if times:
            return f"✅ Ответ от {host}: среднее {times[0]} мс ({loss_val})"
        times_all = re.findall(r"время[=\s]*(\d+)\s*мс|time[=<]\s*(\d+)\s*ms", out, re.IGNORECASE)
        nums = [int(a or b) for a, b in times_all if a or b]
        if nums:
            avg = sum(nums) // len(nums)
            return f"✅ Ответ от {host}: ~{avg} мс ({loss_val})"
        return f"Ответ от {host}:\n{out[-800:]}"
    except Exception as e:
        return f"Ошибка ping: {e}"


def traceroute_host(host: str = "8.8.8.8") -> str:
    try:
        result = _run(["tracert", "-d", "-h", "12", host], timeout=45)
        out = _decode(result.stdout)
        lines = [ln for ln in out.splitlines() if ln.strip()][:18]
        return "🛤 Трассировка:\n" + "\n".join(lines) if lines else "Нет данных traceroute"
    except Exception as e:
        return f"Ошибка traceroute: {e}"


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
        result = _run(["netsh", "wlan", "show", "networks"], timeout=10)
        out = _decode(result.stdout)
        ssids = []
        for line in out.splitlines():
            m = re.search(r"SSID\s+\d+\s*:\s*(.+)", line)
            if m:
                name = m.group(1).strip()
                if name:
                    ssids.append(f"📶 {name}")
        return "\n".join(ssids[:12]) if ssids else "Wi-Fi сети в радиусе не найдены"
    except Exception as e:
        return f"Ошибка: {e}"


def get_mac_and_hostname() -> str:
    host = socket.gethostname()
    mac = "н/д"
    try:
        import uuid as _uuid
        mac = ":".join(f"{(_uuid.getnode() >> ele) & 0xff:02x}" for ele in range(40, -8, -8))
    except Exception:
        pass
    return f"🖥 Имя ПК: `{host}`\n🔗 MAC: `{mac}`\n🏠 Локальный IP: `{get_local_ip()}`"


def flush_dns() -> str:
    try:
        r = _run(["ipconfig", "/flushdns"], timeout=10)
        return "✅ Кэш DNS очищен" if r.returncode == 0 else f"⚠️ flushdns: {_decode(r.stdout)[-300:]}"
    except Exception as e:
        return f"Ошибка: {e}"


def ipconfig_summary() -> str:
    try:
        r = _run(["ipconfig"], timeout=10)
        out = _decode(r.stdout)
        keep = []
        for ln in out.splitlines():
            if any(k in ln.lower() for k in ("адаптер", "adapter", "ipv4", "ipv6", "шлюз", "gateway", "маска", "subnet", "dns")):
                keep.append(ln.rstrip())
        return "🌐 ipconfig:\n" + "\n".join(keep[:40]) if keep else out[-1200:]
    except Exception as e:
        return f"Ошибка: {e}"


def speed_test() -> str:
    """Грубая оценка скорости: скачивание тестового файла ~1–5 МБ."""
    url = "https://speed.cloudflare.com/__down?bytes=2000000"
    try:
        import urllib.request
        t0 = time.perf_counter()
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = resp.read()
        dt = max(time.perf_counter() - t0, 0.001)
        mb = len(data) / (1024 * 1024)
        mbps = (len(data) * 8 / dt) / 1_000_000
        return f"⚡ Тест загрузки: {mb:.2f} МБ за {dt:.2f} с ≈ {mbps:.1f} Мбит/с (Cloudflare)"
    except Exception as e:
        return f"Не удалось измерить скорость: {e}"


# ─────────────────────────────────────────────────────────
# БУФЕР ОБМЕНА С ИСТОРИЕЙ
# ─────────────────────────────────────────────────────────

CLIPBOARD_HISTORY: list[str] = []

def record_clipboard_item(text: str):
    """Добавляет элемент в локальную историю буфера (до 15 элементов)."""
    global CLIPBOARD_HISTORY
    cleaned = (text or "").strip()
    if not cleaned:
        return
    if cleaned in CLIPBOARD_HISTORY:
        CLIPBOARD_HISTORY.remove(cleaned)
    CLIPBOARD_HISTORY.insert(0, cleaned)
    CLIPBOARD_HISTORY = CLIPBOARD_HISTORY[:15]

def get_clipboard() -> str:
    """Возвращает всю сохраненную историю буфера обмена, а не только последний фрагмент."""
    global CLIPBOARD_HISTORY
    try:
        import pyperclip
        cur = pyperclip.paste()
        if cur and cur.strip():
            record_clipboard_item(cur)
    except Exception:
        pass

    if not CLIPBOARD_HISTORY:
        return "(Буфер обмена пуст)"

    lines = [f"📋 *История буфера обмена (всего: {len(CLIPBOARD_HISTORY)}):*\n"]
    for i, item in enumerate(CLIPBOARD_HISTORY[:10], start=1):
        preview = item.replace("\r", "").replace("\n", " ")
        if len(preview) > 100:
            preview = preview[:100] + "..."
        lines.append(f"{i}. `{preview}`")
    
    # Добавляем полный последний текст в конце
    latest = CLIPBOARD_HISTORY[0]
    if len(latest) > 600:
        latest = latest[:600] + "\n...(обрезано)"
    lines.append(f"\n*Последний скопированный текст:*\n{latest}")

    return "\n".join(lines)


def set_clipboard(text: str) -> str:
    try:
        import pyperclip
        pyperclip.copy(text)
        record_clipboard_item(text)
        return "✅ Текст скопирован в буфер обмена"
    except Exception as e:
        return f"Ошибка: {e}"


# ─────────────────────────────────────────────────────────
# ПИТАНИЕ И ЭКРАН НОУТБУКА
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
        return f"🔋 Аккумулятор: {batt.percent:.0f}%\n{status}\n⏱ Осталось: {time_left}"
    except Exception as e:
        return f"Ошибка: {e}"


def get_screen_resolution() -> str:
    try:
        user32 = ctypes.windll.user32
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        vw = user32.GetSystemMetrics(78)
        vh = user32.GetSystemMetrics(79)
        n = user32.GetSystemMetrics(80)
        return f"🖥 Основной: {w}×{h}\n🖥 Виртуальный стол: {vw}×{vh}\n📺 Мониторов: {n}"
    except Exception as e:
        return f"Ошибка: {e}"


def get_idle_time() -> str:
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(info)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        millis = ctypes.windll.kernel32.GetTickCount() - info.dwTime
        sec = millis // 1000
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        return f"⏱ Простой ввода: {h}ч {m}мин {s}с"
    return "Не удалось узнать время простоя"


def hibernate_pc() -> str:
    try:
        _run(["shutdown", "/h"], timeout=5)
        return "💤 Команда гибернации отправлена"
    except Exception as e:
        return f"Ошибка гибернации: {e}"


def cancel_shutdown() -> str:
    r = _run(["shutdown", "/a"], timeout=5)
    if r.returncode == 0:
        return "✅ Запланированное выключение/перезагрузка отменены"
    return "⚠️ Нечего отменять или нет прав"


# ─────────────────────────────────────────────────────────
# КЛАВИАТУРНАЯ ПОДСВЕТКА (3 РЕЖИМА: ЯРКИЙ -> СРЕДНИЙ -> ВЫКЛ) ЧЕРЕЗ F11
# ─────────────────────────────────────────────────────────

KEYBOARD_BACKLIGHT_STATE = 0  # 0: Выкл/Начальный, 1: Яркий, 2: Средний, 3: Выключен

def toggle_keyboard_backlight() -> str:
    """
    Пытается переключить подсветку клавиатуры несколькими способами:
    1) эмуляция нажатия F11 через keybd_event (старый способ),
    2) эмуляция через SendInput (рекомендовано),
    3) если ни один способ не сработал — возвращает диагностическую подсказку.

    Замечание: многие ноутбуки требуют аппаратной клавиши Fn+F11 — её нельзя сэмулировать
    программно, поэтому в таких случаях функция вернёт подсказку пользователю.
    """
    global KEYBOARD_BACKLIGHT_STATE
    try:
        import ctypes
        from ctypes import wintypes

        # Попытка 1: keybd_event (на старых системах)
        try:
            VK_F11 = 0x7A
            KEYEVENTF_KEYUP = 0x0002
            ctypes.windll.user32.keybd_event(VK_F11, 0, 0, 0)
            time.sleep(0.05)
            ctypes.windll.user32.keybd_event(VK_F11, 0, KEYEVENTF_KEYUP, 0)
            used_method = "keybd_event"
        except Exception:
            used_method = None

        # Попытка 2: SendInput (более современный и надежный способ)
        if not used_method:
            try:
                # DEFINE TYPES
                class KEYBDINPUT(ctypes.Structure):
                    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", wintypes.ULONG_PTR)]

                class INPUT(ctypes.Structure):
                    _fields_ = [("type", wintypes.DWORD), ("ki", KEYBDINPUT)]

                SendInput = ctypes.windll.user32.SendInput
                # VK code for F11
                VK_F11 = 0x7A
                KEYEVENTF_KEYUP = 0x0002
                inp = INPUT()
                inp.type = 1  # INPUT_KEYBOARD
                inp.ki = KEYBDINPUT(VK_F11, 0, 0, 0, 0)
                SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
                time.sleep(0.03)
                inp.ki = KEYBDINPUT(VK_F11, 0, KEYEVENTF_KEYUP, 0, 0)
                SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
                used_method = "SendInput"
            except Exception:
                used_method = None

        # Если ни один метод не сработал — информируем
        if not used_method:
            return (
                "⚠️ Невозможно программно переключить подсветку клавиатуры на этом устройстве.\n"
                "Часто подсветка управляется аппаратной клавишей Fn+F11, её нельзя сэмулировать программно.\n"
                "Попробуйте нажать Fn+F11 вручную или используйте утилиту производителя ноутбука."
            )

        # Обновляем внутреннее состояние (эмуляция трёхпозиционного переключателя)
        KEYBOARD_BACKLIGHT_STATE = (KEYBOARD_BACKLIGHT_STATE % 3) + 1
        mode_names = {
            1: "1️⃣ Максимальная яркость (Яркий)",
            2: "2️⃣ Умеренная яркость (Менее яркий)",
            3: "3️⃣ Подсветка выключена"
        }
        name = mode_names.get(KEYBOARD_BACKLIGHT_STATE, f"Режим {KEYBOARD_BACKLIGHT_STATE}")
        return f"⌨ ({used_method}) Подсветка клавиатуры: *{name}*"
    except Exception as e:
        logger.exception("toggle_keyboard_backlight failure")
        return f"⚠️ Ошибка переключения подсветки: {e}"


def do_not_disturb_mode() -> str:
    """
    Включает или выключает режим «Тихий час / Не беспокоить» (Focus Assist) в Windows 10/11.
    """
    try:
        # Способ 1: через реестр уведомлений Windows
        ps_script = """
        $p = 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings'
        if (-not (Test-Path $p)) { New-Item -Path $p -Force | Out-Null }
        $v = (Get-ItemProperty -Path $p -Name NOC_GLOBAL_SETTING_TOASTS_ENABLED -ErrorAction SilentlyContinue).NOC_GLOBAL_SETTING_TOASTS_ENABLED
        if ($v -eq 0) {
            Set-ItemProperty -Path $p -Name NOC_GLOBAL_SETTING_TOASTS_ENABLED -Value 1 -Type DWord
            Write-Output 'ENABLED'
        } else {
            Set-ItemProperty -Path $p -Name NOC_GLOBAL_SETTING_TOASTS_ENABLED -Value 0 -Type DWord
            Write-Output 'DISABLED'
        }
        """
        res = _run(["powershell", "-NoProfile", "-Command", ps_script], timeout=10)
        out = _decode(res.stdout).strip().upper()
        if "DISABLED" in out:
            return "🔕 Режим «Тихий час» ВКЛЮЧЕН (системные всплывающие уведомления отключены)."
        else:
            return "🔔 Режим «Тихий час» ВЫКЛЮЧЕН (уведомления включены в обычном режиме)."
    except Exception as e:
        return f"Ошибка переключения режима «Тихий час»: {e}"


def toggle_dark_mode() -> str:
    try:
        import winreg
        path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE)
        try:
            current, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        except FileNotFoundError:
            current = 1
        new_val = 0 if int(current) == 1 else 1
        winreg.SetValueEx(key, "AppsUseLightTheme", 0, winreg.REG_DWORD, new_val)
        winreg.SetValueEx(key, "SystemUsesLightTheme", 0, winreg.REG_DWORD, new_val)
        winreg.CloseKey(key)
        return "🌙 Тёмная тема" if new_val == 0 else "☀️ Светлая тема"
    except Exception as e:
        return f"Ошибка смены темы: {e}"


def open_night_light() -> str:
    os.startfile("ms-settings:nightlight")
    return "🌙 Открыты настройки ночного света"


# ─────────────────────────────────────────────────────────
# ФАЙЛЫ И КОРЗИНА
# ─────────────────────────────────────────────────────────

def empty_recycle_bin() -> str:
    try:
        r = _run([
            "powershell", "-NoProfile", "-Command",
            "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"
        ], timeout=20)
        return "🗑 Корзина очищена." if r.returncode == 0 else "⚠️ Корзина: возможно уже пуста"
    except Exception as e:
        return f"Ошибка очистки корзины: {e}"


def recycle_bin_info() -> str:
    try:
        r = _run([
            "powershell", "-NoProfile", "-Command",
            "(New-Object -ComObject Shell.Application).NameSpace(10).Items() | Measure-Object | Select-Object -ExpandProperty Count"
        ], timeout=15)
        count = _decode(r.stdout).strip() or "?"
        return f"🗑 В корзине элементов: {count}"
    except Exception as e:
        return f"Ошибка: {e}"


def get_desktop_folder_sizes() -> str:
    desktop = Path.home() / "Desktop"
    if not desktop.exists():
        return "Рабочий стол не найден"
    lines = []
    try:
        for item in sorted(desktop.iterdir())[:15]:
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
    base = Path(search_dir) if search_dir else Path.home() / "Desktop"
    results = []
    try:
        for p in base.rglob(f"*{query}*"):
            results.append(str(p))
            if len(results) >= 12:
                break
    except Exception as e:
        return f"Ошибка поиска: {e}"
    if not results:
        return f"🔍 По запросу «{query}» ничего не найдено в {base}"
    return "🔍 Найдено:\n" + "\n".join(results)


def get_downloads_list() -> str:
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


def get_file_info(path: str) -> str:
    p = Path(os.path.expandvars(path))
    if not p.exists():
        return f"❌ Не найдено: {p}"
    st = p.stat()
    kind = "папка" if p.is_dir() else "файл"
    size = st.st_size
    from datetime import datetime
    mtime = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")
    return (
        f"📄 {p.name}\nТип: {kind}\nПуть: {p}\n"
        f"Размер: {size} байт ({size/1024:.1f} КБ)\nИзменён: {mtime}"
    )


def zip_path(source: str, destination: Optional[str] = None) -> str:
    src = Path(os.path.expandvars(source))
    if not src.exists():
        return f"❌ Нет такого пути: {src}"
    dest = Path(os.path.expandvars(destination)) if destination else src.with_suffix(".zip")
    if src.is_dir():
        archive = shutil.make_archive(str(dest.with_suffix("")), "zip", root_dir=src)
        return f"📦 Архив создан: {archive}"
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(src, src.name)
    return f"📦 Архив создан: {dest}"


def unzip_path(source: str, destination: Optional[str] = None) -> str:
    src = Path(os.path.expandvars(source))
    if not src.exists():
        return f"❌ Архив не найден: {src}"
    dest = Path(os.path.expandvars(destination)) if destination else src.with_suffix("")
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src, "r") as zf:
        zf.extractall(dest)
    return f"📂 Распаковано в: {dest}"


# ─────────────────────────────────────────────────────────
# БЫСТРЫЙ ЗАПУСК И WINDOWS
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
            subprocess.Popen([path], creationflags=CREATE_NO_WINDOW)
        else:
            subprocess.Popen(path, shell=True)
        return f"✅ Запущено: {app_key}"
    except Exception as e:
        return f"❌ Ошибка запуска: {e}"


def open_windows_tool(tool: str) -> str:
    mapping = {
        "task_scheduler": ("taskschd.msc", "Планировщик задач"),
        "device_manager": ("devmgmt.msc", "Диспетчер устройств"),
        "event_viewer": ("eventvwr.msc", "Просмотр событий"),
        "services": ("services.msc", "Службы"),
        "disk_cleanup": ("cleanmgr.exe", "Очистка диска"),
        "snipping": ("ms-screenclip:", "Ножницы"),
        "osk": ("osk.exe", "Экранная клавиатура"),
        "magnifier": ("magnify.exe", "Экранная лупа"),
        "sound": ("mmsys.cpl", "Параметры звука"),
        "display": ("ms-settings:display", "Параметры экрана"),
        "network": ("ms-settings:network", "Параметры сети"),
        "bluetooth": ("ms-settings:bluetooth", "Bluetooth"),
        "apps": ("ms-settings:appsfeatures", "Приложения"),
        "update": ("ms-settings:windowsupdate", "Центр обновления"),
    }
    key = (tool or "").strip().lower().replace(" ", "_")
    aliases = {
        "планировщик": "task_scheduler", "устройства": "device_manager",
        "события": "event_viewer", "службы": "services", "очистка": "disk_cleanup",
        "ножницы": "snipping", "клавиатура": "osk", "лупа": "magnifier",
        "звук": "sound", "экран": "display", "сеть": "network",
        "bluetooth": "bluetooth", "приложения": "apps", "обновления": "update",
    }
    key = aliases.get(key, key)
    item = mapping.get(key)
    if not item:
        os.startfile("ms-settings:")
        return "⚙️ Открыты параметры Windows"
    target, title = item
    try:
        os.startfile(target)
        return f"✅ Открыто: {title}"
    except Exception:
        subprocess.Popen(target, shell=True)
        return f"✅ Запущено: {title}"


def open_task_scheduler() -> str:
    return open_windows_tool("task_scheduler")


def open_device_manager() -> str:
    return open_windows_tool("device_manager")


def open_event_viewer() -> str:
    return open_windows_tool("event_viewer")


def restart_explorer() -> str:
    try:
        _run(["taskkill", "/f", "/im", "explorer.exe"], timeout=8)
        subprocess.Popen("explorer.exe", shell=True)
        return "🔄 Проводник перезапущен"
    except Exception as e:
        return f"Ошибка: {e}"


# ─────────────────────────────────────────────────────────
# ОКНА
# ─────────────────────────────────────────────────────────

def _enum_windows() -> list[tuple[int, str]]:
    import win32gui
    result = []

    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title.strip():
                result.append((hwnd, title))
        return True

    win32gui.EnumWindows(cb, None)
    return result


def list_open_windows() -> str:
    wins = _enum_windows()[:20]
    if not wins:
        return "Окна не найдены"
    return "🪟 Открытые окна:\n" + "\n".join(f"• {t}" for _, t in wins)


def get_active_window() -> str:
    try:
        import win32gui
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        return f"🎯 Активное окно: {title or '(без заголовка)'}"
    except Exception as e:
        return f"Ошибка: {e}"


def focus_window(query: str) -> str:
    try:
        import win32gui
        import win32con
        q = query.lower()
        for hwnd, title in _enum_windows():
            if q in title.lower():
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                return f"✅ На передний план: {title}"
        return f"⚠️ Окно «{query}» не найдено"
    except Exception as e:
        return f"Ошибка: {e}"


def show_desktop() -> str:
    import pyautogui
    pyautogui.hotkey("win", "d")
    return "🖥 Показан рабочий стол (Win+D)"


# ─────────────────────────────────────────────────────────
# ЖЕЛЕЗО / БЕЗОПАСНОСТЬ
# ─────────────────────────────────────────────────────────

def get_hardware_info() -> str:
    import psutil
    import platform
    cpu = platform.processor() or "н/д"
    cores = psutil.cpu_count(logical=True)
    freq = psutil.cpu_freq()
    freq_s = f"{freq.current:.0f} МГц" if freq else "н/д"
    ram = psutil.virtual_memory()
    gpu = "н/д"
    try:
        r = _run([
            "powershell", "-NoProfile", "-Command",
            "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"
        ], timeout=12)
        names = [ln.strip() for ln in _decode(r.stdout).splitlines() if ln.strip()]
        if names:
            gpu = ", ".join(names[:3])
    except Exception:
        pass
    return (
        f"🖥 ОС: {platform.platform()}\n"
        f"🧠 CPU: {cpu}\nЯдер: {cores}, частота: {freq_s}\n"
        f"💾 RAM: {ram.total // (1024**3)} ГБ ({ram.percent}%)\n"
        f"🎮 GPU: {gpu}"
    )


def list_usb_devices() -> str:
    try:
        r = _run([
            "powershell", "-NoProfile", "-Command",
            "Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match '^USB' } | Select-Object -ExpandProperty FriendlyName"
        ], timeout=20)
        names = sorted({ln.strip() for ln in _decode(r.stdout).splitlines() if ln.strip()})
        if not names:
            return "USB-устройства не найдены"
        return "🔌 USB:\n" + "\n".join(f"• {n}" for n in names[:25])
    except Exception as e:
        return f"Ошибка: {e}"


def list_printers() -> str:
    try:
        import win32print
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        printers = win32print.EnumPrinters(flags)
        names = [p[2] for p in printers if p[2]]
        default = win32print.GetDefaultPrinter()
        if not names:
            return "Принтеры не найдены"
        lines = [f"{'⭐' if n == default else '•'} {n}" for n in names]
        return "🖨 Принтеры:\n" + "\n".join(lines)
    except Exception as e:
        return f"Ошибка: {e}"


def list_startup_apps() -> str:
    import winreg
    names = []
    for hive, path in (
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
    ):
        try:
            key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
        except OSError:
            continue
        i = 0
        while True:
            try:
                n, v, _ = winreg.EnumValue(key, i)
                names.append(f"• {n}")
                i += 1
            except OSError:
                break
        winreg.CloseKey(key)
    startup = Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup"
    if startup.exists():
        for p in startup.iterdir():
            if p.suffix.lower() not in (".ini",):
                names.append(f"• {p.name} (Startup)")
    return "🚀 Автозагрузка:\n" + "\n".join(names[:30]) if names else "Список автозагрузки пуст"


def firewall_status() -> str:
    try:
        r = _run(["netsh", "advfirewall", "show", "allprofiles", "state"], timeout=10)
        out = _decode(r.stdout)
        states = re.findall(r"(Domain|Private|Public|Доменный|Частный|Общедоступный).{0,40}(ON|OFF|Вкл|Выкл)", out, re.I | re.S)
        if states:
            return "🛡 Брандмауэр:\n" + "\n".join(f"• {a}: {b}" for a, b in states[:6])
        return out[-800:] or "Нет данных брандмауэра"
    except Exception as e:
        return f"Ошибка: {e}"


def defender_status() -> str:
    try:
        r = _run([
            "powershell", "-NoProfile", "-Command",
            "Get-MpComputerStatus | Select-Object AMServiceEnabled,AntivirusEnabled,RealTimeProtectionEnabled,AntivirusSignatureLastUpdated | Format-List"
        ], timeout=15)
        return "🛡 Microsoft Defender:\n" + (_decode(r.stdout).strip() or "нет данных")
    except Exception as e:
        return f"Ошибка: {e}"


# ─────────────────────────────────────────────────────────
# УТИЛИТЫ
# ─────────────────────────────────────────────────────────

def generate_password(length: int = 16) -> str:
    length = max(8, min(64, int(length or 16)))
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    pwd = "".join(secrets.choice(alphabet) for _ in range(length))
    try:
        import pyperclip
        pyperclip.copy(pwd)
        extra = " (скопирован в буфер)"
    except Exception:
        extra = ""
    return f"🔐 Пароль{extra}: `{pwd}`"


def generate_uuid() -> str:
    return f"🆔 UUID: `{uuid.uuid4()}`"


def hash_text(text: str, algo: str = "sha256") -> str:
    algo = (algo or "sha256").lower()
    if algo not in hashlib.algorithms_available:
        algo = "sha256"
    h = hashlib.new(algo)
    h.update(text.encode("utf-8"))
    return f"#️⃣ {algo}: `{h.hexdigest()}`"


def base64_convert(text: str, mode: str = "encode") -> str:
    if (mode or "encode").lower() in ("decode", "декод", "расшифровать"):
        try:
            raw = base64.b64decode(text.encode("utf-8"), validate=False)
            return "🔓 Base64 decode:\n" + raw.decode("utf-8", errors="replace")[:1500]
        except Exception as e:
            return f"Ошибка decode: {e}"
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    return f"🔒 Base64 encode:\n`{encoded}`"


def random_util(kind: str = "number", min_value: int = 1, max_value: int = 100) -> str:
    k = (kind or "number").lower()
    if k in ("coin", "монета"):
        return "🪙 " + random.choice(["орёл", "решка"])
    if k in ("dice", "кубик"):
        return f"🎲 Выпало: {random.randint(1, 6)}"
    return f"🎲 Случайное число: {random.randint(int(min_value), int(max_value))}"


def get_datetime_info() -> str:
    from datetime import datetime
    now = datetime.now()
    return f"📅 {now.strftime('%A, %d.%m.%Y')}\n🕒 {now.strftime('%H:%M:%S')}"


def speak_text(text: str) -> str:
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 175)
        engine.say(text)
        engine.runAndWait()
        return f"🔊 Произнесено: {text[:120]}"
    except Exception:
        try:
            escaped = text.replace("'", "''")[:400]
            _run([
                "powershell", "-NoProfile", "-Command",
                f"Add-Type -AssemblyName System.Speech; "
                f"(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{escaped}')"
            ], timeout=30)
            return f"🔊 Произнесено (SAPI): {text[:120]}"
        except Exception as e:
            return f"Ошибка озвучки: {e}"


def generate_qr_png(data: str) -> ExtraResult:
    try:
        import qrcode
        img = qrcode.make(data)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return ExtraResult(True, f"📷 QR-код для: {data[:80]}", photo_bytes=buf.getvalue(), photo_name="qr.png")
    except Exception as e:
        return ExtraResult(False, f"Ошибка QR: {e}")


def set_wallpaper(path: str) -> str:
    p = Path(os.path.expandvars(path))
    if not p.exists() or p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".bmp"):
        return "❌ Укажите существующий файл изображения (.jpg/.png/.bmp)"
    SPI_SETDESKWALLPAPER = 20
    ok = ctypes.windll.user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, str(p), 3)
    return "✅ Обои рабочего стола обновлены" if ok else "⚠️ Windows не принял файл обоев"


# ─────────────────────────────────────────────────────────
# ТОП-50 ДОПОЛНИТЕЛЬНЫХ СИСТЕМНЫХ ФУНКЦИЙ И УТИЛИТ
# ─────────────────────────────────────────────────────────

def laptop_screen_sleep() -> str:
    """Переводит экран ноутбука в режим ожидания/сна для экономии энергии."""
    try:
        ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
        return "💻 Экран ноутбука переведен в режим энергосбережения (включится от любого касания клавиатуры или мыши)."
    except Exception as e:
        return f"Ошибка: {e}"

def set_power_plan(mode: str = "balanced") -> str:
    """
    Устанавливает схему питания ноутбука:
    - performance (высокая производительность)
    - balanced (сбалансированная)
    - saver (экономия энергии)
    """
    plans = {
        "performance": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
        "balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",
        "saver": "a1841308-3541-4fab-bc81-f71556f20b4a"
    }
    m = (mode or "balanced").lower()
    guid = plans.get(m, plans["balanced"])
    try:
        _run(["powercfg", "/setactive", guid], timeout=5)
        names = {"performance": "⚡ Максимальная производительность", "balanced": "⚖️ Сбалансированный режим", "saver": "🔋 Экономия энергии"}
        return f"🔋 Схема электропитания переключена на: {names.get(m, m)}"
    except Exception as e:
        return f"Ошибка смены схемы питания: {e}"

def get_battery_report() -> str:
    """Генерирует официальный HTML отчет об аккумуляторе ноутбука (емкость, износ, циклы)."""
    try:
        report_path = Path(os.environ.get("TEMP", "C:\\Windows\\Temp")) / "battery_report.html"
        _run(["powercfg", "/batteryreport", "/output", str(report_path)], timeout=15)
        if report_path.exists():
            return f"🔋 Отчет об аккумуляторе сформирован:\n`{report_path}`"
        return "⚠️ Не удалось создать отчет аккумулятора."
    except Exception as e:
        return f"Ошибка batteryreport: {e}"

def clear_browser_cache() -> str:
    """Очищает временные кэши Chrome, Edge и Яндекс Браузера."""
    user_local = Path(os.environ.get("LOCALAPPDATA", ""))
    cache_dirs = [
        user_local / "Google/Chrome/User Data/Default/Cache",
        user_local / "Google/Chrome/User Data/Default/Code Cache",
        user_local / "Microsoft/Edge/User Data/Default/Cache",
        user_local / "Yandex/YandexBrowser/User Data/Default/Cache",
    ]
    freed_bytes = 0
    count = 0
    for d in cache_dirs:
        if d.exists():
            try:
                for f in d.rglob("*"):
                    if f.is_file():
                        try:
                            s = f.stat().st_size
                            f.unlink()
                            freed_bytes += s
                            count += 1
                        except Exception:
                            pass
            except Exception:
                pass
    mb = freed_bytes / (1024 * 1024)
    return f"🧹 Очистка кэша браузеров: удалено {count} файлов, освобождено {mb:.1f} МБ."

def create_restore_point(description: str = "Jarvis Backup") -> str:
    """Создает контрольную точку восстановления системы Windows."""
    try:
        ps_cmd = f"Checkpoint-Computer -Description '{description}' -RestorePointType 'MODIFY_SETTINGS' -ErrorAction SilentlyContinue"
        _run(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=30)
        return f"🛡 Запрос на создание точки восстановления «{description}» выполнен."
    except Exception as e:
        return f"Ошибка точки восстановления: {e}"

def lock_windows_session() -> str:
    """Блокирует экран Windows (Win+L)."""
    try:
        ctypes.windll.user32.LockWorkStation()
        return "🔒 Компьютер заблокирован (Win+L)"
    except Exception as e:
        return f"Ошибка блокировки: {e}"

def sleep_pc_mode() -> str:
    """Переводит ноутбук в спящий режим."""
    try:
        _run(["powershell", "-NoProfile", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState('Suspend', $false, $false)"], timeout=5)
        return "😴 Ноутбук переведен в спящий режим"
    except Exception as e:
        return f"Ошибка сна: {e}"

def minimize_all_windows() -> str:
    """Сворачивает все окна (Win+D или Win+M)."""
    try:
        import pyautogui
        pyautogui.hotkey("win", "d")
        return "🖥 Все окна свернуты / показан рабочий стол"
    except Exception as e:
        return f"Ошибка: {e}"

def close_active_window() -> str:
    """Мягко закрывает текущее активное окно (Alt+F4)."""
    try:
        import pyautogui
        pyautogui.hotkey("alt", "f4")
        return "❌ Нажато Alt+F4 для активного окна"
    except Exception as e:
        return f"Ошибка: {e}"

def open_notepad_quick_note(text: str) -> str:
    """Быстро открывает Блокнот с указанной заметкой."""
    try:
        temp_file = Path(tempfile.gettempdir()) / f"jarvis_note_{int(time.time())}.txt"
        temp_file.write_text(text, encoding="utf-8")
        subprocess.Popen(["notepad.exe", str(temp_file)])
        return f"📝 Заметка открыта в Блокноте:\n{text[:150]}"
    except Exception as e:
        return f"Ошибка: {e}"

def set_process_volume(process_name: str, volume_percent: int) -> str:
    """Устанавливает уровень звука для конкретной программы (например chrome.exe, telegram.exe)."""
    try:
        from pycaw.pycaw import AudioUtilities
        sessions = AudioUtilities.GetAllSessions()
        target = process_name.lower().replace(".exe", "")
        found = False
        for s in sessions:
            if s.Process and target in s.Process.name().lower():
                vol = s.SimpleAudioVolume
                vol.SetMasterVolume(max(0.0, min(1.0, volume_percent / 100.0)), None)
                found = True
        if found:
            return f"🔊 Громкость для приложения «{process_name}» установлена на {volume_percent}%"
        return f"⚠️ Процесс «{process_name}» не найден в списке активных источников звука."
    except Exception as e:
        return f"Ошибка звука процесса: {e}"

def list_audio_devices() -> str:
    """Выводит список устройств воспроизведения звука."""
    try:
        ps_cmd = "Get-CimInstance Win32_SoundDevice | Select-Object -ExpandProperty Name"
        r = _run(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=8)
        lines = [ln.strip() for ln in _decode(r.stdout).splitlines() if ln.strip()]
        return "🎧 Аудиоустройства:\n" + "\n".join(f"• {x}" for x in lines[:10]) if lines else "Аудиоустройства не найдены"
    except Exception as e:
        return f"Ошибка: {e}"

def get_installed_updates() -> str:
    """Показывает последние установленные обновления Windows."""
    try:
        ps_cmd = "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 5 HotFixID, Description, InstalledOn | Format-Table -HideTableHeaders"
        r = _run(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=10)
        lines = [ln.strip() for ln in _decode(r.stdout).splitlines() if ln.strip()]
        return "🔄 Последние обновления Windows:\n" + "\n".join(lines[:8]) if lines else "Нет данных об обновлениях"
    except Exception as e:
        return f"Ошибка: {e}"

def toggle_caps_lock() -> str:
    """Переключает Caps Lock."""
    try:
        import pyautogui
        pyautogui.press("capslock")
        return "⌨ Нажат Caps Lock"
    except Exception as e:
        return f"Ошибка: {e}"

def press_multimedia_mute() -> str:
    """Мгновенно переключает системный Mute."""
    from services.media_control import change_volume
    return change_volume("mute")

def open_url_direct(url_or_name: str) -> str:
    """Умное открытие сайта или сервиса (Gmail, YouTube, GitHub, VK и т.д.)."""
    from services.web_client import open_url_or_search
    return f"🌐 Открыто в браузере: {open_url_or_search(url_or_name)}"

def mouse_move_to(x: int, y: int) -> str:
    """Перемещает курсор мыши в точные экранные координаты."""
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.moveTo(x, y, duration=0.2)
        return f"🖱 Курсор перемещен в координаты ({x}, {y})"
    except Exception as e:
        return f"Ошибка мыши: {e}"

def mouse_click_at(x: int, y: int, button: str = "left", clicks: int = 1) -> str:
    """Кликает мышью в координаты (x, y)."""
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.click(x=x, y=y, clicks=clicks, button=button)
        return f"🖱 Клик ({button}, {clicks}x) в ({x}, {y})"
    except Exception as e:
        return f"Ошибка клика: {e}"

def mouse_drag_to(x: int, y: int) -> str:
    """Зажимает ЛКМ и перетаскивает мышь в точку (x, y)."""
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.dragTo(x, y, duration=0.4, button="left")
        return f"🖱 Перетаскивание (Drag & Drop) в ({x}, {y})"
    except Exception as e:
        return f"Ошибка перетаскивания: {e}"

def mouse_scroll_units(amount: int) -> str:
    """Скроллит колесо мыши на amount делений."""
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.scroll(amount)
        direction = "вверх ⬆" if amount > 0 else "вниз ⬇"
        return f"📜 Скролл {direction} ({amount})"
    except Exception as e:
        return f"Ошибка скролла: {e}"


# ─────────────────────────────────────────────────────────
# ДИСПЕТЧЕР INTENT'ОВ
# ─────────────────────────────────────────────────────────

def dispatch_extra(intent: str, params: Dict[str, Any], session: Any = None) -> Optional[ExtraResult]:
    """Возвращает ExtraResult если intent известен расширению, иначе None."""
    try:
        if intent == "get_clipboard":
            return ExtraResult(True, "📋 Буфер:\n" + get_clipboard())
        if intent == "set_clipboard":
            return ExtraResult(True, set_clipboard(params.get("text", "")))
        if intent == "get_local_ip":
            return ExtraResult(True, f"🏠 Локальный IP: `{get_local_ip()}`")
        if intent == "get_public_ip":
            return ExtraResult(True, f"🌍 Внешний IP: `{get_public_ip()}`")
        if intent == "ping_host":
            return ExtraResult(True, ping_host(params.get("host") or "8.8.8.8"))
        if intent == "traceroute_host":
            return ExtraResult(True, traceroute_host(params.get("host") or "8.8.8.8"))
        if intent == "get_network_adapters":
            return ExtraResult(True, "📡 Адаптеры:\n" + get_network_adapters())
        if intent == "scan_wifi":
            return ExtraResult(True, get_wifi_networks())
        if intent == "get_mac_hostname":
            return ExtraResult(True, get_mac_and_hostname())
        if intent == "flush_dns":
            return ExtraResult(True, flush_dns())
        if intent == "ipconfig_summary":
            return ExtraResult(True, ipconfig_summary())
        if intent == "speed_test":
            return ExtraResult(True, speed_test())
        if intent in ("turn_off_monitor", "laptop_screen_sleep"):
            return ExtraResult(True, laptop_screen_sleep())
        if intent == "get_screen_info":
            return ExtraResult(True, get_screen_resolution())
        if intent == "get_idle_time":
            return ExtraResult(True, get_idle_time())
        if intent == "empty_recycle_bin":
            return ExtraResult(True, empty_recycle_bin())
        if intent == "recycle_bin_info":
            return ExtraResult(True, recycle_bin_info())
        if intent == "list_downloads":
            return ExtraResult(True, "⬇️ Загрузки:\n" + get_downloads_list())
        if intent == "folder_sizes":
            return ExtraResult(True, get_desktop_folder_sizes())
        if intent == "get_file_info":
            return ExtraResult(True, get_file_info(params.get("path", "")))
        if intent == "zip_path":
            return ExtraResult(True, zip_path(params.get("source", ""), params.get("destination")))
        if intent == "unzip_path":
            return ExtraResult(True, unzip_path(params.get("source", ""), params.get("destination")))
        if intent == "open_windows_tool":
            return ExtraResult(True, open_windows_tool(params.get("tool", "")))
        if intent == "toggle_notifications":
            return ExtraResult(True, do_not_disturb_mode())
        if intent == "toggle_dark_mode":
            return ExtraResult(True, toggle_dark_mode())
        if intent == "open_night_light":
            return ExtraResult(True, open_night_light())
        if intent == "restart_explorer":
            return ExtraResult(True, restart_explorer())
        if intent == "hibernate_pc":
            return ExtraResult(True, hibernate_pc())
        if intent == "cancel_shutdown":
            return ExtraResult(True, cancel_shutdown())
        if intent == "list_windows":
            return ExtraResult(True, list_open_windows())
        if intent == "get_active_window":
            return ExtraResult(True, get_active_window())
        if intent == "focus_window":
            return ExtraResult(True, focus_window(params.get("query", "")))
        if intent == "show_desktop":
            return ExtraResult(True, show_desktop())
        if intent == "get_hardware_info":
            return ExtraResult(True, get_hardware_info())
        if intent == "list_usb":
            return ExtraResult(True, list_usb_devices())
        if intent == "list_printers":
            return ExtraResult(True, list_printers())
        if intent == "list_startup":
            return ExtraResult(True, list_startup_apps())
        if intent == "firewall_status":
            return ExtraResult(True, firewall_status())
        if intent == "defender_status":
            return ExtraResult(True, defender_status())
        if intent == "generate_password":
            return ExtraResult(True, generate_password(params.get("length") or 16))
        if intent == "generate_uuid":
            return ExtraResult(True, generate_uuid())
        if intent == "hash_text":
            return ExtraResult(True, hash_text(params.get("text", ""), params.get("algo") or "sha256"))
        if intent == "base64_convert":
            return ExtraResult(True, base64_convert(params.get("text", ""), params.get("mode") or "encode"))
        if intent == "random_util":
            return ExtraResult(True, random_util(params.get("kind") or "number", params.get("min_value") or 1, params.get("max_value") or 100))
        if intent == "get_datetime":
            return ExtraResult(True, get_datetime_info())
        if intent == "speak_text":
            return ExtraResult(True, speak_text(params.get("text", "")))
        if intent == "generate_qr":
            return generate_qr_png(params.get("data") or params.get("text") or "jarvis")
        if intent == "set_wallpaper":
            return ExtraResult(True, set_wallpaper(params.get("path", "")))
        if intent == "type_text":
            return ExtraResult(True, type_text(params.get("text", "")))
        if intent == "press_hotkey":
            return ExtraResult(True, press_hotkey(params.get("keys", "")))
        if intent == "youtube_search":
            return ExtraResult(True, youtube_search(params.get("query", "")))
        if intent == "maps_search":
            return ExtraResult(True, maps_search(params.get("query", "")))
        if intent == "translate_text":
            return ExtraResult(True, translate_text(params.get("text", ""), params.get("target_lang") or "ru"))
        if intent == "color_picker":
            return ExtraResult(True, color_at_cursor())
        if intent == "get_volume_level":
            return ExtraResult(True, get_volume_level())
        if intent == "screenshot_delay":
            return take_delayed_screenshot(params.get("seconds") or 3)
        if intent == "open_ms_settings":
            page = params.get("page") or ""
            uri = f"ms-settings:{page}" if page else "ms-settings:"
            os.startfile(uri)
            return ExtraResult(True, f"⚙️ Параметры: {uri}")
        if intent == "autostart_status":
            from services.autostart import autostart_status
            return ExtraResult(True, autostart_status())
        if intent == "ensure_autostart":
            from services.autostart import ensure_autostart
            return ExtraResult(True, ensure_autostart())
        if intent == "set_power_plan":
            return ExtraResult(True, set_power_plan(params.get("mode", "balanced")))
        if intent == "battery_report":
            return ExtraResult(True, get_battery_report())
        if intent == "clear_browser_cache":
            return ExtraResult(True, clear_browser_cache())
        if intent == "create_restore_point":
            return ExtraResult(True, create_restore_point(params.get("description", "Jarvis Backup")))
        if intent == "lock_pc":
            return ExtraResult(True, lock_windows_session())
        if intent == "sleep_pc":
            return ExtraResult(True, sleep_pc_mode())
        if intent == "minimize_windows":
            return ExtraResult(True, minimize_all_windows())
        if intent == "close_active_window":
            return ExtraResult(True, close_active_window())
        if intent == "quick_note":
            return ExtraResult(True, open_notepad_quick_note(params.get("text", "Заметка")))
        if intent == "set_process_volume":
            return ExtraResult(True, set_process_volume(params.get("process_name", ""), int(params.get("volume", 50))))
        if intent == "list_audio_devices":
            return ExtraResult(True, list_audio_devices())
        if intent == "installed_updates":
            return ExtraResult(True, get_installed_updates())
        if intent == "toggle_caps_lock":
            return ExtraResult(True, toggle_caps_lock())
        if intent == "toggle_mute":
            return ExtraResult(True, press_multimedia_mute())
        if intent == "mouse_move":
            return ExtraResult(True, mouse_move_to(int(params.get("x", 0)), int(params.get("y", 0))))
        if intent == "mouse_click":
            return ExtraResult(True, mouse_click_at(int(params.get("x", 0)), int(params.get("y", 0)), params.get("button", "left"), int(params.get("clicks", 1))))
        if intent == "mouse_drag":
            return ExtraResult(True, mouse_drag_to(int(params.get("x", 0)), int(params.get("y", 0))))
        if intent == "mouse_scroll":
            return ExtraResult(True, mouse_scroll_units(int(params.get("amount", 300))))
        if intent == "keyboard_backlight":
            return ExtraResult(True, toggle_keyboard_backlight())
    except Exception as e:
        logger.error("dispatch_extra %s: %s", intent, e, exc_info=True)
        return ExtraResult(False, f"❌ {intent}: {e}")
    return None
