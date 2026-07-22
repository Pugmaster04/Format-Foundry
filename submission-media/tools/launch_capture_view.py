"""Launch a deterministic Format Foundry view for authentic media capture."""

from __future__ import annotations

import argparse
import sys
import tkinter as tk
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

from PIL import ImageGrab

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modular_file_utility_suite import SuiteApp  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tab", default="Convert", help="Module name to display")
    parser.add_argument("--geometry", default="1600x900+0+0", help="Tk window geometry")
    parser.add_argument("--screenshot", type=Path, help="Capture the client area to PNG, then close")
    parser.add_argument("--delay-ms", type=int, default=6000, help="Wait for background detection before capture")
    return parser.parse_args()


def capture_client_area(root: tk.Tk, destination: Path) -> None:
    root.update_idletasks()
    left = root.winfo_rootx()
    top = root.winfo_rooty()
    right = left + root.winfo_width()
    bottom = top + root.winfo_height()
    destination.parent.mkdir(parents=True, exist_ok=True)
    ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True).save(destination, format="PNG")
    root.destroy()


def main() -> None:
    args = parse_args()
    original_load_settings = SuiteApp._load_settings

    def capture_settings(app: SuiteApp) -> dict[str, Any]:
        settings = cast(dict[str, Any], original_load_settings(app))
        settings.update(
            {
                "first_run_done": True,
                "show_startup_animation": False,
                "check_updates_on_startup": False,
                "prompt_backend_install_on_startup": False,
                "fullscreen": False,
                "borderless_maximized": False,
                "show_overview_panel": False,
                "reduce_motion": True,
                "idea_bank_addon_enabled": args.tab.strip().casefold() == "idea bank",
            }
        )
        return settings

    with patch.object(SuiteApp, "_load_settings", capture_settings):
        root = tk.Tk()
        app = SuiteApp(root)
        app.select_tab(args.tab)
        root.geometry(args.geometry)
        root.update_idletasks()
        root.deiconify()
        root.lift()
        root.focus_force()
        if args.screenshot:
            root.attributes("-topmost", True)
            root.after(max(250, args.delay_ms), lambda: capture_client_area(root, args.screenshot.resolve()))
        root.mainloop()


if __name__ == "__main__":
    main()
