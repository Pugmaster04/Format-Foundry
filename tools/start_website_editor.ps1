$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$projectPython = Join-Path $projectRoot '.venv-windows\Scripts\python.exe'
$pythonPrefix = @()
if (Test-Path -LiteralPath $projectPython) {
    $pythonExecutable = $projectPython
} else {
    $pythonCommand = Get-Command py.exe,python.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $pythonCommand) {
        Write-Host 'Python is needed to open the local appearance editor. Install Python 3.11 or newer, then run this launcher again.'
        exit 1
    }
    $pythonExecutable = $pythonCommand.Source
    if ($pythonCommand.Name -eq 'py.exe') { $pythonPrefix = @('-3') }
}
& $pythonExecutable @pythonPrefix -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Please install Python 3.11 or newer, then run this launcher again.'
    exit 1
}
$editorArguments = @($pythonPrefix) + @('-m', 'tools.website_editor')
Start-Process -FilePath $pythonExecutable -ArgumentList $editorArguments -WorkingDirectory $projectRoot -WindowStyle Hidden
