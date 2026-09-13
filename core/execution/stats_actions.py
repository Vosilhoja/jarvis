import asyncio
from typing import Tuple
from telegram import Bot
from core.intent_schema import StepModel
from core.task_queue import UserTaskSession

async def handle_get_weekly_report(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    from services.usage_stats import get_weekly_report
    msg = await asyncio.to_thread(get_weekly_report)
    await bot.send_message(chat_id=session.user_id, text=msg, parse_mode="Markdown")
    return True, "✅ Еженедельная сводка отправлена"
