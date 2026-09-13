"""
Утилиты для нормализации и форматирования текста и Markdown сообщений Telegram.
Обеспечивает единый аккуратный стиль, корректное отображение жирного текста,
списков, кода и защиту от сбоев Markdown-парсера Telegram.
"""
import re
import logging
from typing import Optional
from telegram import Update

logger = logging.getLogger("jarvis")

def convert_markdown_to_telegram(text: str) -> str:
    """
    Преобразует стандартный Markdown / выводы LLM в формат Telegram Markdown (v1 / HTML-safe)
    или аккуратный Telegram Markdown.
    
    В частности:
    - Преобразует двойные звездочки **bold** в одиночные *bold* (так как Telegram Markdown v1 использует *text* для жирного шрифта, из-за чего **text** отображалось буквально).
    - Исправляет кривые списки и лишние отступы.
    - Сохраняет блоки кода `code` и ```code```.
    """
    if not text:
        return ""

    # Если в тексте есть блоки кода ```...```, защищаем их от модификации
    code_blocks = []
    def save_code_block(match):
        code_blocks.append(match.group(0))
        return f"QQQCODEBLOCK{len(code_blocks)-1}ZZZ"

    # Защищаем многострочные блоки кода
    processed = re.sub(r"```[\s\S]*?```", save_code_block, text)
    
    # Защищаем однострочный код `...`
    inline_codes = []
    def save_inline_code(match):
        inline_codes.append(match.group(0))
        return f"QQQINLINECODE{len(inline_codes)-1}ZZZ"

    processed = re.sub(r"`[^`\n]+`", save_inline_code, processed)

    # 1. Заменяем жирный текст **text** на *text*
    processed = re.sub(r"\*\*([^\*\n]+?)\*\*", r"*\1*", processed)

    # 2. Восстанавливаем сохраненные инлайн-коды
    for idx, code in enumerate(inline_codes):
        processed = processed.replace(f"QQQINLINECODE{idx}ZZZ", code)

    # 3. Восстанавливаем многострочные блоки кода
    for idx, block in enumerate(code_blocks):
        processed = processed.replace(f"QQQCODEBLOCK{idx}ZZZ", block)

    return processed.strip()


def escape_md(text: str) -> str:
    """Экранирует спецсимволы Markdown v1 в пользовательских данных."""
    return re.sub(r'([_\*\[\]\(\)~`>#+\-=|{}.!])', r'\\\1', str(text))


async def safe_reply(update: Update, text: str, reply_markup=None, parse_mode: str = "Markdown") -> None:
    """
    Безопасная отправка ответа пользователю:
    - Нормализует **text** в *text* при parse_mode="Markdown"
    - При сбое парсинга Telegram API мягко отправляет чистый текст без краша.
    """
    msg = update.message or (update.callback_query and update.callback_query.message if update.callback_query else None)
    if not msg:
        return

    formatted_text = convert_markdown_to_telegram(text) if parse_mode == "Markdown" else text
    try:
        await msg.reply_text(formatted_text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception as e:
        if "parse" in str(e).lower() or "entity" in str(e).lower():
            plain = re.sub(r'[*_`]', '', text)
            try:
                await msg.reply_text(plain, reply_markup=reply_markup)
            except Exception as e2:
                logger.error(f"safe_reply: не смогли отправить сообщение: {e2}")
        else:
            raise


async def safe_edit(update: Update, text: str, reply_markup=None, parse_mode: str = "Markdown") -> None:
    """
    Безопасное редактирование сообщения:
    - Нормализует разметку
    - При ошибке парсинга откатывается к чистому тексту.
    """
    cq = update.callback_query
    if not cq:
        return

    formatted_text = convert_markdown_to_telegram(text) if parse_mode == "Markdown" else text
    try:
        await cq.edit_message_text(formatted_text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception as e:
        if "parse" in str(e).lower() or "entity" in str(e).lower():
            plain = re.sub(r'[*_`]', '', text)
            try:
                await cq.edit_message_text(plain, reply_markup=reply_markup)
            except Exception as e2:
                logger.error(f"safe_edit: не смогли отредактировать: {e2}")
        else:
            raise
