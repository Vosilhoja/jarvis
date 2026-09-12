# Регистрация Jarvis в автозапуске Windows (вход в систему).
# Можно запускать без прав администратора — тогда сработает реестр и папка Автозагрузка.

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$TaskName = "JarvisAssistant"
$WatchdogScript = Join-Path $ProjectDir "watchdog.py"

function Find-PythonW {
    $candidates = @()
    $cmdW = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    $cmdP = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($cmdW) { $candidates += $cmdW.Source }
    if ($cmdP) { $candidates += $cmdP.Source }
    $candidates += @(
        "$env:LOCALAPPDATA\Programs\Python\Python313\pythonw.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\pythonw.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\pythonw.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\pythonw.exe"
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path $c)) { return $c }
    }
    throw "Не найден pythonw.exe / python.exe. Установите Python и повторите."
}

$PythonCmd = Find-PythonW
$Launch = "`"$PythonCmd`" `"$WatchdogScript`""

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Автозапуск Jarvis: $TaskName" -ForegroundColor Cyan
Write-Host "Каталог: $ProjectDir"
Write-Host "Команда: $Launch"

# 1) HKCU Run — работает без админа и стартует в сессии пользователя
$runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
New-Item -Path $runKey -Force | Out-Null
Set-ItemProperty -Path $runKey -Name $TaskName -Value $Launch
Write-Host "[OK] Запись в реестре HKCU\\...\\Run" -ForegroundColor Green

# 2) VBS в папке Автозагрузка
$startup = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
New-Item -ItemType Directory -Force -Path $startup | Out-Null
$vbsPath = Join-Path $startup "JarvisAssistant.vbs"
$pyEsc = $PythonCmd.Replace("\", "\\")
$wdEsc = $WatchdogScript.Replace("\", "\\")
$cwdEsc = $ProjectDir.Replace("\", "\\")
@"
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "$cwdEsc"
sh.Run """$pyEsc"" ""$wdEsc""", 0, False
"@ | Set-Content -Path $vbsPath -Encoding ASCII
Write-Host "[OK] VBS в Автозагрузке: $vbsPath" -ForegroundColor Green

# 3) Планировщик (если получится)
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($ExistingTask) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}
try {
    $Action = New-ScheduledTaskAction -Execute $PythonCmd -Argument "`"$WatchdogScript`"" -WorkingDirectory $ProjectDir
    $Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Days 0)
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings | Out-Null
    Write-Host "[OK] Задача Планировщика зарегистрирована" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Планировщик недоступен (не критично): $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Jarvis будет запускаться сразу после входа в Windows." -ForegroundColor Green
