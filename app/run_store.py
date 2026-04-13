from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.domain.models import ResearchRequest, ResearchRunDetail, ResearchRunSummary, RunStatus


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ResearchRunStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def initialize(self) -> None:
        db_file = Path(self._db_path)
        if db_file.parent != Path("."):
            db_file.parent.mkdir(parents=True, exist_ok=True)

        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS research_runs (
                    run_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    result_json TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT
                )
                """
            )
            connection.commit()

    def create_run(self, run_id: str, request: dict) -> ResearchRunDetail:
        request_model = ResearchRequest.model_validate(request)
        now = utc_now_iso()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO research_runs (
                    run_id,
                    status,
                    request_json,
                    result_json,
                    error_message,
                    created_at,
                    updated_at,
                    completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    "queued",
                    json.dumps(request_model.model_dump(), ensure_ascii=True, sort_keys=True),
                    None,
                    None,
                    now,
                    now,
                    None,
                ),
            )
            connection.commit()
        return self.get_run(run_id)

    def get_run(self, run_id: str) -> ResearchRunDetail | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    run_id,
                    status,
                    request_json,
                    result_json,
                    error_message,
                    created_at,
                    updated_at,
                    completed_at
                FROM research_runs
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_detail(row)

    def list_runs(self) -> list[ResearchRunSummary]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    run_id,
                    status,
                    request_json,
                    result_json,
                    error_message,
                    created_at,
                    updated_at,
                    completed_at
                FROM research_runs
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [self._row_to_summary(row) for row in rows]

    def set_status(self, run_id: str, status: RunStatus) -> ResearchRunDetail:
        now = utc_now_iso()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE research_runs
                SET status = ?, updated_at = ?, error_message = NULL
                WHERE run_id = ?
                """,
                (status, now, run_id),
            )
            connection.commit()
        if cursor.rowcount == 0:
            raise KeyError(run_id)
        return self._require_run(run_id)

    def store_result(self, run_id: str, status: RunStatus, result: dict) -> ResearchRunDetail:
        now = utc_now_iso()
        completed_at = now if status in {"completed", "failed"} else None
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE research_runs
                SET
                    status = ?,
                    result_json = ?,
                    error_message = NULL,
                    updated_at = ?,
                    completed_at = ?
                WHERE run_id = ?
                """,
                (
                    status,
                    json.dumps(result, ensure_ascii=True, sort_keys=True),
                    now,
                    completed_at,
                    run_id,
                ),
            )
            connection.commit()
        if cursor.rowcount == 0:
            raise KeyError(run_id)
        return self._require_run(run_id)

    def mark_failed(self, run_id: str, error_message: str) -> ResearchRunDetail:
        now = utc_now_iso()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE research_runs
                SET
                    status = ?,
                    error_message = ?,
                    updated_at = ?,
                    completed_at = ?
                WHERE run_id = ?
                """,
                ("failed", error_message, now, now, run_id),
            )
            connection.commit()
        if cursor.rowcount == 0:
            raise KeyError(run_id)
        return self._require_run(run_id)

    def fail_incomplete_runs(self, error_message: str) -> int:
        now = utc_now_iso()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE research_runs
                SET
                    status = ?,
                    error_message = ?,
                    updated_at = ?,
                    completed_at = ?
                WHERE status IN (?, ?)
                """,
                ("failed", error_message, now, now, "queued", "running"),
            )
            connection.commit()
        return cursor.rowcount

    def _require_run(self, run_id: str) -> ResearchRunDetail:
        run = self.get_run(run_id)
        if run is None:
            raise KeyError(run_id)
        return run

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _row_to_detail(self, row: sqlite3.Row) -> ResearchRunDetail:
        request = ResearchRequest.model_validate(json.loads(row["request_json"]))
        result = json.loads(row["result_json"]) if row["result_json"] else None
        warnings: list[str] = []
        if isinstance(result, dict):
            raw_warnings = result.get("warnings", [])
            if isinstance(raw_warnings, list):
                warnings = [str(item) for item in raw_warnings]

        return ResearchRunDetail(
            run_id=row["run_id"],
            status=row["status"],
            request=request,
            result=result,
            warnings=warnings,
            error_message=row["error_message"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            completed_at=row["completed_at"],
        )

    def _row_to_summary(self, row: sqlite3.Row) -> ResearchRunSummary:
        detail = self._row_to_detail(row)
        return ResearchRunSummary.model_validate(detail.model_dump(exclude={"result", "warnings"}))
