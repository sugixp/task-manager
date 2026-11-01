"""Regenerate the README screenshots of the web interface.

Usage (from the project root):
    pip install -r requirements-e2e.txt
    python -m playwright install chromium
    python scripts/screenshot.py

Uses a temporary database filled with sample tasks, so your own tasks.db
is never touched.
"""

from __future__ import annotations

import sys
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from task_manager.core import TaskManager  # noqa: E402
from task_manager.web.app import create_app  # noqa: E402

DOCS_DIR = PROJECT_ROOT / "docs"

SAMPLE_TASKS = [
    # (title, priority, done)
    ("Update portfolio with the new web UI", "high", False),
    ("Prepare for the technical interview", "high", False),
    ("Plan next sprint", "medium", False),
    ("Read Fluent Python, chapter 5", "low", False),
    ("Write unit tests for the core", "high", True),
    ("Review pull requests", "medium", True),
]

SHOTS = [
    # (file name, viewport, extra browser-context options)
    ("screenshot.png", {"width": 1280, "height": 800}, {}),
    (
        "screenshot-mobile.png",
        {"width": 390, "height": 844},
        {"is_mobile": True, "has_touch": True},
    ),
]


def seed(db_path: Path) -> None:
    manager = TaskManager(db_path)
    for title, priority, done in SAMPLE_TASKS:
        task = manager.add_task(title, priority)
        if done:
            manager.set_done(task.id, True)


def main() -> None:
    DOCS_DIR.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "screenshot.db"
        seed(db_path)

        # Port 0 lets the OS pick a free port.
        server = make_server("127.0.0.1", 0, create_app(db_path))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{server.server_port}/"

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                for file_name, viewport, options in SHOTS:
                    context = browser.new_context(
                        viewport=viewport,
                        device_scale_factor=2,
                        color_scheme="light",
                        **options,
                    )
                    page = context.new_page()
                    page.goto(url)
                    # Remove the autofocus ring so the capture looks idle.
                    page.evaluate("document.activeElement.blur()")
                    page.screenshot(path=DOCS_DIR / file_name)
                    context.close()
                    print(f"Saved docs/{file_name}")
                browser.close()
        finally:
            server.shutdown()


if __name__ == "__main__":
    main()
