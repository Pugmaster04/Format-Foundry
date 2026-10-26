[CmdletBinding()]
param(
    [ValidateSet("Candidate", "Store")]
    [string]$Mode = "Candidate",
    [string]$IdentityFile = "",
    [string]$StoreVersion = "",
    [string]$PythonPath = "",
    [switch]$SkipFreeze
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$repoRoot = $PSScriptRoot
Push-Location $repoRoot
try {
    if (-not $PythonPath) {
        if ($env:VIRTUAL_ENV -and (Test-Path "$env:VIRTUAL_ENV\Scripts\python.exe")) {
            $PythonPath = "$env:VIRTUAL_ENV\Scripts\python.exe"
        } elseif (Test-Path ".venv-windows\Scripts\python.exe") {
            $PythonPath = (Resolve-Path ".venv-windows\Scripts\python.exe").Path
        } else {
            $systemPython = (Get-Command python -ErrorAction Stop).Source
            & $systemPython -m venv .venv-windows
            if ($LASTEXITCODE -ne 0) { throw "Install Python 3.12 or newer with venv support, then run this build again." }
            $PythonPath = (Resolve-Path ".venv-windows\Scripts\python.exe").Path
        }
    }
    if (-not $SkipFreeze) {
        & $PythonPath -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) { throw "MSIX build dependencies could not be installed in the build environment." }
    }
    $arguments = @("-m", "tools.build_msix_package", "--mode", $Mode.ToLowerInvariant())
    if ($IdentityFile) { $arguments += @("--identity-file", $IdentityFile) }
    if ($StoreVersion) { $arguments += @("--store-version", $StoreVersion) }
    if ($SkipFreeze) { $arguments += "--skip-freeze" }
    & $PythonPath @arguments
    if ($LASTEXITCODE -ne 0) { throw "MSIX build or validation failed (exit code $LASTEXITCODE)." }
} finally {
    Pop-Location
}
