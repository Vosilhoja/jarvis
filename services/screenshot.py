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

def take_screenshot(monitor_index: int | None = None) -> BytesIO:
    """
    Делает скриншот. Порядок методов:
    1. PIL ImageGrab (работает в GUI-процессе бота)
    2. mss.MSS (новый API)
    3. pyautogui
    """
    buf = BytesIO()

    # 1. PIL ImageGrab
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        img.save(buf, format="PNG")
        buf.seek(0)
        logger.info("Скриншот: PIL ImageGrab OK")
        return buf
    except Exception as e:
        logger.warning(f"PIL ImageGrab failed: {e}")

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
            logger.info("Скриншот: mss MSS OK")
            return buf
    except Exception as e:
        logger.warning(f"mss MSS failed: {e}")

    # 3. pyautogui
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        img = pyautogui.screenshot()
        img.save(buf, format="PNG")
        buf.seek(0)
        logger.info("Скриншот: pyautogui OK")
        return buf
    except Exception as e:
        logger.error(f"pyautogui failed: {e}")

    raise RuntimeError("Не удалось сделать скриншот: все методы провалились")

def take_desktop_screenshot(desktop_num: int, monitor_index: int | None = None, return_to_original: bool = True) -> BytesIO:
    from services.desktops_control import get_current_desktop_number, switch_to_desktop_number

    initial_desktop = get_current_desktop_number()
    logger.info(f"Скриншот стола {desktop_num}: исходный был {initial_desktop}")

    try:
        if initial_desktop != desktop_num:
            switch_to_desktop_number(desktop_num)
            time.sleep(1.5)  # Ждём анимацию + полный рендер

        return take_screenshot(monitor_index)
    finally:
        if return_to_original and initial_desktop != desktop_num:
            time.sleep(0.3)
            switch_to_desktop_number(initial_desktop)
            time.sleep(0.5)

def take_multiple_desktops_screenshots(desktops: List[int], monitor_index: int | None = None) -> List[tuple[int, BytesIO]]:
    from services.desktops_control import get_current_desktop_number, switch_to_desktop_number

    initial_desktop = get_current_desktop_number()
    results = []

    try:
        for d in desktops:
            switch_to_desktop_number(d)
            time.sleep(1.5)  # Ждём анимацию + полный рендер
            buf = take_screenshot(monitor_index)
            results.append((d, buf))
    finally:
        switch_to_desktop_number(initial_desktop)
        time.sleep(0.5)

    return results
