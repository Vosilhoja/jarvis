import os
import re
import urllib.parse
import webbrowser
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import requests

logger = logging.getLogger("jarvis")

def open_url_or_search(query: str):
    """Открывает URL в браузере по умолчанию или запускает поисковый запрос."""
    query = query.strip()
    if query.startswith("http://") or query.startswith("https://"):
        url = query
    elif "." in query and not " " in query:
        url = f"https://{query}"
    else:
        url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
    
    logger.info(f"Открытие URL: {url}")
    webbrowser.open(url)
    return url

def search_web_summary(query: str) -> str:
    """Выполняет веб-поиск и возвращает краткую выжимку."""
    # Используем публичный DuckDuckGo Instant Answer API
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote_plus(query)}&format=json&no_html=1&skip_disambig=1"
        res = requests.get(url, timeout=5).json()
        abstract = res.get("AbstractText", "")
        if abstract:
            source = res.get("AbstractURL", "")
            return f"{abstract}\n\nИсточник: {source}"
    except Exception as e:
        logger.warning(f"DuckDuckGo API ошибка: {e}")

    # Fallback через Википедию
    try:
        import wikipedia
        wikipedia.set_lang("ru")
        page = wikipedia.page(query, auto_suggest=True)
        return f"{page.summary[:500]}...\n\nИсточник: {page.url}"
    except Exception:
        pass

    return f"Поиск выполнен. Подробные результаты открыты в браузере."

def download_wikipedia_article(query: str, destination_dir: Optional[str] = None) -> str:
    """
    Ищет статью в Википедии (рус/англ), скачивает её текст и сохраняет в .txt файл.
    """
    import wikipedia
    wikipedia.set_lang("ru")
    try:
        page = wikipedia.page(query, auto_suggest=True)
        title = page.title
        content = page.content
        url = page.url
    except Exception:
        # Попробуем на английском
        wikipedia.set_lang("en")
        try:
            page = wikipedia.page(query, auto_suggest=True)
            title = page.title
            content = page.content
            url = page.url
        except Exception as e:
            raise RuntimeError(f"Статья в Wikipedia по запросу «{query}» не найдена: {e}")

    # Определяем папку сохранения
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

def download_file_by_url(url: str, destination: Optional[str] = None) -> str:
    """Скачивает произвольный файл по прямой ссылке."""
    if not destination:
        dest_folder = Path(os.environ.get("USERPROFILE", "C:\\Users\\Default")) / "Downloads"
        file_name = url.split("/")[-1].split("?")[0] or "downloaded_file.bin"
        target_path = dest_folder / file_name
    else:
        target_path = Path(destination)
        if target_path.is_dir():
            file_name = url.split("/")[-1].split("?")[0] or "downloaded_file.bin"
            target_path = target_path / file_name

    response = requests.get(url, stream=True, timeout=15)
    response.raise_for_status()

    with open(target_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    return f"Файл успешно скачан в: {target_path}"

def get_weather_forecast(city: Optional[str] = None) -> str:
    """Получает текущую погоду через wttr.in."""
    location = city.strip() if city else ""
    try:
        url = f"https://wttr.in/{urllib.parse.quote(location)}?format=3&m"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200 and resp.text.strip():
            return f"🌤 Погода: {resp.text.strip()}"
    except Exception as e:
        logger.warning(f"Ошибка получения погоды: {e}")
    return "Не удалось получить данные о погоде."

def get_exchange_rates(currency: str = "USD") -> str:
    """Получает курс валют ЦБ РФ."""
    try:
        resp = requests.get("https://www.cbr-xml-daily.ru/daily_json.js", timeout=5).json()
        valute = resp.get("Valute", {})
        cur = currency.upper()
        if cur in valute:
            info = valute[cur]
            return f"💵 Курс {cur}: {info['Value']:.2f} ₽ (изм. {info['Value'] - info['Previous']:+.2f} ₽)"
        else:
            # Выводим USD и EUR
            usd = valute.get("USD", {}).get("Value", 0)
            eur = valute.get("EUR", {}).get("Value", 0)
            cny = valute.get("CNY", {}).get("Value", 0)
            return f"💵 Курсы валют ЦБ РФ:\nUSD: {usd:.2f} ₽ | EUR: {eur:.2f} ₽ | CNY: {cny:.2f} ₽"
    except Exception as e:
        logger.warning(f"Ошибка получения курсов: {e}")
        return "Не удалось получить актуальные курсы валют."
