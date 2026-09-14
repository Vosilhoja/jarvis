"""Hardware, display, audio, and general Windows utilities."""
from __future__ import annotations

import ctypes
import io
import os
from datetime import datetime
from pathlib import Path

from ._common import ExtraResult, _decode, _run

_DND_STATE: dict = {"enabled": False, "prev_muted": False}


def toggle_keyboard_backlight() -> str:
    methods_ok = []
    for cls, method, label in (("LENOVO_GAMEZONE_DATA", "SetKeyboardLight(1)", "Lenovo WMI"),
                               ("AWCCWmi", "ToggleKeyboardBacklight()", "Dell WMI")):
        try:
            r = _run(["powershell", "-NoProfile", "-Command",
                      f"$m = Get-WmiObject -Namespace root/WMI -Class {cls} -ErrorAction SilentlyContinue; if ($m) {{ $m.{method} }}"], timeout=3)
            if r.returncode == 0:
                methods_ok.append(label)
        except Exception:
            pass
    if methods_ok:
        return f"⌨ Подсветка клавиатуры переключена ({', '.join(methods_ok)})."
    return ("⌨ Не удалось найти поддерживаемый WMI-интерфейс подсветки клавиатуры для вашей модели ноутбука.\n"
            "Это ожидаемо: единого системного способа переключить подсветку в Windows не существует — "
            "у каждого производителя своя закрытая реализация.\n\n"
            "Используйте аппаратную комбинацию клавиш (обычно `Fn+Пробел` или `Fn+F5..F12`, зависит от модели) "
            "или фирменную утилиту производителя.")


def do_not_disturb_mode() -> str:
    from services.media_control import change_volume
    _DND_STATE["enabled"] = not _DND_STATE["enabled"]
    try:
        if _DND_STATE["enabled"]:
            change_volume("mute")
            return "🔕 Режим *Тихий час* ВКЛЮЧЁН\n\n• Системный звук заглушён (Mute)\n• Нажмите снова для выключения"
        change_volume("unmute")
        return "🔔 Режим *Тихий час* ВЫКЛЮЧЕН\n\n• Системный звук возвращён\n• Нажмите снова для включения"
    except Exception as e:
        _DND_STATE["enabled"] = not _DND_STATE["enabled"]
        return f"⚠️ Не удалось переключить режим тихого часа: {e}"


def get_hardware_info() -> str:
    import platform, psutil
    ram = psutil.virtual_memory()
    return (f"🖥 ОС: {platform.platform()}\n🧠 CPU: {platform.processor() or 'н/д'} "
            f"(ядер: {psutil.cpu_count(logical=True)})\n💾 RAM: {ram.total // (1024**3)} ГБ ({ram.percent}% использовано)")


def list_usb_devices() -> str:
    try:
        r = _run(["powershell", "-NoProfile", "-Command",
                  "Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -match '^USB' } | Select-Object -ExpandProperty FriendlyName"], timeout=20)
        names = sorted({x.strip() for x in _decode(r.stdout).splitlines() if x.strip()})
        return "🔌 USB:\n" + "\n".join(f"• {n}" for n in names[:25]) if names else "USB-устройства не найдены"
    except Exception as e:
        return f"Ошибка: {e}"


def list_printers() -> str:
    try:
        import win32print
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        names = [p[2] for p in win32print.EnumPrinters(flags) if p[2]]
        return "🖨 Принтеры:\n" + "\n".join(f"• {n}" for n in names) if names else "Принтеры не найдены"
    except Exception as e:
        return f"Ошибка: {e}"


def list_startup_apps() -> str:
    import winreg
    names = []
    for hive, path in ((winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
                       (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run")):
        try:
            key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
            i = 0
            while True:
                try:
                    names.append(f"• {winreg.EnumValue(key, i)[0]}")
                    i += 1
                except OSError:
                    break
            winreg.CloseKey(key)
        except OSError:
            pass
    return "🚀 Автозагрузка:\n" + "\n".join(names[:30]) if names else "Список автозагрузки пуст"


def get_datetime_info() -> str:
    now = datetime.now()
    return f"📅 {now.strftime('%A, %d.%m.%Y')}\n🕒 {now.strftime('%H:%M:%S')}"


def speak_text(text: str) -> str:
    try:
        escaped = text.replace("'", "''")[:400]
        _run(["powershell", "-NoProfile", "-Command",
              f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{escaped}')"], timeout=15)
        return f"🔊 Произнесено: {text[:120]}"
    except Exception as e:
        return f"Ошибка озвучки: {e}"


def generate_qr_png(data: str) -> ExtraResult:
    try:
        import qrcode
        buf = io.BytesIO()
        qrcode.make(data).save(buf, format="PNG")
        return ExtraResult(True, f"📷 QR-код для: {data[:80]}", photo_bytes=buf.getvalue(), photo_name="qr.png")
    except Exception as e:
        return ExtraResult(False, f"Ошибка QR: {e}")


def toggle_dark_mode() -> str:
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize", 0, winreg.KEY_READ | winreg.KEY_SET_VALUE)
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


def clear_browser_cache() -> str:
    user_local = Path(os.environ.get("LOCALAPPDATA", ""))
    dirs = [user_local / x for x in ("Google/Chrome/User Data/Default/Cache", "Google/Chrome/User Data/Default/Code Cache", "Microsoft/Edge/User Data/Default/Cache", "Yandex/YandexBrowser/User Data/Default/Cache")]
    freed = count = 0
    for directory in dirs:
        if directory.exists():
            try:
                for f in directory.rglob("*"):
                    if f.is_file():
                        try:
                            size = f.stat().st_size
                            f.unlink()
                            freed += size
                            count += 1
                        except Exception:
                            pass
            except Exception:
                pass
    return f"🧹 Очистка кэша браузеров: удалено {count} файлов, освобождено {freed / (1024 * 1024):.1f} МБ."


def create_restore_point(description: str = "Jarvis Backup") -> str:
    try:
        _run(["powershell", "-NoProfile", "-Command",
              f"Checkpoint-Computer -Description '{description}' -RestorePointType 'MODIFY_SETTINGS' -ErrorAction SilentlyContinue"], timeout=30)
        return f"🛡 Запрос на создание точки восстановления «{description}» выполнен."
    except Exception as e:
        return f"Ошибка точки восстановления: {e}"


def set_wallpaper(path: str) -> str:
    p = Path(os.path.expandvars(path))
    if not p.exists() or p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".bmp"):
        return "❌ Укажите существующий файл изображения (.jpg/.png/.bmp)"
    ok = ctypes.windll.user32.SystemParametersInfoW(20, 0, str(p), 3)
    return "✅ Обои рабочего стола обновлены" if ok else "⚠️ Windows не принял файл обоев"


def list_audio_devices() -> str:
    try:
        r = _run(["powershell", "-NoProfile", "-Command",
                  "Get-CimInstance Win32_SoundDevice | Select-Object -ExpandProperty Name"], timeout=8)
        lines = [x.strip() for x in _decode(r.stdout).splitlines() if x.strip()]
        return "🎧 Аудиоустройства:\n" + "\n".join(f"• {x}" for x in lines[:10]) if lines else "Аудиоустройства не найдены"
    except Exception as e:
        return f"Ошибка: {e}"


def set_process_volume(process_name: str, volume_percent: int) -> str:
    try:
        from pycaw.pycaw import AudioUtilities
        target, found = process_name.lower().replace(".exe", ""), False
        for session in AudioUtilities.GetAllSessions():
            if session.Process and target in session.Process.name().lower():
                session.SimpleAudioVolume.SetMasterVolume(max(0.0, min(1.0, volume_percent / 100.0)), None)
                found = True
        return (f"🔊 Громкость для приложения «{process_name}» установлена на {volume_percent}%"
                if found else f"⚠️ Процесс «{process_name}» не найден в списке активных источников звука.")
    except Exception as e:
        return f"Ошибка звука процесса: {e}"


def get_installed_updates() -> str:
    try:
        r = _run(["powershell", "-NoProfile", "-Command",
                  "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 5 HotFixID, Description, InstalledOn | Format-Table -HideTableHeaders"], timeout=10)
        lines = [x.strip() for x in _decode(r.stdout).splitlines() if x.strip()]
        return "🔄 Последние обновления Windows:\n" + "\n".join(lines[:8]) if lines else "Нет данных об обновлениях"
    except Exception as e:
        return f"Ошибка: {e}"
