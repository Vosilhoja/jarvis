import os
import re
from pathlib import Path
from dotenv import load_dotenv

# Базовая директория проекта
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Обязательные ключи доступа
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()


def parse_allowed_user_ids(raw_value: str) -> list[int]:
    """Разбирает список Telegram user IDs из .env.

    Поддерживает форматы: "123, 456", "123\n456", "123;456" и одиночный ID.
    Список очищается от пустых значений и дубликатов.
    """
    if raw_value is None:
        return []

    values = re.split(r"[\s,;]+", str(raw_value).strip())
    normalized: list[int] = []
    seen: set[int] = set()
    for item in values:
        if not item:
            continue
        try:
            user_id = int(item)
        except ValueError:
            continue
        if user_id not in seen:
            normalized.append(user_id)
            seen.add(user_id)
    return normalized


def parse_allowed_user_ids_from_env_file(env_text: str) -> list[int]:
    """Читает только значение ALLOWED_TELEGRAM_USER_IDS из .env-файла."""
    if not env_text:
        return []

    for line in env_text.splitlines():
        key, _, value = line.partition("=")
        if key.strip() == "ALLOWED_TELEGRAM_USER_IDS":
            return parse_allowed_user_ids(value)
    return []


# Поддержка как ALLOWED_TELEGRAM_USER_IDS (список через запятую), так и ALLOWED_USER_ID (один ID)
_raw_ids = os.getenv("ALLOWED_TELEGRAM_USER_IDS", "").strip() or os.getenv("ALLOWED_USER_ID", "0").strip()
ALLOWED_USER_IDS = parse_allowed_user_ids(_raw_ids)

# Для обратной совместимости
ALLOWED_USER_ID = ALLOWED_USER_IDS[0] if ALLOWED_USER_IDS else 0

# Настройки ИИ (модели с большим бесплатным лимитом, не gemini-3.x-flash)
AI_MODEL_NAME = os.getenv("AI_MODEL_NAME", "gemini-2.0-flash").strip()
AI_FALLBACK_MODEL_NAME = os.getenv("AI_FALLBACK_MODEL_NAME", "gemini-2.5-flash").strip()
AI_MODEL_CHAIN = [
    m for m in (
        AI_MODEL_NAME,
        AI_FALLBACK_MODEL_NAME,
        "gemini-2.0-flash",
        "gemini-2.5-flash",
        "gemini-2.0-flash-lite",
        "gemini-flash-latest",
    ) if m
]
# уникальный порядок
_seen = set()
AI_MODEL_CHAIN = [m for m in AI_MODEL_CHAIN if not (m in _seen or _seen.add(m))]
AI_MAX_STEPS_PER_MESSAGE = int(os.getenv("AI_MAX_STEPS_PER_MESSAGE", "15"))
AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.2"))

# Поиск приложений
APPS_SCAN_PATHS = [p.strip() for p in os.getenv("APPS_SCAN_PATHS", "").split(",") if p.strip()]
APPS_CACHE_TTL_HOURS = int(os.getenv("APPS_CACHE_TTL_HOURS", "24"))
APP_MATCH_MIN_SCORE = float(os.getenv("APP_MATCH_MIN_SCORE", "60.0"))

# Пути к данным
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
REMINDERS_DB_PATH = DATA_DIR / "reminders.json"
APPS_CACHE_PATH = DATA_DIR / "apps_cache.json"
USER_CONTEXT_PATH = DATA_DIR / "user_context.json"
SCENARIOS_PATH = DATA_DIR / "scenarios.json"

# Мониторинг и пороги алертов
BACKGROUND_CHECK_INTERVAL_SEC = int(os.getenv("BACKGROUND_CHECK_INTERVAL_SEC", "120"))
DISK_FREE_THRESHOLD_GB = float(os.getenv("DISK_FREE_THRESHOLD_GB", "10.0"))
CPU_LOAD_THRESHOLD_PERCENT = float(os.getenv("CPU_LOAD_THRESHOLD_PERCENT", "90.0"))
RAM_LOAD_THRESHOLD_PERCENT = float(os.getenv("RAM_LOAD_THRESHOLD_PERCENT", "90.0"))
TEMP_THRESHOLD_CELSIUS = float(os.getenv("TEMP_THRESHOLD_CELSIUS", "85.0"))
APP_NOT_RESPONDING_TIMEOUT_SEC = int(os.getenv("APP_NOT_RESPONDING_TIMEOUT_SEC", "15"))

# Распознавание речи
STT_PROVIDER = os.getenv("STT_PROVIDER", "google").strip().lower()
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "ru-RU").strip()

def validate_config() -> None:
    """Проверяет корректность обязательных переменных конфигурации."""
    missing = []
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not GOOGLE_API_KEY:
        missing.append("GOOGLE_API_KEY")

    if missing:
        raise RuntimeError(
            f"Не заполнены обязательные переменные в файле .env: {', '.join(missing)}.\n"
            "Скопируйте .env.example в .env и укажите свои параметры."
        )
