"""Build the static GitHub Pages demo into _site/.

The demo reuses the Flask app's stylesheet and fonts, so they are copied here
instead of being duplicated in the repository.

Usage (from the project root):
    python scripts/build_demo.py
    python -m http.server --directory _site   # preview at http://localhost:8000
"""

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = PROJECT_ROOT / "demo"
STATIC_DIR = PROJECT_ROOT / "task_manager" / "web" / "static"
SITE_DIR = PROJECT_ROOT / "_site"


def main() -> None:
    shutil.rmtree(SITE_DIR, ignore_errors=True)
    shutil.copytree(DEMO_DIR, SITE_DIR)
    shutil.copy2(STATIC_DIR / "style.css", SITE_DIR / "style.css")
    shutil.copytree(STATIC_DIR / "fonts", SITE_DIR / "fonts")  # used by style.css
    print(f"Demo built in {SITE_DIR.relative_to(PROJECT_ROOT)}/")


if __name__ == "__main__":
    main()
