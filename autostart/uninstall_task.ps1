# PowerShell-скрипт для удаления Jarvis из Планировщика заданий Windows
# Запускать от имени Администратора (Run as Administrator)

$TaskName = "JarvisAssistant"

Write-Host "Поиск задачи '$TaskName' в Планировщике заданий..." -ForegroundColor Cyan

$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if ($ExistingTask) {
    # Останавливаем, если сейчас запущена
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "[УСПЕХ] Задача '$TaskName' удалена из автозагрузки." -ForegroundColor Green
} else {
    Write-Host "Задача '$TaskName' не найдена в Планировщике." -ForegroundColor Yellow
}
