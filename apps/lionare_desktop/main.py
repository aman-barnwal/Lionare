from __future__ import annotations

import sys
from pathlib import Path

# Support both `python -m apps.lionare_desktop.main` and direct file execution.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from apps.lionare_desktop.app import run
except ImportError:
    from app import run  # type: ignore


if __name__ == "__main__":
    raise SystemExit(run())
