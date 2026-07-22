[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("AzureArtifactSigning", "Pfx")]
    [string]$Mode,
    [string]$Repository = "Pugmaster04/Format-Foundry",
    [string]$EnvironmentName = "windows-release-signing",
    [string]$AzureClientId = "",
    [string]$AzureTenantId = "",
    [string]$AzureSubscriptionId = "",
    [string]$ArtifactSigningEndpoint = "",
    [string]$ArtifactSigningAccountName = "",
    [string]$CertificateProfileName = "",
    [string]$PfxPath = "",
    [Security.SecureString]$PfxPassword,
    [string]$TimestampUrl = "http://timestamp.digicert.com"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Require-Value {
    param([string]$Name, [string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) {
        throw "$Name is required for $Mode configuration."
    }
}

function Invoke-Gh {
    param([string[]]$Arguments, [string]$FailureMessage)
    & $script:GhPath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$FailureMessage (gh exit code $LASTEXITCODE)."
    }
}

function Set-EnvironmentSecret {
    param([string]$Name, [string]$Value)

    # Redirect stdin directly so passwords are neither placed on the command line nor altered with a trailing newline.
    $startInfo = [Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $script:GhPath
    $startInfo.Arguments = "secret set $Name --repo $Repository --env $EnvironmentName"
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardInput = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    try {
        if (-not $process.Start()) {
            throw "Unable to start GitHub CLI."
        }
        $process.StandardInput.Write($Value)
        $process.StandardInput.Close()
        $stdout = $process.StandardOutput.ReadToEnd()
        $stderr = $process.StandardError.ReadToEnd()
        $process.WaitForExit()
        if ($process.ExitCode -ne 0) {
            throw "Unable to store the $Name environment secret. $stderr"
        }
        if (-not [string]::IsNullOrWhiteSpace($stdout)) {
            Write-Host ($stdout.Trim())
        }
    } finally {
        $process.Dispose()
    }
}

function Set-EnvironmentVariable {
    param([string]$Name, [string]$Value)
    Invoke-Gh -Arguments @(
        "variable", "set", $Name,
        "--body", $Value,
        "--repo", $Repository,
        "--env", $EnvironmentName
    ) -FailureMessage "Unable to store the $Name environment variable"
}

$gh = Get-Command "gh" -ErrorAction Stop
$script:GhPath = $gh.Source
if ($Repository -notmatch "^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$") {
    throw "Repository must use the owner/name format."
}
if ($EnvironmentName -notmatch "^[A-Za-z0-9_.-]+$") {
    throw "EnvironmentName contains unsupported characters."
}
Invoke-Gh -Arguments @("auth", "status") -FailureMessage "GitHub CLI authentication is required"
$environmentPayload = '{"deployment_branch_policy":{"protected_branches":false,"custom_branch_policies":true}}'
$environmentPayload | & $script:GhPath api --method PUT "repos/$Repository/environments/$EnvironmentName" --input - --silent
if ($LASTEXITCODE -ne 0) {
    throw "Unable to create or update the GitHub signing environment."
}
$policiesJson = & $script:GhPath api "repos/$Repository/environments/$EnvironmentName/deployment-branch-policies"
if ($LASTEXITCODE -ne 0) {
    throw "Unable to inspect the GitHub signing environment's deployment policy."
}
$policies = $policiesJson | ConvertFrom-Json
$hasReleaseTagPolicy = @(
    $policies.branch_policies | Where-Object { $_.name -eq "v*" -and $_.type -eq "tag" }
).Count -gt 0
if (-not $hasReleaseTagPolicy) {
    '{"name":"v*","type":"tag"}' |
        & $script:GhPath api --method POST "repos/$Repository/environments/$EnvironmentName/deployment-branch-policies" --input - --silent
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to restrict the GitHub signing environment to release tags."
    }
}

if ($Mode -eq "AzureArtifactSigning") {
    Require-Value -Name "AzureClientId" -Value $AzureClientId
    Require-Value -Name "AzureTenantId" -Value $AzureTenantId
    Require-Value -Name "AzureSubscriptionId" -Value $AzureSubscriptionId
    Require-Value -Name "ArtifactSigningEndpoint" -Value $ArtifactSigningEndpoint
    Require-Value -Name "ArtifactSigningAccountName" -Value $ArtifactSigningAccountName
    Require-Value -Name "CertificateProfileName" -Value $CertificateProfileName

    $endpoint = $null
    if (-not [Uri]::TryCreate($ArtifactSigningEndpoint, [UriKind]::Absolute, [ref]$endpoint) -or
        $endpoint.Scheme -ne "https" -or
        -not $endpoint.Host.EndsWith(".codesigning.azure.net", [StringComparison]::OrdinalIgnoreCase)) {
        throw "ArtifactSigningEndpoint must be the HTTPS endpoint issued by Azure Artifact Signing."
    }

    Set-EnvironmentSecret -Name "AZURE_CLIENT_ID" -Value $AzureClientId
    Set-EnvironmentSecret -Name "AZURE_TENANT_ID" -Value $AzureTenantId
    Set-EnvironmentSecret -Name "AZURE_SUBSCRIPTION_ID" -Value $AzureSubscriptionId
    Set-EnvironmentVariable -Name "AZURE_ARTIFACT_SIGNING_ENDPOINT" -Value $endpoint.AbsoluteUri
    Set-EnvironmentVariable -Name "AZURE_ARTIFACT_SIGNING_ACCOUNT_NAME" -Value $ArtifactSigningAccountName
    Set-EnvironmentVariable -Name "AZURE_ARTIFACT_SIGNING_CERTIFICATE_PROFILE_NAME" -Value $CertificateProfileName
    Set-EnvironmentVariable -Name "WINDOWS_SIGNING_PROVIDER" -Value "azure-artifact-signing"

    Write-Host "Configured Azure Artifact Signing metadata for $Repository ($EnvironmentName)."
    Write-Host "The Azure service principal must also have the Artifact Signing Certificate Profile Signer role."
    Write-Host "Its federated credential subject must be: repo:$Repository`:environment:$EnvironmentName"
    exit 0
}

Require-Value -Name "PfxPath" -Value $PfxPath
$resolvedPfx = (Resolve-Path -LiteralPath $PfxPath).Path
if (-not $PfxPassword) {
    $PfxPassword = Read-Host "PFX password" -AsSecureString
}
$plainPassword = [Net.NetworkCredential]::new("", $PfxPassword).Password
$certificate = $null
try {
    $certificate = [Security.Cryptography.X509Certificates.X509Certificate2]::new(
        $resolvedPfx,
        $plainPassword,
        [Security.Cryptography.X509Certificates.X509KeyStorageFlags]::EphemeralKeySet
    )
    if (-not $certificate.HasPrivateKey) {
        throw "The PFX does not contain a private key."
    }
    if ($certificate.NotAfter.ToUniversalTime() -le [DateTime]::UtcNow.AddDays(30)) {
        throw "The PFX certificate is expired or expires within 30 days."
    }
    $codeSigningOid = "1.3.6.1.5.5.7.3.3"
    $ekuExtension = $certificate.Extensions |
        Where-Object { $_ -is [Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension] } |
        Select-Object -First 1
    $hasCodeSigningEku = $ekuExtension -and @($ekuExtension.EnhancedKeyUsages | Where-Object { $_.Value -eq $codeSigningOid }).Count -gt 0
    if (-not $hasCodeSigningEku) {
        throw "The PFX certificate does not include the Code Signing enhanced key usage."
    }

    $certificateBase64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($resolvedPfx))
    Set-EnvironmentSecret -Name "WINDOWS_SIGNING_CERTIFICATE_BASE64" -Value $certificateBase64
    Set-EnvironmentSecret -Name "WINDOWS_SIGNING_CERTIFICATE_PASSWORD" -Value $plainPassword
    Set-EnvironmentVariable -Name "WINDOWS_SIGNING_TIMESTAMP_URL" -Value $TimestampUrl
    Set-EnvironmentVariable -Name "WINDOWS_SIGNING_PROVIDER" -Value "pfx"

    Write-Host "Configured PFX signing for $Repository ($EnvironmentName)."
    Write-Host "Certificate subject: $($certificate.Subject)"
    Write-Host "Certificate expires: $($certificate.NotAfter.ToUniversalTime().ToString('u'))"
} finally {
    $plainPassword = $null
    if ($certificate) {
        $certificate.Dispose()
    }
}
