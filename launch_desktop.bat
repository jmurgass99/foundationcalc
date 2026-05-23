@echo off
REM Launch the FoundationDesignJm desktop app.
REM Double-click this file from Explorer, or run it from any PowerShell.

setlocal
cd /d "%~dp0"
python -m foundationdesignjm.desktop
if errorlevel 1 (
    echo.
    echo Press any key to close...
    pause >nul
)
endlocal
