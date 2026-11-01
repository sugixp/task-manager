import re

import pytest

from task_manager.core import TaskManager
from task_manager.web.app import create_app


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "tasks.db"


@pytest.fixture
def client(db_path):
    app = create_app(db_path)
    app.testing = True
    return app.test_client()


@pytest.fixture
def manager(db_path, client):
    # Same database the app uses, to arrange and inspect state directly.
    return TaskManager(db_path)


def test_index_shows_empty_state(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"No tasks yet" in response.data


def test_add_task(client, manager):
    response = client.post(
        "/tasks", data={"title": "Buy milk", "priority": "high"}, follow_redirects=True
    )

    assert b"Task &#34;Buy milk&#34; added." in response.data
    [task] = manager.list_tasks()
    assert (task.title, task.priority) == ("Buy milk", "high")


def test_add_blank_task_shows_validation_error(client, manager):
    response = client.post("/tasks", data={"title": "   ", "priority": "medium"})

    assert response.status_code == 400
    assert b"Title cannot be empty." in response.data
    assert manager.list_tasks() == []


def test_filter_by_status(client, manager):
    manager.add_task("Pending task")
    manager.set_done(manager.add_task("Done task").id, True)

    pending_page = client.get("/?status=pending").data
    done_page = client.get("/?status=done").data

    assert b"Pending task" in pending_page and b"Done task" not in pending_page
    assert b"Done task" in done_page and b"Pending task" not in done_page


def test_unknown_status_falls_back_to_all(client):
    assert client.get("/?status=bogus").status_code == 200


def test_toggle_task_keeps_current_filter(client, manager):
    task = manager.add_task("Buy milk")

    response = client.post(f"/tasks/{task.id}/toggle", data={"status": "pending"})

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/?status=pending")
    assert manager.get_task(task.id).done is True


def test_edit_task(client, manager):
    task = manager.add_task("Buy milk")

    assert b'value="Buy milk"' in client.get(f"/tasks/{task.id}/edit").data
    client.post(
        f"/tasks/{task.id}/edit", data={"title": "Buy bread", "priority": "low"}
    )

    updated = manager.get_task(task.id)
    assert (updated.title, updated.priority) == ("Buy bread", "low")


def test_edit_task_with_invalid_data_shows_error(client, manager):
    task = manager.add_task("Buy milk")

    response = client.post(
        f"/tasks/{task.id}/edit", data={"title": "", "priority": "medium"}
    )

    assert response.status_code == 400
    assert b"Title cannot be empty." in response.data
    assert manager.get_task(task.id).title == "Buy milk"


def test_delete_task(client, manager):
    task = manager.add_task("Buy milk")

    response = client.post(f"/tasks/{task.id}/delete", follow_redirects=True)

    assert b"Task &#34;Buy milk&#34; deleted." in response.data
    assert manager.list_tasks() == []


def test_unknown_task_redirects_with_error(client):
    response = client.post("/tasks/42/toggle", follow_redirects=True)

    assert response.status_code == 200
    assert b"Task 42 not found." in response.data


def test_task_titles_are_html_escaped(client, manager):
    manager.add_task("<script>alert(1)</script>")

    page = client.get("/").data

    assert b"<script>alert(1)</script>" not in page
    assert b"&lt;script&gt;" in page


def test_corrupted_database_warning_is_shown(db_path):
    db_path.write_text("not a database")
    client = create_app(db_path).test_client()

    assert b"was corrupted" in client.get("/").data


def test_stylesheet_assets_are_served(client):
    css = client.get("/static/style.css").get_data(as_text=True)
    urls = re.findall(r'url\("([^"]+)"\)', css)

    assert urls, "expected the stylesheet to reference font files"
    for url in urls:
        assert client.get(f"/static/{url}").status_code == 200, url
