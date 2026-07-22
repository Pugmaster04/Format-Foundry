[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("Binaries", "Installer", "Stage")]
    [string]$Phase,
    [string]$RepoRoot = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = Join-Path $PSScriptRoot ".."
}
$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
$pythonCommand = Get-Command "python" -ErrorAction Stop
$python = $pythonCommand.Source

function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [Parameter(Mandatory = $true)]
        [string]$FailureMessage
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$FailureMessage (exit code $LASTEXITCODE)."
    }
}

function Get-PackageVersion {
    $extractor = Join-Path $RepoRoot "tools\extract_app_version.py"
    $output = & $python $extractor
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to determine the canonical package version from app_identity.py."
    }
    $version = [string]($output | Select-Object -Last 1)
    $version = $version.Trim()
    if ([string]::IsNullOrWhiteSpace($version)) {
        throw "The extracted package version was empty."
    }
    return $version
}

function Invoke-HistoricalSnapshot {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Reason,
        [switch]$IncludeBuildOutputs
    )

    $snapshotScript = Join-Path $RepoRoot "tools\create_historical_snapshot.ps1"
    if (-not (Test-Path -LiteralPath $snapshotScript -PathType Leaf)) {
        return
    }
    $arguments = @{
        RepoRoot = $RepoRoot
        Reason = $Reason
    }
    if ($IncludeBuildOutputs) {
        $arguments["IncludeBuildOutputs"] = $true
    }
    & $snapshotScript @arguments | Out-Null
}

function Build-Binaries {
    Write-Host "[preflight] Verifying repo integrity..."
    Invoke-NativeCommand -FilePath $python -Arguments @(
        "-m", "tools.verify_repo_integrity", $RepoRoot
    ) -FailureMessage "Repo integrity verification failed"

    $version = Get-PackageVersion
    Write-Host "[metadata] Generating Windows version resources for $version..."
    Invoke-NativeCommand -FilePath $python -Arguments @(
        (Join-Path $RepoRoot "tools\generate_windows_version_info.py")
    ) -FailureMessage "Windows version metadata generation failed"

    Write-Host "[snapshot] Creating pre-build source snapshot..."
    Invoke-HistoricalSnapshot -Reason "pre-build"

    Write-Host "[build] Building app one-file executable..."
    Invoke-NativeCommand -FilePath $python -Arguments @(
        "-m", "PyInstaller", "--noconfirm", "--clean", "FormatFoundry.spec"
    ) -FailureMessage "App build failed"

    Write-Host "[build] Building updater one-file executable..."
    Invoke-NativeCommand -FilePath $python -Arguments @(
        "-m", "PyInstaller", "--noconfirm", "--clean", "FormatFoundry_Updater.spec"
    ) -FailureMessage "Updater build failed"

    Write-Host "[build] Building optional one-folder portable app..."
    Invoke-NativeCommand -FilePath $python -Arguments @(
        "-m", "PyInstaller", "--noconfirm", "--clean", "FormatFoundry_Portable.spec"
    ) -FailureMessage "Portable app build failed"

    foreach ($name in @("FormatFoundry.exe", "FormatFoundry_Updater.exe")) {
        $path = Join-Path $RepoRoot "dist\$name"
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Expected Windows binary was not produced: $path"
        }
    }
    $portableExecutable = Join-Path $RepoRoot "dist\FormatFoundry_Portable\FormatFoundry.exe"
    if (-not (Test-Path -LiteralPath $portableExecutable -PathType Leaf)) {
        throw "Expected portable Windows binary was not produced: $portableExecutable"
    }
}

function Find-InnoSetupCompiler {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return $candidate
        }
    }
    throw "Inno Setup compiler not found. Install Inno Setup 6 and run the build again."
}

function Build-Installer {
    foreach ($name in @("FormatFoundry.exe", "FormatFoundry_Updater.exe")) {
        $path = Join-Path $RepoRoot "dist\$name"
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Installer input is missing: $path. Build and sign the binaries first."
        }
    }

    $iscc = Find-InnoSetupCompiler
    Write-Host "[build] Compiling the installer with $iscc..."
    Invoke-NativeCommand -FilePath $iscc -Arguments @(
        (Join-Path $RepoRoot "installer\FormatFoundry.iss")
    ) -FailureMessage "Installer build failed"

    $setupPath = Join-Path $RepoRoot "installer_output\FormatFoundry_Setup.exe"
    if (-not (Test-Path -LiteralPath $setupPath -PathType Leaf)) {
        throw "Expected Windows installer was not produced: $setupPath"
    }
}

function Stage-Release {
    $version = Get-PackageVersion
    $stageDirectory = Join-Path $RepoRoot "release_bins"
    New-Item -ItemType Directory -Path $stageDirectory -Force | Out-Null

    $sourceFiles = [ordered]@{
        "FormatFoundry_${version}.exe" = Join-Path $RepoRoot "dist\FormatFoundry.exe"
        "FormatFoundry_Updater_${version}.exe" = Join-Path $RepoRoot "dist\FormatFoundry_Updater.exe"
        "FormatFoundry_Setup_${version}.exe" = Join-Path $RepoRoot "installer_output\FormatFoundry_Setup.exe"
    }
    $portableDirectory = Join-Path $RepoRoot "dist\FormatFoundry_Portable"
    $portableArchiveName = "FormatFoundry_Portable_${version}_windows_x86_64.zip"
    $portableArchivePath = Join-Path $stageDirectory $portableArchiveName
    foreach ($entry in $sourceFiles.GetEnumerator()) {
        if (-not (Test-Path -LiteralPath $entry.Value -PathType Leaf)) {
            throw "Release staging input is missing: $($entry.Value)"
        }
    }

    Write-Host "[stage] Removing obsolete Windows release names..."
    $legacyNames = @(
        "UniversalConversionHub_UCH.exe",
        "UniversalConversionHub_HCB.exe",
        "UniversalFileUtilitySuite.exe",
        "UniversalConversionHub_UCH_Updater.exe",
        "UniversalConversionHub_HCB_Updater.exe",
        "UniversalFileUtilitySuite_Updater.exe"
    )
    foreach ($name in $legacyNames) {
        $legacyPath = Join-Path $RepoRoot "dist\$name"
        if (Test-Path -LiteralPath $legacyPath -PathType Leaf) {
            Remove-Item -LiteralPath $legacyPath -Force
        }
    }
    foreach ($name in @(
        "UniversalConversionHub_UCH_Setup.exe",
        "UniversalConversionHub_HCB_Setup.exe",
        "UniversalFileUtilitySuite_Setup.exe"
    )) {
        $legacyPath = Join-Path $RepoRoot "installer_output\$name"
        if (Test-Path -LiteralPath $legacyPath -PathType Leaf) {
            Remove-Item -LiteralPath $legacyPath -Force
        }
    }
    Get-ChildItem -LiteralPath $stageDirectory -Filter "*.exe" -File -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -like "FormatFoundry*.exe" -or
            $_.Name -like "UniversalConversionHub*.exe" -or
            $_.Name -like "UniversalFileUtilitySuite*.exe"
        } |
        Remove-Item -Force
    $signatureReceipt = Join-Path $stageDirectory "WINDOWS_SIGNATURES_VERIFIED.json"
    if (Test-Path -LiteralPath $signatureReceipt -PathType Leaf) {
        Remove-Item -LiteralPath $signatureReceipt -Force
    }

    Write-Host "[stage] Copying versioned Windows release assets..."
    foreach ($entry in $sourceFiles.GetEnumerator()) {
        Copy-Item -LiteralPath $entry.Value -Destination (Join-Path $stageDirectory $entry.Key) -Force
    }
    if (-not (Test-Path -LiteralPath $portableDirectory -PathType Container)) {
        throw "Portable release directory is missing: $portableDirectory"
    }
    $licensePath = Join-Path $RepoRoot "LICENSE"
    if (-not (Test-Path -LiteralPath $licensePath -PathType Leaf)) {
        throw "Release license is missing: $licensePath"
    }
    Copy-Item -LiteralPath $licensePath -Destination (Join-Path $portableDirectory "LICENSE") -Force
    if (Test-Path -LiteralPath $portableArchivePath -PathType Leaf) {
        Remove-Item -LiteralPath $portableArchivePath -Force
    }
    Compress-Archive -Path (Join-Path $portableDirectory "*") -DestinationPath $portableArchivePath -CompressionLevel Optimal

    Write-Host "[validate] Checking the public install surface..."
    $setupName = "FormatFoundry_Setup_${version}.exe"
    Invoke-NativeCommand -FilePath $python -Arguments @(
        (Join-Path $RepoRoot "tools\validate_install_surface.py"),
        "--readme", (Join-Path $RepoRoot "README.md"),
        "--artifacts", $stageDirectory, (Join-Path $RepoRoot "installer_output"), (Join-Path $RepoRoot "dist"),
        "--required-asset", $setupName
    ) -FailureMessage "Install surface validation failed"

    $checksumLines = foreach ($entry in $sourceFiles.GetEnumerator()) {
        $stagedPath = Join-Path $stageDirectory $entry.Key
        $hash = (Get-FileHash -LiteralPath $stagedPath -Algorithm SHA256).Hash.ToLowerInvariant()
        "$hash  $($entry.Key)"
    }
    $portableHash = (Get-FileHash -LiteralPath $portableArchivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    $checksumLines += "$portableHash  $portableArchiveName"
    $platformChecksumPath = Join-Path $stageDirectory "SHA256SUMS-windows"
    [System.IO.File]::WriteAllLines(
        $platformChecksumPath,
        [string[]]$checksumLines,
        [System.Text.ASCIIEncoding]::new()
    )
    Copy-Item -LiteralPath $platformChecksumPath -Destination (Join-Path $stageDirectory "SHA256SUMS") -Force

    Write-Host "[snapshot] Creating post-build source and artifact snapshot..."
    Invoke-HistoricalSnapshot -Reason "release-build" -IncludeBuildOutputs

    Write-Host "Windows release assets staged in $stageDirectory"
    foreach ($name in $sourceFiles.Keys) {
        Write-Host "  $name"
    }
    Write-Host "  $portableArchiveName"
    Write-Host "  SHA256SUMS-windows"
    Write-Host "  SHA256SUMS (local latest-build alias)"
}

Push-Location $RepoRoot
try {
    switch ($Phase) {
        "Binaries" { Build-Binaries }
        "Installer" { Build-Installer }
        "Stage" { Stage-Release }
    }
} finally {
    Pop-Location
}
