"""Fast, human-sounding replies for conversational messages.

Small-talk must not enter the command planner: a greeting is a conversation,
not a request to control Windows.
"""
from __future__ import annotations

import re
from datetime import datetime


_GREETING_RE = re.compile(
    r"^(?:привет|прив|здравствуй|здравствуйте|доброе утро|добрый день|"
    r"добрый вечер|доброй ночи|хай|hello|hi)[!.?]*$",
    re.IGNORECASE,
)
_STATUS_RE = re.compile(
    r"^(?:как дела|как ты|ты тут|ты живой|на месте|ты работаешь|"
    r"все нормально|всё нормально)[?!. ]*$",
    re.IGNORECASE,
)
_THANKS_RE = re.compile(
    r"^(?:спасибо|благодарю|красава|молодец|умница)[!. ]*$",
    re.IGNORECASE,
)
_GOODBYE_RE = re.compile(
    r"^(?:пока|до свидания|до связи|спокойной ночи|отбой)[!. ]*$",
    re.IGNORECASE,
)
_CAPABILITIES_RE = re.compile(
    r"^(?:что ты умеешь|какие у тебя функции|помощь|help|кто ты)[?!. ]*$",
    re.IGNORECASE,
)


def _display_name(name: str | None) -> str:
    name = (name or "").strip()
    return name if name else "шеф"


def reply_for_small_talk(text: str, user_name: str | None = None, now: datetime | None = None) -> str | None:
    """Return a concise contextual reply, or ``None`` for a non-conversational message."""
    normalized = re.sub(r"\s+", " ", (text or "").strip())
    if not normalized:
        return None

    name = _display_name(user_name)
    current = now or datetime.now()
    if _GREETING_RE.fullmatch(normalized):
        hour = current.hour
        if "утро" in normalized.lower() or 5 <= hour < 12:
            opening = "Доброе утро"
        elif "вечер" in normalized.lower() or 18 <= hour < 24:
            opening = "Добрый вечер"
        elif "ноч" in normalized.lower() or hour < 5:
            opening = "Доброй ночи"
        else:
            opening = "Привет"
        return f"{opening}, {name}. Я на связи и слежу за системой. Что делаем?"

    if _STATUS_RE.fullmatch(normalized):
        return f"В полном порядке, {name}: я онлайн, локальный контур готов к командам, а Gemini подключу для вопросов и знаний."

    if _THANKS_RE.fullmatch(normalized):
        return f"Всегда пожалуйста, {name}. Я рядом."

    if _GOODBYE_RE.fullmatch(normalized):
        return f"До связи, {name}. Оставлю мониторинг и напоминания включёнными."

    if _CAPABILITIES_RE.fullmatch(normalized):
        return (
            "Я Jarvis, твой оператор Windows. Могу управлять приложениями, окнами, мышью, "
            "клавиатурой, звуком и рабочими столами, делать скриншоты, искать файлы, "
            "ставить напоминания и следить за состоянием ПК. Команды управления выполняю "
            "локально, а вопросы и поиск знаний передаю Gemini."
        )
    return None


def is_small_talk(text: str) -> bool:
    """Whether text should bypass both the command planner and PC executor."""
    return reply_for_small_talk(text) is not None
