import subprocess
import psutil
import webbrowser
import asyncio
from typing import Optional

BROWSER_PROCESS_NAMES = {
    "chrome": "chrome.exe",
    "edge": "msedge.exe",
    "yandex": "browser.exe",
    "firefox": "firefox.exe",
}

def open_new_tab(url: str, browser: Optional[str] = None) -> str:
    """Открывает URL в новой вкладке браузера по умолчанию (или конкретного, если указан)."""
    if browser and browser in BROWSER_PROCESS_NAMES:
        exe = BROWSER_PROCESS_NAMES[browser]
        try:
            subprocess.Popen([exe, url])
            return f"🌐 Открыл {url} в {browser}"
        except FileNotFoundError:
            pass  # fallback ниже
    webbrowser.open_new_tab(url)
    return f"🌐 Открыл {url} в браузере по умолчанию"

def open_incognito(url: str, browser: str = "chrome") -> str:
    """Открывает URL в режиме инкогнито/приватном окне."""
    flags = {"chrome": "--incognito", "edge": "--inprivate", "yandex": "--incognito", "firefox": "-private-window"}
    exe = BROWSER_PROCESS_NAMES.get(browser, "chrome.exe")
    flag = flags.get(browser, "--incognito")
    subprocess.Popen([exe, flag, url])
    return f"🕵️ Открыл {url} в приватном режиме ({browser})"

def close_browser(browser: str) -> str:
    """Полностью закрывает указанный браузер (все окна/процессы)."""
    exe = BROWSER_PROCESS_NAMES.get(browser)
    if not exe:
        return f"❌ Неизвестный браузер: {browser}"
    killed = 0
    for proc in psutil.process_iter(["pid", "name"]):
        if proc.info["name"] and proc.info["name"].lower() == exe.lower():
            try:
                proc.terminate()
                killed += 1
            except Exception:
                pass
    return f"🚪 Закрыто процессов {browser}: {killed}" if killed else f"⚠️ {browser} не был запущен"

def list_running_browsers() -> str:
    """Показывает, какие браузеры сейчас запущены и сколько у них процессов (вкладок/окон)."""
    counts = {}
    for proc in psutil.process_iter(["name"]):
        name = (proc.info["name"] or "").lower()
        for key, exe in BROWSER_PROCESS_NAMES.items():
            if name == exe.lower():
                counts[key] = counts.get(key, 0) + 1
    if not counts:
        return "Ни один браузер сейчас не запущен."
    return "🌐 Запущенные браузеры:\n" + "\n".join(f"• {k}: {v} процессов" for k, v in counts.items())

def new_tab_in_active_browser(url: str) -> str:
    """Открывает вкладку в уже АКТИВНОМ окне браузера через Ctrl+T + вставку адреса (без запуска нового процесса)."""
    import pyautogui
    import pyperclip
    import time
    pyautogui.hotkey("ctrl", "t")
    time.sleep(0.3)
    old_clip = pyperclip.paste()
    pyperclip.copy(url)
    pyautogui.hotkey("ctrl", "v")
    pyautogui.press("enter")
    pyperclip.copy(old_clip)
    return f"🌐 Открыта новая вкладка: {url}"

def close_current_tab() -> str:
    import pyautogui
    pyautogui.hotkey("ctrl", "w")
    return "❌ Текущая вкладка закрыта (Ctrl+W)"

def switch_tab(direction: str = "next") -> str:
    import pyautogui
    combo = ("ctrl", "tab") if direction == "next" else ("ctrl", "shift", "tab")
    pyautogui.hotkey(*combo)
    return f"↔️ Переключено на {'следующую' if direction=='next' else 'предыдущую'} вкладку"
