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

    def parse_time_expression(self, when_str: str) -> Optional[datetime]:
        """Парсит естественное время на русском языке в объект datetime."""
        now = datetime.now()
        s = when_str.strip().lower()

        # 1. "через X ч Y мин" / "через X часов Y минут"
        m_compound = re.search(r"через\s+(\d+)\s*(?:ч|час|часа|часов)\s*(?:и\s*)?(\d+)\s*(?:м|мин|минут[уы]?)?", s)
        if m_compound:
            h = int(m_compound.group(1))
            m = int(m_compound.group(2))
            return now + timedelta(hours=h, minutes=m)

        # 2. "через X сек"
        m_sec = re.search(r"через\s+(\d+)\s*(?:с|сек|секунд[уы]?)", s)
        if m_sec:
            return now + timedelta(seconds=int(m_sec.group(1)))

        # 3. "через X минут"
        m_min = re.search(r"через\s+(\d+)\s*(?:м|мин|минут[уы]?)", s)
        if m_min:
            return now + timedelta(minutes=int(m_min.group(1)))

        # 4. "через X часов"
        m_hour = re.search(r"через\s+(\d+)\s*(?:ч|час|часа|часов)", s)
        if m_hour:
            return now + timedelta(hours=int(m_hour.group(1)))

        # 5. "завтра в HH:MM"
        m_tomorrow = re.search(r"завтра\s+(?:в\s+)?(\d{1,2})[:\.](\d{2})", s)
        if m_tomorrow:
            h, m = int(m_tomorrow.group(1)), int(m_tomorrow.group(2))
            cand = (now + timedelta(days=1)).replace(hour=h, minute=m, second=0, microsecond=0)
            return cand

        # 6. "послезавтра в HH:MM"
        m_after_tomorrow = re.search(r"послезавтра\s+(?:в\s+)?(\d{1,2})[:\.](\d{2})", s)
        if m_after_tomorrow:
            h, m = int(m_after_tomorrow.group(1)), int(m_after_tomorrow.group(2))
            cand = (now + timedelta(days=2)).replace(hour=h, minute=m, second=0, microsecond=0)
            return cand

        # 7. "сегодня в HH:MM" или просто "в HH:MM"
        m_at = re.search(r"(?:сегодня\s+)?в\s+(\d{1,2})[:\.](\d{2})", s)
        if m_at:
            h, m = int(m_at.group(1)), int(m_at.group(2))
            cand = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if cand <= now:
                cand += timedelta(days=1)
            return cand

        # 8. Резервный вызов dateparser если установлен
        try:
            import dateparser
            parsed = dateparser.parse(s, settings={"PREFER_DATES_FROM": "future", "DATE_ORDER": "DMY"})
            if parsed:
                return parsed
        except Exception:
            pass

        return None

    def add_reminder(self, chat_id: int, text: str, when_str: str) -> Dict[str, Any]:
        """Парсит естественное время и добавляет в список."""
        now = datetime.now()
        target_time = self.parse_time_expression(when_str)
        if not target_time:
            target_time = now + timedelta(minutes=15)

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

    def cancel_reminder(self, reminder_id: str, chat_id: Optional[int] = None) -> bool:
        rid = (reminder_id or "").strip().lower()
        for r in self.reminders:
            if chat_id and r.get("chat_id") != chat_id:
                continue
            if not r.get("active", True):
                continue
            if str(r.get("id", "")).lower().startswith(rid) or rid in str(r.get("text", "")).lower():
                r["active"] = False
                self.save()
                return True
        return False

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

                # Проактивное действие: при критических системных алертах создаём напоминание
                try:
                    # Попытаемся добавить напоминание для первого разрешённого пользователя
                    from config import ALLOWED_USER_ID
                    chat_for_reminder = ALLOWED_USER_ID if ALLOWED_USER_ID else None
                    if chat_for_reminder:
                        # Предотвращаем дубли: проверим активные напоминания на похожий текст
                        existing = reminder_manager.get_active_reminders(chat_for_reminder)
                        found_similar = False
                        for r in existing:
                            txt = (r.get("text") or "").lower()
                            if alert.get("key", "").lower() in txt or alert.get("msg", "").split()[0].lower() in txt:
                                found_similar = True
                                break
                        if not found_similar:
                            # Подбираем разумное время напоминания в зависимости от типа аларта
                            when = "через 1 час"
                            if alert.get("type") == "cpu":
                                when = "через 10 минут"
                            elif alert.get("type") == "ram":
                                when = "через 30 минут"
                            elif alert.get("type") == "disk":
                                when = "через 2 часа"

                            reminder_manager.add_reminder(chat_for_reminder, alert.get("msg", "Проверьте систему"), when)
                except Exception:
                    # Не фатально — лог и продолжаем
                    logger.debug("Не удалось автоматически создать напоминание для аларта")

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
