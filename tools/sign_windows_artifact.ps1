[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Find-SignTool {
    $command = Get-Command "signtool.exe" -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $roots = @(
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin",
        "$env:ProgramFiles\Windows Kits\10\bin"
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }
    foreach ($root in $roots) {
        $candidate = Get-ChildItem -LiteralPath $root -Filter "signtool.exe" -File -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match "\\x64\\signtool\.exe$" } |
            Sort-Object -Property FullName -Descending |
            Select-Object -First 1
        if ($candidate) {
            return $candidate.FullName
        }
    }
    throw "signtool.exe was not found. Install the Windows SDK before producing a signed release."
}

$required = $env:REQUIRE_WINDOWS_SIGNING -match "^(1|true|yes)$"
$certificateBase64 = [string]$env:WINDOWS_SIGNING_CERTIFICATE_BASE64
$certificatePath = [string]$env:WINDOWS_SIGNING_PFX_PATH
$certificatePassword = [string]$env:WINDOWS_SIGNING_CERTIFICATE_PASSWORD
$timestampUrl = [string]$env:WINDOWS_SIGNING_TIMESTAMP_URL
if (-not $timestampUrl) {
    $timestampUrl = "http://timestamp.digicert.com"
}

if (-not $certificateBase64 -and -not $certificatePath) {
    if ($required) {
        throw "Tagged releases require WINDOWS_SIGNING_CERTIFICATE_BASE64 (or WINDOWS_SIGNING_PFX_PATH)."
    }
    Write-Host "No Windows signing credential configured; skipping non-release artifact signing."
    exit 0
}
if (-not $certificatePassword) {
    throw "WINDOWS_SIGNING_CERTIFICATE_PASSWORD is required for the protected PFX credential."
}

$artifactPath = (Resolve-Path -LiteralPath $Path).Path
$temporaryPfx = $null
try {
    if ($certificateBase64) {
        $temporaryPfx = Join-Path ([System.IO.Path]::GetTempPath()) ("format-foundry-signing-{0}.pfx" -f [guid]::NewGuid())
        $cleanBase64 = $certificateBase64 -replace "\s", ""
        [System.IO.File]::WriteAllBytes($temporaryPfx, [Convert]::FromBase64String($cleanBase64))
        $certificatePath = $temporaryPfx
    } else {
        $certificatePath = (Resolve-Path -LiteralPath $certificatePath).Path
    }

    $signTool = Find-SignTool
    & $signTool sign /fd SHA256 /td SHA256 /tr $timestampUrl /f $certificatePath /p $certificatePassword $artifactPath | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "Authenticode signing failed for $artifactPath (signtool exit code $LASTEXITCODE)."
    }
    & $signTool verify /pa /all /v $artifactPath | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "Authenticode verification failed for $artifactPath (signtool exit code $LASTEXITCODE)."
    }
} finally {
    if ($temporaryPfx -and (Test-Path -LiteralPath $temporaryPfx)) {
        Remove-Item -LiteralPath $temporaryPfx -Force
    }
}
