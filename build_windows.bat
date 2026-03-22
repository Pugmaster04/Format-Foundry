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
echo App EXE:      dist\UniversalConversionHub_UCH.exe
echo Updater EXE:  dist\UniversalConversionHub_UCH_Updater.exe
echo Installer:    installer_output\UniversalConversionHub_UCH_Setup.exe
pause

