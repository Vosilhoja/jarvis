import time
import logging
import winreg
import uuid
import pyautogui

logger = logging.getLogger("jarvis")

def get_desktop_count() -> int:
    """
    Возвращает актуальное количество виртуальных рабочих столов Windows
    путем чтения массива VirtualDesktopIDs из реестра.
    """
    try:
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\VirtualDesktops"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            val, _ = winreg.QueryValueEx(key, "VirtualDesktopIDs")
            if isinstance(val, bytes) and len(val) >= 16:
                count = len(val) // 16
                return max(1, count)
    except Exception as e:
        logger.debug(f"Не удалось прочитать VirtualDesktopIDs из реестра: {e}")
    return 1

def get_current_desktop_number() -> int:
    """
    Определяет текущий активный виртуальный рабочий стол (1-indexed).
    Сравнивает CurrentVirtualDesktop с элементами массива VirtualDesktopIDs.
    """
    try:
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\VirtualDesktops"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            val, _ = winreg.QueryValueEx(key, "VirtualDesktopIDs")
            cur, _ = winreg.QueryValueEx(key, "CurrentVirtualDesktop")
            if isinstance(val, bytes) and isinstance(cur, bytes) and len(val) >= 16:
                cur_uuid = uuid.UUID(bytes_le=cur)
                all_uuids = [uuid.UUID(bytes_le=val[i:i+16]) for i in range(0, len(val), 16)]
                if cur_uuid in all_uuids:
                    return all_uuids.index(cur_uuid) + 1
    except Exception as e:
        logger.debug(f"Не удалось определить CurrentVirtualDesktop: {e}")
    return 1

def switch_desktop_direction(direction: str):
    """Переключает рабочий стол влево или вправо (Win+Ctrl+Left / Win+Ctrl+Right)."""
    if direction == "left":
        pyautogui.hotkey("win", "ctrl", "left")
    else:
        pyautogui.hotkey("win", "ctrl", "right")
    time.sleep(0.35)

def switch_to_desktop_number(target_num: int):
    """
    Надежно переключается на указанный рабочий стол.
    Использует разницу между текущим столом или сброс в крайний левый (1-й) стол.
    """
    total = get_desktop_count()
    target_num = max(1, min(target_num, total))
    current = get_current_desktop_number()

    logger.info(f"Переключение на рабочий стол: целевой={target_num}, текущий={current}, всего={total}")

    if current == target_num:
        return

    # Относительное переключение если текущий стол известен
    diff = target_num - current
    if diff > 0:
        for _ in range(diff):
            pyautogui.hotkey("win", "ctrl", "right")
            time.sleep(0.18)
    elif diff < 0:
        for _ in range(abs(diff)):
            pyautogui.hotkey("win", "ctrl", "left")
            time.sleep(0.18)
    else:
        # Fallback сброс
        for _ in range(total + 2):
            pyautogui.hotkey("win", "ctrl", "left")
            time.sleep(0.08)
        for _ in range(target_num - 1):
            pyautogui.hotkey("win", "ctrl", "right")
            time.sleep(0.15)

    time.sleep(0.35)  # Дать Windows обновить реестр и рендер

def create_virtual_desktop() -> int:
    """Создает новый виртуальный рабочий стол (Win+Ctrl+D) и возвращает общее количество."""
    pyautogui.hotkey("win", "ctrl", "d")
    time.sleep(0.4)
    return get_desktop_count()
