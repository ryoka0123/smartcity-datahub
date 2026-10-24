@echo off
cd /d "%~dp0"
echo Iniciando SmartCity DataHub en http://127.0.0.1:5000 ...
start http://127.0.0.1:5000/sensores
".venv\Scripts\python.exe" app.py
pause
