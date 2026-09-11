import time
import asyncio
import logging
from typing import List, Dict, Any, Optional
from core.intent_schema import StepModel

logger = logging.getLogger("jarvis")

class UserTaskSession:
    """Сессия очереди задач для конкретного пользователя Telegram."""
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.queue: asyncio.Queue[StepModel] = asyncio.Queue()
        self.is_running: bool = False
        self.current_step: Optional[StepModel] = None
        self.history: List[Dict[str, Any]] = []
        self.context_memory: Dict[str, Any] = {} # Сохранение путей, файлов, результатов между шагами
        self.pending_confirmation: Optional[Dict[str, Any]] = None # Для опасных действий

    def add_steps(self, steps: List[StepModel]):
        for step in steps:
            self.queue.put_nowait(step)
        logger.info(f"Добавлено {len(steps)} шагов в очередь пользователя {self.user_id}. В очереди: {self.queue.qsize()}")

    def clear(self):
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except Exception:
                break
        self.current_step = None
        self.is_running = False
        self.pending_confirmation = None

class TaskQueueManager:
    """Управляет сессиями всех пользователей."""
    def __init__(self):
        self.sessions: Dict[int, UserTaskSession] = {}

    def get_session(self, user_id: int) -> UserTaskSession:
        if user_id not in self.sessions:
            self.sessions[user_id] = UserTaskSession(user_id)
        return self.sessions[user_id]

# Синглтон
task_queue_manager = TaskQueueManager()
