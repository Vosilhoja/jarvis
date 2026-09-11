from io import BytesIO
from typing import List, Dict, Any
from PIL import Image
import mss

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

def take_screenshot(monitor_index: int | None = None) -> BytesIO:
    """
    Делает снимок экрана:
    - monitor_index is None или 0 -> объединённый скриншот всех мониторов
    - monitor_index >= 1 -> конкретный монитор (нумерация с 1)
    """
    with mss.mss() as sct:
        idx = 0 if monitor_index is None else monitor_index
        # Проверяем допустимость индекса
        if idx >= len(sct.monitors):
            idx = 0
        monitor = sct.monitors[idx]
        shot = sct.grab(monitor)
        
        # Конвертация mss BGRA в Pillow RGB
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf
