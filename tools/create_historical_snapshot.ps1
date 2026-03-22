param(
    [string]$RepoRoot = "",
    [string]$Reason = "manual",
    [switch]$IncludeBuildOutputs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
$RepoRoot = (Resolve-Path $RepoRoot).Path
Set-Location $RepoRoot

function Get-AppVersion {
    $mainScript = Join-Path $RepoRoot "modular_file_utility_suite.py"
    if (-not (Test-Path $mainScript)) {
        return "unknown"
    }
    $line = Select-String -Path $mainScript -Pattern 'APP_VERSION\s*=\s*"([^"]+)"' | Select-Object -First 1
    if ($line -and $line.Matches.Count -gt 0) {
        return $line.Matches[0].Groups[1].Value
    }
    return "unknown"
}

function Copy-SafeTree {
    param(
        [string]$SourceRoot,
        [string]$DestinationRoot
    )
    $excludedNames = @(
        ".git",
        ".githooks",
        "archive",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".venv",
        "venv",
        "env",
        "build",
        "dist",
        "installer_output",
        "suite_output",
        "release_bins"
    )
    Get-ChildItem -Path $SourceRoot -Force | ForEach-Object {
        if ($excludedNames -contains $_.Name) {
            return
        }
        Copy-Item -Path $_.FullName -Destination $DestinationRoot -Recurse -Force
    }
}

function Copy-ExistingArtifacts {
    param(
        [string]$ArtifactRoot,
        [string[]]$RelativePaths
    )
    foreach ($relativePath in $RelativePaths) {
        $candidate = Join-Path $RepoRoot $relativePath
        if (Test-Path $candidate) {
            Copy-Item -Path $candidate -Destination (Join-Path $ArtifactRoot ([System.IO.Path]::GetFileName($candidate))) -Force
        }
    }
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$safeReason = ($Reason -replace '[^A-Za-z0-9._-]', "_")
$version = Get-AppVersion

$snapshotRoot = Join-Path $RepoRoot ("archive\history\v{0}\{1}_{2}" -f $version, $timestamp, $safeReason)
$sourceRoot = Join-Path $snapshotRoot "source"
New-Item -ItemType Directory -Path $sourceRoot -Force | Out-Null

Copy-SafeTree -SourceRoot $RepoRoot -DestinationRoot $sourceRoot

if ($IncludeBuildOutputs.IsPresent) {
    $artifactRoot = Join-Path $snapshotRoot "artifacts"
    New-Item -ItemType Directory -Path $artifactRoot -Force | Out-Null

    # Capture current artifact names and keep legacy fallback support for older builds.
    Copy-ExistingArtifacts -ArtifactRoot $artifactRoot -RelativePaths @(
        "dist\UniversalConversionHub_UCH.exe",
        "dist\UniversalConversionHub_HCB.exe",
        "dist\UniversalFileUtilitySuite.exe",
        "dist\UniversalConversionHub_UCH_Updater.exe",
        "dist\UniversalConversionHub_HCB_Updater.exe",
        "dist\UniversalFileUtilitySuite_Updater.exe",
        "installer_output\UniversalConversionHub_UCH_Setup.exe",
        "installer_output\UniversalConversionHub_HCB_Setup.exe",
        "installer_output\UniversalFileUtilitySuite_Setup.exe"
    )

    $stagedDir = Join-Path $RepoRoot "release_bins"
    if (Test-Path $stagedDir) {
        Copy-Item -Path $stagedDir -Destination (Join-Path $artifactRoot "release_bins") -Recurse -Force
    }
}

$snapshotMeta = [ordered]@{
    timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")
    reason = $Reason
    version = $version
    include_build_outputs = [bool]$IncludeBuildOutputs.IsPresent
    repo_root = $RepoRoot
}

$metaPath = Join-Path $snapshotRoot "snapshot.json"
$snapshotMeta | ConvertTo-Json -Depth 4 | Set-Content -Path $metaPath -Encoding UTF8

Write-Host ("Historical snapshot created: {0}" -f $snapshotRoot)

