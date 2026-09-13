# harness-kit 2026.09.7 — pytest path for keeping-current tests.
"""Put `infra/` and `app/` on sys.path whether these tests run in the kit
(`reference/keeping-current/tests/`) or after STANDUP copies them to a project's
`tests/` (parent = project root, where `infra/` was installed).
"""
from __future__ import annotations

import sys
import pathlib

_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
