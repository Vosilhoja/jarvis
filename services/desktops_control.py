import time
import logging
import winreg
import uuid
import subprocess
import tempfile
import sys
import os

logger = logging.getLogger("jarvis")
PYTHON = sys.executable


def get_desktop_count() -> int:
    try:
        import pyvda
        desktops = pyvda.get_virtual_desktops()
        if desktops:
            return len(desktops)
    except Exception as e:
        logger.debug(f"pyvda get_virtual_desktops failed: {e}")

    try:
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\VirtualDesktops"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            val, _ = winreg.QueryValueEx(key, "VirtualDesktopIDs")
            if isinstance(val, bytes) and len(val) >= 16:
                return max(1, len(val) // 16)
    except Exception as e:
        logger.debug(f"Реестр VirtualDesktopIDs failed: {e}")
    return 1


def get_current_desktop_number() -> int:
    try:
        import pyvda
        cur = pyvda.VirtualDesktop.current()
        if cur and cur.number:
            return cur.number
    except Exception as e:
        logger.debug(f"pyvda current failed: {e}")

    try:
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\VirtualDesktops"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            val, _ = winreg.QueryValueEx(key, "VirtualDesktopIDs")
            cur, _ = winreg.QueryValueEx(key, "CurrentVirtualDesktop")
            if isinstance(val, bytes) and isinstance(cur, bytes) and len(val) >= 16:
                cur_uuid = uuid.UUID(bytes_le=cur)
                all_uuids = [uuid.UUID(bytes_le=val[i:i+16]) for i in range(0, len(val), 16)]
                if cur_uuid in all_uuids:
                    return all_uuids.index(cur_uuid) + 1
    except Exception as e:
        logger.debug(f"Реестр CurrentVirtualDesktop failed: {e}")
    return 1


def _switch_via_subprocess(steps: int, direction: str):
    """
    Нажимает Win+Ctrl+Right/Left через subprocess.
    Subprocess запускается в контексте рабочего стола и имеет полный доступ к вводу.
    """
    script_file = tempfile.mktemp(suffix="_switch.py")
    script_code = f"""\
import pyautogui, time
pyautogui.FAILSAFE = False
for _ in range({steps}):
    pyautogui.hotkey('win', 'ctrl', '{direction}')
    time.sleep(0.4)
"""
    try:
        with open(script_file, "w", encoding="utf-8") as f:
            f.write(script_code)

        subprocess.run(
            [PYTHON, script_file],
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except Exception as e:
        logger.error(f"subprocess switch failed: {e}")
    finally:
        try:
            os.unlink(script_file)
        except Exception:
            pass


def switch_to_desktop_number(target_num: int):
    """
    Переключается на рабочий стол target_num (1-indexed).
    Сначала пробует pyvda COM API, при сбое — subprocess Win+Ctrl+←/→.
    """
    logger.info(f"Переключение на рабочий стол {target_num}")

    # 1. pyvda COM API (надёжно, работает из любого потока)
    try:
        import pyvda
        desktops = pyvda.get_virtual_desktops()
        if desktops and 1 <= target_num <= len(desktops):
            desktops[target_num - 1].go()
            time.sleep(0.4)
            logger.info(f"pyvda: переключено на стол {target_num}")
            return
    except Exception as e:
        logger.warning(f"pyvda switch failed: {e}, используем subprocess Win+Ctrl+←/→")

    # 2. Subprocess Win+Ctrl+←/→ (с анимацией)
    total = get_desktop_count()
    target_num = max(1, min(target_num, total))
    current = get_current_desktop_number()

    if current == target_num:
        return

    diff = target_num - current
    steps = abs(diff)
    direction = "right" if diff > 0 else "left"

    logger.info(f"subprocess: {current} -> {target_num}, {steps}x {direction}")
    _switch_via_subprocess(steps, direction)
    time.sleep(0.5)


def switch_desktop_direction(direction: str):
    cur = get_current_desktop_number()
    if direction == "left":
        switch_to_desktop_number(cur - 1)
    else:
        switch_to_desktop_number(cur + 1)


def create_virtual_desktop() -> int:
    try:
        import pyvda
        pyvda.VirtualDesktop.create()
        time.sleep(0.3)
        return len(pyvda.get_virtual_desktops())
    except Exception as e:
        logger.warning(f"pyvda create failed: {e}")
        old_count = get_desktop_count()
        script_file = tempfile.mktemp(suffix="_newdesk.py")
        with open(script_file, "w") as f:
            f.write("import pyautogui, time\npyautogui.FAILSAFE=False\npyautogui.hotkey('win','ctrl','d')\ntime.sleep(0.5)\n")
        try:
            subprocess.run([PYTHON, script_file], timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
        finally:
            try: os.unlink(script_file)
            except: pass
        for _ in range(12):
            time.sleep(0.1)
            if get_desktop_count() > old_count:
                break
        return get_desktop_count()
