@echo off
setlocal

set ROOT=%~dp0
set ROOT_CLEAN=%ROOT:~0,-1%
cd /d "%ROOT%"

echo [1/7] Building Windows app and updater binaries...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%tools\build_windows_release_phase.ps1" -Phase Binaries -RepoRoot "%ROOT_CLEAN%"
if errorlevel 1 (
  echo Windows binary build failed.
  exit /b 1
)

echo [2/7] Applying Authenticode to app and updater when PFX signing is configured...
for %%F in ("%ROOT%dist\FormatFoundry.exe" "%ROOT%dist\FormatFoundry_Updater.exe" "%ROOT%dist\FormatFoundry_Portable\FormatFoundry.exe") do (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%tools\sign_windows_artifact.ps1" -Path "%%~fF"
  if errorlevel 1 (
    echo Windows executable signing failed.
    exit /b 10
  )
)

echo [3/7] Building installer from the app and updater binaries...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%tools\build_windows_release_phase.ps1" -Phase Installer -RepoRoot "%ROOT_CLEAN%"
if errorlevel 1 (
  echo Windows installer build failed.
  exit /b 3
)

echo [4/7] Applying Authenticode to the installer when PFX signing is configured...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%tools\sign_windows_artifact.ps1" -Path "%ROOT%installer_output\FormatFoundry_Setup.exe"
if errorlevel 1 (
  echo Windows installer signing failed.
  exit /b 11
)

echo [5/7] Staging and validating versioned Windows release assets...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%tools\build_windows_release_phase.ps1" -Phase Stage -RepoRoot "%ROOT_CLEAN%"
if errorlevel 1 (
  echo Windows release staging failed.
  exit /b 5
)

set PACKAGE_VERSION=
for /f "usebackq delims=" %%i in (`python "%ROOT%tools\extract_app_version.py"`) do set PACKAGE_VERSION=%%i
if "%PACKAGE_VERSION%"=="" (
  echo Unable to determine APP_VERSION from modular_file_utility_suite.py.
  exit /b 6
)

echo [6/7] Build validation complete.
echo [7/7] Done.
echo App EXE:      "%ROOT%dist\FormatFoundry.exe"
echo Updater EXE:  "%ROOT%dist\FormatFoundry_Updater.exe"
echo Installer:    "%ROOT%installer_output\FormatFoundry_Setup.exe"
echo Portable ZIP: "%ROOT%release_bins\FormatFoundry_Portable_%PACKAGE_VERSION%_windows_x86_64.zip"
echo Versioned public assets: "%ROOT%release_bins\FormatFoundry_%PACKAGE_VERSION%.exe", "%ROOT%release_bins\FormatFoundry_Updater_%PACKAGE_VERSION%.exe", "%ROOT%release_bins\FormatFoundry_Setup_%PACKAGE_VERSION%.exe"
echo Checksums:    "%ROOT%release_bins\SHA256SUMS"
endlocal
