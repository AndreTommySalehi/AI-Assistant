# Jarvis AI - Windows Task Scheduler Setup (HIDDEN MODE)
# Run as Administrator for best results
# This creates a scheduled task that runs Jarvis COMPLETELY HIDDEN

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = (Get-Command python).Source
$PythonWExe = $PythonExe -replace "python.exe", "pythonw.exe"
$JarvisScript = Join-Path $ScriptDir "main.py"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  JARVIS TASK SCHEDULER SETUP" -ForegroundColor Cyan
Write-Host "  (HIDDEN BACKGROUND MODE)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "WARNING: Not running as Administrator" -ForegroundColor Yellow
    Write-Host "Some features may not work properly" -ForegroundColor Yellow
    Write-Host ""
}

# Check Python
if (-not (Test-Path $PythonExe)) {
    Write-Host "ERROR: Python not found" -ForegroundColor Red
    exit 1
}

# Prefer pythonw.exe (no console window)
if (Test-Path $PythonWExe) {
    $PythonToUse = $PythonWExe
    Write-Host "Using: pythonw.exe (HIDDEN mode)" -ForegroundColor Green
} else {
    $PythonToUse = $PythonExe
    Write-Host "Using: python.exe (will show console)" -ForegroundColor Yellow
}

Write-Host "Python: $PythonToUse" -ForegroundColor Green
Write-Host "Script: $JarvisScript" -ForegroundColor Green
Write-Host ""

# Create the task
$TaskName = "Jarvis AI Assistant"
$TaskDescription = "Marvel-inspired AI assistant running in wake word mode (hidden)"

Write-Host "Creating scheduled task..." -ForegroundColor Yellow

try {
    # Remove existing task if it exists
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    
    # Create action - use pythonw.exe to hide console
    $Action = New-ScheduledTaskAction `
        -Execute $PythonToUse `
        -Argument "`"$JarvisScript`" --wake" `
        -WorkingDirectory $ScriptDir
    
    # Create trigger - at logon
    $Trigger = New-ScheduledTaskTrigger -AtLogOn
    
    # Create settings - NO VISIBLE WINDOW
    $Settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -RestartCount 3 `
        -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
        -Hidden
    
    # Create principal (run in background)
    $Principal = New-ScheduledTaskPrincipal `
        -UserId "$env:USERDOMAIN\$env:USERNAME" `
        -LogonType Interactive `
        -RunLevel Highest
    
    # Register the task
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Description $TaskDescription `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal `
        -Force | Out-Null
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  SUCCESS!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Task '$TaskName' created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Configuration:" -ForegroundColor Cyan
    Write-Host "  - Mode: COMPLETELY HIDDEN (no console windows)" -ForegroundColor White
    Write-Host "  - Starts: At user login (automatic)" -ForegroundColor White
    Write-Host "  - Listening: Always (wake word mode)" -ForegroundColor White
    Write-Host "  - Works in: ANY app (Chrome, games, etc.)" -ForegroundColor White
    Write-Host "  - Auto-restart: Yes (if crashes)" -ForegroundColor White
    Write-Host "  - Battery: Runs on battery power" -ForegroundColor White
    Write-Host ""
    
    # Ask to start now
    $response = Read-Host "Start Jarvis now? (Y/N)"
    if ($response -eq 'Y' -or $response -eq 'y') {
        Write-Host ""
        Write-Host "Starting Jarvis in HIDDEN mode..." -ForegroundColor Yellow
        Start-ScheduledTask -TaskName $TaskName
        Start-Sleep -Seconds 3
        Write-Host ""
        Write-Host "Jarvis is now running in the background!" -ForegroundColor Green
        Write-Host ""
        Write-Host "TEST IT: Say 'Jarvis, what time is it?'" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "You won't see any windows - that's normal!" -ForegroundColor Yellow
        Write-Host "Jarvis is listening from any app you use." -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Management:" -ForegroundColor Cyan
    Write-Host "  - Check if running: Task Manager -> Details tab -> Look for pythonw.exe" -ForegroundColor White
    Write-Host "  - Stop: Task Manager -> End pythonw.exe task" -ForegroundColor White
    Write-Host "  - Restart: Task Scheduler -> Right-click '$TaskName' -> Run" -ForegroundColor White
    Write-Host "  - Disable auto-start: Task Scheduler -> Disable '$TaskName'" -ForegroundColor White
    Write-Host ""
    Write-Host "After reboot, Jarvis will start automatically (hidden)." -ForegroundColor Green
    Write-Host ""
    
} catch {
    Write-Host ""
    Write-Host "ERROR: Failed to create task" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Try running as Administrator" -ForegroundColor Yellow
    exit 1
}

Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")