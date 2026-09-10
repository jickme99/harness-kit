# harness-kit 2026.09 — reference tool, proven in the origin project's harness.
"""Fingerprint a kit's files, and later tell which of them a project still has untouched.

Live. Every kit release writes `kit-manifest.json` with a `kit_version` (see CHANGELOG.md).
A stamped project carries a copy of that stamp; `classify` is how an upgrade tells which
files it may regenerate. That question is the whole reason a kit is hard: the files a
project never touched can be regenerated freely, and the files it customised are the ones
an upgrade must not quietly overwrite. Nothing tells the two apart after the fact except
a fingerprint taken before. Poll for *whether* to upgrade from CHANGELOG.md
(`spec/versioning.md`); use this tool for *which files* in this tree.

    # in the kit's own checkout: fingerprint the files the kit ships
    python reference/tools/kit_manifest.py generate --list kit-files.txt --root . --version 2026.09.4 --out kit-manifest.json

    # in a project that installed the kit: which files are still the kit's?
    python scripts/kit_manifest.py classify --manifest kit-manifest.json --root .

`generate` reads a LIST FILE (one kit-relative path per line, `#` comments and blank lines
ignored) rather than globbing a tree: what belongs to the kit is a decision, and a glob would
silently adopt whatever happened to be sitting in the directory.

`classify` puts every manifest file in exactly one bucket:

  **unmodified** — present, and its content hashes to the manifest's value. THESE are what an
      upgrade pull request may regenerate in place. The output says so in words, because a
      list of file names with no statement of what may be done to them is exactly the kind of
      instrument that gets read wrong once and then trusted forever.
  **customized** — present, and its content differs. An upgrade must leave these alone, or
      surface them as conflicts for a human. Never rewrite one silently.
  **missing** — not present. Deleted deliberately, or never installed. An upgrade must not
      silently restore a file someone removed on purpose.

**Deterministic:** sorted keys, no timestamps, no host paths in the output. Same tree in, same
bytes out — a manifest is meant to be committed and diffed.

**Line endings are normalised (CRLF -> LF) before hashing**, and that is a decision rather
than an oversight: a Windows checkout of an untouched file is not a customisation, and a tool
that called it one would report a project's whole kit as customised on the first clone. An
edit that consists ONLY of changing line endings is therefore invisible here, which is the
trade taken deliberately.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

#: Said in the classify output itself, not only in this docstring. The upgrade path reads the
#: JSON; the person deciding whether to trust it reads this sentence.
UNMODIFIED_MEANING = (
    "the `unmodified` files are byte-identical to the kit and are what an upgrade pull "
    "request may regenerate in place; `customized` files carry local edits and an upgrade "
    "must leave them alone or raise them as conflicts; `missing` files are absent and must "
    "not be silently restored."
)


class KitError(RuntimeError):
    """The manifest or the tree cannot be read as what it claims to be."""


def digest(path: pathlib.Path) -> str:
    """sha256 of a file's content with CRLF normalised to LF. See the module docstring."""
    try:
        data = path.read_bytes()
    except OSError as e:
        raise KitError(f"cannot read {path}: {e}") from e
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def read_list(list_file: pathlib.Path) -> list[str]:
    """The kit's file list: one repo-relative path per line, `#` comments, blanks ignored."""
    if not list_file.exists():
        raise KitError(f"kit file list {list_file} does not exist - the kit's membership is "
                       "a decision that has to be written down somewhere")
    out: list[str] = []
    seen: set[str] = set()
    for n, raw in enumerate(list_file.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # `lstrip("./")` would be wrong here and quietly so: it strips a CHARACTER SET, so
        # `../outside.md` becomes `outside.md` and a traversal reads as an ordinary member.
        norm = line.replace("\\", "/")
        while norm.startswith("./"):
            norm = norm[2:]
        if norm.startswith("/") or ".." in norm.split("/"):
            raise KitError(f"{list_file} line {n}: kit paths are relative and may not "
                           "escape the root")
        if norm in seen:
            raise KitError(f"{list_file} line {n}: {norm} is listed twice")
        seen.add(norm)
        out.append(norm)
    if not out:
        raise KitError(f"{list_file} names no files - refusing to write an empty manifest, "
                       "which would classify every project as fully customised")
    return sorted(out)


def generate(list_file: pathlib.Path, root: pathlib.Path, version: str) -> dict:
    """`{kit_version, files: {path: sha256}}` for every path the list names."""
    if not version.strip():
        raise KitError("a manifest needs a kit version string - an unversioned manifest "
                       "cannot say which upgrade it is the baseline for")
    paths = read_list(list_file)
    files: dict[str, str] = {}
    for rel in paths:
        full = root / rel
        if not full.is_file():
            raise KitError(f"{rel} is named by the kit file list but is not a file under "
                           f"{root} - a manifest that skipped it would ship a kit missing a "
                           "file nobody noticed")
        files[rel] = digest(full)
    return {"files": files, "kit_version": version.strip()}


def classify(manifest: dict, root: pathlib.Path) -> dict:
    """Each manifest file as unmodified / customized / missing, plus the three lists."""
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), dict):
        raise KitError("manifest has no `files` mapping - refusing to classify a project "
                       "against a manifest that states nothing")
    files = manifest["files"]
    if not files:
        raise KitError("manifest lists no files - every project would read as fully "
                       "customised, which is a silent wrong answer, not an empty one")
    version = manifest.get("kit_version")
    if not version:
        raise KitError("manifest has no `kit_version` - a classification that cannot name "
                       "its baseline is not evidence for anything")
    status: dict[str, str] = {}
    for rel, expected in sorted(files.items()):
        if not isinstance(expected, str) or len(expected) != 64:
            raise KitError(f"manifest entry {rel} is not a sha256 hex digest")
        full = root / rel
        if not full.exists():
            status[rel] = "missing"
        elif not full.is_file():
            raise KitError(f"{rel} exists under {root} but is not a file - the tree does "
                           "not have the shape the manifest describes")
        else:
            status[rel] = "unmodified" if digest(full) == expected else "customized"
    return {
        "customized": sorted(k for k, v in status.items() if v == "customized"),
        "files": status,
        "kit_version": version,
        "missing": sorted(k for k, v in status.items() if v == "missing"),
        "note": UNMODIFIED_MEANING,
        "unmodified": sorted(k for k, v in status.items() if v == "unmodified"),
    }


def canonical(payload: dict) -> str:
    """The bytes a manifest is committed as: sorted keys, two-space indent, one newline."""
    return json.dumps(payload, sort_keys=True, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="mode", required=True)

    g = sub.add_parser("generate", help="fingerprint the kit's files into a manifest")
    g.add_argument("--list", dest="list_file", type=pathlib.Path, required=True,
                   help="the kit file list: one kit-relative path per line")
    g.add_argument("--root", type=pathlib.Path, default=pathlib.Path("."),
                   help="the kit checkout the listed paths are relative to")
    g.add_argument("--version", required=True, help="the kit version this manifest baselines")
    g.add_argument("--out", type=pathlib.Path, help="write here instead of stdout")

    c = sub.add_parser("classify", help="unmodified / customized / missing, per kit file")
    c.add_argument("--manifest", type=pathlib.Path, required=True)
    c.add_argument("--root", type=pathlib.Path, default=pathlib.Path("."),
                   help="the project tree the kit was installed into")
    c.add_argument("--out", type=pathlib.Path, help="write here instead of stdout")

    args = ap.parse_args(argv)
    try:
        if args.mode == "generate":
            payload = generate(args.list_file, args.root, args.version)
        else:
            if not args.manifest.exists():
                raise KitError(f"manifest {args.manifest} does not exist")
            try:
                manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                raise KitError(f"manifest {args.manifest} is not valid JSON: {e}") from e
            payload = classify(manifest, args.root)
    except KitError as e:
        print(f"kit-manifest: FAILED\n{e}", file=sys.stderr)
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
