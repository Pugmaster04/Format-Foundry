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
    (1024, 768, 100, "settings"),
    (1280, 720, 150, "settings"),
    (1024, 768, 100, "first-run"),
    (1280, 720, 150, "first-run"),
    (1280, 720, 150, "images"),
    (1280, 720, 150, "torrents"),
    (1024, 768, 100, "code-languages"),
    (1280, 720, 150, "code-languages"),
    (1280, 720, 150, "dark"),
    (1280, 720, 150, "contrast"),
    (1024, 768, 100, "updater"),
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


def _prevent_activation(root: Any) -> None:
    if os.name != "nt":
        return
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    user32.GetParent.argtypes = [wintypes.HWND]
    user32.GetParent.restype = wintypes.HWND
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = ctypes.c_long
    user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
    user32.SetWindowLongW.restype = ctypes.c_long
    user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    user32.SetWindowPos.restype = wintypes.BOOL
    hwnd = user32.GetParent(root.winfo_id()) or root.winfo_id()
    style = user32.GetWindowLongW(hwnd, -20)
    user32.SetWindowLongW(hwnd, -20, style | 0x08000000)  # WS_EX_NOACTIVATE
    user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x37)  # Preserve bounds and z-order while applying the style.


def child_probe(
    width: int, height: int, scale: int, surface: str, output: Path, result_path: Path,
    origin_x: int = 0, origin_y: int = 0, no_activate: bool = False,
) -> int:
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
            "dark_mode": surface == "dark",
            "high_contrast_mode": surface == "contrast",
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
    root.withdraw()
    failures: list[str] = []
    try:
        app = SuiteApp(root)
        app.select_tab({"pc-health": "PC Health", "images": "Images", "torrents": "Torrents", "code-languages": "Code Languages"}.get(surface, "Convert"))
        root.geometry(f"{width}x{height}+{origin_x}+{origin_y}")
        root.update_idletasks()
        if no_activate:
            _prevent_activation(root)
        root.deiconify()
        if not no_activate:
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
            footer = getattr(widget, "module_action_footer", None)
            if footer is not None and footer.winfo_ismapped():
                critical_widgets.append(footer)
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

        if surface == "code-languages":
            language_tab: Any = app.tabs.get("Code Languages")
            if language_tab is None:
                failures.append("Code Languages tab was not available")
            else:
                canvas = language_tab.module_scroll_canvas
                for control_name in ("translate_button", "project_button"):
                    control = getattr(language_tab, control_name, None)
                    if control is None or not control.winfo_ismapped() or control.winfo_width() <= 1:
                        failures.append(f"Code Languages control is not reachable: {control_name}")
                        continue
                    for _ in range(40):
                        cx, cy, cw, ch = widget_bounds(canvas)
                        bx, by, bw, bh = widget_bounds(control)
                        if bx >= cx and by >= cy and bx + bw <= cx + cw and by + bh <= cy + ch:
                            break
                        previous = canvas.yview()
                        canvas.yview_scroll(1, "units")
                        root.update()
                        if canvas.yview() == previous:
                            failures.append(f"Code Languages action cannot be scrolled into view: {control_name}")
                            break
                    else:
                        failures.append(f"Code Languages action remained outside the viewport: {control_name}")

        captured_root: Any = root
        dialog = None

        def check_dialog(window: Any, required_text: str) -> None:
            window.geometry(f"{min(width, 800)}x{min(height, 600)}+{origin_x}+{origin_y}")
            window.update()
            buttons = []
            for child in descendants(window):
                try:
                    if child.cget("text") == required_text:
                        buttons.append(child)
                except tk.TclError:
                    pass
            if not buttons:
                failures.append(f"Missing dialog action: {required_text}")
            for child in buttons:
                x, y, w, h = widget_bounds(child)
                rx, ry, rw, rh = widget_bounds(window)
                if not child.winfo_ismapped() or x < rx or y < ry or x + w > rx + rw or y + h > ry + rh:
                    failures.append(f"Dialog action is clipped: {required_text}")

        if surface == "settings":
            app._open_settings_dialog()
            dialog = next(child for child in root.winfo_children() if isinstance(child, tk.Toplevel))
            check_dialog(dialog, "Save Settings")
            captured_root = dialog
        elif surface == "first-run":
            app.settings["first_run_done"] = False
            def inspect_wizard() -> None:
                wizard = next(child for child in root.winfo_children() if isinstance(child, tk.Toplevel))
                check_dialog(wizard, "Save and Continue")
                for child in descendants(wizard):
                    try:
                        if child.cget("text") == "Save and Continue":
                            child.invoke()
                            return
                    except tk.TclError:
                        pass
                wizard.destroy()
            root.after(200, inspect_wizard)
            app._run_first_run_setup_wizard()
            if not app.settings["first_run_done"]:
                failures.append("First-run acceptance did not save the setup choices")
        elif surface == "updater":
            from suite_updater import UpdaterApp
            dialog = tk.Toplevel(root)
            updater = UpdaterApp(dialog)
            dialog.geometry(f"{width}x{height}+0+0")
            dialog.update()
            # Exercise the real scroll range, not just the root window bounds.
            if updater._body_canvas.yview()[1] < 1:
                updater._body_canvas.yview_moveto(1)
                dialog.update()
                if updater._body_canvas.yview()[0] <= 0:
                    failures.append("Updater content did not scroll")
            captured_root = dialog

        output.parent.mkdir(parents=True, exist_ok=True)
        cx, cy, cw, ch = widget_bounds(captured_root)
        image = ImageGrab.grab(
            bbox=(cx, cy, cx + cw, cy + ch),
            all_screens=True,
        )
        image.save(output, format="PNG")
        if dialog is not None:
            dialog.destroy()
        try:
            root.attributes("-topmost", False)
        except tk.TclError:
            pass
        payload = {
            "requested": {"width": width, "height": height, "scale_percent": scale},
            "surface": surface,
            "actual": {"width": actual_width, "height": actual_height},
            "origin": {"x": root_x, "y": root_y},
            "screenshot": output.name,
            "failures": failures,
        }
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 0 if not failures else 1
    finally:
        root.destroy()


def parent_probe(
    output_dir: Path, origin_x: int = 0, origin_y: int = 0, no_activate: bool = False,
    only_surface: str | None = None,
) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="format-foundry-ui-probe-") as temporary_directory:
        temp_root = Path(temporary_directory)
        cases = tuple((*viewport, "convert") for viewport in VIEWPORTS) + SURFACE_CASES
        if only_surface:
            cases = tuple(case for case in cases if case[3] == only_surface)
            if not cases:
                raise ValueError(f"No layout cases configured for {only_surface}")
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
                    "--origin-x",
                    str(origin_x),
                    "--origin-y",
                    str(origin_y),
                    *(("--no-activate",) if no_activate else ()),
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
    parser.add_argument("--surface", choices=("convert", "pc-health", "settings", "first-run", "images", "torrents", "code-languages", "dark", "contrast", "updater"), default="convert")
    parser.add_argument("--only-surface", choices=("convert", "pc-health", "settings", "first-run", "images", "torrents", "code-languages", "dark", "contrast", "updater"))
    parser.add_argument("--origin-x", type=int, default=0)
    parser.add_argument("--origin-y", type=int, default=0)
    parser.add_argument("--no-activate", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    if args.child:
        if args.output is None or args.result is None:
            parser.error("--output and --result are required in child mode")
        return child_probe(args.width, args.height, args.scale, args.surface, args.output, args.result, args.origin_x, args.origin_y, args.no_activate)
    return parent_probe(args.output_dir, args.origin_x, args.origin_y, args.no_activate, args.only_surface)


if __name__ == "__main__":
    raise SystemExit(main())
