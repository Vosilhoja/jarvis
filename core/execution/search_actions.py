from typing import Tuple
from telegram import Bot
from core.intent_schema import StepModel
from core.task_queue import UserTaskSession
from core.execution.common import resolve_path_aliases
from services.web_client import (
    open_url_or_search,
    search_web_summary,
    download_wikipedia_article,
    download_file_by_url,
    get_weather_forecast,
    get_exchange_rates
)

async def handle_open_website(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    url = open_url_or_search(step.params["url_or_query"])
    return True, f"✅ Открыл сайт в браузере: {url}"

async def handle_web_search(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    summary = await search_web_summary(step.params["query"])
    await bot.send_message(
        chat_id=session.user_id,
        text=f"🌐 *Результат поиска:*\n\n{summary}",
        parse_mode="Markdown"
    )
    return True, "✅ Поиск в интернете завершен"

async def handle_download_from_wikipedia(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    query = step.params["query"]
    dest = step.params.get("destination") or session.context_memory.get("last_created_folder") or str(resolve_path_aliases("рабочий стол"))
    dest_path = str(resolve_path_aliases(dest))
    msg = await download_wikipedia_article(query, dest_path)
    return True, f"✅ {msg}"

async def handle_download_file(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    url = step.params["url"]
    dest = step.params.get("destination") or session.context_memory.get("last_created_folder")
    msg = await download_file_by_url(url, dest)
    return True, f"✅ {msg}"

async def handle_get_weather(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    msg = await get_weather_forecast(step.params.get("city"))
    await bot.send_message(chat_id=session.user_id, text=msg)
    return True, "✅ Погода получена"

async def handle_get_exchange_rate(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    msg = await get_exchange_rates(step.params.get("currency", "USD"))
    await bot.send_message(chat_id=session.user_id, text=msg)
    return True, "✅ Курсы валют получены"
