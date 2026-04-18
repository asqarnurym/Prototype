"""Shared bootstrap helpers for evaluation scripts."""

from __future__ import annotations

import sys
from pathlib import Path

EVALUATION_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EVALUATION_DIR.parents[1]


def ensure_project_root_on_path() -> Path:
    """Make repo-root imports work for direct script execution."""
    root_str = str(PROJECT_ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return PROJECT_ROOT
