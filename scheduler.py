import uuid
import json
import time
import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

from config import (
    REMINDERS_DB_PATH,
    BACKGROUND_CHECK_INTERVAL_SEC,
    DISK_FREE_THRESHOLD_GB,
    CPU_LOAD_THRESHOLD_PERCENT,
    RAM_LOAD_THRESHOLD_PERCENT
)
from services.notifier import notifier
from services.system_monitor import check_system_thresholds, find_hung_windows

logger = logging.getLogger("jarvis")

class ReminderManager:
    """Управляет сохранением и проверкой напоминаний в JSON."""
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.reminders: List[Dict[str, Any]] = []
        self.load()

    def load(self):
        if self.db_path.exists():
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    self.reminders = json.load(f)
            except Exception as e:
                logger.error(f"Ошибка загрузки напоминаний: {e}")
                self.reminders = []
        else:
            self.reminders = []

    def save(self):
        try:
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(self.reminders, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения напоминаний: {e}")

    def add_reminder(self, chat_id: int, text: str, when_str: str) -> Dict[str, Any]:
        """Парсит естественное время (например 'через 15 минут', 'в 18:30') и добавляет в список."""
        now = datetime.now()
        target_time = now + timedelta(minutes=15) # По умолчанию

        # Простые паттерны
        m_min = re.search(r"через\s+(\d+)\s+(мин|минут)", when_str.lower())
        m_hour = re.search(r"через\s+(\d+)\s+(час|часа|часов)", when_str.lower())
        m_at = re.search(r"в\s+(\d{1,2})[:\.](\d{2})", when_str.lower())

        if m_min:
            target_time = now + timedelta(minutes=int(m_min.group(1)))
        elif m_hour:
            target_time = now + timedelta(hours=int(m_hour.group(1)))
        elif m_at:
            h, m = int(m_at.group(1)), int(m_at.group(2))
            cand = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if cand <= now:
                cand += timedelta(days=1)
            target_time = cand

        rem_id = str(uuid.uuid4())
        reminder = {
            "id": rem_id,
            "chat_id": chat_id,
            "text": text,
            "next_trigger_at": target_time.strftime("%Y-%m-%d %H:%M:%S"),
            "trigger_timestamp": target_time.timestamp(),
            "active": True,
            "created_at": now.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.reminders.append(reminder)
        self.save()
        logger.info(f"Создано напоминание: {text} на {target_time}")
        return reminder

    def get_active_reminders(self, chat_id: Optional[int] = None) -> List[Dict[str, Any]]:
        active = [r for r in self.reminders if r.get("active", True)]
        if chat_id:
            active = [r for r in active if r.get("chat_id") == chat_id]
        active.sort(key=lambda x: x.get("trigger_timestamp", 0))
        return active

    def pop_due_reminders(self) -> List[Dict[str, Any]]:
        now_ts = time.time()
        due = []
        for r in self.reminders:
            if r.get("active", True) and r.get("trigger_timestamp", 0) <= now_ts:
                r["active"] = False
                due.append(r)
        if due:
            self.save()
        return due

reminder_manager = ReminderManager(REMINDERS_DB_PATH)

async def background_monitoring_loop():
    """
    Фоновый поток-демон:
    1. Проверяет напоминания и шлет алерты
    2. Проверяет пороги диска, ОЗУ, ЦП
    3. Проверяет зависшие приложения
    4. Ежедневный утренний брифинг в 09:00
    """
    logger.info("Фоновый планировщик и система мониторинга Jarvis запущены.")
    last_daily_report_date = None

    while True:
        try:
            # 1. Напоминания
            due = reminder_manager.pop_due_reminders()
            for r in due:
                await notifier.send_notification(
                    text=f"⏰ *НАПОМИНАНИЕ:*\n«{r['text']}»",
                    topic_key=f"reminder_{r['id']}",
                    min_interval_sec=0,
                    urgency="normal"
                )

            # 2. Пороги системы
            alerts = check_system_thresholds(
                disk_threshold_gb=DISK_FREE_THRESHOLD_GB,
                cpu_threshold=CPU_LOAD_THRESHOLD_PERCENT,
                ram_threshold=RAM_LOAD_THRESHOLD_PERCENT
            )
            for alert in alerts:
                await notifier.send_notification(
                    text=alert["msg"],
                    topic_key=alert["key"],
                    min_interval_sec=3600, # Не чаще 1 раза в час
                    urgency="high"
                )

            # 3. Зависшие приложения (IsHungAppWindow)
            hung = find_hung_windows()
            if hung:
                hung_titles = ", ".join([f"«{h['title']}»" for h in hung[:3]])
                await notifier.send_notification(
                    text=f"⚠️ Обнаружены зависшие окна приложений: {hung_titles}. Вы можете закрыть их через меню процессов.",
                    topic_key="hung_windows",
                    min_interval_sec=1800,
                    urgency="high"
                )

            # 4. Ежедневная утренняя сводка (в 9:00 утра)
            now = datetime.now()
            today_str = now.strftime("%Y-%m-%d")
            if now.hour == 9 and last_daily_report_date != today_str:
                from services.system_info import get_system_metrics
                m = get_system_metrics()
                active_rem = len(reminder_manager.get_active_reminders())
                report_text = (
                    f"☀️ *Доброе утро! Ежедневный отчет Jarvis:*\n\n"
                    f"🖥 Состояние ПК:\n"
                    f"• CPU: {m['cpu_percent']}%\n"
                    f"• RAM: {m['ram_percent']}%\n"
                    f"• Uptime: {m['uptime']}\n"
                    f"• Активных напоминаний: {active_rem}\n\n"
                    "Система работает стабильно и готова к работе."
                )
                await notifier.send_notification(report_text, topic_key="daily_report", min_interval_sec=43200)
                last_daily_report_date = today_str

        except Exception as e:
            logger.error(f"Ошибка в фоновом цикле мониторинга: {e}", exc_info=True)

        await asyncio.sleep(BACKGROUND_CHECK_INTERVAL_SEC)
