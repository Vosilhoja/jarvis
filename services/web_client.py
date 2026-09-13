import os
import re
import urllib.parse
import webbrowser
import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any

import httpx
from cachetools import TTLCache

logger = logging.getLogger("jarvis")

# Кэш на 10 минут (600 секунд) для погоды и курсов валют
_weather_cache = TTLCache(maxsize=32, ttl=600)
_rates_cache = TTLCache(maxsize=32, ttl=600)

POPULAR_SITES = {
    "гмаил": "https://mail.google.com",
    "gmail": "https://mail.google.com",
    "почта": "https://mail.google.com",
    "гугл": "https://www.google.com",
    "google": "https://www.google.com",
    "ютуб": "https://www.youtube.com",
    "youtube": "https://www.youtube.com",
    "гитхаб": "https://github.com",
    "github": "https://github.com",
    "телеграм": "https://web.telegram.org",
    "telegram": "https://web.telegram.org",
    "тг": "https://web.telegram.org",
    "ватсап": "https://web.whatsapp.com",
    "whatsapp": "https://web.whatsapp.com",
    "яндекс": "https://ya.ru",
    "yandex": "https://ya.ru",
    "яндекс музыка": "https://music.yandex.ru",
    "вк": "https://vk.com",
    "vk": "https://vk.com",
    "вконтакте": "https://vk.com",
    "госуслуги": "https://www.gosuslugi.ru",
    "чатгпт": "https://chatgpt.com",
    "chatgpt": "https://chatgpt.com",
    "википедия": "https://ru.wikipedia.org",
    "wikipedia": "https://wikipedia.org",
    "рутуб": "https://rutube.ru",
    "кинопоиск": "https://www.kinopoisk.ru",
    "вайлдберриз": "https://www.wildberries.ru",
    "ozon": "https://www.ozon.ru",
    "озон": "https://www.ozon.ru",
    "авито": "https://www.avito.ru",
}


def open_url_or_search(query: str) -> str:
    """Открывает URL в браузере или сопоставляет популярный сайт."""
    q = query.strip()
    clean_q = re.sub(
        r"^(зайди\s*(в|на)?\s*(сайт)?|перейди\s*(в|на)?\s*(сайт)?|открой\s*(сайт)?)\s*",
        "",
        q,
        flags=re.IGNORECASE,
    ).strip().lower()

    if clean_q in POPULAR_SITES:
        url = POPULAR_SITES[clean_q]
    elif any(k in clean_q for k in POPULAR_SITES):
        url = None
        for k, v in POPULAR_SITES.items():
            if k in clean_q:
                url = v
                break
        if not url:
            url = f"https://www.google.com/search?q={urllib.parse.quote_plus(q)}"
    elif q.startswith("http://") or q.startswith("https://"):
        url = q
    elif "." in clean_q and " " not in clean_q:
        url = f"https://{clean_q}"
    else:
        url = f"https://www.google.com/search?q={urllib.parse.quote_plus(q)}"

    logger.info(f"Открытие URL: {url}")
    webbrowser.open(url)
    return url


async def search_web_summary(query: str) -> str:
    """Асинхронно выполняет веб-поиск и возвращает краткую выжимку."""
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote_plus(query)}&format=json&no_html=1&skip_disambig=1"
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                res = resp.json()
                abstract = res.get("AbstractText", "")
                if abstract:
                    source = res.get("AbstractURL", "")
                    return f"{abstract}\n\nИсточник: {source}"
    except Exception as e:
        logger.warning(f"DuckDuckGo API ошибка: {e}")

    # Fallback через Википедию (запускаем в threadpool, чтобы не блокировать event loop)
    try:
        def _wiki_lookup():
            import wikipedia
            wikipedia.set_lang("ru")
            page = wikipedia.page(query, auto_suggest=True)
            return f"{page.summary[:500]}...\n\nИсточник: {page.url}"

        return await asyncio.to_thread(_wiki_lookup)
    except Exception:
        pass

    return "Поиск выполнен. Подробные результаты открыты в браузере."


async def download_wikipedia_article(query: str, destination_dir: Optional[str] = None) -> str:
    """Ищет статью в Википедии и асинхронно сохраняет её текст в .txt файл."""
    def _fetch_and_save():
        import wikipedia
        wikipedia.set_lang("ru")
        try:
            page = wikipedia.page(query, auto_suggest=True)
            title = page.title
            content = page.content
            url = page.url
        except Exception:
            wikipedia.set_lang("en")
            try:
                page = wikipedia.page(query, auto_suggest=True)
                title = page.title
                content = page.content
                url = page.url
            except Exception as e:
                raise RuntimeError(f"Статья в Wikipedia по запросу «{query}» не найдена: {e}")

        if not destination_dir or not Path(destination_dir).exists():
            dest_folder = Path(os.environ.get("USERPROFILE", "C:\\Users\\Default")) / "Desktop"
        else:
            dest_folder = Path(destination_dir)

        clean_title = re.sub(r'[\\/*?:"<>|]', "", title)
        file_path = dest_folder / f"Википедия - {clean_title}.txt"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"Заголовок: {title}\n")
            f.write(f"Ссылка: {url}\n\n")
            f.write(content)

        return f"Статья «{title}» скачана и сохранена в: {file_path}"

    return await asyncio.to_thread(_fetch_and_save)


async def download_file_by_url(url: str, destination: Optional[str] = None) -> str:
    """Асинхронно скачивает произвольный файл по прямой ссылке с таймаутом 8 секунд."""
    if not destination:
        dest_folder = Path(os.environ.get("USERPROFILE", "C:\\Users\\Default")) / "Downloads"
        file_name = url.split("/")[-1].split("?")[0] or "downloaded_file.bin"
        target_path = dest_folder / file_name
    else:
        target_path = Path(destination)
        if target_path.is_dir():
            file_name = url.split("/")[-1].split("?")[0] or "downloaded_file.bin"
            target_path = target_path / file_name

    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                with open(target_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=16384):
                        f.write(chunk)
    except httpx.TimeoutException:
        raise RuntimeError("Таймаут скачивания (8 сек) превышен. Файл слишком большой или сервер не отвечает.")

    return f"Файл успешно скачан в: {target_path}"


async def get_weather_forecast(city: Optional[str] = None) -> str:
    """Асинхронно получает текущую погоду через wttr.in с кэшированием на 10 минут."""
    location = (city or "").strip().lower()
    cache_key = location or "default"
    if cache_key in _weather_cache:
        return _weather_cache[cache_key]

    try:
        url = f"https://wttr.in/{urllib.parse.quote(location)}?format=3&m"
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200 and resp.text.strip():
                result = f"🌤 Погода: {resp.text.strip()}"
                _weather_cache[cache_key] = result
                return result
    except Exception as e:
        logger.warning(f"Ошибка получения погоды: {e}")

    return "Не удалось получить данные о погоде."


async def get_exchange_rates(currency: str = "USD") -> str:
    """Асинхронно получает курсы валют ЦБ РФ с кэшированием на 10 минут."""
    cur = currency.upper()
    cache_key = f"rates_{cur}"
    if cache_key in _rates_cache:
        return _rates_cache[cache_key]

    try:
        url = "https://www.cbr-xml-daily.ru/daily_json.js"
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                valute = data.get("Valute", {})
                if cur in valute:
                    info = valute[cur]
                    result = f"💵 Курс {cur}: {info['Value']:.2f} ₽ (изм. {info['Value'] - info['Previous']:+.2f} ₽)"
                else:
                    usd = valute.get("USD", {}).get("Value", 0)
                    eur = valute.get("EUR", {}).get("Value", 0)
                    cny = valute.get("CNY", {}).get("Value", 0)
                    result = f"💵 Курсы валют ЦБ РФ:\nUSD: {usd:.2f} ₽ | EUR: {eur:.2f} ₽ | CNY: {cny:.2f} ₽"
                _rates_cache[cache_key] = result
                return result
    except Exception as e:
        logger.warning(f"Ошибка получения курсов: {e}")

    return "Не удалось получить актуальные курсы валют."
