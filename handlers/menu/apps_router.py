"""Application discovery and quick-launch actions."""
from handlers.menu.common import safe_reply

APP_FAST_MAP = {"🌐 Chrome":"chrome","📨 Telegram":"telegram","💻 VS Code":"vscode","🧮 Калькулятор":"calc","📝 Блокнот":"notepad","🎨 Paint":"mspaint","⚙️ Панель упр.":"control","💻 CMD":"cmd","🔵 PowerShell":"powershell","📊 Диспетчер задач":"taskmgr","🛡 Защитник Win":"defender","📁 Проводник":"explorer"}

async def handle_apps(update, context, text: str) -> bool:
    if text in APP_FAST_MAP:
        from services.extra_functions import quick_launch
        await update.message.reply_text(f"🚀 {quick_launch(APP_FAST_MAP[text])}"); return True
    from core.app_resolver import app_resolver
    if text == "📦 Все программы ПК":
        apps = app_resolver.apps_index; names = sorted({a.get("display_name", "") for a in apps if a.get("display_name")})
        await safe_reply(update, f"📦 *Установленные программы на ПК (всего найдено: {len(apps)}):*\n\n" + "\n".join(f"• {n}" for n in names[:35]) + f"\n\n_Показаны первые 35 из {len(apps)}._"); return True
    if text == "🔍 Найти программу":
        context.user_data["awaiting_app_search"] = True
        await update.message.reply_text("🔍 *Напишите название программы для запуска:*", parse_mode="Markdown"); return True
    return False
