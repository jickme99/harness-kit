"""No package manager in a runtime image — the guard on the Dockerfile itself.

Every `Dockerfile*` at the root of this repository must end its build by removing pip and PROVING it
is gone: scanners read pip's vendored libraries as packages of the image, and no dependency of ours can
move a library pip vendors (the first live freshness job went RED on exactly that on
2026-09-11; security playbook section 3). The block is checked AFTER the last `pip install`, because a
removal that runs before an install is a removal that never happened.

Fails if a Dockerfile has no such block, if the block sits before the last install, or if any one of
the three proofs (import, launcher, filesystem) has been dropped from it.
"""
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCKERFILES = sorted(p for p in ROOT.glob("Dockerfile*") if p.is_file())
PROOFS = {
    "the uninstall": "python3 -m pip uninstall -y pip",
    "the import check": '! python3 -c "import pip"',
    "the launcher check": "command -v pip pip3",
    "the filesystem check": "site-packages/pip-*.dist-info",
}


def test_the_runtime_image_removes_pip_and_proves_it():
    if not DOCKERFILES:
        kit_factory = (ROOT / "templates" / "freshness.yml").is_file()
        if not kit_factory:
            pytest.fail("this tree copied the keeping-current tests but has no Dockerfile* "
                        "at the root — a container project must have one; skipping here "
                        "would hide an image that still ships pip")
        pytest.skip("no Dockerfile in this tree — the kit factory has none")
    for dockerfile in DOCKERFILES:
        text = dockerfile.read_text(encoding="utf-8")
        installs = [m.end() for m in re.finditer(r"pip install", text)]
        tail = text[max(installs):] if installs else text
        missing = [name for name, needle in PROOFS.items() if needle not in tail]
        assert not missing, (f"{dockerfile.name}: after its last `pip install` the build does not carry "
                             f"{', '.join(missing)} — the image would ship with pip (and pip's vendored libraries) in it.")
