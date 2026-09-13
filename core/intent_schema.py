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
    desktop_number: Optional[int] = Field(None, description="Номер виртуального рабочего стола Windows (например 1, 2, 3...)")

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

class StartGuardParams(BaseModel):
    delay_sec: Optional[int] = Field(5, description="Задержка перед активацией охраны в секундах (чтобы успеть убрать руку)")

class StopGuardParams(BaseModel):
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

class TextOnlyParams(BaseModel):
    text: str = Field(..., description="Текст")

class HostParams(BaseModel):
    host: Optional[str] = Field("8.8.8.8", description="Хост или IP")

class OptionalPathParams(BaseModel):
    path: str = Field(..., description="Путь к файлу или папке")

class ZipParams(BaseModel):
    source: str = Field(..., description="Что архивировать")
    destination: Optional[str] = Field(None, description="Куда сохранить zip")

class ToolParams(BaseModel):
    tool: str = Field(..., description="Инструмент Windows: task_scheduler, device_manager, event_viewer, services, disk_cleanup, snipping, osk")

class WindowQueryParams(BaseModel):
    query: str = Field(..., description="Часть заголовка окна")

class PasswordParams(BaseModel):
    length: Optional[int] = Field(16, description="Длина пароля")

class HashParams(BaseModel):
    text: str = Field(..., description="Текст для хеширования")
    algo: Optional[str] = Field("sha256", description="Алгоритм: md5, sha1, sha256")

class Base64Params(BaseModel):
    text: str = Field(..., description="Текст")
    mode: Optional[Literal["encode", "decode"]] = Field("encode", description="encode или decode")

class RandomParams(BaseModel):
    kind: Optional[str] = Field("number", description="number / coin / dice")
    min_value: Optional[int] = Field(1)
    max_value: Optional[int] = Field(100)

class QrParams(BaseModel):
    data: str = Field(..., description="Данные для QR-кода")

class HotkeyParams(BaseModel):
    keys: str = Field(..., description="Комбинация клавиш, например ctrl+s")

class TranslateParams(BaseModel):
    text: str = Field(..., description="Текст для перевода")
    target_lang: Optional[str] = Field("ru", description="Целевой язык: ru, en")

class QueryParams(BaseModel):
    query: str = Field(..., description="Поисковый запрос")

class DelayScreenshotParams(BaseModel):
    seconds: Optional[int] = Field(3, description="Задержка перед снимком в секундах")

class SettingsPageParams(BaseModel):
    page: Optional[str] = Field("", description="Страница ms-settings, например display")

class EmptyParams(BaseModel):
    pass


class MouseCoordsParams(BaseModel):
    x: int = Field(..., description="Координата X на экране")
    y: int = Field(..., description="Координата Y на экране")

class MouseClickParams(BaseModel):
    x: Optional[int] = Field(None, description="Координата X (если None - клик в текущей позиции)")
    y: Optional[int] = Field(None, description="Координата Y (если None - клик в текущей позиции)")
    button: Optional[Literal["left", "right", "middle"]] = Field("left", description="Кнопка мыши: left, right, middle")
    clicks: Optional[int] = Field(1, description="Количество кликов (1 или 2)")

class MouseScrollParams(BaseModel):
    amount: int = Field(300, description="Количество делений скролла (положительное - вверх, отрицательное - вниз)")

class PowerPlanParams(BaseModel):
    mode: Optional[Literal["performance", "balanced", "saver"]] = Field("balanced", description="Схема питания")

class ProcessVolumeParams(BaseModel):
    process_name: str = Field(..., description="Имя процесса (например chrome, spotify)")
    volume: int = Field(..., description="Уровень звука (0-100)")

class NoteParams(BaseModel):
    text: str = Field(..., description="Текст заметки")

class BrowserTabParams(BaseModel):
    url: str = Field(..., description="URL-адрес веб-страницы")
    browser: Optional[str] = Field(None, description="Браузер: chrome, edge, yandex, firefox (по умолчанию системный)")

class BrowserIncognitoParams(BaseModel):
    url: str = Field(..., description="URL-адрес для открытия в приватном режиме")
    browser: Optional[str] = Field("chrome", description="Браузер: chrome, edge, yandex, firefox")

class CloseBrowserParams(BaseModel):
    browser: str = Field(..., description="Имя браузера для закрытия (chrome, edge, yandex, firefox)")

class TabUrlParams(BaseModel):
    url: str = Field(..., description="URL-адрес новой вкладки")

class SwitchTabParams(BaseModel):
    direction: Optional[Literal["next", "prev"]] = Field("next", description="Направление переключения: next (следующая) или prev (предыдущая)")


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
    "start_guard": {"model": StartGuardParams, "desc": "Включение режима охраны ПК: при любом движении мыши экран блокируется и отправляется тревога"},
    "stop_guard": {"model": StopGuardParams, "desc": "Отключение режима охраны ПК"},

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

    # Расширенные функции (50+)
    "get_clipboard": {"model": EmptyParams, "desc": "Показать содержимое и историю буфера обмена"},
    "set_clipboard": {"model": TextOnlyParams, "desc": "Положить текст в буфер обмена"},
    "get_local_ip": {"model": EmptyParams, "desc": "Локальный IP компьютера"},
    "get_public_ip": {"model": EmptyParams, "desc": "Внешний публичный IP"},
    "ping_host": {"model": HostParams, "desc": "Пинг хоста"},
    "traceroute_host": {"model": HostParams, "desc": "Трассировка маршрута"},
    "get_network_adapters": {"model": EmptyParams, "desc": "Список сетевых адаптеров"},
    "scan_wifi": {"model": EmptyParams, "desc": "Сканирование Wi-Fi сетей"},
    "get_mac_hostname": {"model": EmptyParams, "desc": "Имя ПК, MAC и локальный IP"},
    "flush_dns": {"model": EmptyParams, "desc": "Очистка DNS-кэша"},
    "ipconfig_summary": {"model": EmptyParams, "desc": "Краткая сводка ipconfig"},
    "speed_test": {"model": EmptyParams, "desc": "Оценка скорости загрузки"},
    "get_battery": {"model": EmptyParams, "desc": "Заряд аккумулятора"},
    "laptop_screen_sleep": {"model": EmptyParams, "desc": "Перевести экран ноутбука в режим ожидания/сна"},
    "get_screen_info": {"model": EmptyParams, "desc": "Разрешение экрана и параметры дисплея"},
    "get_idle_time": {"model": EmptyParams, "desc": "Время простоя клавиатуры/мыши"},
    "empty_recycle_bin": {"model": EmptyParams, "desc": "Очистить корзину"},
    "recycle_bin_info": {"model": EmptyParams, "desc": "Сколько элементов в корзине"},
    "list_downloads": {"model": EmptyParams, "desc": "Последние файлы в Загрузках"},
    "folder_sizes": {"model": EmptyParams, "desc": "Размеры папок на рабочем столе"},
    "get_file_info": {"model": OptionalPathParams, "desc": "Свойства файла или папки"},
    "zip_path": {"model": ZipParams, "desc": "Упаковать файл/папку в zip"},
    "unzip_path": {"model": ZipParams, "desc": "Распаковать zip-архив"},
    "open_windows_tool": {"model": ToolParams, "desc": "Открыть оснастку Windows (планировщик, устройства, службы...)"},
    "toggle_notifications": {"model": EmptyParams, "desc": "Переключить системные уведомления / режим тихий час"},
    "toggle_dark_mode": {"model": EmptyParams, "desc": "Переключить тёмную/светлую тему"},
    "open_night_light": {"model": EmptyParams, "desc": "Открыть ночной свет Windows"},
    "restart_explorer": {"model": EmptyParams, "desc": "Перезапустить проводник explorer.exe"},
    "hibernate_pc": {"model": EmptyParams, "desc": "Гибернация ПК"},
    "cancel_shutdown": {"model": EmptyParams, "desc": "Отменить запланированное выключение"},
    "list_windows": {"model": EmptyParams, "desc": "Список открытых окон"},
    "get_active_window": {"model": EmptyParams, "desc": "Заголовок активного окна"},
    "focus_window": {"model": WindowQueryParams, "desc": "Вывести окно на передний план по названию"},
    "show_desktop": {"model": EmptyParams, "desc": "Свернуть всё / показать рабочий стол"},
    "minimize_windows": {"model": EmptyParams, "desc": "Свернуть все окна"},
    "close_active_window": {"model": EmptyParams, "desc": "Закрыть активное окно (Alt+F4)"},
    "get_hardware_info": {"model": EmptyParams, "desc": "CPU, RAM, GPU, ОС"},
    "list_usb": {"model": EmptyParams, "desc": "Список USB-устройств"},
    "list_printers": {"model": EmptyParams, "desc": "Список принтеров"},
    "list_startup": {"model": EmptyParams, "desc": "Программы в автозагрузке"},
    "firewall_status": {"model": EmptyParams, "desc": "Состояние брандмауэра"},
    "defender_status": {"model": EmptyParams, "desc": "Состояние Microsoft Defender"},
    "generate_password": {"model": PasswordParams, "desc": "Сгенерировать пароль и скопировать"},
    "generate_uuid": {"model": EmptyParams, "desc": "Сгенерировать UUID"},
    "hash_text": {"model": HashParams, "desc": "Хеш текста"},
    "base64_convert": {"model": Base64Params, "desc": "Encode/decode Base64"},
    "random_util": {"model": RandomParams, "desc": "Случайное число, монета или кубик"},
    "get_datetime": {"model": EmptyParams, "desc": "Текущие дата и время"},
    "speak_text": {"model": TextOnlyParams, "desc": "Озвучить текст голосом Windows"},
    "generate_qr": {"model": QrParams, "desc": "Сгенерировать QR-код картинкой"},
    "set_wallpaper": {"model": OptionalPathParams, "desc": "Установить обои рабочего стола"},
    "type_text": {"model": TextOnlyParams, "desc": "Вставить текст в активное окно"},
    "press_hotkey": {"model": HotkeyParams, "desc": "Нажать горячие клавиши"},
    "youtube_search": {"model": QueryParams, "desc": "Поиск на YouTube"},
    "maps_search": {"model": QueryParams, "desc": "Поиск на картах"},
    "translate_text": {"model": TranslateParams, "desc": "Перевод текста"},
    "color_picker": {"model": EmptyParams, "desc": "Цвет пикселя под курсором"},
    "get_volume_level": {"model": EmptyParams, "desc": "Текущая громкость системы"},
    "screenshot_delay": {"model": DelayScreenshotParams, "desc": "Скриншот с задержкой"},
    "open_ms_settings": {"model": SettingsPageParams, "desc": "Открыть страницу параметров Windows"},
    "autostart_status": {"model": EmptyParams, "desc": "Проверить автозапуск Jarvis"},
    "ensure_autostart": {"model": EmptyParams, "desc": "Включить автозапуск Jarvis при входе в Windows"},
    "set_power_plan": {"model": PowerPlanParams, "desc": "Установить схему электропитания ноутбука (производительность/баланс/энергосбережение)"},
    "battery_report": {"model": EmptyParams, "desc": "Сформировать отчет о состоянии аккумулятора ноутбука"},
    "clear_browser_cache": {"model": EmptyParams, "desc": "Очистить кэш браузеров"},
    "create_restore_point": {"model": TextOnlyParams, "desc": "Создать точку восстановления Windows"},
    "quick_note": {"model": NoteParams, "desc": "Быстрая заметка в Блокноте"},
    "set_process_volume": {"model": ProcessVolumeParams, "desc": "Установить громкость для конкретной программы"},
    "list_audio_devices": {"model": EmptyParams, "desc": "Список звуковых устройств"},
    "installed_updates": {"model": EmptyParams, "desc": "Последние обновления Windows"},
    "toggle_caps_lock": {"model": EmptyParams, "desc": "Переключить Caps Lock"},
    "toggle_mute": {"model": EmptyParams, "desc": "Переключить Mute (без звука)"},
    "mouse_move": {"model": MouseCoordsParams, "desc": "Переместить курсор мыши в координаты X, Y"},
    "mouse_click": {"model": MouseClickParams, "desc": "Кликнуть мышью в указанные координаты или на месте"},
    "mouse_drag": {"model": MouseCoordsParams, "desc": "Перетащить (drag & drop) мышь в точку X, Y"},
    "mouse_scroll": {"model": MouseScrollParams, "desc": "Прокрутить колесо мыши"},
    "keyboard_backlight": {"model": EmptyParams, "desc": "Переключить подсветку клавиатуры (F11: яркий, средний, выкл)"},
    "refresh_apps_index": {"model": EmptyParams, "desc": "Принудительно обновить список установленных программ ПК"},
    "open_browser_tab": {"model": BrowserTabParams, "desc": "Открыть URL в новой вкладке браузера (по умолчанию или указанного)"},
    "open_incognito": {"model": BrowserIncognitoParams, "desc": "Открыть URL в приватном режиме/инкогнито"},
    "close_browser": {"model": CloseBrowserParams, "desc": "Закрыть все процессы указанного браузера"},
    "list_browsers": {"model": EmptyParams, "desc": "Список запущенных браузеров и процессов"},
    "new_tab": {"model": TabUrlParams, "desc": "Открыть новую вкладку в уже активном окне браузера"},
    "close_tab": {"model": EmptyParams, "desc": "Закрыть текущую активную вкладку браузера (Ctrl+W)"},
    "switch_tab": {"model": SwitchTabParams, "desc": "Переключить вкладку в активном браузере (следующая/предыдущая)"},
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
