"""Build the static GitHub Pages demo into _site/.

The demo reuses the Flask app's stylesheet, so it is copied here instead of
being duplicated in the repository.

Usage (from the project root):
    python scripts/build_demo.py
    python -m http.server --directory _site   # preview at http://localhost:8000
"""

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = PROJECT_ROOT / "demo"
STYLESHEET = PROJECT_ROOT / "task_manager" / "web" / "static" / "style.css"
SITE_DIR = PROJECT_ROOT / "_site"


def main() -> None:
    shutil.rmtree(SITE_DIR, ignore_errors=True)
    shutil.copytree(DEMO_DIR, SITE_DIR)
    shutil.copy2(STYLESHEET, SITE_DIR / "style.css")
    print(f"Demo built in {SITE_DIR.relative_to(PROJECT_ROOT)}/")


if __name__ == "__main__":
    main()
