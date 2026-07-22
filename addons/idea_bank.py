"""Optional Idea Bank workspace for capturing and organizing project concepts."""

from __future__ import annotations

import csv
import io
import json
import tkinter as tk
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tkinter import StringVar, filedialog, messagebox, ttk
from typing import Any

from support_runtime import atomic_write_text

ADDON_ID = "idea-bank"
ADDON_NAME = "Idea Bank"
ADDON_VERSION = "1.0"
DATA_SCHEMA = "format-foundry/idea-bank/v1"
IDEA_STATUSES = ("Inbox", "Exploring", "Planned", "Completed", "Archived")
MAX_DATA_BYTES = 16 * 1024 * 1024
MAX_IDEAS = 10_000


class IdeaBankError(RuntimeError):
    """Raised when Idea Bank data is invalid or cannot be saved safely."""


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _clean_text(value: Any, *, limit: int) -> str:
    return str(value or "").replace("\x00", "").strip()[:limit]


def _normalize_tags(values: str | Iterable[str]) -> tuple[str, ...]:
    raw_values = values.split(",") if isinstance(values, str) else values
    tags: list[str] = []
    seen: set[str] = set()
    for raw_value in raw_values:
        tag = _clean_text(raw_value, limit=48)
        key = tag.casefold()
        if not tag or key in seen:
            continue
        seen.add(key)
        tags.append(tag)
        if len(tags) >= 20:
            break
    return tuple(tags)


def _csv_safe(value: Any) -> str:
    text = str(value or "")
    if text.lstrip().startswith(("=", "+", "-", "@")):
        return f"'{text}"
    return text


@dataclass(frozen=True)
class IdeaRecord:
    idea_id: str
    title: str
    description: str
    tags: tuple[str, ...]
    status: str
    created_at_utc: str
    updated_at_utc: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> IdeaRecord:
        idea_id = _clean_text(payload.get("id"), limit=80)
        title = _clean_text(payload.get("title"), limit=200)
        if not idea_id or not title:
            raise IdeaBankError("Every saved idea must contain an ID and title.")
        status = _clean_text(payload.get("status"), limit=32) or "Inbox"
        if status not in IDEA_STATUSES:
            status = "Inbox"
        raw_tags = payload.get("tags", [])
        tags = _normalize_tags(raw_tags if isinstance(raw_tags, (list, tuple)) else str(raw_tags))
        created = _clean_text(payload.get("created_at_utc"), limit=40) or utc_now()
        updated = _clean_text(payload.get("updated_at_utc"), limit=40) or created
        return cls(
            idea_id=idea_id,
            title=title,
            description=_clean_text(payload.get("description"), limit=20_000),
            tags=tags,
            status=status,
            created_at_utc=created,
            updated_at_utc=updated,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.idea_id,
            "title": self.title,
            "description": self.description,
            "tags": list(self.tags),
            "status": self.status,
            "created_at_utc": self.created_at_utc,
            "updated_at_utc": self.updated_at_utc,
        }


class IdeaBankStore:
    def __init__(self, data_path: Path):
        self.data_path = Path(data_path)
        self.records: list[IdeaRecord] = []
        self.load()

    def load(self) -> list[IdeaRecord]:
        if not self.data_path.exists():
            self.records = []
            return []
        if self.data_path.stat().st_size > MAX_DATA_BYTES:
            raise IdeaBankError("Idea Bank data exceeds the 16 MB safety limit.")
        try:
            payload = json.loads(self.data_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise IdeaBankError(f"Idea Bank data could not be read: {exc}") from exc
        if not isinstance(payload, dict) or payload.get("schema") != DATA_SCHEMA:
            raise IdeaBankError("Idea Bank data has an unsupported schema.")
        raw_ideas = payload.get("ideas", [])
        if not isinstance(raw_ideas, list):
            raise IdeaBankError("Idea Bank data does not contain a valid idea list.")
        if len(raw_ideas) > MAX_IDEAS:
            raise IdeaBankError(f"Idea Bank is limited to {MAX_IDEAS:,} ideas per workspace.")
        records: list[IdeaRecord] = []
        seen_ids: set[str] = set()
        for raw_idea in raw_ideas:
            if not isinstance(raw_idea, dict):
                raise IdeaBankError("Idea Bank contains a malformed record.")
            record = IdeaRecord.from_dict(raw_idea)
            if record.idea_id in seen_ids:
                raise IdeaBankError(f"Idea Bank contains a duplicate ID: {record.idea_id}")
            seen_ids.add(record.idea_id)
            records.append(record)
        self.records = records
        return list(records)

    def save(self) -> None:
        payload = {
            "schema": DATA_SCHEMA,
            "addon_version": ADDON_VERSION,
            "ideas": [record.to_dict() for record in self.records],
        }
        content = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        if len(content.encode("utf-8")) > MAX_DATA_BYTES:
            raise IdeaBankError("Idea Bank data exceeds the 16 MB safety limit.")
        try:
            atomic_write_text(self.data_path, content)
        except OSError as exc:
            raise IdeaBankError(f"Idea Bank data could not be saved: {exc}") from exc

    def create(self, *, title: str, description: str = "", tags: str | Iterable[str] = (), status: str = "Inbox") -> IdeaRecord:
        clean_title = _clean_text(title, limit=200)
        if not clean_title:
            raise IdeaBankError("An idea title is required.")
        clean_status = status if status in IDEA_STATUSES else "Inbox"
        timestamp = utc_now()
        record = IdeaRecord(
            idea_id=str(uuid.uuid4()),
            title=clean_title,
            description=_clean_text(description, limit=20_000),
            tags=_normalize_tags(tags),
            status=clean_status,
            created_at_utc=timestamp,
            updated_at_utc=timestamp,
        )
        if len(self.records) >= MAX_IDEAS:
            raise IdeaBankError(f"Idea Bank is limited to {MAX_IDEAS:,} ideas per workspace.")
        self.records.append(record)
        try:
            self.save()
        except IdeaBankError:
            self.records.pop()
            raise
        return record

    def update(
        self,
        idea_id: str,
        *,
        title: str,
        description: str,
        tags: str | Iterable[str],
        status: str,
    ) -> IdeaRecord:
        existing = self.get(idea_id)
        clean_title = _clean_text(title, limit=200)
        if not clean_title:
            raise IdeaBankError("An idea title is required.")
        updated = IdeaRecord(
            idea_id=existing.idea_id,
            title=clean_title,
            description=_clean_text(description, limit=20_000),
            tags=_normalize_tags(tags),
            status=status if status in IDEA_STATUSES else "Inbox",
            created_at_utc=existing.created_at_utc,
            updated_at_utc=utc_now(),
        )
        index = self.records.index(existing)
        self.records[index] = updated
        try:
            self.save()
        except IdeaBankError:
            self.records[index] = existing
            raise
        return updated

    def delete(self, idea_id: str) -> IdeaRecord:
        record = self.get(idea_id)
        index = self.records.index(record)
        self.records.pop(index)
        try:
            self.save()
        except IdeaBankError:
            self.records.insert(index, record)
            raise
        return record

    def get(self, idea_id: str) -> IdeaRecord:
        for record in self.records:
            if record.idea_id == idea_id:
                return record
        raise IdeaBankError("The selected idea no longer exists.")

    def search(self, query: str = "", status: str = "All") -> list[IdeaRecord]:
        query_key = query.strip().casefold()
        matches: list[IdeaRecord] = []
        for record in self.records:
            if status != "All" and record.status != status:
                continue
            haystack = "\n".join((record.title, record.description, " ".join(record.tags), record.status)).casefold()
            if query_key and query_key not in haystack:
                continue
            matches.append(record)
        return sorted(matches, key=lambda item: (item.updated_at_utc, item.created_at_utc), reverse=True)

    def export_csv(self, destination: Path) -> None:
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(("Title", "Status", "Tags", "Description", "Created UTC", "Updated UTC", "ID"))
        for record in self.search():
            writer.writerow(
                (
                    _csv_safe(record.title),
                    _csv_safe(record.status),
                    _csv_safe(", ".join(record.tags)),
                    _csv_safe(record.description),
                    record.created_at_utc,
                    record.updated_at_utc,
                    record.idea_id,
                )
            )
        atomic_write_text(Path(destination), output.getvalue())


class IdeaBankTab(ttk.Frame):
    """Top-level optional workspace that remains independent of conversion jobs."""

    def __init__(self, master: tk.Misc, app: Any):
        super().__init__(master, style="Surface.TFrame", padding=12)
        self.app = app
        self.data_path = Path(app.appdata_dir) / "addons" / ADDON_ID / "ideas.json"
        self.search_var = StringVar(value="")
        self.filter_status_var = StringVar(value="All")
        self.title_var = StringVar(value="")
        self.tags_var = StringVar(value="")
        self.status_var = StringVar(value="Inbox")
        self.summary_var = StringVar(value="0 ideas")
        self.feedback_var = StringVar(value="Ready.")
        self.selected_idea_id = ""
        self.store_error = ""
        self._refresh_after_id = ""
        try:
            self.store = IdeaBankStore(self.data_path)
        except IdeaBankError as exc:
            self.store = IdeaBankStore.__new__(IdeaBankStore)
            self.store.data_path = self.data_path
            self.store.records = []
            self.store_error = str(exc)
        self._build_ui()
        self.search_var.trace_add("write", lambda *_args: self._schedule_refresh())
        self.refresh()

    def _scaled(self, value: int) -> int:
        scaler = getattr(self.app, "_scaled", None)
        return int(scaler(value)) if callable(scaler) else value

    def _build_ui(self) -> None:
        hero = ttk.Frame(self, style="ModuleHero.TFrame")
        hero.pack(fill="x", pady=(0, self._scaled(10)))
        hero_inner = ttk.Frame(hero, style="ModuleHeroBody.TFrame", padding=(14, 10))
        hero_inner.pack(fill="x")
        ttk.Label(hero_inner, text="Idea Bank", style="ModuleTitle.TLabel").pack(anchor="w")
        summary = ttk.Label(
            hero_inner,
            text="Capture product ideas, add context and tags, then move promising concepts into a plan.",
            style="ModuleSummary.TLabel",
            justify="left",
        )
        summary.pack(anchor="w", pady=(4, 0), fill="x")
        bind_wrap = getattr(self.app, "_bind_responsive_wrap", None)
        if callable(bind_wrap):
            bind_wrap(summary, padding=24, minimum=280)

        toolbar = ttk.Frame(self, style="Surface.TFrame")
        toolbar.pack(fill="x", pady=(0, self._scaled(8)))
        ttk.Label(toolbar, text="Search").grid(row=0, column=0, sticky="w")
        search_entry = ttk.Entry(toolbar, textvariable=self.search_var)
        search_entry.grid(row=0, column=1, sticky="ew", padx=(self._scaled(6), self._scaled(10)))
        ttk.Label(toolbar, text="Status").grid(row=0, column=2, sticky="w")
        status_filter = ttk.Combobox(
            toolbar,
            textvariable=self.filter_status_var,
            values=("All", *IDEA_STATUSES),
            state="readonly",
            width=12,
        )
        status_filter.grid(row=0, column=3, sticky="ew", padx=(self._scaled(6), self._scaled(10)))
        status_filter.bind("<<ComboboxSelected>>", lambda _event: self.refresh(), add="+")
        ttk.Button(toolbar, text="New Idea", style="PrimaryApp.TButton", command=self.new_idea).grid(row=0, column=4, sticky="e")
        toolbar.columnconfigure(1, weight=1)
        ttk.Label(toolbar, textvariable=self.summary_var, style="Muted.TLabel").grid(
            row=1,
            column=0,
            columnspan=5,
            sticky="w",
            pady=(self._scaled(5), 0),
        )

        panes = ttk.Panedwindow(self, orient="horizontal")
        panes.pack(fill="both", expand=True)

        list_card = ttk.LabelFrame(panes, text="Ideas", style="Card.TLabelframe", padding=8)
        editor_card = ttk.LabelFrame(panes, text="Idea details", style="Card.TLabelframe", padding=10)
        panes.add(list_card, weight=3)
        panes.add(editor_card, weight=2)

        tree_host = ttk.Frame(list_card, style="Card.TFrame")
        tree_host.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(
            tree_host,
            columns=("status", "tags", "updated"),
            show="tree headings",
            selectmode="browse",
        )
        self.tree.heading("#0", text="Title")
        self.tree.heading("status", text="Status")
        self.tree.heading("tags", text="Tags")
        self.tree.heading("updated", text="Updated")
        self.tree.column("#0", width=self._scaled(190), minwidth=self._scaled(150), stretch=True)
        self.tree.column("status", width=self._scaled(85), minwidth=self._scaled(80), stretch=False)
        self.tree.column("tags", width=self._scaled(110), minwidth=self._scaled(90), stretch=True)
        self.tree.column("updated", width=self._scaled(105), minwidth=self._scaled(105), stretch=False)
        tree_scroll = ttk.Scrollbar(tree_host, orient="vertical", command=self.tree.yview)
        tree_scroll_x = ttk.Scrollbar(tree_host, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_scroll.set, xscrollcommand=tree_scroll_x.set)
        tree_scroll_x.pack(side="bottom", fill="x")
        self.tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_selection_changed, add="+")

        editor_card.columnconfigure(1, weight=1)
        editor_card.rowconfigure(4, weight=1)
        ttk.Label(editor_card, text="Title").grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(editor_card, textvariable=self.title_var).grid(row=0, column=1, sticky="ew", pady=(0, 6))
        ttk.Label(editor_card, text="Status").grid(row=1, column=0, sticky="w", pady=(0, 6))
        ttk.Combobox(
            editor_card,
            textvariable=self.status_var,
            values=IDEA_STATUSES,
            state="readonly",
        ).grid(row=1, column=1, sticky="ew", pady=(0, 6))
        ttk.Label(editor_card, text="Tags").grid(row=2, column=0, sticky="w", pady=(0, 6))
        ttk.Entry(editor_card, textvariable=self.tags_var).grid(row=2, column=1, sticky="ew", pady=(0, 6))
        ttk.Label(editor_card, text="Comma-separated tags", style="Muted.TLabel").grid(
            row=3,
            column=1,
            sticky="w",
            pady=(0, 6),
        )
        ttk.Label(editor_card, text="Notes").grid(row=4, column=0, sticky="nw")
        palette = self.app._theme_palette(bool(self.app.dark_mode_var.get()))
        self.description_text = tk.Text(
            editor_card,
            wrap="word",
            height=12,
            undo=True,
            bg=palette["input_bg"],
            fg=palette["input_fg"],
            insertbackground=palette["input_fg"],
            highlightthickness=1,
            highlightbackground=palette["input_border"],
            relief="flat",
            padx=self._scaled(8),
            pady=self._scaled(8),
        )
        self.description_text.grid(row=4, column=1, sticky="nsew")

        actions = ttk.Frame(editor_card, style="Card.TFrame")
        actions.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(self._scaled(10), 0))
        buttons = [
            ttk.Button(actions, text="Save", style="PrimaryApp.TButton", command=self.save_current),
            ttk.Button(actions, text="Archive", style="QuietApp.TButton", command=self.archive_current),
            ttk.Button(actions, text="Delete", style="DangerApp.TButton", command=self.delete_current),
            ttk.Button(actions, text="Export CSV", style="QuietApp.TButton", command=self.export_csv),
        ]
        flow_layout = getattr(self.app, "_bind_flow_layout", None)
        if callable(flow_layout):
            flow_layout(actions, buttons, min_item_width=105, horizontal_gap=6, vertical_gap=6, stretch=True, max_columns=2)
        else:
            for index, button in enumerate(buttons):
                button.grid(row=index // 2, column=index % 2, sticky="ew", padx=3, pady=3)
                actions.columnconfigure(index % 2, weight=1)

        ttk.Label(self, textvariable=self.feedback_var, style="Muted.TLabel").pack(anchor="w", pady=(self._scaled(8), 0))
        if self.store_error:
            self.feedback_var.set(f"Data needs attention: {self.store_error}")

    def _notify(self, message: str) -> None:
        self.feedback_var.set(message)
        status_var = getattr(self.app, "status_left_var", None)
        status_setter = getattr(status_var, "set", None)
        if callable(status_setter):
            status_setter(message)
        logger: Callable[[str], None] | None = getattr(self.app, "log", None)
        if callable(logger):
            logger(f"Idea Bank: {message}")

    def _schedule_refresh(self) -> None:
        if self._refresh_after_id:
            self.after_cancel(self._refresh_after_id)
        self._refresh_after_id = self.after(120, self._run_scheduled_refresh)

    def _run_scheduled_refresh(self) -> None:
        self._refresh_after_id = ""
        self.refresh()

    def refresh(self, *, select_id: str = "") -> None:
        current = select_id or self.selected_idea_id
        for item_id in self.tree.get_children(""):
            self.tree.delete(item_id)
        matches = self.store.search(self.search_var.get(), self.filter_status_var.get())
        for record in matches:
            updated = record.updated_at_utc.replace("T", " ").replace("Z", "")[:16]
            self.tree.insert(
                "",
                "end",
                iid=record.idea_id,
                text=record.title,
                values=(record.status, ", ".join(record.tags), updated),
            )
        total = len(self.store.records)
        self.summary_var.set(f"Showing {len(matches)} of {total} idea{'s' if total != 1 else ''}")
        if current and self.tree.exists(current):
            self.tree.selection_set(current)
            self.tree.focus(current)
            self.tree.see(current)

    def new_idea(self) -> None:
        self.selected_idea_id = ""
        self.tree.selection_remove(self.tree.selection())
        self.title_var.set("")
        self.tags_var.set("")
        self.status_var.set("Inbox")
        self.description_text.delete("1.0", "end")
        self.feedback_var.set("New idea ready. Add a title and save.")

    def _on_selection_changed(self, _event: Any = None) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        try:
            record = self.store.get(str(selected[0]))
        except IdeaBankError as exc:
            self._notify(str(exc))
            return
        self.selected_idea_id = record.idea_id
        self.title_var.set(record.title)
        self.tags_var.set(", ".join(record.tags))
        self.status_var.set(record.status)
        self.description_text.delete("1.0", "end")
        self.description_text.insert("1.0", record.description)
        self.feedback_var.set(f"Editing {record.title}")

    def save_current(self) -> None:
        if self.store_error:
            messagebox.showerror(ADDON_NAME, self.store_error)
            return
        try:
            payload = {
                "title": self.title_var.get(),
                "description": self.description_text.get("1.0", "end-1c"),
                "tags": self.tags_var.get(),
                "status": self.status_var.get(),
            }
            if self.selected_idea_id:
                record = self.store.update(self.selected_idea_id, **payload)
                action = "Updated"
            else:
                record = self.store.create(**payload)
                self.selected_idea_id = record.idea_id
                action = "Saved"
        except IdeaBankError as exc:
            messagebox.showerror(ADDON_NAME, str(exc))
            return
        self.refresh(select_id=record.idea_id)
        self._notify(f"{action} idea: {record.title}")

    def archive_current(self) -> None:
        if not self.selected_idea_id:
            messagebox.showinfo(ADDON_NAME, "Select an idea to archive.")
            return
        self.status_var.set("Archived")
        self.save_current()

    def delete_current(self) -> None:
        if not self.selected_idea_id:
            messagebox.showinfo(ADDON_NAME, "Select an idea to delete.")
            return
        record = self.store.get(self.selected_idea_id)
        if not messagebox.askyesno(ADDON_NAME, f"Delete this idea?\n\n{record.title}"):
            return
        try:
            self.store.delete(record.idea_id)
        except IdeaBankError as exc:
            messagebox.showerror(ADDON_NAME, str(exc))
            return
        self.new_idea()
        self.refresh()
        self._notify(f"Deleted idea: {record.title}")

    def export_csv(self) -> None:
        destination = filedialog.asksaveasfilename(
            title="Export Idea Bank",
            defaultextension=".csv",
            initialfile="format-foundry-idea-bank.csv",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if not destination:
            return
        try:
            self.store.export_csv(Path(destination))
        except (IdeaBankError, OSError) as exc:
            messagebox.showerror(ADDON_NAME, f"Idea export failed:\n{exc}")
            return
        self._notify(f"Exported {len(self.store.records)} ideas to CSV.")
