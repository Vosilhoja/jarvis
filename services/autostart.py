"""
Автозапуск Jarvis вместе с Windows.

Бот должен жить в сессии пользователя (экран, звук, рабочие столы),
поэтому регистрируем вход в систему (logon), а не SYSTEM AtStartup.

Способы (все сразу, чтобы сработало без прав администратора):
  1. HKCU\\...\\Run
  2. Ярлык/VBS в папке Автозагрузка
  3. Планировщик заданий (если доступен)
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from config import BASE_DIR

logger = logging.getLogger("jarvis")

TASK_NAME = "JarvisAssistant"
RUN_VALUE_NAME = "JarvisAssistant"
CREATE_NO_WINDOW = 0x08000000


def pythonw_path() -> str:
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    if pythonw.exists():
        return str(pythonw)
    return str(exe)


def watchdog_path() -> Path:
    return BASE_DIR / "watchdog.py"


def startup_vbs_path() -> Path:
    startup = Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup"
    startup.mkdir(parents=True, exist_ok=True)
    return startup / "JarvisAssistant.vbs"


def launch_command() -> str:
    return f'"{pythonw_path()}" "{watchdog_path()}"'


def _write_startup_vbs() -> Path:
    vbs = startup_vbs_path()
    py = pythonw_path().replace("\\", "\\\\")
    wd = str(watchdog_path()).replace("\\", "\\\\")
    cwd = str(BASE_DIR).replace("\\", "\\\\")
    content = (
        'Set sh = CreateObject("WScript.Shell")\r\n'
        f'sh.CurrentDirectory = "{cwd}"\r\n'
        f'sh.Run """{py}"" ""{wd}""", 0, False\r\n'
    )
    vbs.write_text(content, encoding="utf-8")
    return vbs


def _register_run_key() -> None:
    import winreg

    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    )
    try:
        winreg.SetValueEx(key, RUN_VALUE_NAME, 0, winreg.REG_SZ, launch_command())
    finally:
        winreg.CloseKey(key)


def _register_schtask() -> None:
    tr = launch_command()
    cmd = [
        "schtasks",
        "/Create",
        "/TN",
        TASK_NAME,
        "/TR",
        tr,
        "/SC",
        "ONLOGON",
        "/RL",
        "LIMITED",
        "/F",
    ]
    subprocess.run(
        cmd,
        capture_output=True,
        timeout=20,
        creationflags=CREATE_NO_WINDOW,
        cwd=str(BASE_DIR),
    )


def ensure_autostart() -> str:
    """Регистрирует автозапуск. Безопасно вызывать при каждом старте бота."""
    ok: list[str] = []
    errors: list[str] = []

    try:
        _register_run_key()
        ok.append("реестр Run")
    except Exception as e:
        errors.append(f"реестр: {e}")
        logger.warning("Автозапуск (реестр): %s", e)

    try:
        path = _write_startup_vbs()
        ok.append(f"Автозагрузка ({path.name})")
    except Exception as e:
        errors.append(f"Startup: {e}")
        logger.warning("Автозапуск (Startup): %s", e)

    try:
        _register_schtask()
        ok.append("Планировщик")
    except Exception as e:
        errors.append(f"schtasks: {e}")
        logger.warning("Автозапуск (schtasks): %s", e)

    summary = "Автозапуск при входе в Windows: " + (", ".join(ok) if ok else "не установлен")
    if errors:
        summary += ". Частичные ошибки: " + "; ".join(errors)
    logger.info(summary)
    return summary


def autostart_status() -> str:
    import winreg

    lines = ["📌 Статус автозапуска Jarvis:"]
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ,
        )
        try:
            val, _ = winreg.QueryValueEx(key, RUN_VALUE_NAME)
            lines.append(f"✅ Реестр Run: {val}")
        except FileNotFoundError:
            lines.append("❌ Реестр Run: нет записи")
        finally:
            winreg.CloseKey(key)
    except Exception as e:
        lines.append(f"❌ Реестр: {e}")

    vbs = startup_vbs_path()
    lines.append("✅ Папка Автозагрузка: есть VBS" if vbs.exists() else "❌ Папка Автозагрузка: нет VBS")

    try:
        r = subprocess.run(
            ["schtasks", "/Query", "/TN", TASK_NAME],
            capture_output=True,
            timeout=10,
            creationflags=CREATE_NO_WINDOW,
        )
        lines.append("✅ Планировщик: задача JarvisAssistant есть" if r.returncode == 0 else "⚠️ Планировщик: задачи нет")
    except Exception:
        lines.append("⚠️ Планировщик: не проверен")

    lines.append(f"▶ Команда: {launch_command()}")
    return "\n".join(lines)
