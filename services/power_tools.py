"""Power, battery and system state management tools."""
from __future__ import annotations

import ctypes
import logging
import subprocess

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


def get_idle_seconds() -> float:
    """Возвращает секунды простоя ввода (мышь/клавиатура), сырое число."""
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(info)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        millis = ctypes.windll.kernel32.GetTickCount() - info.dwTime
        return millis / 1000.0
    return 0.0


def get_idle_time() -> str:
    sec = int(get_idle_seconds())
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    return f"⏱ Простой ввода: {h}ч {m}мин {s}с"


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


def set_power_plan(mode: str = "balanced") -> str:
    plans = {
        "performance": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
        "balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",
        "saver": "a1841308-3541-4fab-bc81-f71556f20b4a",
    }
    guid = plans.get(mode.lower(), plans["balanced"])
    r = _run(["powercfg", "/setactive", guid], timeout=5)
    if r.returncode == 0:
        return f"⚡ Схема питания переключена на: *{mode}*"
    return f"⚠️ Не удалось сменить схему питания: {mode}"


def get_battery_report() -> str:
    import tempfile
    from pathlib import Path
    out = Path(tempfile.gettempdir()) / "battery_report.html"
    _run(["powercfg", "/batteryreport", "/output", str(out)], timeout=15)
    if out.exists():
        return f"🔋 Отчет о батарее сгенерирован: `{out}`"
    return "⚠️ Не удалось сгенерировать отчет о батарее"


def laptop_screen_sleep() -> str:
    """Переводит экран ноутбука в режим ожидания/сна для экономии энергии."""
    try:
        ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
        return "💻 Экран ноутбука переведен в режим энергосбережения (включится от любого касания клавиатуры или мыши)."
    except Exception as e:
        return f"Ошибка: {e}"


def sleep_pc_mode() -> str:
    """Переводит ноутбук в спящий режим."""
    try:
        _run(["powershell", "-NoProfile", "-Command", "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState('Suspend', $false, $false)"], timeout=5)
        return "😴 Ноутбук переведен в спящий режим"
    except Exception as e:
        return f"Ошибка сна: {e}"
