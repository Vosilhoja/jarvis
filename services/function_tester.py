"""
Function tester for Jarvis: runs a dry-run simulation of many service functions
without performing real system-affecting operations.
Generates a JSON report at runtime: ./.function_test_report.json

Usage: python -m services.function_tester (or run as script)
"""
from __future__ import annotations

import importlib
import inspect
import json
import logging
import os
import types
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("jarvis.test")

REPORT_PATH = Path.cwd() / ".function_test_report.json"

# A conservative registry of functions to test with example args
TEST_REGISTRY: Dict[str, List[Any]] = {
    "services.extra_functions.get_local_ip": [],
    "services.extra_functions.get_public_ip": [],
    "services.extra_functions.ping_host": ["8.8.8.8"],
    "services.extra_functions.get_screen_resolution": [],
    "services.extra_functions.get_idle_time": [],
    "services.extra_functions.toggle_keyboard_backlight": [],
    "services.extra_functions.mouse_move_to": [10, 10],
    "services.extra_functions.mouse_click_at": [10, 10, "left", 1],
    "services.extra_functions.mouse_drag_to": [20, 20],
    "services.extra_functions.mouse_scroll_units": [3],
    "services.extra_functions.open_notepad_quick_note": ["test note from tester"],
    "services.extra_functions.take_screenshot": [],
    "services.screenshot.take_screenshot": [],
    "services.extra_functions.get_battery_info": [],
    "services.new_features.generate_system_health_summary": [],
}

# Auto-discovery settings: when new functions are added under services/, discover and add safe ones to TEST_REGISTRY
AUTO_REGISTRY_PATH = Path.cwd() / ".auto_test_registry.json"
DANGEROUS_KEYWORDS = [
    'shutdown', 'restart', 'format', 'delete', 'erase', 'factory', 'empty_recycle_bin',
    'hibernate', 'sleep', 'shutdown_pc', 'restart_pc', 'poweroff', 'reboot', 'factory_reset'
]


def discover_tests() -> Dict[str, Dict[str, object]]:
    """Discover callables under services/ and return a mapping with metadata.
    Safe functions (no dangerous keywords) are merged into TEST_REGISTRY with default args=[]
    Returns a dict of discovered entries: {path: {'args': [], 'skipped': bool, 'reason': str}}
    """
    discovered: Dict[str, Dict[str, object]] = {}
    services_dir = Path(__file__).parent
    for p in services_dir.glob('*.py'):
        name = p.stem
        if name.startswith('_') or name in ('function_tester',):
            continue
        mod_path = f"services.{name}"
        try:
            mod = importlib.import_module(mod_path)
        except Exception as e:
            logger.debug("discover_tests: failed to import %s: %s", mod_path, e)
            continue
        for attr_name, obj in inspect.getmembers(mod, inspect.isfunction):
            if getattr(obj, '__module__', None) != mod.__name__:
                continue
            if attr_name.startswith('_'):
                continue
            path = f"{mod.__name__}.{attr_name}"
            # default metadata
            meta = {'args': [], 'skipped': False, 'reason': ''}
            doc = inspect.getdoc(obj) or ''
            # parse AUTO_TEST: JSON-like in docstring, e.g. AUTO_TEST: [1,2]
            import ast
            for line in doc.splitlines():
                if line.strip().startswith('AUTO_TEST:'):
                    try:
                        raw = line.split(':', 1)[1].strip()
                        meta['args'] = ast.literal_eval(raw)
                    except Exception:
                        meta['reason'] = 'AUTO_TEST parse failed'
            # detect dangerous names
            lname = attr_name.lower()
            if any(k in lname for k in DANGEROUS_KEYWORDS):
                meta['skipped'] = True
                meta['reason'] = 'Matches dangerous keyword'
            discovered[path] = meta
            # Merge safe ones into TEST_REGISTRY if not present
            if not meta['skipped'] and path not in TEST_REGISTRY:
                logger.info('discover_tests: adding %s to TEST_REGISTRY (args=%s)', path, meta['args'])
                TEST_REGISTRY[path] = meta['args']

    # write auto registry to disk for review
    try:
        AUTO_REGISTRY_PATH.write_text(json.dumps(discovered, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        logger.exception('Failed to write auto registry')
    return discovered

# Run discovery at module import time so new functions are visible automatically
try:
    _ = discover_tests()
except Exception:
    logger.exception('discover_tests failed during import')

# Stubs for system-affecting operations
class StubCompletedProcess:
    def __init__(self, returncode=0, stdout=b"", stderr=b""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

@contextmanager
def dry_run_patches():
    """Context manager that monkeypatches risky functions to safe stubs."""
    # Patch subprocess.run/_run
    import subprocess
    import builtins
    import types

    orig_subprocess_run = subprocess.run

    def fake_run(cmd, capture_output=True, timeout=None, shell=False, creationflags=0):
        logger.info("[dry-run] subprocess.run called: %s", cmd)
        return StubCompletedProcess(returncode=0, stdout=b"(dry-run)" )

    subprocess.run = fake_run

    # Patch os.startfile
    import os as _os
    orig_startfile = getattr(_os, "startfile", None)
    def fake_startfile(path):
        logger.info("[dry-run] os.startfile called: %s", path)
        return None
    _os.startfile = fake_startfile

    # Patch pyautogui if present
    fake_pyautogui = types.SimpleNamespace()
    def _fake_noop(*a, **k):
        logger.info("[dry-run] pyautogui stub called with %s %s", a, k)
        return None
    try:
        import pyautogui as real_pyautogui
        orig_pyautogui = real_pyautogui
        # Replace functions used in extra_functions
        real_pyautogui_fail = getattr(real_pyautogui, 'FAILSAFE', None)
        real_pyautogui.FAILSAFE = False
        real_pyautogui.moveTo = lambda *a, **k: logger.info("[dry-run] pyautogui.moveTo %s %s", a, k)
        real_pyautogui.click = lambda *a, **k: logger.info("[dry-run] pyautogui.click %s %s", a, k)
        real_pyautogui.dragTo = lambda *a, **k: logger.info("[dry-run] pyautogui.dragTo %s %s", a, k)
        real_pyautogui.scroll = lambda *a, **k: logger.info("[dry-run] pyautogui.scroll %s %s", a, k)
        real_pyautogui.hotkey = lambda *a, **k: logger.info("[dry-run] pyautogui.hotkey %s %s", a, k)
    except Exception:
        orig_pyautogui = None

    # Patch ctypes.windll calls to no-op that return reasonable defaults
    try:
        import ctypes
        orig_windll = ctypes.windll
        class FakeDLL:
            def __getattr__(self, name):
                return lambda *a, **k: 0
        ctypes.windll = FakeDLL()
    except Exception:
        orig_windll = None

    # Patch PIL.ImageGrab and mss screenshot functions to return a small PNG bytes object
    try:
        from PIL import Image
        def fake_screenshot_bytes():
            img = Image.new("RGB", (100, 60), color=(73, 109, 137))
            buf = BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            return buf
        # monkeypatch services.screenshot internal functions by attribute assignment later
    except Exception:
        fake_screenshot_bytes = None

    # Yield control to run tests within patched environment
    try:
        yield {
            "orig_subprocess_run": orig_subprocess_run,
            "orig_startfile": orig_startfile,
            "orig_pyautogui": orig_pyautogui,
            "orig_windll": orig_windll,
            "fake_screenshot_bytes": fake_screenshot_bytes,
        }
    finally:
        # restore originals
        subprocess.run = orig_subprocess_run
        if orig_startfile is not None:
            _os.startfile = orig_startfile
        if orig_pyautogui is not None:
            # We can't reliably restore all attributes; best-effort: reload module
            try:
                import importlib
                importlib.reload(orig_pyautogui)
            except Exception:
                pass
        if orig_windll is not None:
            ctypes.windll = orig_windll


@dataclass
class TestResult:
    name: str
    success: bool
    error: Optional[str] = None
    output_repr: Optional[str] = None
    notes: Optional[str] = None


def import_callable(path: str) -> Callable:
    mod_name, fn_name = path.rsplit('.', 1)
    mod = importlib.import_module(mod_name)
    return getattr(mod, fn_name)


def run_single_test(path: str, args: List[Any], fake_screenshot_bytes: Optional[Callable[[], BytesIO]] = None) -> TestResult:
    try:
        fn = import_callable(path)
    except Exception as e:
        return TestResult(name=path, success=False, error=f"Import error: {e}")

    # If target is screenshot functions and we have fake screenshot, monkeypatch it
    if path in ("services.screenshot.take_screenshot", "services.extra_functions.take_screenshot") and fake_screenshot_bytes:
        # in services.screenshot, replace take_screenshot implementation temporarily
        try:
            import services.screenshot as ss
            orig = getattr(ss, 'take_screenshot', None)
            ss.take_screenshot = lambda monitor_index=None: fake_screenshot_bytes()
        except Exception:
            orig = None
    else:
        orig = None

    try:
        # Call the function with provided args
        res = fn(*args) if isinstance(args, (list, tuple)) else fn(args)
        # represent result safely
        if isinstance(res, BytesIO):
            out = f"BytesIO len={len(res.getvalue())}"
        else:
            out = repr(res)
        return TestResult(name=path, success=True, output_repr=out)
    except Exception as e:
        return TestResult(name=path, success=False, error=str(e))
    finally:
        if orig is not None:
            try:
                import importlib
                import services.screenshot as ss
                ss.take_screenshot = orig
            except Exception:
                pass


def run_all_tests() -> List[TestResult]:
    results: List[TestResult] = []
    with dry_run_patches() as ctx:
        fake_screenshot_bytes = ctx.get('fake_screenshot_bytes')
        for path, args in TEST_REGISTRY.items():
            logger.info("Running test: %s with args=%s", path, args)
            res = run_single_test(path, args, fake_screenshot_bytes=fake_screenshot_bytes)
            results.append(res)
    return results


def write_report(results: List[TestResult]):
    data = [asdict(r) for r in results]
    REPORT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    logger.info("Report written to %s", REPORT_PATH)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', default=str(REPORT_PATH))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    results = run_all_tests()
    write_report(results)
    good = sum(1 for r in results if r.success)
    bad = len(results) - good
    print(f"Function tester finished: {good} succeeded, {bad} failed. Report: {REPORT_PATH}")


if __name__ == '__main__':
    main()
