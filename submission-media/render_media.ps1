[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$MediaRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $MediaRoot
$RenderPage = Join-Path $MediaRoot "render.html"
$ExportRoot = Join-Path $MediaRoot "exports"

$browserCandidates = @(
    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)
$Browser = $browserCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
if (-not $Browser) {
    throw "Microsoft Edge or Google Chrome is required to render the submission media."
}

$pythonCandidates = @()
if ($env:VIRTUAL_ENV) {
    $pythonCandidates += Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"
}
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand) {
    $pythonCandidates += $pythonCommand.Source
}
$pythonCandidates += Get-ChildItem -Path "C:\Python*\python.exe" -File -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
$pythonCandidates += Get-ChildItem -Path "$env:LOCALAPPDATA\Programs\Python\Python*\python.exe" -File -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName

$Python = $null
foreach ($candidate in $pythonCandidates | Where-Object { $_ } | Select-Object -Unique) {
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
        continue
    }
    $previousErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    & $candidate -c "import PIL" *> $null
    $probeExitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousErrorAction
    if ($probeExitCode -eq 0) {
        $Python = $candidate
        break
    }
}
if (-not $Python) {
    throw "A Python interpreter with Pillow is required. Install requirements.txt in a virtual environment, activate it, and rerun this script."
}
$RenderUri = ([Uri](Resolve-Path -LiteralPath $RenderPage).Path).AbsoluteUri
$Jobs = @(
    @{ Asset = "cover"; Width = 1200; Height = 800; Output = "devpost-cover-1200x800.png" },
    @{ Asset = "workflow"; Width = 1600; Height = 900; Output = "gallery-01-one-workspace-1600x900.png" },
    @{ Asset = "backend"; Width = 1600; Height = 900; Output = "gallery-02-backend-center-1600x900.png" },
    @{ Asset = "aria2"; Width = 1600; Height = 900; Output = "gallery-03-aria2-downloads-1600x900.png" },
    @{ Asset = "release"; Width = 1600; Height = 900; Output = "gallery-04-cross-platform-release-1600x900.png" },
    @{ Asset = "idea"; Width = 1600; Height = 900; Output = "gallery-05-idea-bank-1600x900.png" },
    @{ Asset = "health"; Width = 1600; Height = 900; Output = "gallery-06-pc-health-1600x900.png" },
    @{ Asset = "demo"; Width = 1920; Height = 1080; Output = "youtube-thumbnail-1920x1080.png" }
)

New-Item -ItemType Directory -Force -Path $ExportRoot | Out-Null
foreach ($Job in $Jobs) {
    $OutputPath = Join-Path $ExportRoot $Job.Output
    if (Test-Path -LiteralPath $OutputPath -PathType Leaf) {
        Remove-Item -LiteralPath $OutputPath -Force
    }
    $BrowserArguments = @(
        "--headless=new",
        "--disable-gpu",
        "--disable-sync",
        "--no-first-run",
        "--hide-scrollbars",
        "--window-size=$($Job.Width),$($Job.Height)",
        "--screenshot=$OutputPath",
        "$RenderUri`?asset=$($Job.Asset)"
    )
    & $Browser $BrowserArguments
    $Deadline = (Get-Date).AddSeconds(10)
    while ((Get-Date) -lt $Deadline) {
        if ((Test-Path -LiteralPath $OutputPath -PathType Leaf) -and (Get-Item -LiteralPath $OutputPath).Length -gt 0) {
            break
        }
        Start-Sleep -Milliseconds 100
    }
    if (-not (Test-Path -LiteralPath $OutputPath -PathType Leaf) -or (Get-Item -LiteralPath $OutputPath).Length -le 0) {
        throw "Failed to render $($Job.Asset) to $OutputPath"
    }
}

Copy-Item `
    -LiteralPath (Join-Path $RepoRoot "assets\universal_file_utility_suite_preview.png") `
    -Destination (Join-Path $ExportRoot "format-foundry-icon-512.png") `
    -Force

& $Python (Join-Path $MediaRoot "tools\stamp_and_manifest.py")
if ($LASTEXITCODE -ne 0) {
    throw "Media provenance stamping failed."
}

& $Python (Join-Path $MediaRoot "tools\package_media_kit.py")
if ($LASTEXITCODE -ne 0) {
    throw "Media archive packaging failed."
}

Write-Host "Submission media rendered in $ExportRoot"
