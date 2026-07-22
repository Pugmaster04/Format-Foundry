"""Optional, read-only PC health snapshot workspace."""

from __future__ import annotations

import ctypes
import json
import os
import platform
import re
import shutil
import subprocess
import threading
import tkinter as tk
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from tkinter import StringVar, filedialog, messagebox, ttk
from typing import Any

from support_runtime import atomic_write_text

ADDON_ID = "pc-health-snapshot"
ADDON_NAME = "PC Health Snapshot"
ADDON_VERSION = "1.0"
SECURITY_TIMEOUT_SECONDS = 8


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def format_bytes(value: int | None) -> str:
    if value is None:
        return "Unavailable"
    amount = float(max(0, value))
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if amount < 1024.0 or unit == "TiB":
            return f"{amount:.1f} {unit}"
        amount /= 1024.0
    return f"{amount:.1f} TiB"


def _format_security_timestamp(value: Any) -> str:
    raw = str(value or "").strip()
    legacy_match = re.fullmatch(r"/Date\((\d+)(?:[+-]\d+)?\)/", raw)
    if legacy_match:
        captured = datetime.fromtimestamp(int(legacy_match.group(1)) / 1000, tz=UTC)
        return captured.strftime("%Y-%m-%d %H:%M UTC")
    return raw or "unknown"


def _memory_snapshot() -> tuple[int | None, int | None]:
    if os.name == "nt":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("memory_load", ctypes.c_ulong),
                ("total_physical", ctypes.c_ulonglong),
                ("available_physical", ctypes.c_ulonglong),
                ("total_page_file", ctypes.c_ulonglong),
                ("available_page_file", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("available_virtual", ctypes.c_ulonglong),
                ("available_extended_virtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.length = ctypes.sizeof(MemoryStatus)
        windll: Any = getattr(ctypes, "windll", None)
        if windll is not None and windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.total_physical), int(status.available_physical)
        return None, None

    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        values: dict[str, int] = {}
        try:
            for line in meminfo.read_text(encoding="utf-8", errors="replace").splitlines():
                key, _, raw_value = line.partition(":")
                if raw_value:
                    values[key] = int(raw_value.strip().split()[0]) * 1024
        except (OSError, ValueError, IndexError):
            return None, None
        return values.get("MemTotal"), values.get("MemAvailable")
    return None, None


def _security_snapshot() -> tuple[str, str]:
    if os.name != "nt":
        return "Platform managed", "Use your distribution security center for provider status."
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if not powershell:
        return "Unavailable", "PowerShell was not found, so Microsoft Defender status could not be read."
    command = (
        "Get-MpComputerStatus | Select-Object AMServiceEnabled,AntivirusEnabled,"
        "RealTimeProtectionEnabled,AntivirusSignatureLastUpdated | ConvertTo-Json -Compress"
    )
    creation_flags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        completed = subprocess.run(
            [powershell, "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=SECURITY_TIMEOUT_SECONDS,
            check=False,
            creationflags=creation_flags,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "Unavailable", f"Microsoft Defender status could not be read: {type(exc).__name__}."
    if completed.returncode != 0:
        return "Unavailable", "Microsoft Defender did not return a readable status."
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return "Unavailable", "Microsoft Defender returned an unexpected response."
    enabled = bool(payload.get("AMServiceEnabled")) and bool(payload.get("AntivirusEnabled"))
    realtime = bool(payload.get("RealTimeProtectionEnabled"))
    signature = _format_security_timestamp(payload.get("AntivirusSignatureLastUpdated"))
    if enabled and realtime:
        return "Protection active", f"Microsoft Defender real-time protection is on. Signature update: {signature}."
    return "Needs attention", "Microsoft Defender antivirus or real-time protection is not reported as active."


@dataclass(frozen=True)
class PCHealthSnapshot:
    captured_at_utc: str
    operating_system: str
    release: str
    architecture: str
    memory_total_bytes: int | None
    memory_available_bytes: int | None
    home_disk_total_bytes: int | None
    home_disk_free_bytes: int | None
    security_status: str
    security_detail: str


def collect_snapshot() -> PCHealthSnapshot:
    memory_total, memory_available = _memory_snapshot()
    try:
        disk = shutil.disk_usage(Path.home())
        disk_total, disk_free = int(disk.total), int(disk.free)
    except OSError:
        disk_total, disk_free = None, None
    security_status, security_detail = _security_snapshot()
    return PCHealthSnapshot(
        captured_at_utc=_utc_now(),
        operating_system=platform.system() or "Unknown",
        release=platform.release() or "Unknown",
        architecture=platform.machine() or "Unknown",
        memory_total_bytes=memory_total,
        memory_available_bytes=memory_available,
        home_disk_total_bytes=disk_total,
        home_disk_free_bytes=disk_free,
        security_status=security_status,
        security_detail=security_detail,
    )


class PCHealthTab(ttk.Frame):
    """Read-only system snapshot adapted from the companion PC app concept."""

    def __init__(self, master: tk.Misc, app: Any):
        super().__init__(master, style="Surface.TFrame")
        self.app = app
        self.snapshot: PCHealthSnapshot | None = None
        self.status_var = StringVar(value="Collecting a local snapshot...")
        self.os_var = StringVar(value="Checking...")
        self.memory_var = StringVar(value="Checking...")
        self.disk_var = StringVar(value="Checking...")
        self.security_var = StringVar(value="Checking...")
        self.security_detail_var = StringVar(value="")
        self._refreshing = False
        self._build_ui()
        self.refresh()

    def _scaled(self, value: int) -> int:
        scaler = getattr(self.app, "_scaled", None)
        return int(scaler(value)) if callable(scaler) else value

    def _build_ui(self) -> None:
        viewport = ttk.Frame(self, style="Surface.TFrame")
        viewport.pack(fill="both", expand=True)
        canvas = tk.Canvas(viewport, highlightthickness=0, borderwidth=0, relief="flat", takefocus=0)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(viewport, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scrollbar.set)

        content = ttk.Frame(canvas, style="Surface.TFrame", padding=12)
        content_window = canvas.create_window((0, 0), window=content, anchor="nw")

        def sync_viewport(_event: tk.Event[Any] | None = None) -> None:
            try:
                canvas_width = max(1, int(canvas.winfo_width()))
                requested_height = max(int(canvas.winfo_height()), int(content.winfo_reqheight()))
                canvas.itemconfigure(content_window, width=canvas_width, height=requested_height)
                canvas.configure(scrollregion=canvas.bbox("all"))
            except (RuntimeError, tk.TclError):
                return

        canvas.bind("<Configure>", sync_viewport, add="+")
        content.bind("<Configure>", sync_viewport, add="+")
        register_wheel = getattr(self.app, "_register_mousewheel_target", None)
        if callable(register_wheel):
            def scroll(units: int) -> None:
                canvas.yview_scroll(units, "units")

            register_wheel(canvas, scroll)
            register_wheel(content, scroll)
        self._scroll_canvas = canvas
        self.after(0, sync_viewport)

        hero = ttk.Frame(content, style="ModuleHero.TFrame")
        hero.pack(fill="x", pady=(0, self._scaled(10)))
        hero_inner = ttk.Frame(hero, style="ModuleHeroBody.TFrame", padding=(14, 10))
        hero_inner.pack(fill="x")
        ttk.Label(hero_inner, text=ADDON_NAME, style="ModuleTitle.TLabel").pack(anchor="w")
        summary = ttk.Label(
            hero_inner,
            text="A private, read-only system overview. It never changes files, security settings, or operating-system configuration.",
            style="ModuleSummary.TLabel",
            justify="left",
        )
        summary.pack(anchor="w", pady=(4, 0), fill="x")
        bind_wrap = getattr(self.app, "_bind_responsive_wrap", None)
        if callable(bind_wrap):
            bind_wrap(summary, padding=24, minimum=280)

        actions = ttk.Frame(content, style="Surface.TFrame")
        actions.pack(fill="x", pady=(0, self._scaled(8)))
        buttons = [
            ttk.Button(actions, text="Refresh Snapshot", style="PrimaryApp.TButton", command=self.refresh),
            ttk.Button(actions, text="Open Storage Analyzer", command=lambda: self.app.select_tab("Storage Analyzer")),
            ttk.Button(actions, text="Export JSON", command=self.export_snapshot),
        ]
        flow_layout = getattr(self.app, "_bind_flow_layout", None)
        if callable(flow_layout):
            flow_layout(actions, buttons, min_item_width=170, horizontal_gap=6, vertical_gap=6, max_columns=3)
        else:
            for button in buttons:
                button.pack(side="left", padx=(0, 6))

        cards = ttk.Frame(content, style="Surface.TFrame")
        cards.pack(fill="both", expand=True)
        cards.columnconfigure(0, weight=1, uniform="health-card")
        cards.columnconfigure(1, weight=1, uniform="health-card")
        self._add_card(cards, 0, 0, "Operating system", self.os_var)
        self._add_card(cards, 0, 1, "Memory", self.memory_var)
        self._add_card(cards, 1, 0, "Home disk", self.disk_var)
        security = self._add_card(cards, 1, 1, "Security provider", self.security_var)
        detail = ttk.Label(security, textvariable=self.security_detail_var, style="CardMuted.TLabel", justify="left")
        detail.pack(anchor="w", fill="x", pady=(5, 0))
        if callable(bind_wrap):
            bind_wrap(detail, padding=20, minimum=220)

        notice = ttk.Label(
            content,
            text=(
                "This add-on is informational and is not antivirus software. On Windows it reads Microsoft Defender status only; "
                "on other systems, use the operating system's security center."
            ),
            style="Warning.TLabel",
            justify="left",
        )
        notice.pack(anchor="w", fill="x", pady=(self._scaled(10), 0))
        self.notice_label = notice
        if callable(bind_wrap):
            bind_wrap(notice, padding=12, minimum=280)
        status = ttk.Label(content, textvariable=self.status_var, style="Muted.TLabel")
        status.pack(anchor="w", pady=(self._scaled(8), 0))
        self.status_label = status

    def _add_card(self, parent: ttk.Frame, row: int, column: int, title: str, value: StringVar) -> ttk.LabelFrame:
        card = ttk.LabelFrame(parent, text=title, style="Card.TLabelframe", padding=12)
        card.grid(row=row, column=column, sticky="nsew", padx=(0 if column == 0 else 5, 5 if column == 0 else 0), pady=5)
        ttk.Label(card, textvariable=value, style="CardValue.TLabel", justify="left").pack(anchor="w", fill="x")
        return card

    def refresh(self) -> None:
        if self._refreshing:
            return
        self._refreshing = True
        self.status_var.set("Collecting a local snapshot...")
        threading.Thread(target=self._collect_in_background, name="pc-health-snapshot", daemon=True).start()

    def _collect_in_background(self) -> None:
        try:
            snapshot = collect_snapshot()
            error = ""
        except Exception as exc:
            snapshot = None
            error = f"Snapshot failed: {type(exc).__name__}."
        dispatcher = getattr(self.app, "call_ui", None)
        if callable(dispatcher):
            dispatcher(lambda: self._apply_snapshot(snapshot, error))
            return
        try:
            self.after(0, lambda: self._apply_snapshot(snapshot, error))
        except (RuntimeError, tk.TclError):
            return

    def _apply_snapshot(self, snapshot: PCHealthSnapshot | None, error: str) -> None:
        self._refreshing = False
        if snapshot is None:
            self.status_var.set(error or "Snapshot unavailable.")
            return
        self.snapshot = snapshot
        self.os_var.set(f"{snapshot.operating_system} {snapshot.release}\n{snapshot.architecture}")
        self.memory_var.set(
            f"{format_bytes(snapshot.memory_available_bytes)} available\nof {format_bytes(snapshot.memory_total_bytes)}"
        )
        self.disk_var.set(f"{format_bytes(snapshot.home_disk_free_bytes)} free\nof {format_bytes(snapshot.home_disk_total_bytes)}")
        self.security_var.set(snapshot.security_status)
        self.security_detail_var.set(snapshot.security_detail)
        self.status_var.set(f"Snapshot captured {snapshot.captured_at_utc}.")
        logger = getattr(self.app, "log", None)
        if callable(logger):
            logger("PC Health Snapshot refreshed (read-only).")

    def export_snapshot(self) -> None:
        if self.snapshot is None:
            messagebox.showinfo(ADDON_NAME, "Refresh the snapshot before exporting it.")
            return
        destination = filedialog.asksaveasfilename(
            title="Export PC health snapshot",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="format-foundry-pc-health.json",
        )
        if not destination:
            return
        payload = {
            "schema": "format-foundry/pc-health-snapshot/v1",
            "addon_version": ADDON_VERSION,
            "read_only": True,
            "snapshot": asdict(self.snapshot),
        }
        try:
            atomic_write_text(Path(destination), json.dumps(payload, indent=2, sort_keys=True) + "\n")
        except OSError as exc:
            messagebox.showerror(ADDON_NAME, f"The snapshot could not be exported:\n{exc}")
            return
        self.status_var.set(f"Snapshot exported to {destination}.")
