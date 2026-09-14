"""Application launching and window management."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ._common import CREATE_NO_WINDOW, _run

QUICK_APPS = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "telegram": str(Path.home() / "AppData/Roaming/Telegram Desktop/Telegram.exe"),
    "vscode": str(Path.home() / "AppData/Local/Programs/Microsoft VS Code/Code.exe"),
    "explorer": "explorer.exe", "calc": "calc.exe", "notepad": "notepad.exe",
    "taskmgr": "taskmgr.exe", "mspaint": "mspaint.exe", "regedit": "regedit.exe",
    "cmd": "cmd.exe", "powershell": "powershell.exe", "control": "control.exe",
    "defender": "windowsdefender://", "youtube": "https://www.youtube.com",
}


def quick_launch(app_key: str) -> str:
    path = QUICK_APPS.get(app_key.lower())
    if not path:
        return f"⚠️ Приложение '{app_key}' не найдено в списке быстрого запуска"
    try:
        if path.startswith(("http", "windowsdefender")):
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
        "task_scheduler": ("taskschd.msc", "Планировщик задач"), "device_manager": ("devmgmt.msc", "Диспетчер устройств"),
        "event_viewer": ("eventvwr.msc", "Просмотр событий"), "services": ("services.msc", "Службы"),
        "disk_cleanup": ("cleanmgr.exe", "Очистка диска"), "snipping": ("ms-screenclip:", "Ножницы"),
        "osk": ("osk.exe", "Экранная клавиатура"), "magnifier": ("magnify.exe", "Экранная лупа"),
        "sound": ("mmsys.cpl", "Параметры звука"), "display": ("ms-settings:display", "Параметры экрана"),
        "network": ("ms-settings:network", "Параметры сети"), "bluetooth": ("ms-settings:bluetooth", "Bluetooth"),
        "apps": ("ms-settings:appsfeatures", "Приложения"), "update": ("ms-settings:windowsupdate", "Центр обновления"),
    }
    item = mapping.get((tool or "").strip().lower().replace(" ", "_"))
    if not item:
        os.startfile("ms-settings:")
        return "⚙️ Открыты параметры Windows"
    target, title = item
    try:
        os.startfile(target)
    except Exception:
        subprocess.Popen(target, shell=True)
    return f"✅ Открыто: {title}"


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
    return "Окна не найдены" if not wins else "🪟 Открытые окна:\n" + "\n".join(f"• {t}" for _, t in wins)


def get_active_window() -> str:
    try:
        import win32gui
        title = win32gui.GetWindowText(win32gui.GetForegroundWindow())
        return f"🎯 Активное окно: {title or '(без заголовка)'}"
    except Exception as e:
        return f"Ошибка: {e}"


def focus_window(query: str) -> str:
    try:
        import win32gui, win32con
        for hwnd, title in _enum_windows():
            if query.lower() in title.lower():
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                return f"✅ На передний план: {title}"
        return f"⚠️ Окно «{query}» не найдено"
    except Exception as e:
        return f"Ошибка: {e}"


def hide_all_windows_except_active() -> str:
    try:
        import win32gui, win32con, win32process, psutil
        from config import HIDE_WINDOWS_EXCLUDE_PROCESSES
        active_hwnd, hidden, skipped = win32gui.GetForegroundWindow(), 0, 0
        for hwnd, title in _enum_windows():
            if hwnd == active_hwnd or title in {"Program Manager", ""}:
                continue
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if psutil.Process(pid).name().lower() in HIDE_WINDOWS_EXCLUDE_PROCESSES:
                    skipped += 1
                    continue
            except Exception:
                pass
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                hidden += 1
            except Exception:
                pass
        title = win32gui.GetWindowText(active_hwnd) or "(без заголовка)"
        note = f" (не тронуто из исключений: {skipped})" if skipped else ""
        return (f"🙈 Других окон не найдено — активно только «{title}»{note}" if hidden == 0
                else f"🙈 Свёрнуто окон: {hidden}. Осталось активным: «{title}»{note}")
    except Exception as e:
        return f"Ошибка: {e}"
