# harness-kit 2026.09 — offer project customizations back to the kit.
"""Proposal-only harvest from a STAMPED project. Never copies files into the kit.

    python scripts/kit_harvest.py --project . --kit /path/to/harness-kit

Reports:
  **customized** — stamp members whose content drifted; reverse-mapped to the kit
    path when STANDUP has one. These are the files a kit PR might take a pattern from.
  **extra** — files under scripts/, .cursor/, or .claude/ that are not in the stamp
    and are not a mapped kit dest. Product trees (app/, tests/ beyond kit contracts)
    are out of scope — that would be a glob.

Activation is a kit PR through the kit Merge gate. Declining is recorded feedback.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

_TOOLS = pathlib.Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
from kit_manifest import KitError, canonical, classify
from kit_poll import install_map

EXTRA_PREFIXES = ("scripts/", ".cursor/", ".claude/")
SKIP_NAMES = {"cursor-hook-debug.jsonl"}
EXTRA_REASON = (
    "present under a harness dir, not in the stamp, not a mapped kit dest"
)
OFFER = "pattern or conflict — do not copy bytes into the kit without Accept"
HARVEST_NOTE = (
    "propose a kit PR; never copy from this output into the kit. "
    "Origin paths, env names, and denylists stay in the project"
)


def _skip_extra(path: pathlib.Path) -> bool:
    return (
        not path.is_file()
        or path.name in SKIP_NAMES
        or path.suffix == ".pyc"
        or "__pycache__" in path.parts
    )


def extra_files(project: pathlib.Path, stamp_files: set[str],
                mapped_dests: set[str]) -> list[dict]:
    """Harness-adjacent files the stamp does not name. Bounded dirs, not a tree glob."""
    known = stamp_files | mapped_dests
    out: list[dict] = []
    for prefix in EXTRA_PREFIXES:
        root = project / prefix.rstrip("/")
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if _skip_extra(path):
                continue
            rel = path.relative_to(project).as_posix()
            if rel in known:
                continue
            out.append({"project": rel, "reason": EXTRA_REASON})
    return sorted(out, key=lambda r: r["project"])


def harvest(project: pathlib.Path, kit: pathlib.Path,
            map_from: list[pathlib.Path] | None = None) -> dict:
    stamp_path = project / "kit-manifest.json"
    if not stamp_path.is_file():
        raise KitError("project has no kit-manifest.json — stamp first (kit_stamp.py)")
    mapping = install_map(project, kit, map_from)
    try:
        stamp = json.loads(stamp_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise KitError(f"project kit-manifest.json is not valid JSON: {e}") from e
    classified = classify(stamp, project)
    reverse = mapping["reverse"]
    customized = [
        {"project": rel, "kit": reverse.get(rel), "offer": OFFER}
        for rel in classified["customized"]
    ]
    mapped_dests = {
        row["project"] for row in mapping["present"] + mapping["absent"]
    }
    return {
        "customized": customized,
        "extra": extra_files(project, set(classified["files"]), mapped_dests),
        "kit_version": mapping["kit_version"],
        "local_version": classified["kit_version"],
        "never_self_apply": True,
        "note": HARVEST_NOTE,
        "unmodified_count": len(classified["unmodified"]),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", type=pathlib.Path, required=True)
    ap.add_argument("--kit", type=pathlib.Path, required=True)
    ap.add_argument("--map-from", type=pathlib.Path, action="append", dest="map_from")
    ap.add_argument("--out", type=pathlib.Path)
    args = ap.parse_args(argv)
    try:
        payload = harvest(args.project, args.kit, args.map_from)
    except KitError as e:
        print(f"kit-harvest: FAILED\n{e}", file=sys.stderr)
        return 1
    text = canonical(payload)
    if args.out:
        args.out.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
