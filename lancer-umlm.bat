@echo off
cd /d C:\Projects\nachdit\umlm
call venv\Scripts\activate
start /B python manage.py runserver
timeout /t 3 /nobreak >nul
cd umlm-desktop
call npm start
taskkill /F /IM python.exe /T