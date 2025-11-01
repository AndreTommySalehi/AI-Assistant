@echo off
echo ========================================
echo   JARVIS OPTIMIZATION UPDATE
echo ========================================
echo.
echo This will:
echo  - Install required packages for auto-focus
echo  - Update voice system for faster response
echo  - Fix console flashing issue
echo  - Enable auto-window-switching
echo.
pause

REM Stop any running Jarvis instances
echo.
echo Stopping Jarvis...
taskkill /F /IM pythonw.exe 2>NUL
taskkill /F /IM python.exe 2>NUL
timeout /t 2

REM Install new requirements
echo.
echo Installing required packages...
python -m pip install --upgrade pywin32 psutil

REM Backup old files
echo.
echo Creating backups...
if exist "src\voice.py" (
    copy "src\voice.py" "src\voice.py.backup" >NUL 2>&1
    echo   - Backed up voice.py
)
if exist "src\app_launcher.py" (
    copy "src\app_launcher.py" "src\app_launcher.py.backup" >NUL 2>&1
    echo   - Backed up app_launcher.py
)

REM Instructions
echo.
echo ========================================
echo   MANUAL STEPS REQUIRED:
echo ========================================
echo.
echo 1. Replace src\voice.py with the new voice_optimized.py
echo    (Copy the new code from the artifact)
echo.
echo 2. Replace src\app_launcher.py with the new version
echo    (Copy the new code from the artifact)
echo.
echo 3. Re-run the task scheduler setup:
echo    Right-click setup_task_scheduler.ps1 -^> Run with PowerShell
echo.
echo 4. Say Y to start Jarvis
echo.
echo ========================================
echo   WHAT'S NEW:
echo ========================================
echo.
echo  ✓ NO MORE console flashing (completely invisible)
echo  ✓ FASTER responses (optimized voice model)
echo  ✓ Auto-focus apps (Chrome/apps come to front)
echo  ✓ Shorter pause detection (quicker listening)
echo.
pause