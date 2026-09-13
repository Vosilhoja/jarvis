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

async def handle_open_browser_tab(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    from services.browser_control import open_new_tab
    url = step.params["url"]
    browser = step.params.get("browser")
    import asyncio
    msg = await asyncio.to_thread(open_new_tab, url, browser)
    return True, msg

async def handle_open_incognito(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    from services.browser_control import open_incognito
    url = step.params["url"]
    browser = step.params.get("browser", "chrome")
    import asyncio
    msg = await asyncio.to_thread(open_incognito, url, browser)
    return True, msg

async def handle_close_browser(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    from services.browser_control import close_browser
    browser = step.params["browser"]
    import asyncio
    msg = await asyncio.to_thread(close_browser, browser)
    return True, msg

async def handle_list_browsers(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    from services.browser_control import list_running_browsers
    import asyncio
    msg = await asyncio.to_thread(list_running_browsers)
    await bot.send_message(chat_id=session.user_id, text=msg)
    return True, "✅ Список браузеров отправлен"

async def handle_new_tab(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    from services.browser_control import new_tab_in_active_browser
    url = step.params["url"]
    import asyncio
    msg = await asyncio.to_thread(new_tab_in_active_browser, url)
    return True, msg

async def handle_close_tab(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    from services.browser_control import close_current_tab
    import asyncio
    msg = await asyncio.to_thread(close_current_tab)
    return True, msg

async def handle_switch_tab(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    from services.browser_control import switch_tab
    direction = step.params.get("direction", "next")
    import asyncio
    msg = await asyncio.to_thread(switch_tab, direction)
    return True, msg

async def handle_refresh_apps_index(step: StepModel, session: UserTaskSession, bot: Bot) -> Tuple[bool, str]:
    from core.app_resolver import app_resolver
    import asyncio
    await asyncio.to_thread(app_resolver.load_or_build_index, force_rebuild=True)
    count = len(app_resolver.apps_index)
    return True, f"🔄 Список программ обновлен. Найдено установленных приложений: {count}"
