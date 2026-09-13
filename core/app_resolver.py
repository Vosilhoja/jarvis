import os
import sys
import time
import json
import winreg
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from rapidfuzz import process, fuzz
import win32com.client

from config import (
    APPS_CACHE_PATH,
    APPS_CACHE_TTL_HOURS,
    APP_MATCH_MIN_SCORE,
    APPS_SCAN_PATHS,
)

logger = logging.getLogger("jarvis")

class AppResolver:
    """
    Сканирует установленные программы Windows (Start Menu, Desktop, Uninstall registry, PATH)
    и выполняет двухступенчатый нечеткий (fuzzy) + ИИ поиск.
    """
    def __init__(self):
        self.cache_file = APPS_CACHE_PATH
        self.ttl_seconds = APPS_CACHE_TTL_HOURS * 3600
        self.apps_index: List[Dict[str, Any]] = []
        self.load_or_build_index()

    def load_or_build_index(self, force_rebuild: bool = False):
        """Загружает кэш из JSON или перестраивает при истечении TTL."""
        if not force_rebuild and self.cache_file.exists():
            try:
                mtime = self.cache_file.stat().st_mtime
                if time.time() - mtime < self.ttl_seconds:
                    try:
                        import orjson
                        data = orjson.loads(self.cache_file.read_bytes())
                    except Exception:
                        with open(self.cache_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                    self.apps_index = data.get("apps", [])
                    logger.info(f"Загружено {len(self.apps_index)} приложений из кэша.")
                    return
            except Exception as e:
                logger.warning(f"Ошибка чтения кэша приложений: {e}")

        logger.info("Сканирование установленных приложений Windows...")
        self.apps_index = self._scan_all_apps()
        self._save_cache()
        logger.info(f"Индексация завершена: найдено {len(self.apps_index)} приложений.")

    def _save_cache(self):
        try:
            try:
                import orjson
                self.cache_file.write_bytes(orjson.dumps({"updated_at": time.time(), "apps": self.apps_index}))
            except Exception:
                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump({"updated_at": time.time(), "apps": self.apps_index}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Не удалось сохранить кэш приложений: {e}")

    def _resolve_shortcut(self, shortcut_path: str) -> Optional[str]:
        """Разворачивает .lnk ярлык в путь к .exe через WScript.Shell."""
        try:
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            target = shortcut.Targetpath
            if target and target.lower().endswith((".exe", ".bat", ".cmd")):
                return target
        except Exception:
            pass
        return None

    def _scan_shortcuts_in_dir(self, dir_path: Path, source_name: str) -> List[Dict[str, Any]]:
        results = []
        if not dir_path.exists():
            return results

        for root, _, files in os.walk(dir_path):
            for file in files:
                ext = Path(file).suffix.lower()
                name_without_ext = Path(file).stem
                full_path = str(Path(root) / file)

                # Пропускаем удаляторы и справку
                lower_stem = name_without_ext.lower()
                if any(x in lower_stem for x in ["uninstall", "деинстал", "удалить", "readme", "help", "справка"]):
                    continue

                exec_path = None
                if ext == ".lnk":
                    exec_path = self._resolve_shortcut(full_path) or full_path
                elif ext in [".exe", ".bat", ".cmd"]:
                    exec_path = full_path

                if exec_path:
                    results.append({
                        "display_name": name_without_ext,
                        "exec_path": exec_path,
                        "source": source_name,
                        "aliases": [name_without_ext.lower(), name_without_ext.replace(" ", "").lower()]
                    })
        return results

    def _scan_registry_uninstall(self) -> List[Dict[str, Any]]:
        results = []
        reg_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]

        for root_hkey, subkey in reg_keys:
            try:
                with winreg.OpenKey(root_hkey, subkey) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as app_key:
                                display_name = ""
                                install_loc = ""
                                display_icon = ""

                                try:
                                    display_name, _ = winreg.QueryValueEx(app_key, "DisplayName")
                                except OSError:
                                    pass

                                try:
                                    install_loc, _ = winreg.QueryValueEx(app_key, "InstallLocation")
                                except OSError:
                                    pass

                                try:
                                    display_icon, _ = winreg.QueryValueEx(app_key, "DisplayIcon")
                                except OSError:
                                    pass

                                if not display_name:
                                    continue

                                # Пытаемся найти исполняемый файл
                                target_exe = None
                                if display_icon and display_icon.lower().endswith(".exe") and Path(display_icon).exists():
                                    target_exe = display_icon
                                elif install_loc and Path(install_loc).exists():
                                    # Поищем .exe в корне папки установки
                                    for f in Path(install_loc).glob("*.exe"):
                                        if not any(x in f.name.lower() for x in ["unins", "setup", "update", "crash"]):
                                            target_exe = str(f)
                                            break

                                if target_exe:
                                    results.append({
                                        "display_name": display_name,
                                        "exec_path": target_exe,
                                        "source": "registry",
                                        "aliases": [display_name.lower(), display_name.replace(" ", "").lower()]
                                    })
                        except OSError:
                            continue
            except OSError:
                continue

        return results

    def _resolve_app_path_registry(self, exe_name: str) -> Optional[str]:
        """Ищет реальный путь программы через HKLM/HKCU App Paths (официальный механизм Windows)."""
        keys = [
            (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}"),
            (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}"),
            (winreg.HKEY_CURRENT_USER, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}"),
        ]
        for hive, path in keys:
            try:
                with winreg.OpenKey(hive, path) as key:
                    value, _ = winreg.QueryValueEx(key, "")  # (по умолчанию) содержит полный путь
                    if value and Path(value).exists():
                        return value
            except OSError:
                continue
        return None


    def _scan_start_apps_powershell(self) -> List[Dict[str, Any]]:
        """Использует Get-StartApps — источник, который видит ВСЁ, что видно в меню Пуск,
        включая UWP/Microsoft Store приложения, которые не ловятся сканированием .lnk и реестра."""
        results = []
        try:
            import subprocess
            ps_cmd = "Get-StartApps | ConvertTo-Json -Compress"
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=0x08000000,
            )
            import json as _json
            data = _json.loads(r.stdout)
            if isinstance(data, dict):
                data = [data]
            for entry in data:
                name = entry.get("Name")
                app_id = entry.get("AppID")
                if not name or not app_id:
                    continue
                # UWP AppID выглядит как "Package_Family!App", обычные - как путь к .exe или GUID
                if "!" in app_id:
                    exec_path = f"shell:AppsFolder\\{app_id}"
                    launch_via = "explorer"
                else:
                    exec_path = app_id
                    launch_via = "direct"
                results.append({
                    "display_name": name,
                    "exec_path": exec_path,
                    "source": "Get-StartApps",
                    "launch_via": launch_via,
                    "aliases": [name.lower(), name.replace(" ", "").lower()]
                })
        except Exception as e:
            logger.warning(f"Get-StartApps сканирование не удалось: {e}")
        return results

    def _scan_all_apps(self) -> List[Dict[str, Any]]:
        all_apps = []
        seen_paths = set()

        # 1. Приоритетный источник: Get-StartApps (видит всё из меню Пуск, включая UWP и Microsoft Store)
        for item in self._scan_start_apps_powershell():
            exec_p = item["exec_path"].lower()
            if exec_p not in seen_paths:
                seen_paths.add(exec_p)
                all_apps.append(item)

        user_appdata = os.getenv("APPDATA", "")
        all_users_profile = os.getenv("ProgramData", "C:\\ProgramData")
        user_profile = os.getenv("USERPROFILE", "C:\\Users\\Default")
        public_profile = os.getenv("PUBLIC", "C:\\Users\\Public")

        scan_dirs = [
            (Path(user_appdata) / r"Microsoft\Windows\Start Menu\Programs", "User Start Menu"),
            (Path(all_users_profile) / r"Microsoft\Windows\Start Menu\Programs", "Common Start Menu"),
            (Path(user_profile) / "Desktop", "User Desktop"),
            (Path(public_profile) / "Desktop", "Public Desktop"),
        ]

        # Дополнительные пути из настроек
        for p in APPS_SCAN_PATHS:
            if Path(p).exists():
                scan_dirs.append((Path(p), f"Custom: {p}"))

        seen_paths = set()
        for directory, source in scan_dirs:
            for item in self._scan_shortcuts_in_dir(directory, source):
                exec_p = item["exec_path"].lower()
                if exec_p not in seen_paths:
                    seen_paths.add(exec_p)
                    all_apps.append(item)

        # Реестр
        for item in self._scan_registry_uninstall():
            exec_p = item["exec_path"].lower()
            if exec_p not in seen_paths:
                seen_paths.add(exec_p)
                all_apps.append(item)

        # Стандартные системные утилиты Windows
        system_tools = [
            {"display_name": "Калькулятор", "exec_path": "calc.exe", "aliases": ["калькулятор", "calc", "calculator"]},
            {"display_name": "Блокнот", "exec_path": "notepad.exe", "aliases": ["блокнот", "notepad", "нотепад"]},
            {"display_name": "Проводник", "exec_path": "explorer.exe", "aliases": ["проводник", "explorer", "папки", "диски"]},
            {"display_name": "Диспетчер задач", "exec_path": "taskmgr.exe", "aliases": ["диспетчер задач", "taskmgr", "task manager"]},
            {"display_name": "Командная строка", "exec_path": "cmd.exe", "aliases": ["командная строка", "терминал", "cmd", "консоль"]},
            {"display_name": "PowerShell", "exec_path": "powershell.exe", "aliases": ["powershell", "павершелл", "терминал"]},
            {"display_name": "Paint", "exec_path": "mspaint.exe", "aliases": ["paint", "паинт", "пэйнт", "рисовалка"]},
            {"display_name": "Яндекс Музыка", "exec_path": "YandexMusic.exe", "aliases": ["яндекс музыка", "янд музыка", "yandex music", "ymusic", "музыка от яндекса"]},
            {"display_name": "Google Chrome", "exec_path": "chrome.exe", "aliases": ["хром", "chrome", "гугл хром", "браузер"]},
            {"display_name": "Telegram", "exec_path": "Telegram.exe", "aliases": ["телеграм", "телега", "tg", "telegram"]},
            {"display_name": "Visual Studio Code", "exec_path": "code", "aliases": ["vs code", "vscode", "код", "вс код"]},
            {"display_name": "Steam", "exec_path": "steam.exe", "aliases": ["стим", "steam"]},
        ]

        for tool in system_tools:
            # Если еще нет в списке с таким именем
            if not any(a["display_name"].lower() == tool["display_name"].lower() for a in all_apps):
                real_path = self._resolve_app_path_registry(tool["exec_path"]) or tool["exec_path"]
                all_apps.append({
                    "display_name": tool["display_name"],
                    "exec_path": real_path,
                    "source": "System/Presets",
                    "aliases": tool["aliases"]
                })

        return all_apps

    def add_user_alias(self, display_name: str, new_alias: str):
        """Добавляет новый пользовательский алиас к программе и сохраняет в кэш."""
        new_alias = new_alias.strip().lower()
        for app in self.apps_index:
            if app["display_name"].lower() == display_name.lower():
                if new_alias not in app.get("aliases", []):
                    app.setdefault("aliases", []).append(new_alias)
                    self._save_cache()
                    logger.info(f"Добавлен алиас '{new_alias}' для приложения '{display_name}'")
                break

    def find_candidates(self, query: str, top_k: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        """
        1-й этап: Нечеткий fuzzy-поиск с rapidfuzz по названию и алиасам.
        Возвращает список пар (app, score).
        """
        q = query.strip().lower()
        candidates = []

        for app in self.apps_index:
            # Сравниваем с display_name
            score_name = fuzz.token_sort_ratio(q, app["display_name"].lower())
            score_partial = fuzz.partial_ratio(q, app["display_name"].lower())
            best_score = max(score_name, score_partial)

            # Сравниваем со всеми алиасами
            for alias in app.get("aliases", []):
                s1 = fuzz.token_sort_ratio(q, alias)
                s2 = fuzz.partial_ratio(q, alias)
                best_score = max(best_score, s1, s2)
                # Точное совпадение алиаса дает 100
                if q == alias or alias in q:
                    best_score = max(best_score, 95.0)

            candidates.append((app, float(best_score)))

        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_k]

    def launch_app(self, app_info: Dict[str, Any]) -> bool:
        """Запускает приложение через explorer (для UWP/Store) или os.startfile/subprocess."""
        exec_path = app_info["exec_path"]

        def _record():
            try:
                from services.usage_stats import record_app_launch
                record_app_launch(app_info.get("display_name", "?"))
            except Exception:
                pass

        try:
            logger.info(f"Запуск приложения: {app_info['display_name']} -> {exec_path} (via={app_info.get('launch_via')})")
            if app_info.get("launch_via") == "explorer":
                import subprocess
                subprocess.Popen(["explorer.exe", exec_path])
                _record()
                return True

            os.startfile(exec_path)
            _record()
            return True
        except Exception as e:
            logger.warning(f"os.startfile не сработал для {exec_path}: {e}, пробуем subprocess...")
            try:
                import subprocess
                subprocess.Popen(exec_path, shell=True)
                _record()
                return True
            except Exception as ex:
                logger.error(f"Не удалось запустить {exec_path}: {ex}")
                return False

# Глобальный синглтон
app_resolver = AppResolver()
