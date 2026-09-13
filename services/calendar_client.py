"""
Интеграция с Google Calendar (readonly): "что у меня сегодня по плану",
"что у меня на этой неделе" — реальная синхронизация с календарём пользователя,
а не ручные напоминания Jarvis.

НАСТРОЙКА (делает сам пользователь, агент это сделать не может):
  1. Зайти на https://console.cloud.google.com/ , создать проект.
  2. APIs & Services → Library → включить "Google Calendar API".
  3. APIs & Services → OAuth consent screen → тип "External" (или "Internal"
     если Google Workspace), заполнить минимум (название приложения, email),
     добавить себя в Test users, если приложение не проходит верификацию.
  4. APIs & Services → Credentials → Create Credentials → OAuth client ID →
     тип приложения "Desktop app".
  5. Скачать JSON и положить его в корень проекта Jarvis под именем
     `credentials.json` (либо указать свой путь через переменную окружения
     GOOGLE_CALENDAR_CREDENTIALS_PATH в .env).
  6. Первый вызов get_today_events()/get_upcoming_events() откроет системный
     браузер на этом же ПК для входа в Google-аккаунт и выдачи разрешения —
     это нужно сделать один раз. После этого токен кэшируется в
     data/google_calendar_token.json и обновляется автоматически, без
     повторного похода в браузер (пока пользователь не отзовёт доступ).

ВАЖНО (см. AGENT_RULES.md, landmine #1): и сам OAuth-флоу (открытие браузера,
ожидание кода), и HTTP-запросы к Google API — блокирующие синхронные вызовы.
core/execution/calendar_actions.py ОБЯЗАН вызывать функции этого модуля через
asyncio.to_thread(...), иначе первый же запуск авторизации заморозит бота для
всех пользователей до завершения входа в браузере.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger("jarvis")

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

SETUP_INSTRUCTIONS = (
    "📅 *Google Calendar не настроен.*\n\n"
    "Чтобы подключить:\n"
    "1. Создайте проект на https://console.cloud.google.com/\n"
    "2. Включите *Google Calendar API* (APIs & Services → Library)\n"
    "3. Настройте OAuth consent screen (тип External, себя — в Test users)\n"
    "4. Credentials → Create Credentials → OAuth client ID → *Desktop app*\n"
    "5. Скачайте JSON и положите в корень проекта Jarvis как `credentials.json`\n"
    "   (или укажите свой путь в `.env` как `GOOGLE_CALENDAR_CREDENTIALS_PATH`)\n\n"
    "После этого просто повторите запрос — откроется браузер для входа в Google."
)


def _get_credentials():
    """
    Возвращает валидные Credentials, обновляя/запрашивая их при необходимости.
    Блокирующая функция (может открыть браузер) — вызывать только через
    asyncio.to_thread из async-хендлеров.
    """
    from config import GOOGLE_CALENDAR_CREDENTIALS_PATH, GOOGLE_CALENDAR_TOKEN_PATH
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if GOOGLE_CALENDAR_TOKEN_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(GOOGLE_CALENDAR_TOKEN_PATH), SCOPES)
        except Exception as e:
            logger.warning(f"calendar_client: не удалось прочитать сохранённый токен: {e}")
            creds = None

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            GOOGLE_CALENDAR_TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
            return creds
        except Exception as e:
            logger.warning(f"calendar_client: не удалось обновить токен, требуется повторный вход: {e}")
            creds = None

    if not GOOGLE_CALENDAR_CREDENTIALS_PATH.exists():
        raise FileNotFoundError(
            f"Файл учётных данных не найден: {GOOGLE_CALENDAR_CREDENTIALS_PATH}"
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(GOOGLE_CALENDAR_CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=0)
    GOOGLE_CALENDAR_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    GOOGLE_CALENDAR_TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return creds


def _get_service():
    from googleapiclient.discovery import build
    creds = _get_credentials()
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _format_event(ev: dict) -> str:
    summary = ev.get("summary", "(без названия)")
    start = ev.get("start", {})
    if "dateTime" in start:
        dt = datetime.fromisoformat(start["dateTime"])
        time_str = dt.strftime("%H:%M")
    else:
        time_str = "весь день"
    location = ev.get("location")
    line = f"• `{time_str}` — {summary}"
    if location:
        line += f" ({location})"
    return line


def get_today_events(max_results: int = 20) -> str:
    """Блокирующая функция — вызывать через asyncio.to_thread."""
    try:
        service = _get_service()
    except FileNotFoundError:
        return SETUP_INSTRUCTIONS
    except Exception as e:
        return f"❌ Ошибка авторизации Google Calendar: {e}"

    now_local = datetime.now().astimezone()
    start_of_day = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    try:
        events_result = service.events().list(
            calendarId="primary",
            timeMin=start_of_day.isoformat(),
            timeMax=end_of_day.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=max_results,
        ).execute()
    except Exception as e:
        return f"❌ Не удалось получить события календаря: {e}"

    items = events_result.get("items", [])
    if not items:
        return "📅 *На сегодня в календаре ничего не запланировано.*"

    lines = ["📅 *План на сегодня:*\n"]
    lines.extend(_format_event(ev) for ev in items)
    return "\n".join(lines)


def get_upcoming_events(days: int = 7, max_results: int = 30) -> str:
    """Блокирующая функция — вызывать через asyncio.to_thread."""
    try:
        service = _get_service()
    except FileNotFoundError:
        return SETUP_INSTRUCTIONS
    except Exception as e:
        return f"❌ Ошибка авторизации Google Calendar: {e}"

    now_local = datetime.now().astimezone()
    end = now_local + timedelta(days=days)

    try:
        events_result = service.events().list(
            calendarId="primary",
            timeMin=now_local.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=max_results,
        ).execute()
    except Exception as e:
        return f"❌ Не удалось получить события календаря: {e}"

    items = events_result.get("items", [])
    if not items:
        return f"📅 *На ближайшие {days} дн. в календаре ничего не запланировано.*"

    lines = [f"📅 *План на ближайшие {days} дн.:*\n"]
    last_date: Optional[str] = None
    for ev in items:
        start = ev.get("start", {})
        raw_date = start.get("dateTime") or start.get("date")
        date_key = raw_date[:10] if raw_date else "?"
        if date_key != last_date:
            try:
                d = datetime.fromisoformat(date_key)
                lines.append(f"\n*{d.strftime('%a %d.%m')}:*")
            except Exception:
                lines.append(f"\n*{date_key}:*")
            last_date = date_key
        lines.append(_format_event(ev))
    return "\n".join(lines)
