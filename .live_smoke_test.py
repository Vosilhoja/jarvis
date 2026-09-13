from services import extra_functions
from services.screenshot import take_screenshot
import pyautogui
import tempfile
import time
import os


def main():
    try:
        pyautogui.FAILSAFE = False
    except Exception:
        pass

    try:
        orig = pyautogui.position()
    except Exception as e:
        print('Failed to get current mouse position:', e)
        orig = None

    try:
        size = pyautogui.size()
        cx, cy = size.width // 2, size.height // 2
    except Exception:
        # Fallback to 800x600 center
        cx, cy = 800 // 2, 600 // 2

    print('Original position:', orig)
    print(f'Moving mouse to center ({cx},{cy})')
    try:
        out = extra_functions.mouse_move_to(cx, cy)
        print('mouse_move_to ->', out)
    except Exception as e:
        print('mouse_move_to exception:', e)

    time.sleep(0.25)

    print('Clicking at center')
    try:
        out = extra_functions.mouse_click_at(cx, cy)
        print('mouse_click_at ->', out)
    except Exception as e:
        print('mouse_click_at exception:', e)

    time.sleep(0.4)

    print('Taking screenshot...')
    try:
        buf = take_screenshot()
        td = tempfile.gettempdir()
        path = os.path.join(td, f'jarvis_live_smoke_{int(time.time())}.png')
        with open(path, 'wb') as f:
            f.write(buf.getvalue())
        print('Screenshot saved to', path)
    except Exception as e:
        print('Screenshot failed:', e)

    time.sleep(0.25)

    if orig:
        try:
            extra_functions.mouse_move_to(orig.x, orig.y)
            print('Restored mouse to original position')
        except Exception as e:
            print('Failed to restore mouse position:', e)

    print('Live smoke test finished')


if __name__ == '__main__':
    main()
