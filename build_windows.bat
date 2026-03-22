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
echo App EXE:      dist\UniversalConversionHub_HCB.exe
echo Updater EXE:  dist\UniversalConversionHub_HCB_Updater.exe
echo Installer:    installer_output\UniversalConversionHub_HCB_Setup.exe
pause
