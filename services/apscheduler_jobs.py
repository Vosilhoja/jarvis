"""
APScheduler-задачи Jarvis.

Пока здесь только одна задача — ежедневный утренний брифинг (см.
services/morning_briefing.py). Специально вынесено в отдельный модуль и НЕ
заменяет существующий scheduler.py::background_monitoring_loop (напоминания,
пороги CPU/RAM/диска, зависшие окна и т.д.) — тот уже работает и трогать его
рискованно без необходимости. APScheduler используется только для новых задач.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import MORNING_GREETING_HOUR, MORNING_GREETING_MINUTE
from services.notifier import notifier

logger = logging.getLogger("jarvis")

_scheduler: AsyncIOScheduler | None = None


async def _send_morning_briefing():
    from services.morning_briefing import build_morning_briefing
    try:
        text = await build_morning_briefing()
        await notifier.send_notification(text, topic_key="morning_briefing", min_interval_sec=3600)
    except Exception as e:
        logger.error(f"Ошибка отправки утреннего брифинга: {e}", exc_info=True)


def start_apscheduler_jobs() -> AsyncIOScheduler:
    """Запускает APScheduler и регистрирует утренний брифинг. Вызывается один раз из main.py::post_init."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    _scheduler = AsyncIOScheduler(timezone=None)  # None = локальный часовой пояс системы
    _scheduler.add_job(
        _send_morning_briefing,
        trigger=CronTrigger(hour=MORNING_GREETING_HOUR, minute=MORNING_GREETING_MINUTE),
        id="morning_briefing",
        replace_existing=True,
        misfire_grace_time=600,  # если ПК спал в момент срабатывания — всё равно прислать в течение 10 мин
    )
    _scheduler.start()
    logger.info(
        f"APScheduler запущен: утренний брифинг в {MORNING_GREETING_HOUR:02d}:{MORNING_GREETING_MINUTE:02d}"
    )
    return _scheduler
