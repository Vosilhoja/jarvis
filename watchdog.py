"""
Watchdog — супервизор для Jarvis.

Возможности:
  - Автоматический перезапуск main.py при любом падении
  - Экспоненциальная задержка при частых падениях (защита от crash-loop)
  - Лог всех stdout/stderr от дочернего процесса
  - Telegram-уведомление пользователю при перезапуске (если bot-token доступен)
  - Счётчик попыток и статистика работы
"""
import subprocess
import sys
import time
import os
import logging
import requests
from pathlib import Path
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

# ──────────────────────────────────────────
# Логирование
# ──────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
log_path = BASE_DIR / "watchdog.log"

logger = logging.getLogger("watchdog")
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

fh = RotatingFileHandler(log_path, maxBytes=3 * 1024 * 1024, backupCount=3, encoding="utf-8")
fh.setFormatter(formatter)
logger.addHandler(fh)

ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(formatter)
logger.addHandler(ch)


# ──────────────────────────────────────────
# Telegram-уведомление
# ──────────────────────────────────────────
def _send_tg_notification(token: str, user_id: int, text: str) -> None:
    """Отправляет Telegram-сообщение напрямую через HTTP (без aiogram/PTB)."""
    if not token or not user_id:
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={"chat_id": user_id, "text": text}, timeout=10)
        if not resp.ok:
            logger.warning(f"Telegram-уведомление не отправлено: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"Ошибка при отправке Telegram-уведомления: {e}")


def _load_env_vars() -> tuple[str, int]:
    """Возвращает (BOT_TOKEN, ALLOWED_USER_ID) из .env файла."""
    env_path = BASE_DIR / ".env"
    token, user_id = "", 0
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                token = line.split("=", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("ALLOWED_TELEGRAM_USER_IDS=") or line.startswith("ALLOWED_USER_ID="):
                raw = line.split("=", 1)[1].strip().split(",")[0].strip()
                try:
                    user_id = int(raw)
                except ValueError:
                    pass
    return token, user_id


# ──────────────────────────────────────────
# Основной цикл наблюдения
# ──────────────────────────────────────────
def run_watchdog():
    main_script = BASE_DIR / "main.py"
    token, user_id = _load_env_vars()

    logger.info("=" * 60)
    logger.info("Watchdog Jarvis запущен.")
    logger.info(f"Цель: {main_script}")
    logger.info(f"Telegram-уведомления: {'ВКЛ' if token and user_id else 'ВЫКЛ'}")
    logger.info("=" * 60)

    attempt = 0
    last_long_run = datetime.now()  # последний "долгий" запуск (>60 сек)

    while True:
        attempt += 1
        start_dt = datetime.now()
        start_ts = time.time()

        logger.info(f"[Попытка {attempt}] Запуск main.py в {start_dt.strftime('%H:%M:%S')}...")

        # Уведомление о перезапуске (не при первом запуске)
        if attempt > 1:
            _send_tg_notification(
                token, user_id,
                f"♻️ Jarvis перезапущен (попытка {attempt}).\n"
                f"Предыдущий сеанс завершился в {start_dt.strftime('%H:%M:%S')}."
            )

        stdout_path = BASE_DIR / "bot_stdout.txt"
        stderr_path = BASE_DIR / "bot_stderr.txt"
        try:
            with open(stdout_path, "a", encoding="utf-8", errors="replace") as out_f, \
                 open(stderr_path, "a", encoding="utf-8", errors="replace") as err_f:
                proc = subprocess.Popen(
                    [sys.executable, str(main_script)],
                    stdout=out_f,
                    stderr=err_f,
                    cwd=str(BASE_DIR),
                )
                code = proc.wait()
            stdout_lines, stderr_lines = "", ""

        except FileNotFoundError:
            logger.critical(f"main.py не найден: {main_script}")
            _send_tg_notification(token, user_id, "❌ КРИТИЧНО: main.py не найден! Watchdog остановлен.")
            break
        except Exception as e:
            logger.error(f"Не удалось запустить процесс: {e}")
            code = -99
            stdout_lines, stderr_lines = "", str(e)

        run_secs = time.time() - start_ts

        # Логируем вывод
        if stdout_lines and stdout_lines.strip():
            logger.info(f"STDOUT:\n{stdout_lines.strip()[-3000:]}")
        if stderr_lines and stderr_lines.strip():
            logger.error(f"STDERR (код={code}):\n{stderr_lines.strip()[-3000:]}")

        logger.warning(
            f"[Попытка {attempt}] main.py завершился с кодом {code} "
            f"(работал {timedelta(seconds=int(run_secs))})"
        )

        # Если процесс работал долго — сбрасываем "быстрое падение"
        if run_secs >= 60:
            last_long_run = datetime.now()

        # Экспоненциальная задержка при коротких падениях
        if run_secs < 10:
            # Считаем быстрые падения подряд с момента последнего долгого запуска
            seconds_since_long = (datetime.now() - last_long_run).total_seconds()
            if seconds_since_long < 300:  # последние 5 минут
                delay = min(30, 5 * attempt)  # макс. 30 сек
            else:
                delay = 60  # если долго крашится — ждём 1 минуту
            logger.warning(f"Процесс упал быстро. Пауза {delay} сек...")
            _send_tg_notification(
                token, user_id,
                f"⚠️ Jarvis упал (код {code}, работал {run_secs:.1f} сек).\n"
                f"Перезапуск через {delay} сек (попытка {attempt+1})."
            )
            time.sleep(delay)
        else:
            # Нормальное завершение или редкий сбой — короткая пауза
            time.sleep(3)


if __name__ == "__main__":
    run_watchdog()
