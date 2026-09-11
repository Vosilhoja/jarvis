# PowerShell-script to register Jarvis in Task Scheduler
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $PSScriptRoot
$TaskName = "JarvisAssistant"
$WatchdogScript = Join-Path $ScriptDir "watchdog.py"

$PythonCmd = "C:\Users\vosil\AppData\Local\Programs\Python\Python312\pythonw.exe"
if (-not (Test-Path $PythonCmd)) {
    $PythonCmd = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
}

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Registering autostart task: $TaskName" -ForegroundColor Cyan
Write-Host "Working Directory: $ScriptDir"
Write-Host "Executable: $PythonCmd"
Write-Host "Script: $WatchdogScript"

$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($ExistingTask) {
    Write-Host "Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

$Action = New-ScheduledTaskAction -Execute $PythonCmd -Argument "`"$WatchdogScript`"" -WorkingDirectory $ScriptDir
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Days 365)

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -RunLevel Highest

Write-Host ""
Write-Host "[SUCCESS] Task $TaskName registered successfully in Windows Task Scheduler!" -ForegroundColor Green
Write-Host "Jarvis will automatically start on Windows logon." -ForegroundColor Green
