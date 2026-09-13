import os
from pathlib import Path

def resolve_path_aliases(raw_path: str) -> Path:
    """Разворачивает алиасы путей и переменные окружения в реальный путь.

    Поддерживает привычные алиасы (рабочий стол, downloads, documents), а также
    Windows- и Unix-форматы путей. Если пользователь передал относительный путь,
    он резолвится относительно домашней директории пользователя.
    """
    if raw_path is None:
        return Path.home()

    value = str(raw_path).strip()
    if not value:
        return Path.home()

    user_home = Path.home()
    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        user_home = Path(userprofile)

    aliases = {
        "рабочий стол": user_home / "Desktop",
        "десктоп": user_home / "Desktop",
        "desktop": user_home / "Desktop",
        "загрузки": user_home / "Downloads",
        "скачанные": user_home / "Downloads",
        "downloads": user_home / "Downloads",
        "документы": user_home / "Documents",
        "мои документы": user_home / "Documents",
        "documents": user_home / "Documents",
        "изображения": user_home / "Pictures",
        "картинки": user_home / "Pictures",
        "pictures": user_home / "Pictures",
        "видео": user_home / "Videos",
        "videos": user_home / "Videos",
        "музыка": user_home / "Music",
        "music": user_home / "Music",
        "home": user_home,
        "~": user_home,
    }

    cleaned = value.lower()
    if cleaned in aliases:
        return aliases[cleaned]

    expanded = os.path.expandvars(os.path.expanduser(value))
    path = Path(expanded)
    if not path.is_absolute():
        path = user_home / path
    return path
