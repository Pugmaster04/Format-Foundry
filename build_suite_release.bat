@echo off
setlocal

set ROOT=%~dp0
set ROOT_CLEAN=%ROOT:~0,-1%
cd /d "%ROOT%"
set SNAPSHOT_SCRIPT=%ROOT%tools\create_historical_snapshot.ps1
set STAGE_DIR=%ROOT%release_bins

if exist "%SNAPSHOT_SCRIPT%" (
  echo [0/6] Creating pre-build source snapshot...
  powershell -NoProfile -ExecutionPolicy Bypass -File "%SNAPSHOT_SCRIPT%" -RepoRoot "%ROOT_CLEAN%" -Reason "pre-build" >nul
)

echo [1/6] Building app one-file executable...
python -m PyInstaller --noconfirm --clean UniversalConversionHub_HCB.spec
if errorlevel 1 (
  echo App build failed.
  exit /b 1
)

echo [2/6] Building updater one-file executable...
python -m PyInstaller --noconfirm --clean UniversalConversionHub_HCB_Updater.spec
if errorlevel 1 (
  echo Updater build failed.
  exit /b 4
)

echo [3/6] Building installer (Inno Setup)...
set ISCC_PATH=
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set ISCC_PATH=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set ISCC_PATH=C:\Program Files\Inno Setup 6\ISCC.exe
if "%ISCC_PATH%"=="" (
  echo Inno Setup compiler not found. Install Inno Setup 6 and run this file again.
  exit /b 2
)
"%ISCC_PATH%" "installer\UniversalConversionHub_HCB.iss"
if errorlevel 1 (
  echo Installer build failed.
  exit /b 3
)

echo [4/6] Staging executables in release_bins...
if not exist "%STAGE_DIR%" mkdir "%STAGE_DIR%"
if exist "%ROOT%dist\UniversalFileUtilitySuite.exe" del /f /q "%ROOT%dist\UniversalFileUtilitySuite.exe" >nul 2>nul
if exist "%ROOT%dist\UniversalFileUtilitySuite_Updater.exe" del /f /q "%ROOT%dist\UniversalFileUtilitySuite_Updater.exe" >nul 2>nul
if exist "%ROOT%installer_output\UniversalFileUtilitySuite_Setup.exe" del /f /q "%ROOT%installer_output\UniversalFileUtilitySuite_Setup.exe" >nul 2>nul
if exist "%STAGE_DIR%\UniversalFileUtilitySuite.exe" del /f /q "%STAGE_DIR%\UniversalFileUtilitySuite.exe" >nul 2>nul
if exist "%STAGE_DIR%\UniversalFileUtilitySuite_Updater.exe" del /f /q "%STAGE_DIR%\UniversalFileUtilitySuite_Updater.exe" >nul 2>nul
if exist "%STAGE_DIR%\UniversalFileUtilitySuite_Setup.exe" del /f /q "%STAGE_DIR%\UniversalFileUtilitySuite_Setup.exe" >nul 2>nul
copy /y "%ROOT%dist\UniversalConversionHub_HCB.exe" "%STAGE_DIR%\UniversalConversionHub_HCB.exe" >nul
copy /y "%ROOT%dist\UniversalConversionHub_HCB_Updater.exe" "%STAGE_DIR%\UniversalConversionHub_HCB_Updater.exe" >nul
copy /y "%ROOT%installer_output\UniversalConversionHub_HCB_Setup.exe" "%STAGE_DIR%\UniversalConversionHub_HCB_Setup.exe" >nul

if exist "%SNAPSHOT_SCRIPT%" (
  echo [5/6] Creating post-build source + artifact snapshot...
  powershell -NoProfile -ExecutionPolicy Bypass -File "%SNAPSHOT_SCRIPT%" -RepoRoot "%ROOT_CLEAN%" -Reason "release-build" -IncludeBuildOutputs >nul
)

echo [6/6] Done.
echo App EXE:      "%ROOT%dist\UniversalConversionHub_HCB.exe"
echo Updater EXE:  "%ROOT%dist\UniversalConversionHub_HCB_Updater.exe"
echo Installer:    "%ROOT%installer_output\UniversalConversionHub_HCB_Setup.exe"
echo Staged all in "%STAGE_DIR%"
endlocal
