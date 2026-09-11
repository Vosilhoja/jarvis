import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные из .env файла
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()

try:
    ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0").strip())
except ValueError:
    ALLOWED_USER_ID = 0

def validate_config() -> None:
    """Проверяет корректность обязательных переменных конфигурации."""
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not GOOGLE_API_KEY:
        missing.append("GOOGLE_API_KEY")
    if not ALLOWED_USER_ID:
        missing.append("ALLOWED_USER_ID")

    if missing:
        raise RuntimeError(
            f"Не заполнены обязательные переменные в файле .env: {', '.join(missing)}.\n"
            "Скопируйте .env.example в .env и укажите свои параметры."
        )
