@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\start_website_editor.ps1"
if errorlevel 1 pause
