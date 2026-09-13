import ctypes
import time
import pyvda

user32 = ctypes.windll.user32

PUL = ctypes.POINTER(ctypes.c_ulong)
class KeyBdInput(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL)
    ]

class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong), ("wParamL", ctypes.c_short), ("wParamH", ctypes.c_ushort)]

class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL)
    ]

class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput), ("mi", MouseInput), ("hi", HardwareInput)]

class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", Input_I)]

VK_LWIN = 0x5B
VK_CONTROL = 0x11
VK_RIGHT = 0x27
VK_LEFT = 0x25
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001

def press_hotkey_sendinput(direction="right"):
    KEYEVENTF_SCANCODE = 0x0008
    vk_arrow = VK_RIGHT if direction == "right" else VK_LEFT
    scan_win = user32.MapVirtualKeyW(VK_LWIN, 0)
    scan_ctrl = user32.MapVirtualKeyW(VK_CONTROL, 0)
    scan_arrow = user32.MapVirtualKeyW(vk_arrow, 0)

    # Win down, Ctrl down, Arrow down
    inputs = [
        Input(type=1, ii=Input_I(ki=KeyBdInput(wVk=VK_LWIN, wScan=scan_win, dwFlags=0, time=0, dwExtraInfo=None))),
        Input(type=1, ii=Input_I(ki=KeyBdInput(wVk=VK_CONTROL, wScan=scan_ctrl, dwFlags=0, time=0, dwExtraInfo=None))),
        Input(type=1, ii=Input_I(ki=KeyBdInput(wVk=vk_arrow, wScan=scan_arrow, dwFlags=KEYEVENTF_EXTENDEDKEY, time=0, dwExtraInfo=None))),
    ]
    arr = (Input * len(inputs))(*inputs)
    user32.SendInput(len(inputs), ctypes.byref(arr), ctypes.sizeof(Input))
    time.sleep(0.08)
    
    # Arrow up, Ctrl up, Win up
    inputs_up = [
        Input(type=1, ii=Input_I(ki=KeyBdInput(wVk=vk_arrow, wScan=scan_arrow, dwFlags=KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, time=0, dwExtraInfo=None))),
        Input(type=1, ii=Input_I(ki=KeyBdInput(wVk=VK_CONTROL, wScan=scan_ctrl, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=None))),
        Input(type=1, ii=Input_I(ki=KeyBdInput(wVk=VK_LWIN, wScan=scan_win, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=None))),
    ]
    arr_up = (Input * len(inputs_up))(*inputs_up)
    user32.SendInput(len(inputs_up), ctypes.byref(arr_up), ctypes.sizeof(Input))

print("Current desktop before:", pyvda.VirtualDesktop.current().number)
press_hotkey_sendinput("right")
time.sleep(0.6)
print("Current desktop after Win+Ctrl+Right:", pyvda.VirtualDesktop.current().number)
time.sleep(0.4)
press_hotkey_sendinput("left")
time.sleep(0.6)
print("Current desktop after Win+Ctrl+Left:", pyvda.VirtualDesktop.current().number)
