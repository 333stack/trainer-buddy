@echo off
rem Installs Trainer Buddy for this Windows user: copies it to %LOCALAPPDATA%\TrainerBuddy,
rem starts it with Windows and adds Start menu entries. Needs Python 3 from python.org.
where py >nul 2>nul && (py -3 "%~dp0trainer_buddy.pyw" --install) || (python "%~dp0trainer_buddy.pyw" --install)
if errorlevel 1 echo. & echo Install failed. Is Python 3 from python.org installed? & pause & exit /b 1
start "" "%LOCALAPPDATA%\TrainerBuddy\trainer_buddy.pyw"
pause
