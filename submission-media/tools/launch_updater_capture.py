"""Launch and capture the real Format Foundry optional-tools center."""

from __future__ import annotations

import argparse
import sys
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

from PIL import ImageGrab

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from suite_updater import UpdaterApp  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--geometry", default="1500x900+0+0", help="Tk window geometry")
    parser.add_argument("--screenshot", type=Path, required=True, help="Destination PNG")
    parser.add_argument("--delay-ms", type=int, default=7000, help="Wait for backend detection before capture")
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
    with patch.object(UpdaterApp, "_save_settings", autospec=True, return_value=None):
        root = tk.Tk()
        UpdaterApp(root, open_backends=True)
        root.geometry(args.geometry)
        root.update_idletasks()
        root.deiconify()
        root.lift()
        root.focus_force()
        root.attributes("-topmost", True)
        root.after(max(250, args.delay_ms), lambda: capture_client_area(root, args.screenshot.resolve()))
        root.mainloop()


if __name__ == "__main__":
    main()
