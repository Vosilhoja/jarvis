"""
Модуль управления медиа и звуком.
Использует pycaw (современный EndpointVolume API) для мгновенной точной установки громкости без эмуляции клавиш.
"""
import logging
import win32api
import win32con
from typing import Optional

logger = logging.getLogger("jarvis")

# ─────────────────────────────────────────────────────────────
#  Виртуальные коды клавиш Windows
# ─────────────────────────────────────────────────────────────
VK_VOLUME_MUTE       = 0xAD
VK_VOLUME_DOWN       = 0xAE
VK_VOLUME_UP         = 0xAF
VK_MEDIA_NEXT_TRACK  = 0xB0
VK_MEDIA_PREV_TRACK  = 0xB1
VK_MEDIA_STOP        = 0xB2
VK_MEDIA_PLAY_PAUSE  = 0xB3

def _press_key(vk_code: int):
    """Посылает событие нажатия виртуальной клавиши Windows."""
    try:
        win32api.keybd_event(vk_code, 0, 0, 0)
        win32api.keybd_event(vk_code, 0, win32con.KEYEVENTF_KEYUP, 0)
    except Exception as e:
        logger.error(f"Ошибка нажатия клавиши {hex(vk_code)}: {e}")

# ─────────────────────────────────────────────────────────────
#  Медиа-управление
# ─────────────────────────────────────────────────────────────

def media_play_pause():
    """Play / Pause текущего медиаплеера."""
    _press_key(VK_MEDIA_PLAY_PAUSE)

def media_next():
    """Следующий трек."""
    _press_key(VK_MEDIA_NEXT_TRACK)

def media_prev():
    """Предыдущий трек."""
    _press_key(VK_MEDIA_PREV_TRACK)

def media_stop():
    """Остановить воспроизведение."""
    _press_key(VK_MEDIA_STOP)

# ─────────────────────────────────────────────────────────────
#  Управление громкостью через современный pycaw
# ─────────────────────────────────────────────────────────────

def _get_endpoint_volume():
    """Получает активный интерфейс EndpointVolume из pycaw."""
    from pycaw.pycaw import AudioUtilities
    speakers = AudioUtilities.GetSpeakers()
    if hasattr(speakers, "EndpointVolume"):
        return speakers.EndpointVolume
    # Для альтернативных версий pycaw
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import IAudioEndpointVolume
    interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return interface.QueryInterface(IAudioEndpointVolume)

def set_volume_pycaw(level_percent: int) -> bool:
    """
    Мгновенно устанавливает системную громкость на точный процент (0-100) без щелчков клавиатуры!
    """
    try:
        volume = _get_endpoint_volume()
        norm_level = max(0.0, min(1.0, float(level_percent) / 100.0))
        volume.SetMasterVolumeLevelScalar(norm_level, None)
        # Если был Mute — снимаем
        if hasattr(volume, "GetMute") and volume.GetMute():
            volume.SetMute(0, None)
        logger.info(f"pycaw: громкость точно установлена на {level_percent}%")
        return True
    except Exception as e:
        logger.warning(f"pycaw SetVolume не сработал ({e})")
        return False

def get_volume_pycaw() -> Optional[int]:
    """Возвращает текущий точный уровень громкости (0-100) или None при ошибке."""
    try:
        volume = _get_endpoint_volume()
        scalar = volume.GetMasterVolumeLevelScalar()
        return round(scalar * 100)
    except Exception as e:
        logger.debug(f"pycaw GetVolume не сработал: {e}")
        return None

def toggle_mute_pycaw() -> bool:
    """Переключает режим Mute через pycaw."""
    try:
        volume = _get_endpoint_volume()
        # Жмём РЕАЛЬНУЮ клавишу mute — она сама переключит системный mute
        # И зажжёт аппаратный индикатор на клавиатуре (чего SetMute() через COM не делает).
        _press_key(VK_VOLUME_MUTE)
        import time as _t
        _t.sleep(0.05)
        return bool(volume.GetMute())
    except Exception:
        _press_key(VK_VOLUME_MUTE)
        return True

def change_volume(direction: str, level: Optional[int] = None) -> str:
    """
    Изменяет громкость:
    - direction="set", level=50 → ровно 50% мгновенно!
    - direction="up"           → +10%
    - direction="down"         → -10%
    - direction="mute"         → переключить mute
    """
    if level is not None:
        target = max(0, min(100, int(level)))
        if set_volume_pycaw(target):
            return f"Громкость установлена ровно на {target}%"
        # Резервный расчет
        cur = get_volume_pycaw() or 50
        diff = target - cur
        steps = abs(diff) // 2
        key = VK_VOLUME_UP if diff > 0 else VK_VOLUME_DOWN
        for _ in range(steps):
            _press_key(key)
        return f"Громкость установлена на ~{target}%"

    if direction == "up":
        cur = get_volume_pycaw()
        if cur is not None:
            new_val = min(100, cur + 10)
            set_volume_pycaw(new_val)
            return f"Громкость увеличена: {new_val}%"
        for _ in range(5):
            _press_key(VK_VOLUME_UP)
        return "Громкость увеличена (+10%)"

    elif direction == "down":
        cur = get_volume_pycaw()
        if cur is not None:
            new_val = max(0, cur - 10)
            set_volume_pycaw(new_val)
            return f"Громкость уменьшена: {new_val}%"
        for _ in range(5):
            _press_key(VK_VOLUME_DOWN)
        return "Громкость уменьшена (-10%)"

    elif direction in ("mute", "unmute"):
        is_muted = toggle_mute_pycaw()
        return "🔇 Звук выключен (Mute)" if is_muted else "🔊 Звук включен"

    return "Громкость изменена"

# ─────────────────────────────────────────────────────────────
#  Управление яркостью экрана ноутбука
# ─────────────────────────────────────────────────────────────

def set_brightness(level: int) -> str:
    """
    Устанавливает яркость экрана ноутбука через WMI или PowerShell.
    """
    level = max(0, min(100, int(level)))

    # Способ 1: WMI WmiSetBrightness
    try:
        import wmi
        w = wmi.WMI(namespace='wmi')
        methods = w.WmiMonitorBrightnessMethods()
        if methods:
            methods[0].WmiSetBrightness(level, 0)
            logger.info(f"WMI: яркость установлена на {level}%")
            return f"Яркость установлена на {level}%"
    except Exception:
        pass

    # Способ 2: PowerShell CIM
    try:
        import subprocess
        ps_cmd = (
            f"(Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightnessMethods)."
            f"WmiSetBrightness(1, {level})"
        )
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            timeout=8,
            creationflags=0x08000000
        )
        if r.returncode == 0:
            return f"Яркость установлена на {level}%"
    except Exception as e:
        logger.warning(f"Ошибка изменения яркости: {e}")

    return f"Яркость запрошена ({level}%), проверьте настройки экрана Windows."
