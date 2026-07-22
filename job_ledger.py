"""Persistent SQLite ledger for resumable Format Foundry batch jobs."""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

JOB_STATUSES = ("queued", "running", "completed", "failed", "interrupted", "canceled")
ACTIVE_JOB_STATUSES = ("queued", "running", "failed", "interrupted")


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


class JobLedger:
    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10.0)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 10000")
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    module TEXT NOT NULL,
                    preset TEXT NOT NULL,
                    input_path TEXT NOT NULL,
                    output_path TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error TEXT NOT NULL DEFAULT '',
                    created_at_utc TEXT NOT NULL,
                    updated_at_utc TEXT NOT NULL,
                    CHECK (status IN ('queued','running','completed','failed','interrupted','canceled'))
                )
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS jobs_status_updated ON jobs(status, updated_at_utc)")

    def recover_interrupted(self) -> int:
        with self._connection() as connection:
            cursor = connection.execute(
                "UPDATE jobs SET status = 'interrupted', error = ?, updated_at_utc = ? WHERE status = 'running'",
                ("The previous app session ended while this job was running.", utc_now()),
            )
            return max(0, int(cursor.rowcount))

    def add(self, job: Mapping[str, Any]) -> dict[str, Any]:
        job_id = str(job.get("job_id") or uuid.uuid4())
        timestamp = utc_now()
        record = {
            "job_id": job_id,
            "module": str(job.get("module", "Convert")),
            "preset": str(job.get("preset", "")),
            "input": str(job.get("input", "")),
            "output": str(job.get("output", "")),
            "config": dict(job.get("config", {})),
            "status": "queued",
            "error": "",
            "created_at_utc": timestamp,
            "updated_at_utc": timestamp,
        }
        if not record["input"] or not record["output"]:
            raise ValueError("Persistent jobs require input and output paths.")
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    job_id, module, preset, input_path, output_path, config_json,
                    status, error, created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["job_id"],
                    record["module"],
                    record["preset"],
                    record["input"],
                    record["output"],
                    json.dumps(record["config"], sort_keys=True),
                    record["status"],
                    record["error"],
                    record["created_at_utc"],
                    record["updated_at_utc"],
                ),
            )
        return record

    def list(self, statuses: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM jobs"
        parameters: tuple[Any, ...] = ()
        if statuses:
            placeholders = ",".join("?" for _ in statuses)
            query += f" WHERE status IN ({placeholders})"
            parameters = tuple(statuses)
        query += " ORDER BY created_at_utc, job_id"
        with self._connection() as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [self._row_to_record(row) for row in rows]

    def update_status(self, job_id: str, status: str, error: str = "") -> None:
        if status not in JOB_STATUSES:
            raise ValueError(f"Unsupported job status: {status}")
        with self._connection() as connection:
            cursor = connection.execute(
                "UPDATE jobs SET status = ?, error = ?, updated_at_utc = ? WHERE job_id = ?",
                (status, str(error)[:4000], utc_now(), str(job_id)),
            )
            if cursor.rowcount != 1:
                raise KeyError(f"Unknown job ID: {job_id}")

    def delete(self, job_id: str) -> None:
        with self._connection() as connection:
            connection.execute("DELETE FROM jobs WHERE job_id = ?", (str(job_id),))

    def clear(self, *, include_completed: bool = True) -> int:
        with self._connection() as connection:
            if include_completed:
                cursor = connection.execute("DELETE FROM jobs")
            else:
                cursor = connection.execute("DELETE FROM jobs WHERE status != 'completed'")
            return max(0, int(cursor.rowcount))

    def prune_completed(self, keep: int = 500) -> int:
        keep = max(0, int(keep))
        with self._connection() as connection:
            cursor = connection.execute(
                """
                DELETE FROM jobs
                WHERE status = 'completed' AND job_id NOT IN (
                    SELECT job_id FROM jobs WHERE status = 'completed'
                    ORDER BY updated_at_utc DESC LIMIT ?
                )
                """,
                (keep,),
            )
            return max(0, int(cursor.rowcount))

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> dict[str, Any]:
        try:
            config = json.loads(str(row["config_json"]))
        except json.JSONDecodeError:
            config = {}
        return {
            "job_id": str(row["job_id"]),
            "module": str(row["module"]),
            "preset": str(row["preset"]),
            "input": str(row["input_path"]),
            "output": str(row["output_path"]),
            "config": config if isinstance(config, dict) else {},
            "status": str(row["status"]),
            "error": str(row["error"]),
            "created_at_utc": str(row["created_at_utc"]),
            "updated_at_utc": str(row["updated_at_utc"]),
        }
