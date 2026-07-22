from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
VIEWPORTS = (
    (1024, 768, 100),
    (1280, 720, 100),
    (1366, 768, 100),
    (1920, 1080, 100),
    (1280, 720, 150),
)
SURFACE_CASES = (
    (1024, 768, 100, "pc-health"),
    (1280, 720, 100, "pc-health"),
    (1280, 720, 150, "pc-health"),
)


def widget_bounds(widget: Any) -> tuple[int, int, int, int]:
    return (
        int(widget.winfo_rootx()),
        int(widget.winfo_rooty()),
        int(widget.winfo_width()),
        int(widget.winfo_height()),
    )


def descendants(widget: Any) -> list[Any]:
    found: list[Any] = []
    for child in widget.winfo_children():
        found.append(child)
        found.extend(descendants(child))
    return found


def child_probe(width: int, height: int, scale: int, surface: str, output: Path, result_path: Path) -> int:
    import tkinter as tk

    from PIL import ImageGrab

    from modular_file_utility_suite import SuiteApp
    from settings_support import save_settings_document

    settings_root = Path(os.environ["FORMAT_FOUNDRY_UI_PROBE_SETTINGS"])
    appdata = settings_root / "FormatFoundry"
    appdata.mkdir(parents=True, exist_ok=True)
    save_settings_document(
        appdata / "settings.json",
        {
            "first_run_done": True,
            "dark_mode": False,
            "high_contrast_mode": False,
            "fullscreen": False,
            "borderless_maximized": False,
            "show_overview_panel": False,
            "idea_bank_addon_enabled": False,
            "pc_health_addon_enabled": surface == "pc-health",
            "reduce_motion": True,
            "compact_density": False,
            "ui_scale_percent": scale,
            "use_hover_tooltips": False,
            "output_folder": str(settings_root / "output"),
            "check_updates_on_startup": False,
            "prompt_backend_install_on_startup": False,
            "show_startup_animation": False,
            "startup_animation_seconds": 1.0,
            "log_max_lines": 4000,
        },
    )

    root = tk.Tk()
    failures: list[str] = []
    try:
        app = SuiteApp(root)
        app.select_tab("PC Health" if surface == "pc-health" else "Convert")
        root.geometry(f"{width}x{height}+0+0")
        root.deiconify()
        root.lift()
        try:
            root.attributes("-topmost", True)
        except tk.TclError:
            pass
        root.update_idletasks()
        root.update()
        if surface == "pc-health" and app.pc_health_tab is not None:
            deadline = time.monotonic() + 12.0
            while bool(getattr(app.pc_health_tab, "_refreshing", False)) and time.monotonic() < deadline:
                root.update()
                time.sleep(0.05)
        time.sleep(0.2)
        root.update()
        actual_width = int(root.winfo_width())
        actual_height = int(root.winfo_height())
        if actual_width > width + 8 or actual_height > height + 8:
            failures.append(f"window expanded beyond requested viewport: {actual_width}x{actual_height}")
        root_x, root_y, _, _ = widget_bounds(root)
        critical_widgets = [app.top_notebook]
        for widget in descendants(root):
            try:
                style_name = str(widget.cget("style"))
            except tk.TclError:
                continue
            if style_name == "StatusBar.TFrame":
                critical_widgets.append(widget)
        for widget in [item for item in critical_widgets if item is not None]:
            x, y, widget_width, widget_height = widget_bounds(widget)
            if widget_width <= 1 or widget_height <= 1:
                failures.append(f"critical widget is not visible: {widget}")
                continue
            if x < root_x - 2 or y < root_y - 2 or x + widget_width > root_x + actual_width + 2 or y + widget_height > root_y + actual_height + 2:
                failures.append(f"critical widget is clipped outside the root: {widget}")

        if surface == "pc-health" and app.pc_health_tab is not None:
            canvas = getattr(app.pc_health_tab, "_scroll_canvas", None)
            reachability_widgets = [
                getattr(app.pc_health_tab, "notice_label", None),
                getattr(app.pc_health_tab, "status_label", None),
            ]
            if canvas is None or any(widget is None for widget in reachability_widgets):
                failures.append("PC Health did not expose its scrollable disclaimer and status surface")
            else:
                canvas.yview_moveto(1.0)
                root.update_idletasks()
                root.update()
                canvas_x, canvas_y, canvas_width, canvas_height = widget_bounds(canvas)
                for widget in reachability_widgets:
                    widget_x, widget_y, widget_width, widget_height = widget_bounds(widget)
                    if (
                        widget_x < canvas_x - 2
                        or widget_y < canvas_y - 2
                        or widget_x + widget_width > canvas_x + canvas_width + 2
                        or widget_y + widget_height > canvas_y + canvas_height + 2
                    ):
                        failures.append(f"PC Health footer is not reachable at maximum scroll: {widget}")
                canvas.yview_moveto(0.0)
                root.update_idletasks()
                root.update()

        output.parent.mkdir(parents=True, exist_ok=True)
        image = ImageGrab.grab(
            bbox=(root.winfo_rootx(), root.winfo_rooty(), root.winfo_rootx() + actual_width, root.winfo_rooty() + actual_height),
            all_screens=True,
        )
        image.save(output, format="PNG")
        try:
            root.attributes("-topmost", False)
        except tk.TclError:
            pass
        payload = {
            "requested": {"width": width, "height": height, "scale_percent": scale},
            "surface": surface,
            "actual": {"width": actual_width, "height": actual_height},
            "screenshot": output.name,
            "failures": failures,
        }
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 0 if not failures else 1
    finally:
        root.destroy()


def parent_probe(output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="format-foundry-ui-probe-") as temporary_directory:
        temp_root = Path(temporary_directory)
        cases = tuple((*viewport, "convert") for viewport in VIEWPORTS) + SURFACE_CASES
        for width, height, scale, surface in cases:
            case_name = f"{surface}-{width}x{height}-scale{scale}"
            screenshot = output_dir / f"{case_name}.png"
            result_path = temp_root / f"{case_name}.json"
            settings_path = temp_root / case_name / "settings"
            environment = dict(os.environ)
            environment["FORMAT_FOUNDRY_UI_PROBE_SETTINGS"] = str(settings_path)
            environment["LOCALAPPDATA"] = str(settings_path)
            environment["XDG_CONFIG_HOME"] = str(settings_path)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--child",
                    "--width",
                    str(width),
                    "--height",
                    str(height),
                    "--scale",
                    str(scale),
                    "--surface",
                    surface,
                    "--output",
                    str(screenshot),
                    "--result",
                    str(result_path),
                ],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=90,
                check=False,
            )
            if result_path.is_file():
                result = json.loads(result_path.read_text(encoding="utf-8"))
                results.append(result)
                failures.extend(f"{case_name}: {issue}" for issue in result.get("failures", []))
            else:
                failures.append(f"{case_name}: probe did not produce a result ({completed.stderr.strip()})")
            if completed.returncode != 0 and not result_path.is_file():
                failures.append(f"{case_name}: child exited with {completed.returncode}")

    manifest = {"schema_version": 1, "passed": not failures, "viewports": results, "failures": failures}
    (output_dir / "layout-probe.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if not failures else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture and validate the supported Format Foundry viewport matrix.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "build" / "ui-layout-probe")
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--scale", type=int, default=100)
    parser.add_argument("--surface", choices=("convert", "pc-health"), default="convert")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    if args.child:
        if args.output is None or args.result is None:
            parser.error("--output and --result are required in child mode")
        return child_probe(args.width, args.height, args.scale, args.surface, args.output, args.result)
    return parent_probe(args.output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
