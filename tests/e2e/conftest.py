"""Fixtures for the end-to-end tests of the static demo.

The demo is built with scripts/build_demo.py and served from _site/ by a
local HTTP server. pytest-playwright provides a fresh browser context (and
therefore empty localStorage) for every test.
"""

import functools
import http.server
import subprocess
import sys
import threading
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SITE_DIR = PROJECT_ROOT / "_site"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="session")
def demo_url():
    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "build_demo.py")], check=True
    )
    handler = functools.partial(QuietHandler, directory=SITE_DIR)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/"
    server.shutdown()
    server.server_close()


@pytest.fixture
def demo(page, demo_url):
    """The demo page, opened fresh. Fails the test on any JavaScript error."""
    errors = []
    page.on("pageerror", lambda error: errors.append(error))
    page.goto(demo_url)
    yield page
    assert not errors, f"JavaScript errors: {errors}"
