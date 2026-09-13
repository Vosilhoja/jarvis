import asyncio
from typing import Tuple
import psutil
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from core.intent_schema import StepModel
from core.task_queue import UserTaskSession
from core.app_resolver import app_resolver
from services.ai_client import ask_gemini_app_choice

async def handle_open_application(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    query = step.params["app_query"]
    candidates = await asyncio.to_thread(app_resolver.find_candidates, query, 5)
    if not candidates:
        return False, f"❌ Не нашел приложения по запросу «{query}»."

    best_app, score = candidates[0]
    if score >= 75.0:
        success = await asyncio.to_thread(app_resolver.launch_app, best_app)
        if success:
            return True, f"✅ Запустил *{best_app['display_name']}* (найдено по «{query}»)"
        return False, f"❌ Ошибка запуска {best_app['display_name']}"

    # Неоднозначность -> асинхронный вызов Gemini в отдельном потоке
    choice_idx = await asyncio.to_thread(ask_gemini_app_choice, query, [c[0] for c in candidates])
    if choice_idx is not None:
        chosen_app = candidates[choice_idx][0]
        app_resolver.add_user_alias(chosen_app["display_name"], query)
        success = await asyncio.to_thread(app_resolver.launch_app, chosen_app)
        if success:
            return True, f"✅ Запустил *{chosen_app['display_name']}* (выбор ИИ по «{query}»)"

    kb_buttons = []
    for c_app, _ in candidates[:3]:
        kb_buttons.append([InlineKeyboardButton(f"Запустить {c_app['display_name']}", callback_data=f"launch_app_{c_app['display_name'][:25]}")])
    kb_buttons.append([InlineKeyboardButton("❌ Отмена", callback_data="main_menu")])

    await bot.send_message(
        chat_id=session.user_id,
        text=f"🤔 Найдено несколько похожих приложений для «{query}». Выберите нужное:",
        reply_markup=InlineKeyboardMarkup(kb_buttons)
    )
    return True, f"⏳ Предложен выбор приложений для «{query}»"

async def handle_close_application(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    query = step.params["app_query"].lower()
    
    def _close():
        killed = 0
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if query in proc.info['name'].lower():
                    proc.terminate()
                    killed += 1
            except Exception:
                continue
        return killed

    killed = await asyncio.to_thread(_close)
    if killed > 0:
        return True, f"✅ Закрыто процессов: {killed} (по запросу «{query}»)"
    return False, f"⚠️ Запущенных процессов по запросу «{query}» не найдено."

async def handle_list_installed_apps(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    q = (step.params.get("query") or "").strip()
    apps = app_resolver.apps_index
    if q:
        from rapidfuzz import process, fuzz
        names = [a.get("display_name", "") for a in apps]
        hits = process.extract(q, names, scorer=fuzz.WRatio, limit=12)
        lines = [f"• {n} ({s:.0f}%)" for n, s, _ in hits]
    else:
        lines = [f"• {a.get('display_name')}" for a in apps[:20]]
    await bot.send_message(chat_id=session.user_id, text="📦 Программы:\n" + "\n".join(lines))
    return True, "✅ Список приложений отправлен"
