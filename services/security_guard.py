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

        # Запоминаем активное окно (детектирует Alt+Tab, клик по таскбару и т.д.,
        # даже если это сделано с клавиатуры/тачпада без движения мыши)
        start_foreground_hwnd = ctypes.windll.user32.GetForegroundWindow()

        # Запоминаем текущий виртуальный рабочий стол (детектирует свайп тачпада
        # 3-4 пальцами или Win+Ctrl+Left/Right — тоже без движения курсора мыши)
        try:
            from services.desktops_control import get_current_desktop_number
            start_desktop = get_current_desktop_number()
        except Exception:
            start_desktop = None

        logger.info(
            f"Режим охраны АКТИВИРОВАН. Позиция: ({start_x}, {start_y}), "
            f"окно: {start_foreground_hwnd}, стол: {start_desktop}"
        )

        desktop_check_counter = 0
        while not self._cancel_event.is_set():
            time.sleep(0.05)
            trigger_reason = None

            # 1. Проверка движения мыши
            try:
                cur_x, cur_y = pyautogui.position()
            except Exception:
                pt = ctypes.wintypes.POINT()
                ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
                cur_x, cur_y = pt.x, pt.y

            if abs(cur_x - start_x) > 3 or abs(cur_y - start_y) > 3:
                trigger_reason = f"мышь переместилась из ({start_x}, {start_y}) в ({cur_x}, {cur_y})"

            # 2. Проверка смены активного окна (Alt+Tab, клик по таскбару, тачпад-жест)
            if not trigger_reason:
                cur_foreground_hwnd = ctypes.windll.user32.GetForegroundWindow()
                if cur_foreground_hwnd != start_foreground_hwnd:
                    trigger_reason = "сменилось активное окно (Alt+Tab / переключение приложения)"

            # 3. Проверка смены виртуального рабочего стола (раз в ~0.5 сек — дороже по CPU)
            if not trigger_reason and start_desktop is not None:
                desktop_check_counter += 1
                if desktop_check_counter >= 10:
                    desktop_check_counter = 0
                    try:
                        from services.desktops_control import get_current_desktop_number
                        cur_desktop = get_current_desktop_number()
                        if cur_desktop != start_desktop:
                            trigger_reason = f"сменился рабочий стол ({start_desktop} → {cur_desktop})"
                    except Exception:
                        pass

            if trigger_reason:
                logger.warning(f"🚨 ОХРАНА СРАБОТАЛА! Причина: {trigger_reason}")
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


def make_guard_alert_callback(bot, chat_id: int, loop=None):
    """Создаёт единый callback тревоги охраны для отправки в Telegram.

    Раньше этот же код (текст тревоги + asyncio.run_coroutine_threadsafe)
    был продублирован дословно в handlers/menu/reply_router.py (запуск через
    кнопку "🛡 Включить охрану") и в core/execution/system_actions.py (запуск
    через AI-интент start_guard) — два места, которые легко было разойтись
    друг с другом. Теперь оба используют эту фабрику.
    """
    import asyncio as _asyncio

    def on_guard_triggered(sx, sy, cx, cy):
        alert_text = (
            f"🚨 *ТРЕВОГА! РЕЖИМ ОХРАНЫ СРАБОТАЛ!*\n\n"
            f"Зафиксировано движение мыши/смена окна или рабочего стола!\n"
            f"📍 Исходные координаты: `({sx}, {sy})`\n"
            f"📍 Новые координаты: `({cx}, {cy})`\n\n"
            f"🔒 *Компьютер немедленно заблокирован!*"
        )
        try:
            target_loop = loop or _asyncio.get_event_loop()
            _asyncio.run_coroutine_threadsafe(
                bot.send_message(chat_id=chat_id, text=alert_text, parse_mode="Markdown"),
                target_loop,
            )
        except Exception as e:
            logger.error(f"Не удалось отправить тревожное сообщение охраны: {e}")

    return on_guard_triggered
