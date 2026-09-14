"""
Утренний брифинг Jarvis: "Доброе утро, сэр!" + погода + план на день из Google Calendar.

Используется двумя путями:
1. Автоматически каждый день в MORNING_GREETING_HOUR:MORNING_GREETING_MINUTE
   (см. services/apscheduler_jobs.py).
2. По кнопке "🌅 Утренний брифинг" в меню "Система" (handlers/menu/reply_router.py) —
   тот же текст по требованию пользователя.
"""
from __future__ import annotations

import asyncio
import logging

from config import MORNING_GREETING_CITY

logger = logging.getLogger("jarvis")


async def build_morning_briefing() -> str:
    """Собирает текст утреннего брифинга: приветствие + погода + события на сегодня."""
    from services.web_client import get_weather_forecast
    from services.calendar_client import get_today_events

    weather_text = "Не удалось получить данные о погоде."
    try:
        weather_text = await get_weather_forecast(MORNING_GREETING_CITY)
    except Exception as e:
        logger.warning(f"Утренний брифинг: ошибка погоды: {e}")

    events_text = "Календарь недоступен."
    try:
        # get_today_events синхронная (Google API client) — уводим в поток,
        # чтобы не блокировать event loop (см. известные грабли в AGENT_RULES.md).
        events_text = await asyncio.to_thread(get_today_events)
    except Exception as e:
        logger.warning(f"Утренний брифинг: ошибка календаря: {e}")

    return (
        "🌅 *Доброе утро, сэр!*\n\n"
        f"☀️ *Погода:*\n{weather_text}\n\n"
        f"📅 *План на сегодня:*\n{events_text}"
    )
