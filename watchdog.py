import subprocess
import sys
import time
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Настройка логирования watchdog
log_path = Path(__file__).resolve().parent / "watchdog.log"
logger = logging.getLogger("watchdog")
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

file_handler = RotatingFileHandler(log_path, maxBytes=2 * 1024 * 1024, backupCount=2, encoding="utf-8")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def run_watchdog():
    main_script = Path(__file__).resolve().parent / "main.py"
    logger.info("Watchdog запущен. Мониторинг main.py...")

    while True:
        logger.info(f"Запуск процесса {main_script}...")
        start_time = time.time()

        try:
            # Запускаем main.py тем же интерпретатором Python
            proc = subprocess.run([sys.executable, str(main_script)])
            code = proc.returncode
        except Exception as e:
            logger.error(f"Не удалось запустить процесс: {e}")
            code = -1

        run_duration = time.time() - start_time
        logger.warning(f"main.py завершил работу с кодом {code} после {run_duration:.1f} сек.")

        # Защита от слишком частых падений (например, если нет интернета или ошибка в .env)
        if run_duration < 5:
            logger.warning("Процесс упал слишком быстро. Пауза 10 секунд перед повторным запуском...")
            time.sleep(10)
        else:
            time.sleep(3)

if __name__ == "__main__":
    run_watchdog()
