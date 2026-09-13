import logging
import time
import sys
import subprocess
import tempfile
import os
from io import BytesIO
from typing import List, Dict, Any

logger = logging.getLogger("jarvis")
PYTHON = sys.executable

def get_monitors_info() -> List[Dict[str, Any]]:
    return [{"index": 0, "name": "Экран 1", "width": 1920, "height": 1080, "left": 0, "top": 0}]

def take_screenshot(monitor_index: int | None = None, retries: int = 3, retry_delay: float = 0.4) -> BytesIO:
    """
    Делает скриншот. Порядок методов на каждую попытку:
    1. PIL ImageGrab
    2. mss.MSS
    3. pyautogui
    Если все три метода упали (например, BitBlt ещё не готов сразу после переключения
    стола) — короткая пауза и повтор всего цикла до `retries` раз.
    """
    last_error = None

    for attempt in range(1, retries + 1):
        buf = BytesIO()

        # 1. PIL ImageGrab
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            img.save(buf, format="PNG")
            buf.seek(0)
            logger.info(f"Скриншот: PIL ImageGrab OK (попытка {attempt})")
            return buf
        except Exception as e:
            last_error = e
            logger.warning(f"PIL ImageGrab попытка {attempt} не сработал: {e}")

        # 2. mss (новый API MSS)
        try:
            import mss as mss_lib
            from PIL import Image
            with mss_lib.MSS() as sct:
                idx = 1  # монитор 1 (0 = все экраны вместе)
                monitor = sct.monitors[idx]
                shot = sct.grab(monitor)
                img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                img.save(buf, format="PNG")
                buf.seek(0)
                logger.info(f"Скриншот: mss MSS OK (попытка {attempt})")
                return buf
        except Exception as e:
            last_error = e
            logger.warning(f"mss MSS попытка {attempt} не сработал: {e}")

        # 3. pyautogui
        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            img = pyautogui.screenshot()
            img.save(buf, format="PNG")
            buf.seek(0)
            logger.info(f"Скриншот: pyautogui OK (попытка {attempt})")
            return buf
        except Exception as e:
            last_error = e
            logger.error(f"pyautogui попытка {attempt} не сработал: {e}")

        if attempt < retries:
            time.sleep(retry_delay)

    raise RuntimeError(f"Не удалось сделать скриншот: все методы провалились ({last_error})")

def _wait_for_desktop(target: int, timeout_steps: int = 25, step_delay: float = 0.1) -> bool:
    """Ждёт, пока текущий стол реально станет target, вместо фиксированного sleep."""
    from services.desktops_control import get_current_desktop_number
    for _ in range(timeout_steps):
        if get_current_desktop_number() == target:
            time.sleep(0.25)  # дать DWM дорисовать кадр после подтверждения
            return True
        time.sleep(step_delay)
    return False

def take_desktop_screenshot(desktop_num: int, monitor_index: int | None = None, return_to_original: bool = True) -> BytesIO:
    from services.desktops_control import get_current_desktop_number, switch_to_desktop_number

    initial_desktop = get_current_desktop_number()
    logger.info(f"Скриншот стола {desktop_num}: исходный был {initial_desktop}")

    try:
        if initial_desktop != desktop_num:
            switch_to_desktop_number(desktop_num)
            _wait_for_desktop(desktop_num)

        return take_screenshot(monitor_index)
    finally:
        if return_to_original and initial_desktop != desktop_num:
            switch_to_desktop_number(initial_desktop)
            _wait_for_desktop(initial_desktop)

def take_multiple_desktops_screenshots(desktops: List[int], monitor_index: int | None = None) -> List[tuple[int, BytesIO]]:
    from services.desktops_control import get_current_desktop_number, switch_to_desktop_number

    initial_desktop = get_current_desktop_number()
    results = []

    try:
        for d in desktops:
            switch_to_desktop_number(d)
            _wait_for_desktop(d)
            buf = take_screenshot(monitor_index)
            results.append((d, buf))
    finally:
        switch_to_desktop_number(initial_desktop)
        _wait_for_desktop(initial_desktop)

    return results
    