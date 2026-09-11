import win32api
import win32con
import logging
from typing import Optional

logger = logging.getLogger("jarvis")

# Константы виртуальных клавиш для мультимедиа
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3

def _press_key(vk_code: int):
    """Посылает событие нажатия виртуальной клавиши Windows."""
    win32api.keybd_event(vk_code, 0, 0, 0)
    win32api.keybd_event(vk_code, 0, win32con.KEYEVENTF_KEYUP, 0)

def media_play_pause():
    _press_key(VK_MEDIA_PLAY_PAUSE)

def media_next():
    _press_key(VK_MEDIA_NEXT_TRACK)

def media_prev():
    _press_key(VK_MEDIA_PREV_TRACK)

def media_stop():
    _press_key(VK_MEDIA_STOP)

def set_volume_pycaw(level_percent: int) -> bool:
    """Устанавливает громкость через pycaw (0-100)."""
    try:
        from pycaw.pycaw import AudioUtilities
        devices = AudioUtilities.GetSpeakers()
        volume = devices.EndpointVolume
        norm_level = max(0.0, min(1.0, level_percent / 100.0))
        volume.SetMasterVolumeLevelScalar(norm_level, None)
        return True
    except Exception as e:
        logger.warning(f"Ошибка pycaw при установке громкости: {e}. Используем эмуляцию кнопок.")
        return False

def change_volume(direction: str, level: Optional[int] = None) -> str:
    """Изменяет громкость или включает mute."""
    if level is not None:
        if set_volume_pycaw(level):
            return f"Громкость установлена на {level}%"
    
    if direction == "up":
        for _ in range(5):
            _press_key(VK_VOLUME_UP)
        return "Громкость увеличена (+10%)"
    elif direction == "down":
        for _ in range(5):
            _press_key(VK_VOLUME_DOWN)
        return "Громкость уменьшена (-10%)"
    elif direction in ("mute", "unmute"):
        _press_key(VK_VOLUME_MUTE)
        return "Звук переключен (Mute/Unmute)"
    
    return "Громкость изменена"

def set_brightness(level: int) -> str:
    """Устанавливает яркость экрана через WMI (для ноутбуков и поддерживаемых мониторов)."""
    level = max(0, min(100, level))
    try:
        import wmi
        w = wmi.WMI(namespace='wmi')
        methods = w.WmiMonitorBrightnessMethods()
        if not methods:
            return "⚠️ Яркость не управляется программно на этом устройстве (внешний монитор или ПК без поддержки DDC/CI)."
        methods[0].WmiSetBrightness(level, 0)
        return f"Яркость установлена на {level}%"
    except Exception as e:
        logger.warning(f"Не удалось изменить яркость: {e}")
        return "⚠️ Яркость не управляется программно на этом мониторе."
