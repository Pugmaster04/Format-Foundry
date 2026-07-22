"""Small accessibility primitives shared by UI and verification code."""

from __future__ import annotations


def _channel_luminance(value: int) -> float:
    channel = max(0, min(255, int(value))) / 255.0
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    value = hex_color.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(character * 2 for character in value)
    if len(value) != 6:
        raise ValueError(f"Expected a 3- or 6-digit hex color, received {hex_color!r}")
    try:
        red, green, blue = (int(value[index : index + 2], 16) for index in (0, 2, 4))
    except ValueError as exc:
        raise ValueError(f"Invalid hex color: {hex_color!r}") from exc
    return 0.2126 * _channel_luminance(red) + 0.7152 * _channel_luminance(green) + 0.0722 * _channel_luminance(blue)


def contrast_ratio(first: str, second: str) -> float:
    lighter, darker = sorted((relative_luminance(first), relative_luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def meets_wcag_aa(foreground: str, background: str, *, large_text: bool = False) -> bool:
    threshold = 3.0 if large_text else 4.5
    return contrast_ratio(foreground, background) >= threshold
