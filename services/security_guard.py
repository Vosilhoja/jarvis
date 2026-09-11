"""
Модуль охраны ПК (Режим сторожа при движении мыши).
При активации дает пользователю 5 секунд, чтобы убрать руку от мыши.
После этого отслеживает координаты курсора.
Если мышь сдвинулась хоть на пиксель:
1. Мгновенно блокирует экран (LockWorkStation).
2. Отправляет тревожное уведомление пользователю в Telegram с фото/скриншотом.
Пользователь может в любой момент выключить режим охраны кнопкой из бота.
"""
import time
import ctypes
import threading
import logging
from typing import Optional, Callable

import pyautogui

logger = logging.getLogger("jarvis")

class SecurityGuard:
    def __init__(self):
        self._is_active = False
        self._thread: Optional[threading.Thread] = None
        self._on_trigger_callback: Optional[Callable] = None
        self._cancel_event = threading.Event()

    def is_active(self) -> bool:
        return self._is_active

    def start_guard(self, on_trigger_callback: Optional[Callable] = None, delay_sec: int = 5) -> str:
        """
        Запускает режим охраны в отдельном потоке.
        """
        if self._is_active:
            return "🛡 Режим охраны УЖЕ активен!"

        self._is_active = True
        self._cancel_event.clear()
        self._on_trigger_callback = on_trigger_callback

        self._thread = threading.Thread(target=self._guard_loop, args=(delay_sec,), daemon=True)
        self._thread.start()
        return f"🛡 *Режим охраны активирован!*\n\nУ вас есть *{delay_sec} секунд*, чтобы убрать руку от мыши. При любом движении мыши экран будет мгновенно заблокирован!"

    def stop_guard(self) -> str:
        """
        Отключает режим охраны.
        """
        if not self._is_active:
            return "🛡 Режим охраны не был активен."

        self._is_active = False
        self._cancel_event.set()
        logger.info("Режим охраны остановлен пользователем.")
        return "🛡 Режим охраны успешно ОТКЛЮЧЕН."

    def _guard_loop(self, delay_sec: int):
        logger.info(f"Режим охраны: задержка {delay_sec} сек...")
        # Ожидаем delay_sec с возможностью досрочной отмены
        for _ in range(delay_sec * 10):
            if self._cancel_event.is_set():
                self._is_active = False
                return
            time.sleep(0.1)

        # Запоминаем исходные координаты
        try:
            start_x, start_y = pyautogui.position()
        except Exception:
            pt = ctypes.wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            start_x, start_y = pt.x, pt.y

        logger.info(f"Режим охраны АКТИВИРОВАН. Исходная позиция: ({start_x}, {start_y})")

        while not self._cancel_event.is_set():
            time.sleep(0.05)
            try:
                cur_x, cur_y = pyautogui.position()
            except Exception:
                pt = ctypes.wintypes.POINT()
                ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
                cur_x, cur_y = pt.x, pt.y

            # Если мышь сдвинулась больше чем на 3 пикселя (защита от микро-дрожания сенсора)
            if abs(cur_x - start_x) > 3 or abs(cur_y - start_y) > 3:
                logger.warning(f"🚨 ОХРАНА СРАБОТАЛА! Мышь переместилась из ({start_x}, {start_y}) в ({cur_x}, {cur_y})!")
                # 1. Блокируем Windows
                ctypes.windll.user32.LockWorkStation()
                self._is_active = False

                # 2. Вызываем колбэк уведомления (если передан)
                if self._on_trigger_callback:
                    try:
                        self._on_trigger_callback(start_x, start_y, cur_x, cur_y)
                    except Exception as e:
                        logger.error(f"Ошибка вызова on_trigger_callback охраны: {e}")
                break

security_guard = SecurityGuard()
