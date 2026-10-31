@echo off
rem Stops Trainer Buddy and removes it, its startup entry and its Start menu entries.
where py >nul 2>nul && (py -3 "%~dp0trainer_buddy.pyw" --uninstall) || (python "%~dp0trainer_buddy.pyw" --uninstall)
pause
