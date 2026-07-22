@echo off
cd /d C:\Users\malak\OneDrive\Desktop\nachdit\umlm
call venv\Scripts\activate
start /B python manage.py runserver
timeout /t 3 /nobreak >nul
cd umlm-desktop
call npm start
