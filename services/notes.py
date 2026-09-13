"""Notes and text manipulation services."""
from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger("jarvis")


def open_notepad_quick_note(text: str) -> str:
    """Создаёт временный файл с текстом и открывает его в Блокноте."""
    try:
        temp_file = Path(tempfile.gettempdir()) / "jarvis_quick_note.txt"
        temp_file.write_text(text, encoding="utf-8")
        subprocess.Popen(["notepad.exe", str(temp_file)])
        return f"📝 Заметка открыта в Блокноте:\n«{text[:100]}»"
    except Exception as e:
        return f"Ошибка создания заметки: {e}"
