@echo off
cd /d "%~dp0"
py -3 src\Timberborn_Save_Tool.py
if errorlevel 1 (
  echo.
  echo Python 3 not detected. Install it from https://www.python.org/downloads/
  pause
)
