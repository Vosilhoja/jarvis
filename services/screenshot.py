import logging
import time
from io import BytesIO
from typing import List, Dict, Any, Optional
from PIL import Image
import mss

logger = logging.getLogger("jarvis")

def get_monitors_info() -> List[Dict[str, Any]]:
    """
    Возвращает список доступных экранов.
    Для ноутбука обычно это монитор 1.
    """
    monitors_list = []
    with mss.mss() as sct:
        for idx, m in enumerate(sct.monitors):
            if idx == 0:
                name = "Все экраны"
            else:
                name = f"Экран {idx} ({m['width']}x{m['height']})"
            monitors_list.append({
                "index": idx,
                "name": name,
                "width": m["width"],
                "height": m["height"],
                "left": m["left"],
                "top": m["top"],
            })
    return monitors_list

def _attach_thread_to_input_desktop():
    """Прикрепляет текущий поток к активному рабочему столу ввода Windows."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
    except Exception as e:
        logger.debug(f"Не удалось прикрепить поток к десктопу: {e}")

def take_screenshot(monitor_index: int | None = None) -> BytesIO:
    """
    Делает снимок экрана с тройным резервированием (mss -> PIL ImageGrab -> pyautogui).
    """
    _attach_thread_to_input_desktop()
    buf = BytesIO()
    
    # 1. Попытка через mss
    try:
        with mss.mss() as sct:
            idx = 0 if monitor_index is None else monitor_index
            if idx >= len(sct.monitors):
                idx = 0
            monitor = sct.monitors[idx]
            shot = sct.grab(monitor)
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            img.save(buf, format="PNG")
            buf.seek(0)
            return buf
    except Exception as e:
        logger.warning(f"mss screenshot не сработал ({e}), переключаемся на PIL ImageGrab...")

    # 2. Попытка через PIL ImageGrab
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab(all_screens=True)
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception as e:
        logger.warning(f"ImageGrab не сработал ({e}), переключаемся на pyautogui...")

    # 3. Попытка через pyautogui
    try:
        import pyautogui
        img = pyautogui.screenshot()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception as e:
        logger.error(f"Все методы создания скриншота завершились ошибкой: {e}")
        raise RuntimeError(f"Не удалось сделать скриншот: {e}")

def take_desktop_screenshot(desktop_num: int, monitor_index: int | None = None, return_to_original: bool = True) -> BytesIO:
    """
    Делает снимок указанного виртуального рабочего стола:
    1. Запоминает исходный активный рабочий стол пользователя.
    2. Переключается на целевой рабочий стол desktop_num.
    3. Делает снимок экрана.
    4. ГАРАНТИРОВАННО возвращается обратно на исходный рабочий стол пользователя!
    """
    from services.desktops_control import get_current_desktop_number, switch_to_desktop_number

    initial_desktop = get_current_desktop_number()
    logger.info(f"Скриншот стола {desktop_num}: исходный рабочий стол был {initial_desktop}")

    try:
        if initial_desktop != desktop_num:
            switch_to_desktop_number(desktop_num)
            time.sleep(0.6)  # Wait for desktop to fully render

        buf = take_screenshot(monitor_index)
        return buf
    finally:
        if return_to_original and initial_desktop != desktop_num:
            logger.info(f"Возврат на исходный рабочий стол {initial_desktop}...")
            time.sleep(0.2)
            switch_to_desktop_number(initial_desktop)
            time.sleep(0.4)

def take_multiple_desktops_screenshots(desktops: List[int], monitor_index: int | None = None) -> List[tuple[int, BytesIO]]:
    """
    Делает скриншоты нескольких рабочих столов последовательно
    и возвращает пользователя на исходный рабочий стол.
    """
    from services.desktops_control import get_current_desktop_number, switch_to_desktop_number

    initial_desktop = get_current_desktop_number()
    results = []

    try:
        for d in desktops:
            switch_to_desktop_number(d)
            time.sleep(0.6)  # Wait for desktop to fully render
            buf = take_screenshot(monitor_index)
            results.append((d, buf))
    finally:
        logger.info(f"Завершен пакетный снимок, возвращаемся на исходный стол {initial_desktop}")
        switch_to_desktop_number(initial_desktop)
        time.sleep(0.4)

    return results
