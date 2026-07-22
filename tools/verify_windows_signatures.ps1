[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Directory,
    [Parameter(Mandatory = $true)]
    [string]$ExpectedNames,
    [string]$AdditionalPaths = "",
    [Parameter(Mandatory = $true)]
    [string]$ReceiptPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = (Resolve-Path -LiteralPath $Directory).Path
$names = @($ExpectedNames -split "\|" | Where-Object { $_ })
if (-not $names.Count) {
    throw "At least one expected Windows artifact name is required."
}

$artifacts = foreach ($name in $names) {
    [ordered]@{ Name = $name; Path = (Join-Path $root $name) }
}
foreach ($additionalPath in @($AdditionalPaths -split "\|" | Where-Object { $_ })) {
    $resolvedPath = if ([System.IO.Path]::IsPathRooted($additionalPath)) {
        $additionalPath
    } else {
        Join-Path $root $additionalPath
    }
    $artifacts += [ordered]@{
        Name = "portable/$([System.IO.Path]::GetFileName($resolvedPath))"
        Path = $resolvedPath
    }
}

$receipt = foreach ($artifact in $artifacts) {
    $name = [string]$artifact.Name
    $path = [string]$artifact.Path
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Expected signed artifact is missing: $path"
    }
    $signature = Get-AuthenticodeSignature -LiteralPath $path
    if ($signature.Status -ne [System.Management.Automation.SignatureStatus]::Valid) {
        throw "Authenticode signature is not valid for $name (status: $($signature.Status); $($signature.StatusMessage))."
    }
    if (-not $signature.SignerCertificate) {
        throw "Authenticode signer certificate is missing for $name."
    }
    if (-not $signature.TimeStamperCertificate) {
        throw "RFC 3161 timestamp certificate is missing for $name."
    }
    [ordered]@{
        name = $name
        sha256 = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
        signer_subject = $signature.SignerCertificate.Subject
        signer_thumbprint = $signature.SignerCertificate.Thumbprint
        certificate_not_after = $signature.SignerCertificate.NotAfter.ToUniversalTime().ToString("o")
        timestamp_subject = $signature.TimeStamperCertificate.Subject
        timestamp_thumbprint = $signature.TimeStamperCertificate.Thumbprint
        timestamp_certificate_not_after = $signature.TimeStamperCertificate.NotAfter.ToUniversalTime().ToString("o")
        status = $signature.Status.ToString()
    }
}

$receiptDirectory = Split-Path -Parent $ReceiptPath
if ($receiptDirectory) {
    New-Item -ItemType Directory -Path $receiptDirectory -Force | Out-Null
}
$receipt | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $ReceiptPath -Encoding UTF8
Write-Host "Verified $($receipt.Count) Authenticode-signed Windows release artifacts."
