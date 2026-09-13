import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


class SafeRotatingFileHandler(RotatingFileHandler):
    """
    RotatingFileHandler с защитой от PermissionError при ротации на Windows
    (файл может быть открыт другим процессом).
    """
    def doRollover(self):
        try:
            super().doRollover()
        except PermissionError:
            # Другой процесс держит файл открытым — пропускаем ротацию
            pass
        except OSError:
            pass


def setup_logging(log_file: str = "jarvis.log") -> logging.Logger:
    """
    Настраивает ротацию логов (макс. 5 МБ, 3 бэкапа) и вывод в консоль.
    """
    logger = logging.getLogger("jarvis")
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Логирование в файл с ротацией (SafeRotatingFileHandler — устойчив к PermissionError)
    log_path = Path(__file__).resolve().parent / log_file
    file_handler = SafeRotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
        delay=True,
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Логирование в консоль (stdout) с поддержкой UTF-8 / эмодзи
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
