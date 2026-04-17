@echo off
setlocal
cd /d "%~dp0"

echo Delegating to the canonical Windows release build...
call build_suite_release.bat
if errorlevel 1 (
  echo Windows release build failed.
  exit /b 1
)

echo.
echo Build complete.
echo App EXE:      dist\FormatFoundry.exe
echo Updater EXE:  dist\FormatFoundry_Updater.exe
echo Installer:    installer_output\FormatFoundry_Setup.exe
pause

