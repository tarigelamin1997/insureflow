"""pytest path bootstrap for the seed-generator unit tests.

The seed generator is the package `02-source-systems/seed`. Because the phase directory name
(`02-source-systems`) is not a legal dotted-module path, the tests import the package as
`seed.*`; this conftest puts `02-source-systems/` on sys.path so that import resolves when
pytest is invoked from the repo root.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PHASE_DIR = Path(__file__).resolve().parents[2]  # .../02-source-systems
if str(_PHASE_DIR) not in sys.path:
    sys.path.insert(0, str(_PHASE_DIR))
