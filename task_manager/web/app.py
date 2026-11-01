"""Web interface. Run with: python -m task_manager.web.app

Debug mode is off by default; set FLASK_DEBUG=1 to enable it locally.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for

from ..core import (
    DEFAULT_PRIORITY,
    PRIORITIES,
    STATUS_FILTERS,
    TaskManager,
    TaskNotFoundError,
    ValidationError,
)


def create_app(db_path: str | Path | None = None) -> Flask:
    app = Flask(__name__)
    # Only used to sign the session cookie that carries flash messages.
    app.secret_key = os.environ.get("TASK_MANAGER_SECRET_KEY") or secrets.token_hex(16)
    manager = TaskManager(db_path)

    startup_warnings = []
    if manager.recovered_from:
        startup_warnings.append(
            "The database file was corrupted and has been moved to "
            f"{manager.recovered_from.name}. Starting with an empty task list."
        )

    @app.before_request
    def show_startup_warnings():
        while startup_warnings:
            flash(startup_warnings.pop(), "error")

    def status_from(values) -> str:
        status = values.get("status", "all")
        return status if status in STATUS_FILTERS else "all"

    def render_index(status, form=None, error=None, code=200):
        page = render_template(
            "index.html",
            tasks=manager.list_tasks(status),
            counts=manager.count_tasks(),
            status=status,
            priorities=PRIORITIES,
            form=form or {"title": "", "priority": DEFAULT_PRIORITY},
            error=error,
        )
        return page, code

    @app.get("/")
    def index():
        return render_index(status_from(request.args))

    @app.post("/tasks")
    def add_task():
        status = status_from(request.form)
        form = {
            "title": request.form.get("title", ""),
            "priority": request.form.get("priority", DEFAULT_PRIORITY),
        }
        try:
            task = manager.add_task(form["title"], form["priority"])
        except ValidationError as error:
            return render_index(status, form=form, error=str(error), code=400)
        flash(f'Task "{task.title}" added.', "success")
        # A new task is pending, so don't send the user back to the "done" view.
        return redirect(url_for("index", status="all" if status == "done" else status))

    @app.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
    def edit_task(task_id):
        task = manager.get_task(task_id)
        status = status_from(request.values)
        if request.method == "GET":
            form = {"title": task.title, "priority": task.priority}
            return render_template(
                "edit.html", task=task, form=form, status=status,
                priorities=PRIORITIES, error=None,
            )

        form = {
            "title": request.form.get("title", ""),
            "priority": request.form.get("priority", ""),
        }
        try:
            manager.update_task(task_id, form["title"], form["priority"])
        except ValidationError as error:
            page = render_template(
                "edit.html", task=task, form=form, status=status,
                priorities=PRIORITIES, error=str(error),
            )
            return page, 400
        flash("Task updated.", "success")
        return redirect(url_for("index", status=status))

    @app.post("/tasks/<int:task_id>/toggle")
    def toggle_task(task_id):
        manager.toggle_done(task_id)
        return redirect(url_for("index", status=status_from(request.form)))

    @app.post("/tasks/<int:task_id>/delete")
    def delete_task(task_id):
        task = manager.get_task(task_id)
        manager.delete_task(task_id)
        flash(f'Task "{task.title}" deleted.', "success")
        return redirect(url_for("index", status=status_from(request.form)))

    @app.errorhandler(TaskNotFoundError)
    def task_not_found(error):
        flash(str(error), "error")
        return redirect(url_for("index"))

    return app


if __name__ == "__main__":
    create_app().run()
