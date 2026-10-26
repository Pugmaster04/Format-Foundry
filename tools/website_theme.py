"""Strict, dependency-free website appearance settings and CSS generation."""

from __future__ import annotations

import json
import re
from typing import Any

DEFAULT_THEME: dict[str, Any] = {
    "schemaVersion": 1, "background": "#07131a", "panel": "#0b1b23", "text": "#eff5f2",
    "muted": "#a7b9b2", "accent": "#1fa58e", "highlight": "#f6efe6", "border": "#add8e6",
    "bodyFont": "plex", "headingFont": "grotesk", "textSize": 16, "contentWidth": 1180,
    "sectionSpacing": 48, "cornerRadius": 32, "buttonShape": "pill", "showGrid": True, "backgroundGlow": True,
}
COLOR_KEYS = ("background", "panel", "text", "muted", "accent", "highlight", "border")
BOUNDS = {"textSize": (14, 20), "contentWidth": (960, 1600), "sectionSpacing": (24, 104), "cornerRadius": (0, 48)}
BODY_FONTS = {"plex": '"IBM Plex Sans", "Segoe UI", sans-serif', "system": '"Segoe UI", system-ui, sans-serif'}
HEADING_FONTS = {
    "grotesk": '"Space Grotesk", "IBM Plex Sans", sans-serif',
    "system": '"Segoe UI", system-ui, sans-serif', "serif": 'Georgia, "Times New Roman", serif',
}
BUTTON_RADII = {"pill": 999, "soft": 12, "square": 3}


def validate_theme(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != set(DEFAULT_THEME):
        raise ValueError("Appearance settings must contain exactly the supported theme fields.")
    if type(value["schemaVersion"]) is not int or value["schemaVersion"] != 1:
        raise ValueError("This appearance file has an unsupported version.")
    result = {key: value[key] for key in DEFAULT_THEME}
    for key in COLOR_KEYS:
        if not isinstance(value[key], str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value[key]):
            raise ValueError(f"{key} must be a six-digit hex color, such as #1fa58e.")
        result[key] = value[key].lower()
    for key, (low, high) in BOUNDS.items():
        if type(value[key]) is not int or not low <= value[key] <= high:
            raise ValueError(f"{key} must be a whole number from {low} to {high}.")
    for key, options in (("bodyFont", BODY_FONTS), ("headingFont", HEADING_FONTS), ("buttonShape", BUTTON_RADII)):
        if not isinstance(value[key], str) or value[key] not in options:
            raise ValueError(f"Choose a supported {key}.")
    for key in ("showGrid", "backgroundGlow"):
        if type(value[key]) is not bool:
            raise ValueError(f"{key} must be true or false.")
    return result


def _rgb(color: str) -> tuple[int, ...]:
    return tuple(int(color[index:index + 2], 16) for index in (1, 3, 5))


def _shift(color: str, offsets: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{max(0, min(255, channel + offset)):02x}" for channel, offset in zip(_rgb(color), offsets, strict=True))


def _channels(color: str) -> str:
    return ", ".join(map(str, _rgb(color)))


def _luminance(color: str) -> float:
    values = [channel / 255 for channel in _rgb(color)]
    values = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in values]
    return sum(channel * weight for channel, weight in zip(values, (0.2126, 0.7152, 0.0722), strict=True))


def contrast(first: str, second: str) -> float:
    light, dark = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def _readable(color: str, background: str) -> str:
    if contrast(color, background) >= 4.5:
        return color
    target = max(("#000000", "#ffffff"), key=lambda candidate: contrast(candidate, background))
    for step in range(1, 21):
        blended = "#" + "".join(
            f"{(channel * (20 - step) + end * step + 10) // 20:02x}"
            for channel, end in zip(_rgb(color), _rgb(target), strict=True)
        )
        if contrast(blended, background) >= 4.5:
            return blended
    return target


def render_theme_css(value: Any) -> str:
    theme = validate_theme(value)
    accent_strong = _shift(theme["accent"], (19, 31, 28))
    accent_pale = _shift(theme["accent"], (188, 90, 106))
    palette = (theme["highlight"], accent_strong, accent_pale)
    ink = max(("#072019", "#ffffff"), key=lambda candidate: min(contrast(candidate, color) for color in palette))
    badge_ink = "#05211c" if ink == "#072019" else ink
    panel = theme["panel"]
    values = {
        "bg": theme["background"], "bg-alt": panel,
        "surface": f"rgba({_channels(panel)}, 0.7)",
        "surface-strong": f"rgba({_channels(_shift(panel, (2, 4, 5)))}, 0.92)",
        "line": f"rgba({_channels(theme['border'])}, 0.12)",
        "line-strong": f"rgba({_channels(theme['border'])}, 0.2)",
        "text": theme["text"], "muted": theme["muted"], "accent": theme["accent"],
        "accent-strong": accent_strong, "sand": theme["highlight"],
        "accent-text": _readable(accent_strong, theme["background"]),
        "highlight-text": _readable(theme["highlight"], theme["background"]),
        "accent-rgb": _channels(theme["accent"]), "accent-strong-rgb": _channels(accent_strong),
        "sand-rgb": _channels(theme["highlight"]), "sand-glow-rgb": _channels(_shift(theme["highlight"], (-13, -25, -42))),
        "bg-rgb": _channels(theme["background"]), "stage-rgb": _channels(_shift(panel, (-1, 1, 3))),
        "card-start-rgb": _channels(_shift(panel, (-2, -4, -5))), "card-end-rgb": _channels(_shift(panel, (-2, -5, -7))),
        "bg-mid": _shift(theme["background"], (1, 4, 5)), "bg-end": _shift(theme["background"], (5, 6, 7)),
        "frame-bg": _shift(theme["background"], (-3, -2, -3)), "accent-pale": accent_pale,
        "button-ink": ink, "badge-ink": badge_ink,
        "sparkle-rgb": "0, 0, 0" if _luminance(theme["background"]) > 0.5 else "255, 255, 255",
        "font-body": BODY_FONTS[theme["bodyFont"]], "font-heading": HEADING_FONTS[theme["headingFont"]],
        "base-text-size": f"{theme['textSize']}px", "content-width": f"{theme['contentWidth']}px",
        "section-space": f"{theme['sectionSpacing']}px", "radius-xl": f"{theme['cornerRadius']}px",
        "radius-lg": f"{max(0, theme['cornerRadius'] - 10)}px", "button-radius": f"{BUTTON_RADII[theme['buttonShape']]}px",
        "grid-opacity": "0.55" if theme["showGrid"] else "0", "background-glow": "1" if theme["backgroundGlow"] else "0",
    }
    return "/* Generated by the Format Foundry appearance editor. */\n:root {\n" + "".join(
        f"  --{key}: {item};\n" for key, item in values.items()
    ) + "}\n"


def theme_json(value: Any) -> str:
    return json.dumps(validate_theme(value), indent=2, allow_nan=False) + "\n"
