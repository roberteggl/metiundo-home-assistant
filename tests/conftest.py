"""Shared test configuration."""

from __future__ import annotations

from pathlib import Path
import sys

import custom_components

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

COMPONENTS_PATH = str(PROJECT_ROOT / "custom_components")
if COMPONENTS_PATH not in custom_components.__path__:
    custom_components.__path__.insert(0, COMPONENTS_PATH)
