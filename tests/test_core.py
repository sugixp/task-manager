import sqlite3

import pytest

from task_manager.core import (
    DB_PATH_ENV_VAR,
    DEFAULT_PRIORITY,
    MAX_TITLE_LENGTH,
    TaskManager,
    TaskNotFoundError,
    ValidationError,
)


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "tasks.db"


@pytest.fixture
def manager(db_path):
    return TaskManager(db_path)


# ---------- adding ----------


def test_add_task_returns_pending_task(manager):
    task = manager.add_task("Buy milk")

    assert task.title == "Buy milk"
    assert task.done is False
    assert task.priority == DEFAULT_PRIORITY
    assert manager.list_tasks() == [task]


def test_add_task_with_priority_is_case_insensitive(manager):
    assert manager.add_task("Pay rent", " HIGH ").priority == "high"


@pytest.mark.parametrize("priority", ["urgent", "", None])
def test_add_task_rejects_invalid_priority(manager, priority):
    with pytest.raises(ValidationError, match="Priority"):
        manager.add_task("Pay rent", priority)


def test_add_task_strips_whitespace(manager):
    assert manager.add_task("  Buy milk  ").title == "Buy milk"


@pytest.mark.parametrize("title", ["", "   ", None])
def test_add_task_rejects_blank_title(manager, title):
    with pytest.raises(ValidationError, match="empty"):
        manager.add_task(title)
    assert manager.list_tasks() == []


def test_add_task_rejects_too_long_title(manager):
    with pytest.raises(ValidationError, match="at most"):
        manager.add_task("x" * (MAX_TITLE_LENGTH + 1))


# ---------- listing and reading ----------


def test_list_tasks_is_empty_for_new_database(manager):
    assert manager.list_tasks() == []


def test_list_tasks_keeps_creation_order(manager):
    titles = ["First", "Second", "Third"]
    for title in titles:
        manager.add_task(title)

    assert [task.title for task in manager.list_tasks()] == titles


def test_list_tasks_orders_pending_first_then_by_priority(manager):
    done_high = manager.add_task("Done high", "high")
    low = manager.add_task("Low", "low")
    high = manager.add_task("High", "high")
    medium = manager.add_task("Medium", "medium")
    manager.set_done(done_high.id, True)

    assert [t.title for t in manager.list_tasks()] == [
        high.title,
        medium.title,
        low.title,
        done_high.title,
    ]


def test_list_tasks_filters_by_status(manager):
    pending = manager.add_task("Pending")
    done = manager.set_done(manager.add_task("Done").id, True)

    assert manager.list_tasks("pending") == [pending]
    assert manager.list_tasks("done") == [done]
    assert len(manager.list_tasks("all")) == 2


def test_list_tasks_rejects_unknown_status(manager):
    with pytest.raises(ValidationError, match="Status"):
        manager.list_tasks("archived")


def test_count_tasks(manager):
    assert manager.count_tasks() == {"all": 0, "pending": 0, "done": 0}

    manager.add_task("Pending")
    manager.set_done(manager.add_task("Done").id, True)

    assert manager.count_tasks() == {"all": 2, "pending": 1, "done": 1}


def test_get_task_unknown_id_raises(manager):
    with pytest.raises(TaskNotFoundError, match="Task 42 not found"):
        manager.get_task(42)


# ---------- editing ----------


def test_update_task_changes_title_and_priority(manager):
    task = manager.add_task("Buy milk")

    updated = manager.update_task(task.id, title="Buy oat milk", priority="low")

    assert (updated.title, updated.priority) == ("Buy oat milk", "low")
    assert manager.get_task(task.id) == updated


def test_update_task_keeps_fields_that_are_not_given(manager):
    task = manager.add_task("Buy milk", "high")

    updated = manager.update_task(task.id, title="Buy bread")

    assert updated.priority == "high"


def test_update_task_validates_input(manager):
    task = manager.add_task("Buy milk")

    with pytest.raises(ValidationError):
        manager.update_task(task.id, title="   ")
    with pytest.raises(ValidationError):
        manager.update_task(task.id, priority="urgent")
    assert manager.get_task(task.id) == task


def test_update_task_unknown_id_raises(manager):
    with pytest.raises(TaskNotFoundError):
        manager.update_task(42, title="Anything")


# ---------- done / pending and deleting ----------


def test_set_done_marks_task_as_done_and_pending(manager):
    task = manager.add_task("Buy milk")

    assert manager.set_done(task.id, True).done is True
    assert manager.set_done(task.id, False).done is False


def test_toggle_done_flips_status(manager):
    task = manager.add_task("Buy milk")

    assert manager.toggle_done(task.id).done is True
    assert manager.toggle_done(task.id).done is False


@pytest.mark.parametrize("method", ["toggle_done", "delete_task"])
def test_unknown_id_raises(manager, method):
    with pytest.raises(TaskNotFoundError):
        getattr(manager, method)(42)


def test_set_done_unknown_id_raises(manager):
    with pytest.raises(TaskNotFoundError):
        manager.set_done(42, True)


def test_delete_task_removes_it(manager):
    keep = manager.add_task("Keep")
    remove = manager.add_task("Remove")

    manager.delete_task(remove.id)

    assert manager.list_tasks() == [keep]


# ---------- persistence and storage ----------


def test_tasks_persist_between_instances(db_path):
    TaskManager(db_path).add_task("Buy milk")

    assert [t.title for t in TaskManager(db_path).list_tasks()] == ["Buy milk"]


def test_creates_missing_parent_directory(tmp_path):
    db_path = tmp_path / "nested" / "dir" / "tasks.db"

    TaskManager(db_path).add_task("Buy milk")

    assert db_path.exists()


def test_db_path_can_be_set_by_environment_variable(tmp_path, monkeypatch):
    db_path = tmp_path / "from-env.db"
    monkeypatch.setenv(DB_PATH_ENV_VAR, str(db_path))

    assert TaskManager().db_path == db_path


def test_corrupted_database_is_moved_aside(db_path):
    db_path.write_text("this is not a sqlite database")

    manager = TaskManager(db_path)

    assert manager.recovered_from is not None
    assert manager.recovered_from.read_text() == "this is not a sqlite database"
    assert manager.list_tasks() == []
    manager.add_task("Works again")  # the fresh database is usable


def test_migrates_legacy_portuguese_schema_without_data_loss(db_path):
    # Schema and data exactly as created by the first version of the project.
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                concluida INTEGER DEFAULT 0
            )
            """
        )
        conn.executemany(
            "INSERT INTO tasks (titulo, concluida) VALUES (?, ?)",
            [("Estudar", 1), ("Ler", 0)],
        )
    conn.close()

    manager = TaskManager(db_path)

    tasks = manager.list_tasks()
    assert sorted((t.id, t.title, t.done, t.priority) for t in tasks) == [
        (1, "Estudar", True, DEFAULT_PRIORITY),
        (2, "Ler", False, DEFAULT_PRIORITY),
    ]
    with sqlite3.connect(db_path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
    conn.close()
    assert {"title", "done", "priority"} <= columns
    assert not {"titulo", "concluida"} & columns

    # New tasks continue the existing ID sequence.
    assert manager.add_task("New").id == 3
