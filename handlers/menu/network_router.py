"""Network diagnostic keyboard actions."""
import asyncio
from handlers.menu.common import safe_reply

async def handle_network(update, context, text: str) -> bool:
    from services.extra_functions import get_public_ip, get_local_ip
    if text == "🌍 Внешний IP":
        await update.message.reply_text(f"🌍 *Внешний IP:* `{get_public_ip()}`", parse_mode="Markdown"); return True
    if text == "🏠 Локальный IP":
        await update.message.reply_text(f"🏠 *Локальный IP:* `{get_local_ip()}`", parse_mode="Markdown"); return True
    threaded = {
        "📡 Адаптеры сети": ("services.extra_functions", "get_network_adapters", "📡 *Сетевые адаптеры:*"),
        "📶 Wi-Fi сети": ("services.extra_functions", "get_wifi_networks", "📶 *Wi-Fi сети:*"),
        "📶 Диагностика сигнала": ("services.wifi_monitor", "get_wifi_diagnostics_report", None),
    }
    if text in threaded:
        module, name, prefix = threaded[text]
        mod = __import__(module, fromlist=[name]); result = await asyncio.to_thread(getattr(mod, name))
        await safe_reply(update, f"{prefix}\n\n{result}" if prefix else result); return True
    if text in ("🏓 Ping 8.8.8.8", "🏓 Ping Яндекс"):
        from services.extra_functions import ping_host
        host = "8.8.8.8" if text.endswith("8.8.8.8") else "ya.ru"
        result = await asyncio.to_thread(ping_host, host)
        await safe_reply(update, f"🏓 *Ping {host}:*\n\n```\n{result}\n```"); return True
    network_actions = {
        "🛤 Трассировка": ("traceroute_host", ("8.8.8.8",), "🛤 *Трассировка маршрута:*"),
        "⚡ Скорость сети": ("speed_test", (), None),
        "🧹 Flush DNS": ("flush_dns", (), None),
        "🌐 ipconfig": ("ipconfig_summary", (), None),
    }
    if text in network_actions:
        name, args, prefix = network_actions[text]
        from services import network_tools
        result = await asyncio.to_thread(getattr(network_tools, name), *args)
        await safe_reply(update, f"{prefix}\n\n{result}" if prefix else result)
        return True
    return False
