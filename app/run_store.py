from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.domain.models import (
    ConversationMessage,
    ResearchConversationDetail,
    ResearchConversationSummary,
    ResearchRequest,
    ResearchRunDetail,
    ResearchRunSummary,
    RunStatus,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_conversation_title(question: str) -> str:
    normalized = " ".join(question.split()).strip()
    if not normalized:
        return "新研究"
    return normalized[:60].rstrip()


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
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    message_id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    run_id TEXT,
                    parent_message_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS research_runs (
                    run_id TEXT PRIMARY KEY,
                    conversation_id TEXT,
                    origin_message_id TEXT,
                    assistant_message_id TEXT,
                    parent_run_id TEXT,
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
            self._ensure_column(connection, "research_runs", "conversation_id", "TEXT")
            self._ensure_column(connection, "research_runs", "origin_message_id", "TEXT")
            self._ensure_column(connection, "research_runs", "assistant_message_id", "TEXT")
            self._ensure_column(connection, "research_runs", "parent_run_id", "TEXT")
            self._backfill_legacy_runs(connection)
            connection.commit()

    def create_run(self, run_id: str, request: dict) -> ResearchRunDetail:
        question = ResearchRequest.model_validate(request).question
        conversation_id = run_id
        self.create_conversation_turn(
            conversation_id=conversation_id,
            run_id=run_id,
            request=request,
            origin_message_id=f"{run_id}-user",
            assistant_message_id=f"{run_id}-assistant",
            title=build_conversation_title(question),
            parent_run_id=None,
        )
        return self._require_run(run_id)

    def create_conversation_turn(
        self,
        conversation_id: str,
        run_id: str,
        request: dict,
        *,
        origin_message_id: str,
        assistant_message_id: str,
        title: str | None = None,
        parent_run_id: str | None = None,
    ) -> tuple[ResearchConversationDetail, ResearchRunDetail]:
        request_model = ResearchRequest.model_validate(request)
        now = utc_now_iso()

        with self._connect() as connection:
            conversation_row = connection.execute(
                """
                SELECT conversation_id, title, created_at, updated_at
                FROM conversations
                WHERE conversation_id = ?
                """,
                (conversation_id,),
            ).fetchone()
            if conversation_row is None:
                conversation_title = title or build_conversation_title(request_model.question)
                connection.execute(
                    """
                    INSERT INTO conversations (
                        conversation_id,
                        title,
                        created_at,
                        updated_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (conversation_id, conversation_title, now, now),
                )
            else:
                connection.execute(
                    """
                    UPDATE conversations
                    SET updated_at = ?
                    WHERE conversation_id = ?
                    """,
                    (now, conversation_id),
                )

            parent_message_id = self._lookup_parent_message_id(connection, parent_run_id)

            connection.execute(
                """
                INSERT INTO conversation_messages (
                    message_id,
                    conversation_id,
                    role,
                    content,
                    run_id,
                    parent_message_id,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    origin_message_id,
                    conversation_id,
                    "user",
                    request_model.question,
                    run_id,
                    parent_message_id,
                    now,
                    now,
                ),
            )
            connection.execute(
                """
                INSERT INTO conversation_messages (
                    message_id,
                    conversation_id,
                    role,
                    content,
                    run_id,
                    parent_message_id,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    assistant_message_id,
                    conversation_id,
                    "assistant",
                    "",
                    run_id,
                    origin_message_id,
                    now,
                    now,
                ),
            )
            connection.execute(
                """
                INSERT INTO research_runs (
                    run_id,
                    conversation_id,
                    origin_message_id,
                    assistant_message_id,
                    parent_run_id,
                    status,
                    request_json,
                    result_json,
                    error_message,
                    created_at,
                    updated_at,
                    completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    conversation_id,
                    origin_message_id,
                    assistant_message_id,
                    parent_run_id,
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
        return self._require_conversation(conversation_id), self._require_run(run_id)

    def get_run(self, run_id: str) -> ResearchRunDetail | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    run_id,
                    conversation_id,
                    origin_message_id,
                    assistant_message_id,
                    parent_run_id,
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
                    conversation_id,
                    origin_message_id,
                    assistant_message_id,
                    parent_run_id,
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

    def get_conversation(self, conversation_id: str) -> ResearchConversationDetail | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT conversation_id, title, created_at, updated_at
                FROM conversations
                WHERE conversation_id = ?
                """,
                (conversation_id,),
            ).fetchone()
            if row is None:
                return None

            messages = [
                self._row_to_message(message_row)
                for message_row in connection.execute(
                    """
                    SELECT
                        message_id,
                        conversation_id,
                        role,
                        content,
                        run_id,
                        parent_message_id,
                        created_at,
                        updated_at
                    FROM conversation_messages
                    WHERE conversation_id = ?
                    ORDER BY created_at ASC, rowid ASC
                    """,
                    (conversation_id,),
                ).fetchall()
            ]
            runs = [
                self._row_to_detail(run_row)
                for run_row in connection.execute(
                    """
                    SELECT
                        run_id,
                        conversation_id,
                        origin_message_id,
                        assistant_message_id,
                        parent_run_id,
                        status,
                        request_json,
                        result_json,
                        error_message,
                        created_at,
                        updated_at,
                        completed_at
                    FROM research_runs
                    WHERE conversation_id = ?
                    ORDER BY created_at ASC, rowid ASC
                    """,
                    (conversation_id,),
                ).fetchall()
            ]
        return self._build_conversation_detail(row, messages, runs)

    def get_conversation_summary(self, conversation_id: str) -> ResearchConversationSummary | None:
        conversation = self.get_conversation(conversation_id)
        if conversation is None:
            return None
        return ResearchConversationSummary.model_validate(
            conversation.model_dump(exclude={"messages", "runs"}),
        )

    def list_conversations(self) -> list[ResearchConversationSummary]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT conversation_id, title, created_at, updated_at
                FROM conversations
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [self._build_conversation_summary(row["conversation_id"]) for row in rows]

    def get_message(self, message_id: str) -> ConversationMessage | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    message_id,
                    conversation_id,
                    role,
                    content,
                    run_id,
                    parent_message_id,
                    created_at,
                    updated_at
                FROM conversation_messages
                WHERE message_id = ?
                """,
                (message_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_message(row)

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
            if cursor.rowcount == 0:
                raise KeyError(run_id)
            self._touch_assistant_message(connection, run_id, now)
            self._touch_conversation(connection, run_id, now)
            connection.commit()
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
            if cursor.rowcount == 0:
                raise KeyError(run_id)
            self._update_assistant_message_content(connection, run_id, status, result, None, now)
            self._touch_conversation(connection, run_id, now)
            connection.commit()
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
            if cursor.rowcount == 0:
                raise KeyError(run_id)
            self._update_assistant_message_content(connection, run_id, "failed", None, error_message, now)
            self._touch_conversation(connection, run_id, now)
            connection.commit()
        return self._require_run(run_id)

    def fail_incomplete_runs(self, error_message: str) -> int:
        now = utc_now_iso()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT run_id
                FROM research_runs
                WHERE status IN (?, ?)
                """,
                ("queued", "running"),
            ).fetchall()
            if not rows:
                return 0
            connection.execute(
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
            for row in rows:
                self._update_assistant_message_content(connection, row["run_id"], "failed", None, error_message, now)
                self._touch_conversation(connection, row["run_id"], now)
            connection.commit()
        return len(rows)

    def _require_run(self, run_id: str) -> ResearchRunDetail:
        run = self.get_run(run_id)
        if run is None:
            raise KeyError(run_id)
        return run

    def _require_conversation(self, conversation_id: str) -> ResearchConversationDetail:
        conversation = self.get_conversation(conversation_id)
        if conversation is None:
            raise KeyError(conversation_id)
        return conversation

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_column(self, connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        existing = {
            row["name"]
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column in existing:
            return
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _backfill_legacy_runs(self, connection: sqlite3.Connection) -> None:
        rows = connection.execute(
            """
            SELECT
                run_id,
                conversation_id,
                origin_message_id,
                assistant_message_id,
                status,
                request_json,
                result_json,
                error_message,
                created_at,
                updated_at
            FROM research_runs
            WHERE conversation_id IS NULL
               OR origin_message_id IS NULL
               OR assistant_message_id IS NULL
            """
        ).fetchall()

        for row in rows:
            request = ResearchRequest.model_validate(json.loads(row["request_json"]))
            result = json.loads(row["result_json"]) if row["result_json"] else None
            conversation_id = row["conversation_id"] or row["run_id"]
            origin_message_id = row["origin_message_id"] or f"{row['run_id']}-user"
            assistant_message_id = row["assistant_message_id"] or f"{row['run_id']}-assistant"
            created_at = row["created_at"]
            updated_at = row["updated_at"]

            connection.execute(
                """
                INSERT OR IGNORE INTO conversations (
                    conversation_id,
                    title,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?)
                """,
                (conversation_id, build_conversation_title(request.question), created_at, updated_at),
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO conversation_messages (
                    message_id,
                    conversation_id,
                    role,
                    content,
                    run_id,
                    parent_message_id,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    origin_message_id,
                    conversation_id,
                    "user",
                    request.question,
                    row["run_id"],
                    None,
                    created_at,
                    updated_at,
                ),
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO conversation_messages (
                    message_id,
                    conversation_id,
                    role,
                    content,
                    run_id,
                    parent_message_id,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    assistant_message_id,
                    conversation_id,
                    "assistant",
                    self._assistant_content(row["status"], result, row["error_message"]),
                    row["run_id"],
                    origin_message_id,
                    created_at,
                    updated_at,
                ),
            )
            connection.execute(
                """
                UPDATE research_runs
                SET
                    conversation_id = ?,
                    origin_message_id = ?,
                    assistant_message_id = ?
                WHERE run_id = ?
                """,
                (conversation_id, origin_message_id, assistant_message_id, row["run_id"]),
            )

    def _lookup_parent_message_id(self, connection: sqlite3.Connection, parent_run_id: str | None) -> str | None:
        if not parent_run_id:
            return None
        row = connection.execute(
            """
            SELECT assistant_message_id
            FROM research_runs
            WHERE run_id = ?
            """,
            (parent_run_id,),
        ).fetchone()
        if row is None:
            raise KeyError(parent_run_id)
        return row["assistant_message_id"]

    def _touch_conversation(self, connection: sqlite3.Connection, run_id: str, updated_at: str) -> None:
        row = connection.execute(
            """
            SELECT conversation_id
            FROM research_runs
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()
        if row is None or not row["conversation_id"]:
            return
        connection.execute(
            """
            UPDATE conversations
            SET updated_at = ?
            WHERE conversation_id = ?
            """,
            (updated_at, row["conversation_id"]),
        )

    def _touch_assistant_message(self, connection: sqlite3.Connection, run_id: str, updated_at: str) -> None:
        row = connection.execute(
            """
            SELECT assistant_message_id
            FROM research_runs
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()
        if row is None or not row["assistant_message_id"]:
            return
        connection.execute(
            """
            UPDATE conversation_messages
            SET updated_at = ?
            WHERE message_id = ?
            """,
            (updated_at, row["assistant_message_id"]),
        )

    def _update_assistant_message_content(
        self,
        connection: sqlite3.Connection,
        run_id: str,
        status: RunStatus,
        result: dict | None,
        error_message: str | None,
        updated_at: str,
    ) -> None:
        row = connection.execute(
            """
            SELECT assistant_message_id
            FROM research_runs
            WHERE run_id = ?
            """,
            (run_id,),
        ).fetchone()
        if row is None or not row["assistant_message_id"]:
            return
        connection.execute(
            """
            UPDATE conversation_messages
            SET content = ?, updated_at = ?
            WHERE message_id = ?
            """,
            (
                self._assistant_content(status, result, error_message),
                updated_at,
                row["assistant_message_id"],
            ),
        )

    def _assistant_content(self, status: RunStatus, result: dict | None, error_message: str | None) -> str:
        if status == "failed":
            return error_message or "研究执行失败。"
        if not isinstance(result, dict):
            return ""

        final_report = self._as_string(result.get("final_report"))
        if final_report:
            return final_report

        draft_report = self._as_string(result.get("draft_report"))
        if draft_report:
            return draft_report

        if status == "interrupted":
            return "研究已暂停，等待人工审核。"
        return ""

    def _as_string(self, value: object) -> str:
        return value if isinstance(value, str) else ""

    def _build_conversation_summary(self, conversation_id: str) -> ResearchConversationSummary:
        conversation = self._require_conversation(conversation_id)
        return ResearchConversationSummary.model_validate(
            conversation.model_dump(exclude={"messages", "runs"}),
        )

    def _build_conversation_detail(
        self,
        row: sqlite3.Row,
        messages: list[ConversationMessage],
        runs: list[ResearchRunDetail],
    ) -> ResearchConversationDetail:
        latest_preview = row["title"]
        if messages:
            for message in reversed(messages):
                if message.content.strip():
                    latest_preview = message.content.strip()
                    break
        latest_run_status = runs[-1].status if runs else None
        return ResearchConversationDetail(
            conversation_id=row["conversation_id"],
            title=row["title"],
            latest_message_preview=latest_preview[:140],
            latest_run_status=latest_run_status,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            messages=messages,
            runs=runs,
        )

    def _row_to_message(self, row: sqlite3.Row) -> ConversationMessage:
        return ConversationMessage(
            message_id=row["message_id"],
            conversation_id=row["conversation_id"],
            role=row["role"],
            content=row["content"],
            run_id=row["run_id"],
            parent_message_id=row["parent_message_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _row_to_detail(self, row: sqlite3.Row) -> ResearchRunDetail:
        request = ResearchRequest.model_validate(json.loads(row["request_json"]))
        result = json.loads(row["result_json"]) if row["result_json"] else None
        warnings: list[str] = []
        if isinstance(result, dict):
            raw_warnings = result.get("warnings", [])
            if isinstance(raw_warnings, list):
                warnings = [str(item) for item in raw_warnings]

        conversation_id = row["conversation_id"] or row["run_id"]
        origin_message_id = row["origin_message_id"] or f"{row['run_id']}-user"
        assistant_message_id = row["assistant_message_id"] or f"{row['run_id']}-assistant"

        return ResearchRunDetail(
            run_id=row["run_id"],
            conversation_id=conversation_id,
            origin_message_id=origin_message_id,
            assistant_message_id=assistant_message_id,
            parent_run_id=row["parent_run_id"],
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
