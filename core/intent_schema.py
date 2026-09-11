from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

# ==========================================
# 1. СХЕМЫ ПАРАМЕТРОВ ДЛЯ КАЖДОГО INTENT'А
# ==========================================

# 4.1 Приложения и рабочие столы
class OpenApplicationParams(BaseModel):
    app_query: str = Field(..., description="Название или запрос приложения (например: 'яндекс музыка', 'хром', 'steam', 'vs code')")

class CloseApplicationParams(BaseModel):
    app_query: str = Field(..., description="Название процесса или окна для закрытия")

class SwitchVirtualDesktopParams(BaseModel):
    direction: Optional[Literal["left", "right"]] = Field(None, description="Направление переключения стола")
    desktop_number: Optional[int] = Field(None, description="Номер виртуального рабочего стола (1, 2, 3...)")

class CreateVirtualDesktopParams(BaseModel):
    pass

class ListRunningProcessesParams(BaseModel):
    filter: Optional[str] = Field(None, description="Фильтр по имени процесса")

class KillProcessParams(BaseModel):
    name_or_pid: str = Field(..., description="PID (число) или имя процесса (например 'chrome.exe' или 1234)")

class ListInstalledAppsParams(BaseModel):
    query: Optional[str] = Field(None, description="Поисковый запрос по установленным программам")

# 4.2 Файлы и проводник
class OpenExplorerPathParams(BaseModel):
    path: str = Field(..., description="Путь или алиас: 'рабочий стол', 'загрузки', 'документы', 'C:\\...'")

class CreateFolderParams(BaseModel):
    name: str = Field(..., description="Имя создаваемой папки")
    parent: Optional[str] = Field(None, description="Родительская папка (по умолчанию рабочий стол)")

class CreateFileParams(BaseModel):
    name: str = Field(..., description="Имя создаваемого файла")
    parent: Optional[str] = Field(None, description="Родительская директория")
    content: Optional[str] = Field("", description="Текстовое содержимое файла")

class MoveItemParams(BaseModel):
    source: str = Field(..., description="Исходный путь к файлу/папке")
    destination: str = Field(..., description="Путь назначения")

class CopyItemParams(BaseModel):
    source: str = Field(..., description="Исходный путь к файлу/папке")
    destination: str = Field(..., description="Путь назначения")

class DeleteItemParams(BaseModel):
    path: str = Field(..., description="Путь к файлу или папке для удаления")

class RenameItemParams(BaseModel):
    path: str = Field(..., description="Текущий путь")
    new_name: str = Field(..., description="Новое имя файла/папки")

class SearchFilesParams(BaseModel):
    query: str = Field(..., description="Имя файла, маска или ключевое слово для поиска")
    root: Optional[str] = Field(None, description="Корневая директория поиска (по умолчанию Рабочий стол или C:\\)")

# 4.3 Система
class TakeScreenshotParams(BaseModel):
    target: Optional[Literal["full_screen", "active_window"]] = Field("full_screen", description="Цель снимка")
    monitor_index: Optional[int] = Field(0, description="Индекс монитора: 0 для всех, 1, 2... для конкретного")

class SetVolumeParams(BaseModel):
    level: Optional[int] = Field(None, description="Уровень громкости от 0 до 100")
    direction: Optional[Literal["up", "down", "mute", "unmute"]] = Field(None, description="Действие со звуком")

class SetBrightnessParams(BaseModel):
    level: int = Field(..., description="Уровень яркости экрана от 0 до 100")

class MediaControlParams(BaseModel):
    action: Literal["play_pause", "next", "prev", "stop"] = Field(..., description="Действие воспроизведения")

class GetSystemStatusParams(BaseModel):
    pass

class GetDiskSpaceParams(BaseModel):
    drive: Optional[str] = Field(None, description="Буква диска, например 'C' или 'D'")

class ShutdownPcParams(BaseModel):
    delay_min: Optional[int] = Field(0, description="Задержка перед выключением в минутах")

class RestartPcParams(BaseModel):
    delay_min: Optional[int] = Field(0, description="Задержка перед перезагрузкой в минутах")

class SleepPcParams(BaseModel):
    pass

class LockPcParams(BaseModel):
    pass

# 4.4 Интернет
class OpenWebsiteParams(BaseModel):
    url_or_query: str = Field(..., description="URL или поисковый запрос сайта")

class WebSearchParams(BaseModel):
    query: str = Field(..., description="Поисковый запрос в поисковике")

class DownloadFromWikipediaParams(BaseModel):
    query: str = Field(..., description="Тема или запрос статьи Википедии для сохранения")
    destination: Optional[str] = Field(None, description="Папка для сохранения статьи")

class DownloadFileParams(BaseModel):
    url: str = Field(..., description="Прямая ссылка на скачивание файла")
    destination: Optional[str] = Field(None, description="Путь или папка сохранения")

# 4.5 Напоминания и планировщик
class SetReminderParams(BaseModel):
    text: str = Field(..., description="Текст напоминания")
    when: str = Field(..., description="Когда напомнить (например: 'через 15 минут', 'в 18:30', 'каждый день в 09:00')")

class ListRemindersParams(BaseModel):
    pass

class CancelReminderParams(BaseModel):
    reminder_id: str = Field(..., description="ID напоминания для отмены")

# 4.6 Сценарии и доп. автоматизации
class RunScenarioParams(BaseModel):
    scenario_name: str = Field(..., description="Название сохраненного сценария/макроса")

class CreateScenarioParams(BaseModel):
    scenario_name: str = Field(..., description="Имя сценария")
    steps_description: str = Field(..., description="Список действий в сценарии")

class FocusModeParams(BaseModel):
    duration_minutes: int = Field(60, description="Длительность режима фокуса в минутах")

class CleanupTempParams(BaseModel):
    pass

class WatchProcessParams(BaseModel):
    process_name: str = Field(..., description="Имя процесса, за завершением которого следить (например blender.exe)")

class GetWeatherParams(BaseModel):
    city: Optional[str] = Field(None, description="Город (по умолчанию автоопределение)")

class GetExchangeRateParams(BaseModel):
    currency: Optional[str] = Field("USD", description="Валюта (USD, EUR, CNY)")

# 4.7 Разговорное и уточняющее
class ChatReplyParams(BaseModel):
    message: str = Field(..., description="Диалоговый ответ пользователю на общий вопрос")

class ClarifyParams(BaseModel):
    question: str = Field(..., description="Уточняющий вопрос пользователю")


# ==========================================
# ЕДИНЫЙ РЕЕСТР ИНТЕНТОВ (SOURCE OF TRUTH)
# ==========================================

INTENT_REGISTRY: Dict[str, Dict[str, Any]] = {
    # Приложения и рабочие столы
    "open_application": {"model": OpenApplicationParams, "desc": "Нечеткий поиск и запуск приложения на ПК"},
    "close_application": {"model": CloseApplicationParams, "desc": "Мягкое/принудительное закрытие запущенной программы"},
    "switch_virtual_desktop": {"model": SwitchVirtualDesktopParams, "desc": "Переключение на виртуальный рабочий стол (по номеру или стрелкам)"},
    "create_virtual_desktop": {"model": CreateVirtualDesktopParams, "desc": "Создание нового виртуального рабочего стола Windows"},
    "list_running_processes": {"model": ListRunningProcessesParams, "desc": "Получение списка запущенных процессов"},
    "kill_process": {"model": KillProcessParams, "desc": "Завершение процесса по имени или PID"},
    "list_installed_apps": {"model": ListInstalledAppsParams, "desc": "Поиск по установленным приложениям"},

    # Файлы и проводник
    "open_explorer_path": {"model": OpenExplorerPathParams, "desc": "Открытие папки в Проводнике Windows"},
    "create_folder": {"model": CreateFolderParams, "desc": "Создание новой папки"},
    "create_file": {"model": CreateFileParams, "desc": "Создание текстового файла с содержимым"},
    "move_item": {"model": MoveItemParams, "desc": "Перемещение файла или папки"},
    "copy_item": {"model": CopyItemParams, "desc": "Копирование файла или папки"},
    "delete_item": {"model": DeleteItemParams, "desc": "Удаление файла или папки (требует подтверждения)"},
    "rename_item": {"model": RenameItemParams, "desc": "Переименование файла или папки"},
    "search_files": {"model": SearchFilesParams, "desc": "Поиск файлов по имени/расширению"},

    # Система
    "take_screenshot": {"model": TakeScreenshotParams, "desc": "Создание снимка экрана (все мониторы или один)"},
    "set_volume": {"model": SetVolumeParams, "desc": "Установка громкости (0-100), mute или up/down"},
    "set_brightness": {"model": SetBrightnessParams, "desc": "Установка яркости экрана монитора"},
    "media_control": {"model": MediaControlParams, "desc": "Управление медиаплеером (play_pause, next, prev)"},
    "get_system_status": {"model": GetSystemStatusParams, "desc": "Сводка о загрузке процессора, ОЗУ, дисков"},
    "get_disk_space": {"model": GetDiskSpaceParams, "desc": "Проверка свободного места на дисках"},
    "shutdown_pc": {"model": ShutdownPcParams, "desc": "Выключение компьютера (требует подтверждения)"},
    "restart_pc": {"model": RestartPcParams, "desc": "Перезагрузка компьютера (требует подтверждения)"},
    "sleep_pc": {"model": SleepPcParams, "desc": "Перевод ПК в спящий режим"},
    "lock_pc": {"model": LockPcParams, "desc": "Блокировка экрана Windows"},

    # Интернет
    "open_website": {"model": OpenWebsiteParams, "desc": "Открытие ссылки или сайта в браузере"},
    "web_search": {"model": WebSearchParams, "desc": "Поиск информации в интернете"},
    "download_from_wikipedia": {"model": DownloadFromWikipediaParams, "desc": "Поиск и сохранение статьи из Wikipedia в файл"},
    "download_file": {"model": DownloadFileParams, "desc": "Скачивание файла по URL-ссылке"},

    # Напоминания и автоматизации
    "set_reminder": {"model": SetReminderParams, "desc": "Установка напоминания (разового или периодического)"},
    "list_reminders": {"model": ListRemindersParams, "desc": "Список всех активных напоминаний"},
    "cancel_reminder": {"model": CancelReminderParams, "desc": "Отмена напоминания по его ID"},
    "run_scenario": {"model": RunScenarioParams, "desc": "Запуск сохраненного макроса/сценария"},
    "create_scenario": {"model": CreateScenarioParams, "desc": "Сохранение цепочки действий в именованный сценарий"},
    "focus_mode": {"model": FocusModeParams, "desc": "Включение режима фокуса для работы"},
    "cleanup_temp": {"model": CleanupTempParams, "desc": "Очистка временных файлов и мусора"},
    "watch_process": {"model": WatchProcessParams, "desc": "Ожидание завершения указанного процесса с уведомлением"},
    "get_weather": {"model": GetWeatherParams, "desc": "Краткий прогноз погоды"},
    "get_exchange_rate": {"model": GetExchangeRateParams, "desc": "Курс валют"},

    # Разговор и уточнение
    "chat_reply": {"model": ChatReplyParams, "desc": "Обычный ответ в диалоге (если запрос пользователя не управляет ПК)"},
    "clarify": {"model": ClarifyParams, "desc": "Уточняющий вопрос пользователю при неоднозначности"},
}

class StepModel(BaseModel):
    intent: str
    params: Dict[str, Any] = Field(default_factory=dict)

class PlanModel(BaseModel):
    steps: List[StepModel] = Field(default_factory=list)

def generate_intents_documentation() -> str:
    """Генерирует описание всех интентов для динамического промпта LLM."""
    docs = []
    for intent_name, info in INTENT_REGISTRY.items():
        model = info["model"]
        fields = []
        for field_name, field_info in model.model_fields.items():
            req = "обязательное" if field_info.is_required() else "опционально"
            fields.append(f"    - `{field_name}` ({req}): {field_info.description}")
        fields_str = "\n".join(fields) if fields else "    (без параметров)"
        docs.append(f"• `{intent_name}` — {info['desc']}\n  Параметры:\n{fields_str}")
    return "\n\n".join(docs)

def validate_step(intent_name: str, params: Dict[str, Any]) -> StepModel:
    """Валидирует один шаг через Pydantic схему."""
    if intent_name not in INTENT_REGISTRY:
        raise ValueError(f"Неизвестный intent: {intent_name}")
    model_cls = INTENT_REGISTRY[intent_name]["model"]
    validated_params = model_cls(**params)
    return StepModel(intent=intent_name, params=validated_params.model_dump())
