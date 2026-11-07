@echo off
cd /d "%~dp0"
py -3 -m pip install --upgrade pyinstaller
if errorlevel 1 (pause & exit /b 1)
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name TimberbornSaveTool --paths src src\Timberborn_Save_Tool.py
if errorlevel 1 (pause & exit /b 1)
echo EXE disponible dans dist\TimberbornSaveTool.exe
pause
