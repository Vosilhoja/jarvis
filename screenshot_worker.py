"""
Вспомогательный скрипт: принимает путь к файлу как аргумент и делает скриншот.
Предназначен для запуска через Windows Task Scheduler в сессии пользователя.
"""
import sys
import os

out_path = sys.argv[1] if len(sys.argv) > 1 else "screenshot.png"

# Метод 1: PIL ImageGrab
try:
    from PIL import ImageGrab
    img = ImageGrab.grab()
    img.save(out_path, "PNG")
    print(f"ImageGrab OK: {out_path}")
    sys.exit(0)
except Exception as e:
    print(f"ImageGrab failed: {e}", file=sys.stderr)

# Метод 2: mss
try:
    import mss
    from PIL import Image
    with mss.MSS() as sct:
        shot = sct.grab(sct.monitors[1])  # монитор 1 (не весь экран)
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        img.save(out_path, "PNG")
    print(f"mss OK: {out_path}")
    sys.exit(0)
except Exception as e:
    print(f"mss failed: {e}", file=sys.stderr)

# Метод 3: pyautogui
try:
    import pyautogui
    pyautogui.FAILSAFE = False
    img = pyautogui.screenshot()
    img.save(out_path, "PNG")
    print(f"pyautogui OK: {out_path}")
    sys.exit(0)
except Exception as e:
    print(f"pyautogui failed: {e}", file=sys.stderr)

print("ALL FAILED", file=sys.stderr)
sys.exit(1)
