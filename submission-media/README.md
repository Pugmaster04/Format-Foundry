# Format Foundry Devpost Media Kit

This directory contains authentic Format Foundry captures and upload-ready promotional art for
the OpenAI Build Week Devpost submission. The promotional slides use real application screenshots;
they do not depict unimplemented interfaces.

For a single-file handoff, use `Format-Foundry-Devpost-Media-Kit.zip` and verify it against
`Format-Foundry-Devpost-Media-Kit.zip.sha256`.

## Recommended upload order

1. `exports/devpost-cover-1200x800.png` - gallery cover and thumbnail
2. `exports/gallery-01-one-workspace-1600x900.png` - core workflow
3. `exports/gallery-02-backend-center-1600x900.png` - backend detection and setup
4. `exports/gallery-03-aria2-downloads-1600x900.png` - downloads and safety guidance
5. `exports/gallery-04-cross-platform-release-1600x900.png` - Windows and Linux delivery
6. `exports/gallery-05-idea-bank-1600x900.png` - optional, local-only Idea Bank add-on
7. `exports/gallery-06-pc-health-1600x900.png` - optional, read-only PC Health Snapshot add-on

Use `exports/youtube-thumbnail-1920x1080.png` for the public demo video. The cover is 3:2, and
all upload-ready images are PNG files below Devpost's 5 MB image limit as checked on 2026-07-18.

Captions and source-image relationships are recorded in `media-catalog.json`. Exact dimensions,
byte sizes, SHA-256 hashes, ownership identity, and provenance metadata are in
`MEDIA_MANIFEST.json`.

## Demo requirement

The current Build Week submission instructions require a public YouTube demo under three minutes
with narration or audio that explains both Codex and GPT-5.6 usage. Follow `VIDEO_STORYBOARD.md`.
Only describe work that actually happened; perform and capture a genuine GPT-5.6 pass before
submission if one is not already documented.

## Rebuild

The five source captures in `screenshots/` were taken from the current Windows app. To launch a
repeatable capture view without changing normal user settings:

```powershell
python submission-media/tools/launch_capture_view.py --tab Convert --screenshot submission-media/screenshots/format-foundry-main-windows.png
python submission-media/tools/launch_capture_view.py --tab Downloads --screenshot submission-media/screenshots/format-foundry-aria2-windows.png
python submission-media/tools/launch_capture_view.py --tab "Idea Bank" --screenshot submission-media/screenshots/format-foundry-idea-bank-windows.png
python tools/ui_layout_probe.py --output-dir build/ui-layout-probe-windows
python submission-media/tools/launch_updater_capture.py --screenshot submission-media/screenshots/format-foundry-backend-center-windows.png
```

The PC Health source capture is copied from
`build/ui-layout-probe-windows/pc-health-1280x720-scale100.png` after the responsive probe passes.

After updating the source captures, regenerate every promotional image and provenance manifest:

```powershell
powershell -ExecutionPolicy Bypass -File submission-media/render_media.ps1
```

The visible copyright line and PNG metadata are attribution evidence, not telemetry or DRM.
