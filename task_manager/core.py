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

CREATE_TABLE_SQL = """
    CREATE TABLE tasks (
        id    INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT    NOT NULL,
        done  INTEGER NOT NULL DEFAULT 0
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

    def add_task(self, title: str) -> Task:
        title = self._clean_title(title)
        cursor = self._write("INSERT INTO tasks (title) VALUES (?)", (title,))
        return self.get_task(cursor.lastrowid)

    def list_tasks(self) -> list[Task]:
        rows = self._query("SELECT id, title, done FROM tasks ORDER BY id")
        return [self._to_task(row) for row in rows]

    def get_task(self, task_id: int) -> Task:
        rows = self._query(
            "SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)
        )
        if not rows:
            raise TaskNotFoundError(task_id)
        return self._to_task(rows[0])

    def complete_task(self, task_id: int) -> Task:
        cursor = self._write("UPDATE tasks SET done = 1 WHERE id = ?", (task_id,))
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
        return Task(id=row["id"], title=row["title"], done=bool(row["done"]))

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

    def _move_corrupted_file(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = self.db_path.with_name(f"{self.db_path.name}.corrupted-{timestamp}")
        self.db_path.rename(backup)
        return backup
