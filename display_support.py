"""Monitor bounds for X11/XWayland, with a bounded no-tool fallback."""
import re
import subprocess


def linux_display_bounds(screen_width, screen_height, pointer):
    fallback = (0, 0, min(screen_width, 1600), min(screen_height, 1000))
    try:
        result = subprocess.run(
            ["xrandr", "--listmonitors"], capture_output=True, text=True,
            timeout=1, check=False,
        )
        if result.returncode:
            return fallback
        monitors = []
        for width, height, x, y in re.findall(
            r"\b(\d+)/\d+x(\d+)/\d+([+-]\d+)([+-]\d+)", result.stdout
        ):
            bounds = (int(x), int(y), int(width), int(height))
            if bounds[2] > 0 and bounds[3] > 0:
                monitors.append(bounds)
        for x, y, width, height in monitors:
            if x <= pointer[0] < x + width and y <= pointer[1] < y + height:
                return x, y, width, height
        return monitors[0] if monitors else fallback
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return fallback
