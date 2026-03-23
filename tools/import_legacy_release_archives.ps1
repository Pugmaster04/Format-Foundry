param(
    [string]$RepoRoot = "",
    [string]$LegacyArchiveRoot = "",
    [string]$ArchiveRoot = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}
$RepoRoot = (Resolve-Path $RepoRoot).Path

function Get-DefaultArchiveRoot {
    param(
        [string]$RepoRoot
    )
    $parent = Split-Path $RepoRoot -Parent
    return (Join-Path $parent "Universal Conversion Hub Archives")
}

if ([string]::IsNullOrWhiteSpace($LegacyArchiveRoot)) {
    $LegacyArchiveRoot = "C:\Users\Pugma\Downloads\New Python Script Suite\archive"
}
if (-not (Test-Path $LegacyArchiveRoot)) {
    throw "Legacy archive root not found: $LegacyArchiveRoot"
}
$LegacyArchiveRoot = (Resolve-Path $LegacyArchiveRoot).Path

if ([string]::IsNullOrWhiteSpace($ArchiveRoot)) {
    $envArchiveRoot = [Environment]::GetEnvironmentVariable("UCH_ARCHIVE_ROOT", "User")
    if ([string]::IsNullOrWhiteSpace($envArchiveRoot)) {
        $envArchiveRoot = [Environment]::GetEnvironmentVariable("UCH_ARCHIVE_ROOT", "Process")
    }
    $ArchiveRoot = if ([string]::IsNullOrWhiteSpace($envArchiveRoot)) { Get-DefaultArchiveRoot -RepoRoot $RepoRoot } else { $envArchiveRoot }
}
if (-not (Test-Path $ArchiveRoot)) {
    New-Item -ItemType Directory -Path $ArchiveRoot -Force | Out-Null
}
$ArchiveRoot = (Resolve-Path $ArchiveRoot).Path

$destinationRoot = Join-Path $ArchiveRoot "legacy_universal_file_utility_suite"
New-Item -ItemType Directory -Path $destinationRoot -Force | Out-Null

$imported = @()
Get-ChildItem -Path $LegacyArchiveRoot -Directory | Where-Object {
    $_.Name -eq "legacy_root" -or $_.Name -like "v0.4*"
} | Sort-Object Name | ForEach-Object {
    $target = Join-Path $destinationRoot $_.Name
    if (Test-Path $target) {
        Remove-Item -Path $target -Recurse -Force
    }
    Copy-Item -Path $_.FullName -Destination $target -Recurse -Force
    $imported += $_.Name
}

$meta = [ordered]@{
    imported_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssK")
    source_root = $LegacyArchiveRoot
    destination_root = $destinationRoot
    archive_root = $ArchiveRoot
    imported_entries = $imported
}

$meta | ConvertTo-Json -Depth 4 | Set-Content -Path (Join-Path $destinationRoot "import_manifest.json") -Encoding UTF8
Write-Host ("Imported legacy archives: {0}" -f ($imported -join ", "))
