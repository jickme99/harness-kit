# harness-kit 2026.09.7 — pytest path for keeping-current tests.
"""Put `infra/` and `app/` on sys.path whether these tests run in the kit
(`reference/keeping-current/tests/`) or after STANDUP copies them to a project's
`tests/` (parent = project root, where `infra/` was installed).

STANDUP copies workflows to `.github/`, not `templates/`. Tests that pin those
files must use `read_chassis`, or THE GATE fails on every container stand-up.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_GITHUB_TEMPLATES = {
    "dependabot.yml": ROOT / ".github" / "dependabot.yml",
    "CODEOWNERS": ROOT / ".github" / "CODEOWNERS",
}


def chassis_file(*rel):
    """Kit: `templates/` / `infra/` next to these tests. Stamp: `.github/` and `infra/`."""
    direct = ROOT.joinpath(*rel)
    if direct.is_file():
        return direct
    if rel and rel[0] == "templates":
        mapped = _GITHUB_TEMPLATES.get(rel[-1], ROOT / ".github" / "workflows" / rel[-1])
        if mapped.is_file():
            return mapped
    return None


@pytest.fixture
def read_chassis():
    def _read(*rel, optional=False):
        path = chassis_file(*rel)
        if path is None:
            if optional:
                pytest.skip(f"{'/'.join(rel)} is not installed in this tree")
            pytest.fail(
                f"{'/'.join(rel)} should exist after Question 3 copy "
                "(kit `templates/` or project `.github/`)"
            )
        return path.read_text(encoding="utf-8")
    return _read
