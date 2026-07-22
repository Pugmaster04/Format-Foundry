# Windows release signing

## What a PFX is

A PFX (`.pfx` or `.p12`) is a password-protected PKCS #12 container. For code signing it normally contains:

- the publisher's code-signing certificate,
- the matching private key, and
- any intermediate certificates needed to build the trust chain.

The certificate identifies the publisher. The private key creates the signature and must never be committed, emailed, or placed in a release archive. Format Foundry ignores `*.pfx`, `*.p12`, and `*.key` files in Git.

A PFX is not automatically trustworthy. A self-signed PFX is useful only for development and internal testing; public Windows users still receive an unknown-publisher warning. Do not generate a self-signed PFX for a public Format Foundry release.

## Recommended public-release path

Use [Azure Artifact Signing](https://learn.microsoft.com/azure/artifact-signing/overview) with GitHub OpenID Connect (OIDC). This keeps the public-trust signing key in Microsoft's managed signing service instead of exporting it into a GitHub secret.

One-time external setup is required because Microsoft must validate the publisher identity:

1. Use a paid Azure subscription in a supported region.
2. Create an Artifact Signing account in the Azure portal.
3. Complete public-trust identity validation. Microsoft performs this step in the portal and it cannot be completed by repository code.
4. Create a public-trust certificate profile.
5. Create a Microsoft Entra application and service principal.
6. Add a federated credential for this GitHub environment subject:

   ```text
   repo:Pugmaster04/Format-Foundry:environment:windows-release-signing
   ```

7. Assign the service principal the **Artifact Signing Certificate Profile Signer** role on the signing account or certificate profile.
8. Configure the GitHub environment values with the repository helper:

   ```powershell
   .\tools\configure_windows_release_signing.ps1 `
     -Mode AzureArtifactSigning `
     -AzureClientId "<application-client-id>" `
     -AzureTenantId "<directory-tenant-id>" `
     -AzureSubscriptionId "<subscription-id>" `
     -ArtifactSigningEndpoint "https://<region>.codesigning.azure.net/" `
     -ArtifactSigningAccountName "<account-name>" `
     -CertificateProfileName "<profile-name>"
   ```

The helper creates the `windows-release-signing` GitHub environment, restricts it to `v*` tags, stores the Azure IDs as environment secrets, stores non-secret account metadata as environment variables, and selects `azure-artifact-signing` as the provider. It never prints credential values.

In GitHub, add deployment protection to the `windows-release-signing` environment so only trusted release maintainers and release tags can use it.

## PFX fallback

The existing PFX path remains available for a code-signing certificate whose issuing policy permits an exportable private key. Modern publicly trusted certificates commonly keep the private key in a hardware token or managed signing service, so confirm the certificate authority's current requirements before choosing this path.

Configure an existing PFX without placing it in the repository:

```powershell
.\tools\configure_windows_release_signing.ps1 `
  -Mode Pfx `
  -PfxPath "X:\secure\publisher-certificate.pfx"
```

The helper prompts for the password, verifies that the PFX contains a private key and Code Signing enhanced key usage, checks that it has more than 30 days remaining, then stores the protected values in the `windows-release-signing` GitHub environment. The PFX itself remains outside the repository.

## Release behavior

- Normal branch CI builds unsigned test artifacts and never receives signing credentials.
- Tagged release builds run in the protected `windows-release-signing` environment.
- Azure signing signs the app and updater before installer compilation, then signs the completed installer.
- The PFX fallback follows the same order locally inside `build_suite_release.bat`.
- Every tagged release verifies all three Authenticode signatures and publishes `WINDOWS_SIGNATURES_VERIFIED.json` before the release job can run.
- Missing, partial, expired, or invalid signing configuration fails closed. An unsigned tagged Windows release cannot be published.

The signing workflow uses SHA-256 file digests and RFC 3161 timestamps so signatures remain verifiable after the signing certificate expires.
