"""Reusable menu input flows kept separate from the button router."""
from __future__ import annotations

import re
from telegram import Update
from telegram.ext import ContextTypes


AWAITING_INPUT_KEYS = (
    "awaiting_screenshot_choice", "awaiting_brightness",
    "awaiting_volume", "awaiting_file_search", "awaiting_app_search",
    "awaiting_qr", "awaiting_file_content_search",
    "awaiting_folder_changes", "awaiting_app_volume",
)


def clear_awaiting(context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in AWAITING_INPUT_KEYS:
        context.user_data.pop(key, None)


def looks_like_keyboard_button(text: str) -> bool:
    return text.startswith((
        "📸", "🖥", "🎛", "📍", "⬅️", "🚀", "🧰", "🤖", "📋", "⏰",
        "🖱", "🌐", "📁", "🎵", "🔑", "⌨", "🧹", "🛤", "⚡", "🏓",
        "🔐", "📷", "🆔", "🗣", "🎲", "🪙", "🪟", "🎯", "🌙", "🔋",
        "🔌", "🖨", "🛡", "⏱", "🗑", "🔄", "📌", "📦", "🔍",
        "📅", "🔧", "📝", "📈",
    ))


def parse_desktop_selection(text: str):
    raw = (text or "").strip().lower()
    if raw in ("все", "all", "*", "всё"):
        return "all"
    if looks_like_keyboard_button(text):
        return None
    parts = [part.strip() for part in re.split(r"[,;]+", raw) if part.strip()]
    if not parts:
        return None
    numbers = []
    for part in parts:
        if not part.isdigit():
            return None
        numbers.append(int(part))
    return numbers or None


async def ask_for_number(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    state_key: str,
    prompt: str,
) -> None:
    context.user_data[state_key] = True
    await update.message.reply_text(prompt, parse_mode="Markdown")
