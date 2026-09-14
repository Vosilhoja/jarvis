# Патч: фичи 12, 21, 22, 29 + библиотеки winloop/msgspec/APScheduler/pynput/send2trash/humanize/loguru

## Как применить
Распакуйте архив поверх `C:\Users\vosil\Desktop\jarvis\` (структура папок совпадает
с репозиторием — файлы лягут туда же, откуда взяты). Затем:

```
pip install -r requirements.txt
```

и перезапустите бота (сначала остановите watchdog.py + main.py, см. предыдущий разбор
в чате — `Stop-Process -Id ... -Force` для обоих, потом `py watchdog.py` заново).

## Новые файлы
- `services/morning_briefing.py` — собирает текст "Доброе утро, сэр!" (погода + план на день из календаря)
- `services/apscheduler_jobs.py` — APScheduler cron-задача, шлёт брифинг автоматически каждый день

## Новые кнопки в меню
- «🌅 Утренний брифинг» и «🙈 Скрыть все окна» — в меню «Система»
- «📂 Что изменилось сегодня» — в меню «Файлы» (спросит папку, можно алиасом: рабочий стол/загрузки/документы)
- «🎚 Громкость приложения» — в меню «Медиа / Звук» (формат ответа: `chrome 30`)

## Настройки (.env, необязательно — есть значения по умолчанию)
```
MORNING_GREETING_HOUR=8
MORNING_GREETING_MINUTE=0
MORNING_GREETING_CITY=          # пусто = автоопределение по IP
```

## Что изменилось под капотом
- `main.py` — winloop (быстрый event loop) + запуск APScheduler в post_init
- `logger_setup.py` — переписан на loguru, перехватывает весь существующий `logging.getLogger("jarvis")` по всему проекту (другие файлы трогать не пришлось)
- `scheduler.py::ReminderManager` — load/save теперь через msgspec.json вместо json (быстрее, обратно совместимо со старым reminders.json)
- `services/security_guard.py` — добавлен 4-й триггер охраны: нажатие любой клавиши (через pynput), в дополнение к движению мыши/смене окна/стола
- `core/execution/file_actions.py::handle_delete_item` — теперь send2trash (Корзина) вместо безвозвратного `shutil.rmtree`/`unlink`
- `services/misc_tools.py` — добавлены `get_folder_changes_today()` и `hide_all_windows_except_active()`, оба зарегистрированы как AI-интенты (можно вызывать и голосом/текстом, не только кнопкой)

## Не включено в этот патч (не выбирались)
Библиотеки dxcam, aiofiles, tenacity, pywinauto, uiautomation, wmi, winotify, pystray,
edge-tts, faster-whisper, pytesseract, speedtest, matplotlib — не добавлялись, как и
не выбранные фичи из списка топ-50.

## Проверено (в Linux-песочнице, статически + через моки Windows-модулей)
py_compile + AST-проверка всех изменённых файлов, реальный функциональный прогон:
loguru-перехват логов, get_folder_changes_today на реальной ФС, hide_all_windows_except_active
с мок-win32gui, роутинг новых кнопок в reply_router (полный сценарий кнопка→ответ→ввод→результат),
security_guard с мок-pynput (нажатие клавиши → блокировка → колбэк), send2trash-вызов в
handle_delete_item, msgspec round-trip + обратная совместимость со старым json.dump-файлом,
сборка утреннего брифинга (погода+календарь) и его отправка через notifier.

pyvda/win32api/pycaw/pynput-с-реальным-X11/winloop на реальной Windows не тестировались —
в Linux-контейнере такой возможности нет (см. ограничения в конце проекта).
