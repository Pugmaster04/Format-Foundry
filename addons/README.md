# Optional Add-ons

Add-ons extend Format Foundry without becoming dependencies of the conversion engine.

## Idea Bank

Idea Bank is bundled with official builds but disabled by default. Enable it from `View -> Idea Bank
add-on` or `Settings -> Add-ons`. Its data is stored separately under the Format Foundry settings
directory in `addons/idea-bank/ideas.json`.

The add-on never runs conversion commands, installs backends, contacts a network service, or reads
the source-code directory. Disabling it removes the workspace tab without deleting saved ideas.

## PC Health Snapshot

PC Health Snapshot is a second built-in add-on, adapted from the read-only PC Health Knowledge
Operator concept. It is bundled but disabled by default. Enable it from `Settings -> Enable PC
Health Snapshot Add-on` or `Settings -> Add-ons`.

The add-on reads only a bounded local system summary: operating-system identity, memory, free space
on the home drive, and Microsoft Defender status on Windows. It never changes files, security
settings, or system configuration, does not contact a network service, and is not antivirus
software. On Linux it leaves provider-specific security status to the distribution's security
center. Deeper folder inspection is routed to Format Foundry's existing Storage Analyzer.
