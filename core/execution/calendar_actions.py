import asyncio
from typing import Tuple
from telegram import Bot
from core.intent_schema import StepModel
from core.task_queue import UserTaskSession

# ВАЖНО: get_today_events/get_upcoming_events из services/calendar_client.py —
# блокирующие синхронные функции (могут делать сетевой запрос к Google API,
# а при первом запуске без токена — открыть системный браузер и ждать вход
# пользователя). Согласно AGENT_RULES.md landmine #1, main.py работает с
# .concurrent_updates(False), поэтому вызывать их напрямую в async-хендлере
# НЕЛЬЗЯ — это заморозит бота для всех пользователей. Всегда через
# asyncio.to_thread.

async def handle_get_today_events(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    from services.calendar_client import get_today_events
    msg = await asyncio.to_thread(get_today_events)
    await bot.send_message(chat_id=session.user_id, text=msg, parse_mode="Markdown")
    return True, "✅ Календарь на сегодня отправлен"

async def handle_get_upcoming_events(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    from services.calendar_client import get_upcoming_events
    days = step.params.get("days") or 7
    msg = await asyncio.to_thread(get_upcoming_events, days)
    await bot.send_message(chat_id=session.user_id, text=msg, parse_mode="Markdown")
    return True, "✅ Предстоящие события календаря отправлены"
