# harness-kit 2026.09 — poll the kit from a stamped project.
"""Build a kit-upgrade worklist. Never copy files.

A project with no `kit-manifest.json` cannot poll. Point `--kit` at a clone of
harness-kit (private: raw GitHub URLs 404). This tool reads local files only —
fetch is the operator's job.

    python scripts/kit_poll.py --project . --kit /path/to/harness-kit

Output is JSON: changelog sections at or above the stamp's `kit_version`, membership
drift mapped through STANDUP, and `classify` of the project stamp against this tree.
**Applies to** is a hint. Unknown or unchecked values stay on the worklist (`consider:
true`, `skip: false`). Same-version sections stay on the worklist. Never self-apply —
the project Merge gate is the activation.

Membership mapping is parsed from STANDUP.md (plus any extra `--map-from` files).
A second mapping table here would go stale the same way a skip-allowlist would.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

_TOOLS = pathlib.Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))
from kit_manifest import KitError, canonical, classify, read_list

#: `YYYY.MM` or `YYYY.MM.N`
_VERSION = re.compile(r"^(\d{4})\.(\d{2})(?:\.(\d+))?$")
_HEADING = re.compile(r"^##\s+(\d{4}\.\d{2}(?:\.\d+)?)\b(.*)$")
_COPY_ARROW = re.compile(r"`([^`]+)`\s*→\s*(?:[^`\n]{0,120})?`([^`]+)`")
_APPLIES = re.compile(r"\*\*Applies to:\*\*\s*(.+)")
_LANE = re.compile(r"\*\*Lane:\*\*\s*(.+)")

NEVER_SELF_APPLY = (
    "propose a project PR through the project's Merge gate; never copy files from "
    "this output; declining an entry is kit feedback, not a silent skip"
)


def parse_version(text: str) -> tuple[int, int, int]:
    """`YYYY.MM` counts as `YYYY.MM.0`. Refuse anything else — fail closed on version."""
    m = _VERSION.fullmatch(text.strip())
    if not m:
        raise KitError(f"not a kit version: {text!r} (expected YYYY.MM or YYYY.MM.N)")
    return int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)


def parse_changelog(text: str) -> list[dict]:
    """Each `## YYYY.MM` / `## YYYY.MM.N` section, in file order."""
    sections: list[dict] = []
    current: dict | None = None
    body: list[str] = []
    for line in text.splitlines():
        head = _HEADING.match(line)
        if head:
            if current is not None:
                current["body"] = "\n".join(body).strip()
                sections.append(current)
            current = {
                "version": head.group(1),
                "heading": line.strip(),
                "rest": head.group(2).strip().lstrip("—- ").strip(),
            }
            body = []
            continue
        if current is not None:
            body.append(line)
    if current is not None:
        current["body"] = "\n".join(body).strip()
        sections.append(current)
    if not sections:
        raise KitError("CHANGELOG.md has no `## YYYY.MM` sections — nothing to poll")
    return sections


def worklist(local_version: str, sections: list[dict]) -> list[dict]:
    """Sections at or above local. Same-version stays. Older are out of scope.

    Applies-to is recorded, never used to drop a row. Skip is always false here;
    a skip is a recorded human decision, not a tool inference.
    """
    local = parse_version(local_version)
    out: list[dict] = []
    for sec in sections:
        ver = parse_version(sec["version"])
        if ver < local:
            continue
        body = sec.get("body") or ""
        applies = _APPLIES.search(body)
        lane = _LANE.search(body)
        out.append({
            "applies_to": applies.group(1).strip() if applies else None,
            "consider": True,
            "heading": sec["heading"],
            "lane": lane.group(1).strip() if lane else None,
            "same_version": ver == local,
            "skip": False,
            "version": sec["version"],
        })
    return out


def copy_rules(text: str) -> list[tuple[str, str]]:
    """`(kit_src, project_dest)` arrows from STANDUP / adapter prose.

    Longer sources first so a file rule wins over a directory prefix.
    """
    rules = [(src.strip(), dest.strip()) for src, dest in _COPY_ARROW.findall(text)]
    return sorted(rules, key=lambda r: len(r[0]), reverse=True)


def _norm(rel: str) -> str:
    return rel.replace("\\", "/").strip()


def map_kit_path(kit_path: str, rules: list[tuple[str, str]]) -> str | None:
    """Project destination for a kit path, or None (kit-repo-only)."""
    kit_path = _norm(kit_path)
    for src, dest in rules:
        src_n = _norm(src)
        dest_n = _norm(dest)
        mapped = _apply_rule(kit_path, src_n, dest_n)
        if mapped is not None:
            return mapped
    return None


def _join_dest(dest: str, rest: str) -> str:
    return f"{dest.rstrip('/')}/{rest.lstrip('/')}"


def _apply_rule(kit_path: str, src: str, dest: str) -> str | None:
    if src.endswith("*.py"):
        prefix = src.removesuffix("*.py")  # keep the slash in `dir/*.py`
        if kit_path.startswith(prefix) and kit_path.endswith(".py"):
            return _join_dest(dest, kit_path[len(prefix):])
        return None
    if src.endswith("/"):
        dir_only = src.rstrip("/")
        prefix = dir_only + "/"
        if kit_path == dir_only or kit_path == prefix:
            return dest.rstrip("/")
        if kit_path.startswith(prefix):
            return _join_dest(dest, kit_path[len(prefix):])
        return None
    if kit_path != src:
        return None
    if dest.endswith("/"):
        return _join_dest(dest, pathlib.Path(kit_path).name)
    return dest


def membership_drift(kit_files: list[str], stamp_files: list[str],
                     rules: list[tuple[str, str]]) -> dict:
    """STANDUP-mapped kit paths vs the project's stamp keys."""
    mapped: dict[str, str] = {}
    kit_repo_only: list[str] = []
    for kit in kit_files:
        dest = map_kit_path(kit, rules)
        if dest is None:
            kit_repo_only.append(kit)
        else:
            mapped[kit] = dest
    stamp = set(stamp_files)
    dests = set(mapped.values())
    new_members = [
        {"kit": k, "project": d}
        for k, d in sorted(mapped.items())
        if d not in stamp
    ]
    project_only = sorted(p for p in stamp if p not in dests)
    return {
        "kit_repo_only": sorted(kit_repo_only),
        "mapped": mapped,
        "new_members": new_members,
        "project_only": project_only,
    }


def _read_json(path: pathlib.Path, what: str) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise KitError(f"{what} is not valid JSON: {e}") from e


def map_source_texts(kit: pathlib.Path,
                     map_from: list[pathlib.Path] | None = None) -> str:
    """STANDUP plus adapter docs (the versioning map), then any --map-from extras."""
    standup = kit / "STANDUP.md"
    if not standup.is_file():
        raise KitError(f"{standup} does not exist — STANDUP.md is the membership map")
    parts = [standup.read_text(encoding="utf-8")]
    adapters = kit / "adapters"
    if adapters.is_dir():
        parts.extend(p.read_text(encoding="utf-8")
                     for p in sorted(adapters.glob("*.md")) if p.is_file())
    for extra in map_from or ():
        if not extra.is_file():
            raise KitError(f"--map-from {extra} does not exist")
        parts.append(extra.read_text(encoding="utf-8"))
    return "\n".join(parts)


def poll(project: pathlib.Path, kit: pathlib.Path,
         map_from: list[pathlib.Path] | None = None) -> dict:
    """Facts for one poll. Raises KitError instead of inventing a version or a skip."""
    stamp_path = project / "kit-manifest.json"
    if not stamp_path.is_file():
        raise KitError("project has no kit-manifest.json — stamp first (STANDUP.md step 5)")
    stamp = _read_json(stamp_path, "project kit-manifest.json")
    local = stamp.get("kit_version")
    if not isinstance(local, str) or not local.strip():
        raise KitError("project stamp has no kit_version")
    parse_version(local)  # fail closed before building a worklist

    changelog_path = kit / "CHANGELOG.md"
    if not changelog_path.is_file():
        raise KitError(f"{changelog_path} does not exist — point --kit at a harness-kit clone")
    kit_manifest_path = kit / "kit-manifest.json"
    kit_version = None
    if kit_manifest_path.is_file():
        kit_version = _read_json(kit_manifest_path, "kit kit-manifest.json").get("kit_version")

    rows = worklist(local, parse_changelog(changelog_path.read_text(encoding="utf-8")))
    rules = copy_rules(map_source_texts(kit, map_from))
    kit_list = kit / "kit-files.txt"
    kit_files = read_list(kit_list)
    files = stamp.get("files")
    stamp_files = list(files) if isinstance(files, dict) else []
    drift = membership_drift(kit_files, stamp_files, rules)

    return {
        "classify": classify(stamp, project),
        "kit_version": kit_version,
        "local_version": local,
        "membership": {
            "kit_repo_only": drift["kit_repo_only"],
            "new_members": drift["new_members"],
            "project_only": drift["project_only"],
        },
        "never_self_apply": True,
        "note": NEVER_SELF_APPLY,
        "worklist": rows,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", type=pathlib.Path, required=True,
                    help="stamped project checkout (must contain kit-manifest.json)")
    ap.add_argument("--kit", type=pathlib.Path, required=True,
                    help="harness-kit clone (CHANGELOG.md, STANDUP.md, kit-files.txt)")
    ap.add_argument("--map-from", type=pathlib.Path, action="append", dest="map_from",
                    help="extra prose to parse for copy arrows (adapter docs); repeatable")
    ap.add_argument("--out", type=pathlib.Path, help="write JSON here instead of stdout")
    args = ap.parse_args(argv)
    try:
        payload = poll(args.project, args.kit, args.map_from)
    except KitError as e:
        print(f"kit-poll: FAILED\n{e}", file=sys.stderr)
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
