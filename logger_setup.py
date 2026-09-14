import logging
import sys
from pathlib import Path

from loguru import logger as _loguru_logger


class _InterceptHandler(logging.Handler):
    """
    Перенаправляет все стандартные logging-записи (logger.info/warning/error из
    десятков файлов проекта, которые делают `logging.getLogger("jarvis")`) в loguru,
    чтобы получить ротацию/цвета/фильтрацию loguru без правки каждого файла.
    """
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = _loguru_logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        _loguru_logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(log_file: str = "jarvis.log") -> logging.Logger:
    """
    Настраивает loguru (ротация 5 МБ, 3 бэкапа, устойчиво к PermissionError на
    Windows через enqueue=True) и прозрачно перехватывает весь существующий
    `logging.getLogger("jarvis")` по всему проекту — остальные файлы менять не нужно.
    """
    logger = logging.getLogger("jarvis")
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.INFO)

    log_path = Path(__file__).resolve().parent / log_file

    _loguru_logger.remove()  # убираем дефолтный sink loguru, настраиваем свои

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass

    _loguru_logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> [<level>{level}</level>] [jarvis] {message}",
        colorize=True,
        enqueue=True,
        backtrace=False,
        diagnose=False,
    )
    try:
        _loguru_logger.add(
            log_path,
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} [{level}] [jarvis] {message}",
            rotation="5 MB",
            retention=3,
            encoding="utf-8",
            enqueue=True,
            backtrace=False,
            diagnose=False,
        )
    except (PermissionError, OSError) as exc:
        # На Windows лог-файл может быть захвачен другим процессом/экземпляром бота.
        # В этом случае продолжаем логировать в stdout/stderr без ротации, чтобы
        # один неудачный rollover не убивал весь runtime.
        _loguru_logger.add(
            sys.stderr,
            level="WARNING",
            format="<yellow>{time:YYYY-MM-DD HH:mm:ss}</yellow> [<level>{level}</level>] [jarvis] {message}",
            colorize=True,
            enqueue=True,
            backtrace=False,
            diagnose=False,
        )
        _loguru_logger.warning(
            "Не удалось открыть лог-файл %s для ротации: %s. Логирование продолжается без ротации.",
            log_path,
            exc,
        )

    logger.addHandler(_InterceptHandler())
    logger.propagate = False

    return logger
