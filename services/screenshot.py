import logging
from io import BytesIO
from typing import List, Dict, Any
from PIL import Image
import mss

logger = logging.getLogger("jarvis")

def get_monitors_info() -> List[Dict[str, Any]]:
    """
    Возвращает список доступных мониторов.
    Индекс 0 в mss — это объединённый виртуальный экран (все мониторы).
    Индексы 1..N — индивидуальные физические мониторы.
    """
    monitors_list = []
    with mss.mss() as sct:
        for idx, m in enumerate(sct.monitors):
            if idx == 0:
                name = "Все мониторы (панорама)"
            else:
                name = f"Монитор {idx} ({m['width']}x{m['height']})"
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

    # 2. Попытка через PIL ImageGrab (all_screens=True для всех мониторов)
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
