@echo off
chcp 65001 >nul
setlocal
set "PY=C:\Users\xushijie\.workbuddy\binaries\python\versions\3.13.12\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "%~dp0flash_robot.py" %*
echo.
pause
