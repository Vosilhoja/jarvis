import time
import logging
from typing import Dict, Any, Optional
from telegram import Bot
from config import ALLOWED_USER_IDS, TELEGRAM_BOT_TOKEN

logger = logging.getLogger("jarvis")

class Notifier:
    """
    Единая точка отправки проактивных уведомлений в Telegram с защитой от спама.
    """
    def __init__(self):
        self.bot: Optional[Bot] = None
        # Кэш времени последних отправленных уведомлений по ключу темы: {topic_key: timestamp}
        self.last_sent_times: Dict[str, float] = {}

    def set_bot(self, bot: Bot):
        self.bot = bot

    async def send_notification(self, text: str, topic_key: Optional[str] = None, min_interval_sec: int = 3600, urgency: str = "normal"):
        """
        Отправляет уведомление всем авторизованным пользователям с антиспам-проверкой.
        """
        if not self.bot:
            logger.warning(f"Notifier: bot не инициализирован, не могу отправить: {text}")
            return

        now = time.time()
        if topic_key:
            last_time = self.last_sent_times.get(topic_key, 0.0)
            if now - last_time < min_interval_sec:
                logger.debug(f"Notifier: Пропуск уведомления '{topic_key}' из-за антиспама.")
                return
            self.last_sent_times[topic_key] = now

        prefix = "🚨 *ВНИМАНИЕ!* " if urgency == "high" else "ℹ️ *Уведомление Jarvis:* "
        full_text = f"{prefix}\n\n{text}"

        for user_id in ALLOWED_USER_IDS:
            try:
                await self.bot.send_message(chat_id=user_id, text=full_text, parse_mode="Markdown")
                logger.info(f"Проактивное уведомление отправлено пользователю {user_id}")
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление пользователю {user_id}: {e}")

notifier = Notifier()
