# PowerShell-скрипт для добавления Jarvis в Планировщик заданий Windows
# Запускать от имени Администратора (Run as Administrator)

$ErrorActionPreference = "Stop"

# Получаем текущую директорию скрипта (папка jarvis)
$ScriptDir = Split-Path -Parent $PSScriptRoot
$TaskName = "JarvisAssistant"
$WatchdogScript = Join-Path $ScriptDir "watchdog.py"

# Определяем путь к pythonw.exe (без консольного окна) или python.exe
$PythonCmd = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $PythonCmd) {
    Write-Error "Python не найден в PATH. Убедитесь, что Python установлен и добавлен в системный PATH."
    exit 1
}

$PythonwCmd = $PythonCmd -replace "python\.exe$", "pythonw.exe"
if (-not (Test-Path $PythonwCmd)) {
    $PythonwCmd = $PythonCmd
}

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "   Регистрация задачи автозапуска $TaskName" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Рабочая директория: $ScriptDir"
Write-Host "Исполняемый файл:  $PythonwCmd"
Write-Host "Скрипт:            $WatchdogScript"

# Проверяем, существует ли уже такая задача, и удаляем старую версию
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($ExistingTask) {
    Write-Host "Удаление предыдущей версии задачи..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Создаем действие
$Action = New-ScheduledTaskAction `
    -Execute $PythonwCmd `
    -Argument "`"$WatchdogScript`"" `
    -WorkingDirectory $ScriptDir

# Триггер: при входе пользователя в систему
$Trigger = New-ScheduledTaskTrigger -AtLogOn

# Настройки задачи: работать от батареи, не останавливать при переходе на батарею, перезапускать при сбое
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 365)

# Регистрация с наивысшими правами
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -RunLevel Highest

Write-Host "`n[УСПЕХ] Задача '$TaskName' успешно зарегистрирована в Планировщике заданий!" -ForegroundColor Green
Write-Host "Jarvis будет автоматически стартовать при каждом входе в Windows." -ForegroundColor Green
Write-Host "Для запуска задачи прямо сейчас выполните: Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Cyan
