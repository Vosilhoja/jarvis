"""Services for clipboard management and history."""
from __future__ import annotations

import logging

logger = logging.getLogger("jarvis")

CLIPBOARD_HISTORY: list[str] = []


def record_clipboard_item(text: str) -> None:
    """Добавляет элемент в локальную историю буфера (до 15 элементов)."""
    global CLIPBOARD_HISTORY
    cleaned = (text or "").strip()
    if not cleaned:
        return
    if cleaned in CLIPBOARD_HISTORY:
        CLIPBOARD_HISTORY.remove(cleaned)
    CLIPBOARD_HISTORY.insert(0, cleaned)
    CLIPBOARD_HISTORY = CLIPBOARD_HISTORY[:15]


def get_clipboard() -> str:
    """Возвращает сохраненную историю буфера обмена."""
    global CLIPBOARD_HISTORY
    try:
        import pyperclip
        cur = pyperclip.paste()
        if cur and cur.strip():
            record_clipboard_item(cur)
    except Exception:
        pass

    if not CLIPBOARD_HISTORY:
        return "(Буфер обмена пуст)"

    lines = [f"📋 *История буфера обмена (всего: {len(CLIPBOARD_HISTORY)}):*\n"]
    for i, item in enumerate(CLIPBOARD_HISTORY[:10], start=1):
        preview = item.replace("\r", "").replace("\n", " ")
        if len(preview) > 100:
            preview = preview[:100] + "..."
        lines.append(f"{i}. `{preview}`")

    latest = CLIPBOARD_HISTORY[0]
    if len(latest) > 600:
        latest = latest[:600] + "\n...(обрезано)"
    lines.append(f"\n*Последний скопированный текст:*\n{latest}")

    return "\n".join(lines)


def set_clipboard(text: str) -> str:
    try:
        import pyperclip
        pyperclip.copy(text)
        record_clipboard_item(text)
        return "✅ Текст скопирован в буфер обмена"
    except Exception as e:
        return f"Ошибка: {e}"
