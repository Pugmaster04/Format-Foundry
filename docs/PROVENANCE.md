# Format Foundry Provenance

Format Foundry is proprietary software. The canonical source is
`https://github.com/Pugmaster04/Format-Foundry`, and the copyright holder is Pugmaster04.

## Project identity

Official source and binaries carry this stable project identity:

- Project ID: `io.github.pugmaster04.format-foundry`
- Provenance ID: `ffp1-af300b981ec8a9a505ca56a575193ed8a896f1f4b924019d2e8219290f598bee`
- Schema: `format-foundry/provenance/v1`

The identity is present in both the Python module and a bundled JSON record. It contains no
device identifier, telemetry, user data, or secret key. Run either official executable with
`--provenance` to inspect it.

## Release verification

Tagged releases contain:

- `PROVENANCE.json`, which binds the release version and source commit to every artifact hash
- `SHA256SUMS`, for ordinary checksum verification
- `FormatFoundry_<version>_github-attestation.json`, a GitHub-signed Sigstore bundle
- Authenticode signatures on public Windows executables

Verify any downloaded artifact against the official repository with GitHub CLI:

```text
gh attestation verify <artifact-path> -R Pugmaster04/Format-Foundry
```

On Windows, also inspect the Authenticode publisher:

```powershell
Get-AuthenticodeSignature .\FormatFoundry_Setup_<version>.exe | Format-List
```

## Scope and limitations

Encryption cannot prevent someone who can read source code from copying it, and a secret placed
inside a distributed program is no longer secret. This project therefore uses copyright, Git
history, stable embedded identity, exact hashes, platform signing, and public build attestations.
Together these provide durable authorship and release-origin evidence without hostile DRM or
hidden behavior.
