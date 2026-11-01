"""Business logic and SQLite persistence for tasks.

Interfaces (CLI, web) only talk to ``TaskManager``; they never touch SQL.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

DB_PATH_ENV_VAR = "TASK_MANAGER_DB"
# Default location: project root, resolved from this file so it does not
# depend on the directory the program is started from.
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "tasks.db"

MAX_TITLE_LENGTH = 200
PRIORITIES = ("low", "medium", "high")
DEFAULT_PRIORITY = "medium"
STATUS_FILTERS = {
    "all": "",
    "pending": "WHERE done = 0",
    "done": "WHERE done = 1",
}

CREATE_TABLE_SQL = """
    CREATE TABLE tasks (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        title    TEXT    NOT NULL,
        done     INTEGER NOT NULL DEFAULT 0,
        priority TEXT    NOT NULL DEFAULT 'medium'
    )
"""


class TaskError(Exception):
    """Base class for errors that should be shown to the user."""


class ValidationError(TaskError):
    """Raised when user input is invalid."""


class TaskNotFoundError(TaskError):
    """Raised when a task ID does not exist."""

    def __init__(self, task_id: int) -> None:
        super().__init__(f"Task {task_id} not found.")
        self.task_id = task_id


@dataclass(frozen=True)
class Task:
    id: int
    title: str
    done: bool
    priority: str


def default_db_path() -> Path:
    """Database path from the environment, falling back to the default."""
    return Path(os.environ.get(DB_PATH_ENV_VAR) or DEFAULT_DB_PATH)


class TaskManager:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else default_db_path()
        # Set when a corrupted database file had to be moved aside.
        self.recovered_from: Path | None = None
        self._init_db()

    # ---------- public API ----------

    def add_task(self, title: str, priority: str = DEFAULT_PRIORITY) -> Task:
        title = self._clean_title(title)
        priority = self._clean_priority(priority)
        cursor = self._write(
            "INSERT INTO tasks (title, priority) VALUES (?, ?)", (title, priority)
        )
        return self.get_task(cursor.lastrowid)

    def list_tasks(self, status: str = "all") -> list[Task]:
        """Pending tasks first, then by priority (high first), then oldest first."""
        if status not in STATUS_FILTERS:
            raise ValidationError(
                f"Status must be one of: {', '.join(STATUS_FILTERS)}."
            )
        rows = self._query(
            f"""
            SELECT id, title, done, priority FROM tasks
            {STATUS_FILTERS[status]}
            ORDER BY done,
                     CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                     id
            """
        )
        return [self._to_task(row) for row in rows]

    def count_tasks(self) -> dict[str, int]:
        row = self._query(
            "SELECT COUNT(*) AS total, COALESCE(SUM(done), 0) AS done FROM tasks"
        )[0]
        return {
            "all": row["total"],
            "pending": row["total"] - row["done"],
            "done": row["done"],
        }

    def get_task(self, task_id: int) -> Task:
        rows = self._query(
            "SELECT id, title, done, priority FROM tasks WHERE id = ?", (task_id,)
        )
        if not rows:
            raise TaskNotFoundError(task_id)
        return self._to_task(rows[0])

    def update_task(
        self, task_id: int, title: str | None = None, priority: str | None = None
    ) -> Task:
        """Change the title and/or priority. ``None`` keeps the current value."""
        task = self.get_task(task_id)
        title = task.title if title is None else self._clean_title(title)
        priority = task.priority if priority is None else self._clean_priority(priority)
        self._write(
            "UPDATE tasks SET title = ?, priority = ? WHERE id = ?",
            (title, priority, task_id),
        )
        return self.get_task(task_id)

    def set_done(self, task_id: int, done: bool) -> Task:
        cursor = self._write(
            "UPDATE tasks SET done = ? WHERE id = ?", (int(done), task_id)
        )
        if cursor.rowcount == 0:
            raise TaskNotFoundError(task_id)
        return self.get_task(task_id)

    def toggle_done(self, task_id: int) -> Task:
        cursor = self._write("UPDATE tasks SET done = 1 - done WHERE id = ?", (task_id,))
        if cursor.rowcount == 0:
            raise TaskNotFoundError(task_id)
        return self.get_task(task_id)

    def delete_task(self, task_id: int) -> None:
        cursor = self._write("DELETE FROM tasks WHERE id = ?", (task_id,))
        if cursor.rowcount == 0:
            raise TaskNotFoundError(task_id)

    # ---------- validation ----------

    @staticmethod
    def _clean_title(title: str) -> str:
        title = (title or "").strip()
        if not title:
            raise ValidationError("Title cannot be empty.")
        if len(title) > MAX_TITLE_LENGTH:
            raise ValidationError(
                f"Title must be at most {MAX_TITLE_LENGTH} characters."
            )
        return title

    @staticmethod
    def _clean_priority(priority: str) -> str:
        priority = (priority or "").strip().lower()
        if priority not in PRIORITIES:
            raise ValidationError(
                f"Priority must be one of: {', '.join(PRIORITIES)}."
            )
        return priority

    # ---------- database helpers ----------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with closing(self._connect()) as conn:
            return conn.execute(sql, params).fetchall()

    def _write(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with closing(self._connect()) as conn:
            with conn:  # commits on success, rolls back on error
                return conn.execute(sql, params)

    @staticmethod
    def _to_task(row: sqlite3.Row) -> Task:
        return Task(
            id=row["id"],
            title=row["title"],
            done=bool(row["done"]),
            priority=row["priority"],
        )

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._migrate()
        except sqlite3.DatabaseError as error:
            # OperationalError (e.g. "database is locked") is not corruption.
            if isinstance(error, sqlite3.OperationalError):
                raise
            self.recovered_from = self._move_corrupted_file()
            self._migrate()

    def _migrate(self) -> None:
        """Create the table, or upgrade a database from an older schema."""
        with closing(self._connect()) as conn:
            with conn:
                columns = {
                    row["name"] for row in conn.execute("PRAGMA table_info(tasks)")
                }
                if not columns:
                    conn.execute(CREATE_TABLE_SQL)
                    return
                # The first version of the project used Portuguese column names.
                if "titulo" in columns:
                    conn.execute("ALTER TABLE tasks RENAME COLUMN titulo TO title")
                if "concluida" in columns:
                    conn.execute("ALTER TABLE tasks RENAME COLUMN concluida TO done")
                if "priority" not in columns:
                    conn.execute(
                        "ALTER TABLE tasks ADD COLUMN priority TEXT NOT NULL "
                        f"DEFAULT '{DEFAULT_PRIORITY}'"
                    )

    def _move_corrupted_file(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = self.db_path.with_name(f"{self.db_path.name}.corrupted-{timestamp}")
        self.db_path.rename(backup)
        return backup
