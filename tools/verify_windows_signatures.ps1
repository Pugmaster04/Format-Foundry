[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Directory,
    [Parameter(Mandatory = $true)]
    [string]$ExpectedNames,
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

$receipt = foreach ($name in $names) {
    $path = Join-Path $root $name
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
    [ordered]@{
        name = $name
        sha256 = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
        signer_subject = $signature.SignerCertificate.Subject
        signer_thumbprint = $signature.SignerCertificate.Thumbprint
        certificate_not_after = $signature.SignerCertificate.NotAfter.ToUniversalTime().ToString("o")
        status = $signature.Status.ToString()
    }
}

$receiptDirectory = Split-Path -Parent $ReceiptPath
if ($receiptDirectory) {
    New-Item -ItemType Directory -Path $receiptDirectory -Force | Out-Null
}
$receipt | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $ReceiptPath -Encoding UTF8
Write-Host "Verified $($receipt.Count) Authenticode-signed Windows release artifacts."
