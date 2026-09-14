"""Compatibility facade for the historical Windows miscellaneous tools API."""
from ._common import CREATE_NO_WINDOW, ExtraResult, _decode, _run
from .files import (
    empty_recycle_bin, find_file_broad, get_desktop_folder_sizes, get_downloads_list,
    get_file_info, get_folder_changes_today, recycle_bin_info, search_files, unzip_path,
    zip_path,
)
from .input import (
    close_active_window, minimize_all_windows, mouse_click_at, mouse_drag_to,
    mouse_move_to, mouse_scroll_units, show_desktop, toggle_caps_lock,
)
from .security_tools import (
    base64_convert, defender_status, firewall_status, generate_password, generate_uuid,
    hash_text, random_util,
)
from .system_utilities import (
    clear_browser_cache, create_restore_point, do_not_disturb_mode, generate_qr_png,
    get_datetime_info, get_hardware_info, get_installed_updates, list_audio_devices,
    list_printers, list_startup_apps, list_usb_devices, open_night_light,
    set_process_volume, set_wallpaper, speak_text, toggle_dark_mode,
    toggle_keyboard_backlight,
)
from .window_manager import (
    QUICK_APPS, _enum_windows, focus_window, get_active_window, hide_all_windows_except_active,
    list_open_windows, open_device_manager, open_event_viewer, open_task_scheduler,
    open_windows_tool, quick_launch, restart_explorer,
)

__all__ = [
    "ExtraResult", "CREATE_NO_WINDOW", "empty_recycle_bin", "recycle_bin_info",
    "get_desktop_folder_sizes", "search_files", "find_file_broad", "get_downloads_list",
    "get_file_info", "zip_path", "unzip_path", "QUICK_APPS", "quick_launch",
    "open_windows_tool", "open_device_manager", "open_event_viewer", "open_task_scheduler",
    "restart_explorer", "list_open_windows", "get_active_window", "focus_window",
    "show_desktop", "get_hardware_info", "list_usb_devices", "list_printers",
    "list_startup_apps", "firewall_status", "defender_status", "generate_password",
    "generate_uuid", "hash_text", "base64_convert", "random_util", "get_datetime_info",
    "speak_text", "generate_qr_png", "toggle_keyboard_backlight", "do_not_disturb_mode",
    "toggle_dark_mode", "open_night_light", "mouse_move_to", "mouse_click_at",
    "mouse_drag_to", "mouse_scroll_units", "clear_browser_cache", "create_restore_point",
    "set_wallpaper", "toggle_caps_lock", "list_audio_devices", "set_process_volume",
    "close_active_window", "minimize_all_windows", "get_installed_updates",
    "hide_all_windows_except_active", "get_folder_changes_today",
]
