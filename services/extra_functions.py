"""Compatibility facade re-exporting modular services for legacy callers."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from services.clipboard_tools import (
    CLIPBOARD_HISTORY,
    get_clipboard,
    record_clipboard_item,
    set_clipboard,
)
from services.misc_tools import (
    CREATE_NO_WINDOW,
    ExtraResult,
    QUICK_APPS,
    _decode,
    _run,
    base64_convert,
    defender_status,
    do_not_disturb_mode,
    empty_recycle_bin,
    firewall_status,
    focus_window,
    generate_password,
    generate_qr_png,
    generate_uuid,
    get_active_window,
    get_datetime_info,
    get_desktop_folder_sizes,
    get_downloads_list,
    get_file_info,
    get_hardware_info,
    hash_text,
    list_open_windows,
    list_printers,
    list_startup_apps,
    list_usb_devices,
    mouse_click_at,
    mouse_drag_to,
    mouse_move_to,
    mouse_scroll_units,
    open_device_manager,
    open_event_viewer,
    open_night_light,
    open_task_scheduler,
    open_windows_tool,
    quick_launch,
    random_util,
    recycle_bin_info,
    restart_explorer,
    search_files,
    show_desktop,
    speak_text,
    toggle_dark_mode,
    toggle_keyboard_backlight,
    unzip_path,
    zip_path,
    clear_browser_cache,
    create_restore_point,
    set_wallpaper,
    toggle_caps_lock,
    list_audio_devices,
    set_process_volume,
    close_active_window,
    minimize_all_windows,
    get_installed_updates,
)
from services.network_tools import (
    flush_dns,
    get_local_ip,
    get_mac_and_hostname,
    get_network_adapters,
    get_public_ip,
    get_wifi_networks,
    ipconfig_summary,
    ping_host,
    speed_test,
    traceroute_host,
)
from services.notes import open_notepad_quick_note
from services.power_tools import (
    cancel_shutdown,
    get_battery_info,
    get_battery_report,
    get_idle_time,
    get_screen_resolution,
    hibernate_pc,
    set_power_plan,
    laptop_screen_sleep,
    sleep_pc_mode,
)

logger = logging.getLogger("jarvis")


def dispatch_extra(intent: str, params: Dict[str, Any], session: Any) -> Optional[ExtraResult]:
    """Compatibility dispatcher routing intents to appropriate modular tools."""
    try:
        if intent == "get_clipboard":
            return ExtraResult(True, get_clipboard())
        if intent == "set_clipboard":
            return ExtraResult(True, set_clipboard(params.get("text", "")))
        if intent == "get_local_ip":
            return ExtraResult(True, f"🏠 Локальный IP: `{get_local_ip()}`")
        if intent == "get_public_ip":
            return ExtraResult(True, f"🌍 Внешний IP: `{get_public_ip()}`")
        if intent == "ping_host":
            return ExtraResult(True, ping_host(params.get("host", "8.8.8.8")))
        if intent == "traceroute_host":
            return ExtraResult(True, traceroute_host(params.get("host", "8.8.8.8")))
        if intent == "get_network_adapters":
            return ExtraResult(True, get_network_adapters())
        if intent == "scan_wifi":
            return ExtraResult(True, get_wifi_networks())
        if intent == "get_mac_hostname":
            return ExtraResult(True, get_mac_and_hostname())
        if intent == "flush_dns":
            return ExtraResult(True, flush_dns())
        if intent == "ipconfig_summary":
            return ExtraResult(True, ipconfig_summary())
        if intent == "speed_test":
            return ExtraResult(True, speed_test())
        if intent == "get_battery":
            return ExtraResult(True, get_battery_info())
        if intent == "get_screen_info":
            return ExtraResult(True, get_screen_resolution())
        if intent == "get_idle_time":
            return ExtraResult(True, get_idle_time())
        if intent == "empty_recycle_bin":
            return ExtraResult(True, empty_recycle_bin())
        if intent == "recycle_bin_info":
            return ExtraResult(True, recycle_bin_info())
        if intent == "list_downloads":
            return ExtraResult(True, "⬇️ Загрузки:\n" + get_downloads_list())
        if intent == "folder_sizes":
            return ExtraResult(True, get_desktop_folder_sizes())
        if intent == "get_file_info":
            return ExtraResult(True, get_file_info(params.get("path", "")))
        if intent == "zip_path":
            return ExtraResult(True, zip_path(params.get("source", ""), params.get("destination")))
        if intent == "unzip_path":
            return ExtraResult(True, unzip_path(params.get("source", ""), params.get("destination")))
        if intent == "open_windows_tool":
            return ExtraResult(True, open_windows_tool(params.get("tool", "")))
        if intent == "toggle_notifications":
            return ExtraResult(True, do_not_disturb_mode())
        if intent == "toggle_dark_mode":
            return ExtraResult(True, toggle_dark_mode())
        if intent == "open_night_light":
            return ExtraResult(True, open_night_light())
        if intent == "restart_explorer":
            return ExtraResult(True, restart_explorer())
        if intent == "hibernate_pc":
            return ExtraResult(True, hibernate_pc())
        if intent == "cancel_shutdown":
            return ExtraResult(True, cancel_shutdown())
        if intent == "list_windows":
            return ExtraResult(True, list_open_windows())
        if intent == "get_active_window":
            return ExtraResult(True, get_active_window())
        if intent == "focus_window":
            return ExtraResult(True, focus_window(params.get("query", "")))
        if intent == "show_desktop":
            return ExtraResult(True, show_desktop())
        if intent == "get_hardware_info":
            return ExtraResult(True, get_hardware_info())
        if intent == "list_usb":
            return ExtraResult(True, list_usb_devices())
        if intent == "list_printers":
            return ExtraResult(True, list_printers())
        if intent == "list_startup":
            return ExtraResult(True, list_startup_apps())
        if intent == "firewall_status":
            return ExtraResult(True, firewall_status())
        if intent == "defender_status":
            return ExtraResult(True, defender_status())
        if intent == "generate_password":
            return ExtraResult(True, generate_password(params.get("length") or 16))
        if intent == "generate_uuid":
            return ExtraResult(True, generate_uuid())
        if intent == "hash_text":
            return ExtraResult(True, hash_text(params.get("text", ""), params.get("algo") or "sha256"))
        if intent == "base64_convert":
            return ExtraResult(True, base64_convert(params.get("text", ""), params.get("mode") or "encode"))
        if intent == "random_util":
            return ExtraResult(
                True,
                random_util(
                    params.get("kind") or "number",
                    params.get("min_value") or 1,
                    params.get("max_value") or 100,
                ),
            )
        if intent == "get_datetime":
            return ExtraResult(True, get_datetime_info())
        if intent == "speak_text":
            return ExtraResult(True, speak_text(params.get("text", "")))
        if intent == "generate_qr":
            return generate_qr_png(params.get("data") or params.get("text") or "jarvis")
        if intent == "quick_note":
            return ExtraResult(True, open_notepad_quick_note(params.get("text", "Заметка")))
        if intent == "set_power_plan":
            return ExtraResult(True, set_power_plan(params.get("mode", "balanced")))
        if intent == "battery_report":
            return ExtraResult(True, get_battery_report())
        if intent == "mouse_move":
            return ExtraResult(True, mouse_move_to(int(params.get("x", 0)), int(params.get("y", 0))))
        if intent == "mouse_click":
            return ExtraResult(
                True,
                mouse_click_at(
                    int(params.get("x", 0)),
                    int(params.get("y", 0)),
                    params.get("button", "left"),
                    int(params.get("clicks", 1)),
                ),
            )
        if intent == "mouse_drag":
            return ExtraResult(True, mouse_drag_to(int(params.get("x", 0)), int(params.get("y", 0))))
        if intent == "mouse_scroll":
            return ExtraResult(True, mouse_scroll_units(int(params.get("amount", 300))))
        if intent == "keyboard_backlight":
            return ExtraResult(True, toggle_keyboard_backlight())
        if intent == "clear_browser_cache":
            return ExtraResult(True, clear_browser_cache())
        if intent == "create_restore_point":
            return ExtraResult(True, create_restore_point(params.get("text", "Jarvis Backup")))
        if intent == "set_wallpaper":
            return ExtraResult(True, set_wallpaper(params.get("path", "")))
        if intent == "toggle_caps_lock":
            return ExtraResult(True, toggle_caps_lock())
        if intent == "list_audio_devices":
            return ExtraResult(True, list_audio_devices())
        if intent == "set_process_volume":
            return ExtraResult(True, set_process_volume(params.get("process_name", ""), int(params.get("volume", 50))))
        if intent == "close_active_window":
            return ExtraResult(True, close_active_window())
        if intent == "laptop_screen_sleep":
            return ExtraResult(True, laptop_screen_sleep())
        if intent == "installed_updates":
            return ExtraResult(True, get_installed_updates())
    except Exception as e:
        logger.error("dispatch_extra error on %s: %s", intent, e, exc_info=True)
        return ExtraResult(False, f"❌ {intent}: {e}")
    return None
