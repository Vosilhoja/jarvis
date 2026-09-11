import os
from pathlib import Path
from dotenv import load_dotenv

# Базовая директория проекта
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Обязательные ключи доступа
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()

# Поддержка как ALLOWED_TELEGRAM_USER_IDS (список через запятую), так и ALLOWED_USER_ID (один ID)
_raw_ids = os.getenv("ALLOWED_TELEGRAM_USER_IDS", "").strip() or os.getenv("ALLOWED_USER_ID", "0").strip()
ALLOWED_USER_IDS = []
for item in _raw_ids.split(","):
    item = item.strip()
    if item.isdigit():
        ALLOWED_USER_IDS.append(int(item))

# Для обратной совместимости
ALLOWED_USER_ID = ALLOWED_USER_IDS[0] if ALLOWED_USER_IDS else 0

# Настройки ИИ
AI_MODEL_NAME = os.getenv("AI_MODEL_NAME", "gemini-3.6-flash").strip()
AI_FALLBACK_MODEL_NAME = os.getenv("AI_FALLBACK_MODEL_NAME", "gemini-3.5-flash").strip()
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
