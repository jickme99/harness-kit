# harness-kit 2026.09 — stamp a project from STANDUP mapping.
"""Fingerprint the kit dests that actually exist in this tree.

This is the one stamp method. New projects and the origin consumer run the same
command. Membership is STANDUP+adapter mapping of the kit's `kit-files.txt`,
restricted to files present here — never a glob of the project.

    python scripts/kit_stamp.py --project . --kit /path/to/harness-kit

Writes `kit-files.txt` (project paths) and `kit-manifest.json` (hashes + kit_version).
Refuses to overwrite an existing stamp unless `--refresh`. Does not copy kit files
into the project — install is STANDUP; this only fingerprints what you already
installed. `kit-manifest.json` is the output, not a member of the list.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

_TOOLS = pathlib.Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
from kit_manifest import KitError, canonical, generate
from kit_poll import install_map

LIST_HEADER = (
    "# kit membership for this project. THIS LIST IS A DECISION, NOT A GLOB:\n"
    "# produced by kit_stamp.py from STANDUP+adapter mapping. Only dests that\n"
    "# exist in this tree are named. kit-manifest.json is the fingerprint and\n"
    "# is deliberately not listed. Refresh:\n"
    "#   python scripts/kit_stamp.py --project . --kit <harness-kit> --refresh\n"
)
STAMP_NOTE = (
    "stamp fingerprints dests that exist; it does not copy kit files. "
    "poll for upgrades; harvest to offer customized files back to the kit"
)


def _map_report(mapping: dict) -> dict:
    """The install_map fields stamp reports. Dry-run is this plus dry_run=True."""
    return {
        "absent": mapping["absent"],
        "kit_version": mapping["kit_version"],
        "kit_repo_only": mapping["kit_repo_only"],
        "present": mapping["present"],
    }


def stamp(project: pathlib.Path, kit: pathlib.Path, *,
          refresh: bool = False,
          map_from: list[pathlib.Path] | None = None) -> dict:
    """Write the stamp, or raise. Returns the JSON facts (including counts)."""
    mapping = install_map(project, kit, map_from)
    dests = sorted({row["project"] for row in mapping["present"]})
    if not dests:
        raise KitError(
            "no mapped kit dests exist in this project — copy files per STANDUP.md "
            "before stamping"
        )
    list_path = project / "kit-files.txt"
    manifest_path = project / "kit-manifest.json"
    if (list_path.exists() or manifest_path.exists()) and not refresh:
        raise KitError(
            "project already has kit-files.txt or kit-manifest.json — pass "
            "--refresh to rebuild the stamp from the current tree"
        )
    list_path.write_text(
        LIST_HEADER + "\n".join(dests) + "\n", encoding="utf-8", newline="\n")
    manifest = generate(list_path, project, mapping["kit_version"])
    manifest_path.write_text(canonical(manifest), encoding="utf-8", newline="\n")
    return {
        **_map_report(mapping),
        "never_self_apply": True,
        "note": STAMP_NOTE,
        "stamped": dests,
        "wrote": ["kit-files.txt", "kit-manifest.json"],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", type=pathlib.Path, required=True)
    ap.add_argument("--kit", type=pathlib.Path, required=True)
    ap.add_argument("--refresh", action="store_true",
                    help="rebuild an existing stamp from the current tree")
    ap.add_argument("--map-from", type=pathlib.Path, action="append", dest="map_from")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the plan; do not write kit-files.txt or the manifest")
    args = ap.parse_args(argv)
    try:
        if args.dry_run:
            payload = {
                **_map_report(install_map(args.project, args.kit, args.map_from)),
                "dry_run": True,
            }
        else:
            payload = stamp(args.project, args.kit, refresh=args.refresh,
                            map_from=args.map_from)
    except KitError as e:
        print(f"kit-stamp: FAILED\n{e}", file=sys.stderr)
        return 1
    sys.stdout.write(canonical(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
