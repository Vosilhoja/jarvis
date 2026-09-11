import time
import logging
import pyautogui

logger = logging.getLogger("jarvis")

# Текущий предполагаемый виртуальный рабочий стол (Windows не предоставляет простой прямой API без COM библиотек)
CURRENT_DESKTOP_ESTIMATE = 1

def switch_desktop_direction(direction: str):
    """Переключает рабочий стол влево или вправо (Win+Ctrl+Left / Win+Ctrl+Right)."""
    global CURRENT_DESKTOP_ESTIMATE
    if direction == "left":
        pyautogui.hotkey("win", "ctrl", "left")
        CURRENT_DESKTOP_ESTIMATE = max(1, CURRENT_DESKTOP_ESTIMATE - 1)
    else:
        pyautogui.hotkey("win", "ctrl", "right")
        CURRENT_DESKTOP_ESTIMATE += 1
    time.sleep(0.3)

def switch_to_desktop_number(target_num: int):
    """
    Переключается на указанный рабочий стол.
    Сначала сбрасываемся в крайнее левое положение (серией нажатий Win+Ctrl+Left),
    затем переходим вправо на target_num - 1 шагов.
    """
    global CURRENT_DESKTOP_ESTIMATE
    logger.info(f"Переключение на виртуальный рабочий стол {target_num}")
    
    # Сброс в крайний левый (максимум 10 столов)
    for _ in range(10):
        pyautogui.hotkey("win", "ctrl", "left")
        time.sleep(0.05)
    
    # Переход вправо до нужного номера
    for _ in range(max(0, target_num - 1)):
        pyautogui.hotkey("win", "ctrl", "right")
        time.sleep(0.1)

    CURRENT_DESKTOP_ESTIMATE = target_num

def create_virtual_desktop():
    """Создает новый виртуальный рабочий стол (Win+Ctrl+D)."""
    global CURRENT_DESKTOP_ESTIMATE
    pyautogui.hotkey("win", "ctrl", "d")
    CURRENT_DESKTOP_ESTIMATE += 1
    time.sleep(0.3)
