from __future__ import annotations

from enum import Enum


class RiskLevel(str, Enum):
    SAFE = "safe"
    LOW = "low"
    CONFIRM = "confirm"
    ADMIN = "admin"
    DENY = "deny"


# Action risk mappings
ACTION_RISK_MAP: dict[str, RiskLevel] = {
    # SAFE
    "open_application": RiskLevel.SAFE,
    "list_running_processes": RiskLevel.SAFE,
    "list_installed_apps": RiskLevel.SAFE,
    "open_explorer_path": RiskLevel.SAFE,
    "search_files": RiskLevel.SAFE,
    "take_screenshot": RiskLevel.SAFE,
    "set_volume": RiskLevel.SAFE,
    "set_brightness": RiskLevel.SAFE,
    "media_control": RiskLevel.SAFE,
    "get_system_status": RiskLevel.SAFE,
    "get_disk_space": RiskLevel.SAFE,
    "get_weather": RiskLevel.SAFE,
    "get_exchange_rate": RiskLevel.SAFE,
    "get_local_ip": RiskLevel.SAFE,
    "get_public_ip": RiskLevel.SAFE,
    "get_screen_info": RiskLevel.SAFE,
    "get_datetime": RiskLevel.SAFE,
    "chat_reply": RiskLevel.SAFE,
    "clarify": RiskLevel.SAFE,

    # LOW
    "create_folder": RiskLevel.LOW,
    "create_file": RiskLevel.LOW,
    "move_item": RiskLevel.LOW,
    "copy_item": RiskLevel.LOW,
    "rename_item": RiskLevel.LOW,
    "open_website": RiskLevel.LOW,
    "web_search": RiskLevel.LOW,
    "download_from_wikipedia": RiskLevel.LOW,
    "download_file": RiskLevel.LOW,
    "set_reminder": RiskLevel.LOW,
    "list_reminders": RiskLevel.LOW,
    "cancel_reminder": RiskLevel.LOW,
    "switch_virtual_desktop": RiskLevel.LOW,
    "create_virtual_desktop": RiskLevel.LOW,
    "set_clipboard": RiskLevel.LOW,
    "get_clipboard": RiskLevel.LOW,
    "close_application": RiskLevel.LOW,
    "cleanup_temp": RiskLevel.LOW,

    # CONFIRM
    "delete_file": RiskLevel.CONFIRM,
    "delete_item": RiskLevel.CONFIRM,
    "empty_recycle_bin": RiskLevel.CONFIRM,
    "kill_process": RiskLevel.CONFIRM,
    "lock_pc": RiskLevel.CONFIRM,
    "sleep_pc": RiskLevel.CONFIRM,
    "start_guard": RiskLevel.CONFIRM,
    "stop_guard": RiskLevel.CONFIRM,
    "clear_browser_cache": RiskLevel.CONFIRM,
    "restart_explorer": RiskLevel.CONFIRM,

    # ADMIN
    "shutdown_pc": RiskLevel.ADMIN,
    "restart_pc": RiskLevel.ADMIN,
    "hibernate_pc": RiskLevel.ADMIN,
    "create_restore_point": RiskLevel.ADMIN,
    "set_power_plan": RiskLevel.ADMIN,
    "ensure_autostart": RiskLevel.ADMIN,

    # DENY
    "arbitrary_shell": RiskLevel.DENY,
    "execute_python": RiskLevel.DENY,
    "eval_code": RiskLevel.DENY,
    "format_drive": RiskLevel.DENY,
}


def get_action_risk_level(action_name: str) -> RiskLevel:
    return ACTION_RISK_MAP.get(action_name, RiskLevel.CONFIRM)
