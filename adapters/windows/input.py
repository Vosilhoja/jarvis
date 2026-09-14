"""Mouse and keyboard input actions."""
from __future__ import annotations


def show_desktop() -> str:
    try:
        import pyautogui
        pyautogui.hotkey("win", "d")
        return "🖥 Показан рабочий стол (Win+D)"
    except Exception as e:
        return f"Ошибка: {e}"


def mouse_move_to(x: int, y: int) -> str:
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.moveTo(x, y, duration=0.2)
        return f"🖱 Курсор перемещен в ({x}, {y})"
    except Exception as e:
        return f"Ошибка мыши: {e}"


def mouse_click_at(x: int, y: int, button: str = "left", clicks: int = 1) -> str:
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.click(x=x, y=y, clicks=clicks, button=button)
        return f"🖱 Клик ({button}, {clicks}x) в ({x}, {y})"
    except Exception as e:
        return f"Ошибка клика: {e}"


def mouse_drag_to(x: int, y: int) -> str:
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.dragTo(x, y, duration=0.4, button="left")
        return f"🖱 Drag&Drop в ({x}, {y})"
    except Exception as e:
        return f"Ошибка drag: {e}"


def mouse_scroll_units(amount: int) -> str:
    try:
        import pyautogui
        pyautogui.scroll(amount)
        return f"🖱 Скролл на {amount} ед."
    except Exception as e:
        return f"Ошибка скролла: {e}"


def toggle_caps_lock() -> str:
    try:
        import pyautogui
        pyautogui.press("capslock")
        return "⌨ Нажат Caps Lock"
    except Exception as e:
        return f"Ошибка: {e}"


def close_active_window() -> str:
    try:
        import pyautogui
        pyautogui.hotkey("alt", "f4")
        return "❌ Нажато Alt+F4 для активного окна"
    except Exception as e:
        return f"Ошибка: {e}"


def minimize_all_windows() -> str:
    try:
        import pyautogui
        pyautogui.hotkey("win", "d")
        return "🖥 Все окна свернуты / показан рабочий стол"
    except Exception as e:
        return f"Ошибка: {e}"
