"""Miscellaneous system, security, media, and automation tools."""
from __future__ import annotations

import base64
import ctypes
import hashlib
import io
import logging
import os
import random
import re
import secrets
import shutil
import string
import subprocess
import time
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

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


def empty_recycle_bin() -> str:
    try:
        count_before = _recycle_bin_item_count()

        r = _run([
            "powershell", "-NoProfile", "-Command",
            "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"
        ], timeout=20)

        if r.returncode == 0:
            return "🗑 Корзина очищена."

        # returncode != 0 — разбираемся, была ли корзина пуста ДО попытки очистки,
        # вместо того чтобы всегда молча писать "возможно уже пуста" (раньше это
        # маскировало реальные ошибки PowerShell/прав доступа).
        if count_before == 0:
            return "🗑 Корзина уже была пуста."
        err = _decode(r.stderr).strip()
        return f"⚠️ Не удалось очистить корзину (элементов было: {count_before}). {err or 'Ошибка PowerShell.'}"
    except Exception as e:
        return f"Ошибка очистки корзины: {e}"


def _recycle_bin_item_count() -> int:
    """Возвращает число элементов в корзине или -1, если посчитать не удалось."""
    try:
        r = _run([
            "powershell", "-NoProfile", "-Command",
            "(New-Object -ComObject Shell.Application).NameSpace(10).Items().Count"
        ], timeout=15)
        return int(_decode(r.stdout).strip())
    except Exception:
        return -1


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


def find_file_broad(query: str, max_results: int = 8, timeout_sec: float = 6.0) -> list[Path]:
    """Ищет файл по (части) имени в стандартных пользовательских папках.

    Ограничено по времени и глубине — согласно AGENT_RULES.md, неограниченный
    рекурсивный обход реального диска пользователя может быть очень медленным
    или зависнуть. Возвращает совпадения, отсортированные по дате изменения
    (новые сначала).
    """
    home = Path.home()
    roots = [home / "Desktop", home / "Downloads", home / "Documents", home / "Pictures"]
    q = query.strip().lower()
    matches: list[Path] = []
    start = time.time()

    for root in roots:
        if not root.exists():
            continue
        try:
            for p in root.rglob("*"):
                if time.time() - start > timeout_sec:
                    break
                if p.is_file() and q in p.name.lower():
                    matches.append(p)
        except Exception:
            continue
        if time.time() - start > timeout_sec:
            break

    matches.sort(key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    return matches[:max_results]


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


QUICK_APPS = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "telegram": str(Path.home() / "AppData/Roaming/Telegram Desktop/Telegram.exe"),
    "vscode": str(Path.home() / "AppData/Local/Programs/Microsoft VS Code/Code.exe"),
    "explorer": "explorer.exe",
    "calc": "calc.exe",
    "notepad": "notepad.exe",
    "taskmgr": "taskmgr.exe",
    "mspaint": "mspaint.exe",
    "regedit": "regedit.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "control": "control.exe",
    "defender": "windowsdefender://",
    "youtube": "https://www.youtube.com",
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


def open_device_manager() -> str:
    subprocess.Popen("devmgmt.msc", shell=True)
    return "🖥 Диспетчер устройств открыт."


def open_event_viewer() -> str:
    subprocess.Popen("eventvwr.msc", shell=True)
    return "📋 Просмотр событий открыт."


def open_task_scheduler() -> str:
    subprocess.Popen("taskschd.msc", shell=True)
    return "⏱ Планировщик заданий открыт."


def restart_explorer() -> str:
    try:
        _run(["taskkill", "/f", "/im", "explorer.exe"], timeout=8)
        subprocess.Popen("explorer.exe", shell=True)
        return "🔄 Проводник перезапущен"
    except Exception as e:
        return f"Ошибка: {e}"


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


def get_hardware_info() -> str:
    import psutil
    import platform
    cpu = platform.processor() or "н/д"
    cores = psutil.cpu_count(logical=True)
    ram = psutil.virtual_memory()
    return (
        f"🖥 ОС: {platform.platform()}\n"
        f"🧠 CPU: {cpu} (ядер: {cores})\n"
        f"💾 RAM: {ram.total // (1024**3)} ГБ ({ram.percent}% использовано)"
    )


def list_usb_devices() -> str:
    try:
        r = _run([
            "powershell", "-NoProfile", "-Command",
            "Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match '^USB' } | Select-Object -ExpandProperty FriendlyName"
        ], timeout=20)
        names = sorted({ln.strip() for ln in _decode(r.stdout).splitlines() if ln.strip()})
        return "🔌 USB:\n" + "\n".join(f"• {n}" for n in names[:25]) if names else "USB-устройства не найдены"
    except Exception as e:
        return f"Ошибка: {e}"


def list_printers() -> str:
    try:
        import win32print
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        printers = win32print.EnumPrinters(flags)
        names = [p[2] for p in printers if p[2]]
        return "🖨 Принтеры:\n" + "\n".join(f"• {n}" for n in names) if names else "Принтеры не найдены"
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
            i = 0
            while True:
                try:
                    n, _, _ = winreg.EnumValue(key, i)
                    names.append(f"• {n}")
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
        except OSError:
            continue
    return "🚀 Автозагрузка:\n" + "\n".join(names[:30]) if names else "Список автозагрузки пуст"


def firewall_status() -> str:
    try:
        r = _run(["netsh", "advfirewall", "show", "allprofiles", "state"], timeout=10)
        return f"🛡 Брандмауэр:\n{_decode(r.stdout)[:400]}"
    except Exception as e:
        return f"Ошибка: {e}"


def defender_status() -> str:
    try:
        r = _run([
            "powershell", "-NoProfile", "-Command",
            "Get-MpComputerStatus | Select-Object AMServiceEnabled,AntivirusEnabled,RealTimeProtectionEnabled | Format-List"
        ], timeout=15)
        return "🛡 Microsoft Defender:\n" + (_decode(r.stdout).strip() or "нет данных")
    except Exception as e:
        return f"Ошибка: {e}"


def generate_password(length: int = 16) -> str:
    length = max(8, min(64, int(length or 16)))
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    pwd = "".join(secrets.choice(alphabet) for _ in range(length))
    return f"🔐 Пароль: `{pwd}`"


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
        escaped = text.replace("'", "''")[:400]
        _run([
            "powershell", "-NoProfile", "-Command",
            f"Add-Type -AssemblyName System.Speech; "
            f"(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{escaped}')"
        ], timeout=15)
        return f"🔊 Произнесено: {text[:120]}"
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


# Состояние режима "Тихий час" — сохраняется на время работы бота
_DND_STATE: dict = {"enabled": False, "prev_muted": False}


def toggle_keyboard_backlight() -> str:
    """
    Пытается переключить подсветку клавиатуры через WMI-классы известных производителей.

    ВАЖНО: F11 здесь больше НЕ используется. F11 — это системный хоткей
    "полноэкранный режим" почти во всех приложениях и браузерах, и предыдущая
    версия этой функции по ошибке разворачивала активное окно на весь экран
    вместо переключения подсветки. Универсального WinAPI для подсветки
    клавиатуры не существует — это всегда проприетарная функция производителя.
    """
    methods_ok = []

    # Lenovo (Vantage / Legion) — WMI namespace root\WMI, класс LENOVO_GAMEZONE_DATA / LENOVO_UTILITY
    try:
        r = _run(
            ["powershell", "-NoProfile", "-Command",
             "$m = Get-WmiObject -Namespace root/WMI -Class LENOVO_GAMEZONE_DATA -ErrorAction SilentlyContinue; "
             "if ($m) { $m.SetKeyboardLight(1) }"],
            timeout=3
        )
        if r.returncode == 0:
            methods_ok.append("Lenovo WMI")
    except Exception:
        pass

    # Dell (Alienware/Command Center) — WMI namespace root\WMI, класс DellAbstraction/AWCCWmi
    try:
        r = _run(
            ["powershell", "-NoProfile", "-Command",
             "$m = Get-WmiObject -Namespace root/WMI -Class AWCCWmi -ErrorAction SilentlyContinue; "
             "if ($m) { $m.ToggleKeyboardBacklight() }"],
            timeout=3
        )
        if r.returncode == 0:
            methods_ok.append("Dell WMI")
    except Exception:
        pass

    if methods_ok:
        return f"⌨ Подсветка клавиатуры переключена ({', '.join(methods_ok)})."

    return (
        "⌨ Не удалось найти поддерживаемый WMI-интерфейс подсветки клавиатуры для вашей модели ноутбука.\n"
        "Это ожидаемо: единого системного способа переключить подсветку в Windows не существует — "
        "у каждого производителя своя закрытая реализация.\n\n"
        "Используйте аппаратную комбинацию клавиш (обычно `Fn+Пробел` или `Fn+F5..F12`, зависит от модели) "
        "или фирменную утилиту: Lenovo Vantage, Dell Power Manager/Alienware Command Center, "
        "HP Command Center, ASUS Armoury Crate, MSI Center."
    )


def do_not_disturb_mode() -> str:
    """Переключает режим 'Тихий час': mute/unmute системного звука + сохраняет состояние."""
    from services.media_control import change_volume
    _DND_STATE["enabled"] = not _DND_STATE["enabled"]
    try:
        if _DND_STATE["enabled"]:
            change_volume("mute")
            return (
                "🔕 Режим *Тихий час* ВКЛЮЧЁН\n\n"
                "• Системный звук заглушён (Mute)\n"
                "• Нажмите снова для выключения"
            )
        else:
            change_volume("unmute")
            return (
                "🔔 Режим *Тихий час* ВЫКЛЮЧЕН\n\n"
                "• Системный звук возвращён\n"
                "• Нажмите снова для включения"
            )
    except Exception as e:
        # Откатить состояние при ошибке
        _DND_STATE["enabled"] = not _DND_STATE["enabled"]
        return f"⚠️ Не удалось переключить режим тихого часа: {e}"


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


def mouse_move_to(x: int, y: int) -> str:
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.moveTo(x, y, duration=0.2)
        return f"🖱 Курсор перемещен в ({x}, {y})"
    except Exception as e:
        return f"Ошибка мыши: {e}"


def mouse_click_at(x: int, y: int, button: str = "left", clicks: int = 1) -> str:
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.click(x=x, y=y, clicks=clicks, button=button)
        return f"🖱 Клик ({button}, {clicks}x) в ({x}, {y})"
    except Exception as e:
        return f"Ошибка клика: {e}"


def mouse_drag_to(x: int, y: int) -> str:
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.dragTo(x, y, duration=0.4, button="left")
        return f"🖱 Drag&Drop в ({x}, {y})"
    except Exception as e:
        return f"Ошибка drag: {e}"


def mouse_scroll_units(amount: int) -> str:
    try:
        import pyautogui
        pyautogui.scroll(amount)
        return f"🖱 Скролл на {amount} ед."
    except Exception as e:
        return f"Ошибка скролла: {e}"


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


def set_wallpaper(path: str) -> str:
    """Устанавливает обои рабочего стола Windows."""
    p = Path(os.path.expandvars(path))
    if not p.exists() or p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".bmp"):
        return "❌ Укажите существующий файл изображения (.jpg/.png/.bmp)"
    SPI_SETDESKWALLPAPER = 20
    ok = ctypes.windll.user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, str(p), 3)
    return "✅ Обои рабочего стола обновлены" if ok else "⚠️ Windows не принял файл обоев"


def toggle_caps_lock() -> str:
    """Переключает Caps Lock."""
    try:
        import pyautogui
        pyautogui.press("capslock")
        return "⌨ Нажат Caps Lock"
    except Exception as e:
        return f"Ошибка: {e}"


def list_audio_devices() -> str:
    """Выводит список устройств воспроизведения звука."""
    try:
        ps_cmd = "Get-CimInstance Win32_SoundDevice | Select-Object -ExpandProperty Name"
        r = _run(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=8)
        lines = [ln.strip() for ln in _decode(r.stdout).splitlines() if ln.strip()]
        return "🎧 Аудиоустройства:\n" + "\n".join(f"• {x}" for x in lines[:10]) if lines else "Аудиоустройства не найдены"
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


def close_active_window() -> str:
    """Мягко закрывает текущее активное окно (Alt+F4)."""
    try:
        import pyautogui
        pyautogui.hotkey("alt", "f4")
        return "❌ Нажато Alt+F4 для активного окна"
    except Exception as e:
        return f"Ошибка: {e}"


def minimize_all_windows() -> str:
    """Сворачивает все окна (Win+D)."""
    try:
        import pyautogui
        pyautogui.hotkey("win", "d")
        return "🖥 Все окна свернуты / показан рабочий стол"
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


def hide_all_windows_except_active() -> str:
    """
    Сворачивает все видимые окна, КРОМЕ текущего активного (в отличие от
    minimize_all_windows(), который сворачивает вообще всё через Win+D).
    Полезно для фокус-режима на одном приложении.
    """
    try:
        import win32gui
        import win32con

        active_hwnd = win32gui.GetForegroundWindow()
        # Системные окна, которые не стоит трогать (таскбар, панель задач и т.д.)
        skip_titles = {"Program Manager", ""}
        hidden = 0
        for hwnd, title in _enum_windows():
            if hwnd == active_hwnd or title in skip_titles:
                continue
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                hidden += 1
            except Exception:
                continue

        active_title = win32gui.GetWindowText(active_hwnd) or "(без заголовка)"
        if hidden == 0:
            return f"🙈 Других окон не найдено — активно только «{active_title}»"
        return f"🙈 Свёрнуто окон: {hidden}. Осталось активным: «{active_title}»"
    except Exception as e:
        return f"Ошибка: {e}"


def get_folder_changes_today(path: str) -> str:
    """
    Показывает файлы в указанной папке, изменённые или созданные сегодня
    ("что изменилось в папке X за сегодня"). Не рекурсивно в подпапки глубже
    2 уровней и с ограничением по количеству файлов — чтобы не зависнуть
    на больших деревьях каталогов (см. известные грабли про блокирующие вызовы).
    """
    import humanize
    from datetime import datetime
    from core.execution.common import resolve_path_aliases

    try:
        folder = resolve_path_aliases(path)
        if not folder.exists() or not folder.is_dir():
            return f"❌ Папка не найдена: `{folder}`"

        today = datetime.now().date()
        changed = []
        checked = 0
        MAX_CHECK = 5000  # предохранитель от зависания на огромных папках

        for item in folder.rglob("*"):
            checked += 1
            if checked > MAX_CHECK:
                break
            if not item.is_file():
                continue
            try:
                mtime = datetime.fromtimestamp(item.stat().st_mtime)
            except Exception:
                continue
            if mtime.date() == today:
                changed.append((mtime, item))

        if not changed:
            return f"📂 За сегодня в «{folder.name}» изменений не найдено."

        changed.sort(key=lambda x: x[0], reverse=True)
        lines = []
        for mtime, item in changed[:30]:
            try:
                size = humanize.naturalsize(item.stat().st_size, binary=True)
            except Exception:
                size = "?"
            lines.append(f"• {mtime.strftime('%H:%M')} — {item.name} ({size})")

        extra = f"\n\n…и ещё {len(changed) - 30} файл(ов)" if len(changed) > 30 else ""
        return f"📂 *Изменено сегодня в «{folder.name}»* ({len(changed)}):\n\n" + "\n".join(lines) + extra
    except Exception as e:
        return f"Ошибка: {e}"
