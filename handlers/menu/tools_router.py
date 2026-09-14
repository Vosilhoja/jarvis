"""Standalone utility actions from the tools keyboard."""
import asyncio
from datetime import datetime

async def handle_tools(update, context, text: str) -> bool:
    funcs = {
        "🔐 Пароль": ("adapters.windows.misc_tools", "generate_password", (16,), 3000),
        "🎲 Кубик": ("adapters.windows.misc_tools", "random_util", ("dice",), 3000),
        "🪙 Монета": ("adapters.windows.misc_tools", "random_util", ("coin",), 3000),
        "🎯 Активное окно": ("adapters.windows.misc_tools", "get_active_window", (), 3000),
        "🖥 Свернуть всё": ("adapters.windows.misc_tools", "minimize_all_windows", (), 3000),
        "🌙 Тема Windows": ("adapters.windows.misc_tools", "toggle_dark_mode", (), 3000),
        "🌙 Ночной свет": ("adapters.windows.misc_tools", "open_night_light", (), 3000),
        "🔌 USB": ("adapters.windows.misc_tools", "list_usb_devices", (), 3000),
        "🖨 Принтеры": ("adapters.windows.misc_tools", "list_printers", (), 3000),
        "🚀 Автозагрузка ПО": ("adapters.windows.misc_tools", "list_startup_apps", (), 3000),
        "🛡 Firewall": ("adapters.windows.misc_tools", "firewall_status", (), None),
        "🛡 Defender": ("adapters.windows.misc_tools", "defender_status", (), None),
        "🗑 Корзина (счёт)": ("adapters.windows.misc_tools", "recycle_bin_info", (), None),
        "🔄 Restart Explorer": ("adapters.windows.misc_tools", "restart_explorer", (), None),
    }
    if text == "📷 QR-код":
        context.user_data["awaiting_qr"] = True
        await update.message.reply_text("📷 Отправьте текст или ссылку, которую закодировать в QR:"); return True
    if text == "🗣 Сказать время":
        from adapters.windows.misc_tools import speak_text
        await update.message.reply_text(await asyncio.to_thread(speak_text, f"Сейчас {datetime.now().strftime('%H:%M')}")); return True
    if text == "🔋 Отчет батареи":
        from services.power_tools import get_battery_report
        await update.message.reply_text((await asyncio.to_thread(get_battery_report))[:3000]); return True
    if text == "⏱ Простой":
        from services.power_tools import get_idle_time
        await update.message.reply_text(await asyncio.to_thread(get_idle_time)); return True
    if text == "📌 Автозапуск Jarvis":
        from services.autostart import ensure_autostart, autostart_status
        await update.message.reply_text(await asyncio.to_thread(lambda: ensure_autostart() + "\n\n" + autostart_status())); return True
    if text in funcs:
        module, name, args, limit = funcs[text]
        mod = __import__(module, fromlist=[name])
        result = await asyncio.to_thread(getattr(mod, name), *args)
        await update.message.reply_text(result[:limit] if limit else result, parse_mode="Markdown"); return True
    return False
