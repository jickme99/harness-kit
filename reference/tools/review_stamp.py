# harness-kit 2026.09 — reference tool, proven in the origin project's harness.
"""Stamp the model configuration this repo is actually configured to run under.

Every review line in `reviews/ledger.jsonl` carries the tier configuration that produced it,
and this script is the ONLY sanctioned way to produce that value: it reads the `model:`
frontmatter of every file under `.claude/agents/` and the assignments table in
`docs/MODELS.md`. It never accepts a configuration anyone reports about themselves — a
session's own account of which model it ran on is exactly the claim that cannot be checked
later, and a ledger of unverifiable configurations measures nothing.

    python scripts/review_stamp.py            # canonical configuration JSON, for a ledger line
    python scripts/review_stamp.py --check    # verify files and policy agree; name any drift

Both modes fail CLOSED. A role file the table forgot, a table row naming a file that does not
exist, a model value the vendor adapter table does not list, a missing panel row, an
unparseable table — each is an error naming the thing, never a quiet pass. Consistency is a
precondition of stamping, so `--check` is the stamp with its output thrown away: a
configuration that cannot be stated unambiguously must not be recorded as if it could.

The output is deterministic: sorted keys, compact separators, no timestamps. Same repo state
in, same bytes out — which is what makes "distinct configuration" a groupable fact in
`scripts/review_rates.py` rather than an opinion.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
AGENTS = ROOT / ".claude" / "agents"
POLICY = ROOT / "docs" / "MODELS.md"

#: The panel surfaces that are declared by the policy page alone (they are not files, so
#: nothing else can declare them). All three must be present or the stamp is incomplete.
REQUIRED_PANEL = ("master-chat", "panel-lead-verify", "review-panel-lens")

#: The vendor whose adapter table the assignments are written in. One vendor per stamp: a
#: configuration spanning two vendors would need two adapter tables and is not a thing the
#: harness runs today.
VENDOR = "claude"

_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_BACKTICKED = re.compile(r"\A`([^`]+)`\Z")


class PolicyError(RuntimeError):
    """The files and docs/MODELS.md do not state one unambiguous configuration."""


# ---------------------------------------------------------------- markdown parsing

def _rows(block: list[str]) -> list[list[str]]:
    """Cells of a pipe table, header included, separator row dropped."""
    out = []
    for line in block:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", c or "") for c in cells):
            continue                                    # the |---|---| separator
        out.append(cells)
    return out


def _tables(text: str) -> list[list[list[str]]]:
    tables, block = [], []
    for line in text.splitlines():
        if line.lstrip().startswith("|"):
            block.append(line)
            continue
        if block:
            tables.append(_rows(block))
            block = []
    if block:
        tables.append(_rows(block))
    return tables


def _section(text: str, title: str) -> str:
    """The body of a `## <title>` section, up to the next `## ` heading."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip().lower() == f"## {title}".lower():
            start = i + 1
            break
    if start is None:
        raise PolicyError(f"docs/MODELS.md has no '## {title}' section - the policy page "
                          "cannot be read; refusing to stamp a configuration from a page "
                          "that does not state one")
    end = len(lines)
    for j in range(start, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return "\n".join(lines[start:end])


def _token(cell: str, what: str, where: str) -> str:
    m = _BACKTICKED.match(cell.strip())
    if not m:
        raise PolicyError(f"docs/MODELS.md {where}: {what} must be a single backticked "
                          f"token, got {cell!r}")
    return m.group(1)


# ---------------------------------------------------------------- the three readings

def role_models(agents_dir: pathlib.Path = AGENTS) -> dict[str, str]:
    """`{file stem: model}` from the role files themselves — the ground truth of what runs.

    Keyed by FILE STEM, not by the frontmatter `name:`. Keying by a field two files can
    carry the same value for made a collision silently overwrite: a role vanished from the
    stamped configuration and `--check` still exited 0, which is the one outcome a
    fail-closed checker must not have. The stem is unique by the filesystem, and a `name:`
    that disagrees with its own filename is itself a disagreement worth stopping on — the
    assignments table addresses roles by path, so the two must be the same name."""
    if not agents_dir.is_dir():
        raise PolicyError(f"{agents_dir} not found - run from a repo checkout")
    out: dict[str, str] = {}
    for path in sorted(agents_dir.glob("*.md")):
        m = _FRONTMATTER.match(path.read_text(encoding="utf-8"))
        if not m:
            raise PolicyError(f"{path.name}: no frontmatter block - every role file must "
                              "declare its model")
        fields: dict[str, str] = {}
        for line in m.group(1).splitlines():
            if ":" in line and not line.startswith((" ", "\t")):
                key, _, value = line.partition(":")
                fields[key.strip()] = value.strip()
        name, model = fields.get("name", ""), fields.get("model", "")
        if not name:
            raise PolicyError(f"{path.name}: frontmatter lacks a name")
        if name != path.stem:
            raise PolicyError(f"{path.name}: frontmatter says name: {name}, but the file is "
                              f"{path.stem}.md - a role is addressed by its path in "
                              "docs/MODELS.md, so the two names must agree")
        if not model:
            raise PolicyError(f"{path.name}: frontmatter lacks a model - an unstated model "
                              "is not a default, it is an unknown")
        out[path.stem] = model
    if not out:
        raise PolicyError(f"no role files under {agents_dir}")
    return out


def adapter(text: str, vendor: str = VENDOR) -> dict[str, str]:
    """`{tier: model}` from the vendor adapter table — the only place model names live."""
    body = _section(text, "Vendor adapters")
    marker = body.lower().find(f"**{vendor}")
    if marker < 0:
        raise PolicyError(f"docs/MODELS.md 'Vendor adapters' names no {vendor} table")
    for table in _tables(body[marker:]):
        if not table or [c.lower() for c in table[0][:1]] != ["tier"]:
            continue
        mapping = {}
        for row in table[1:]:
            if len(row) < 2:
                raise PolicyError("docs/MODELS.md vendor adapter row is malformed: "
                                  f"{row!r}")
            mapping[row[0].strip().lower()] = _token(row[1], "model", "vendor adapter")
        if not mapping:
            raise PolicyError(f"docs/MODELS.md {vendor} adapter table has no rows")
        return mapping
    raise PolicyError(f"docs/MODELS.md {vendor} adapter table could not be parsed "
                      "(expected a two-column table whose first header cell is 'Tier')")


def assignments(text: str) -> tuple[dict[str, tuple[str, str]], dict[str, tuple[str, str]]]:
    """`({role file path: (tier, model)}, {panel key: (tier, model)})` from the table."""
    body = _section(text, "Current assignments")
    tables = [t for t in _tables(body)
              if t and [c.lower() for c in t[0][:4]] == ["surface", "kind", "tier", "model"]]
    if not tables:
        raise PolicyError("docs/MODELS.md 'Current assignments' has no table with the "
                          "contract's columns (Surface | Kind | Tier | Model | Notes) - "
                          "refusing to pass an unparseable policy")
    roles: dict[str, tuple[str, str]] = {}
    panel: dict[str, tuple[str, str]] = {}
    for row in tables[0][1:]:
        if len(row) < 4:
            raise PolicyError(f"docs/MODELS.md assignments row is malformed: {row!r}")
        surface = _token(row[0], "surface", "assignments")
        kind, tier = row[1].strip().lower(), row[2].strip().lower()
        model = _token(row[3], "model", "assignments")
        target = {"role": roles, "panel": panel}.get(kind)
        if target is None:
            raise PolicyError(f"docs/MODELS.md assignments row {surface!r} has kind "
                              f"{kind!r}; only 'role' and 'panel' are defined")
        if surface in target:
            raise PolicyError(f"docs/MODELS.md assignments lists {surface!r} twice")
        target[surface] = (tier, model)
    if not roles:
        raise PolicyError("docs/MODELS.md assignments table has no role rows - an empty "
                          "policy must never read as a satisfied one")
    return roles, panel


# ---------------------------------------------------------------- the stamp

def stamp(root: pathlib.Path = ROOT) -> dict:
    """The canonical configuration, or PolicyError naming every disagreement."""
    policy = (root / "docs" / "MODELS.md")
    if not policy.exists():
        raise PolicyError(f"{policy} is missing - the model policy IS the configuration")
    text = policy.read_text(encoding="utf-8")
    tiers = adapter(text)
    table_roles, table_panel = assignments(text)
    files = role_models(root / ".claude" / "agents")

    by_name = {}
    problems: list[str] = []
    for path, (tier, model) in sorted(table_roles.items()):
        full = root / path
        if not full.exists():
            problems.append(f"docs/MODELS.md assigns {path} ({tier}/{model}) but that role "
                            "file does not exist - remove the row or restore the file")
            continue
        name = full.stem
        by_name[name] = (path, tier, model)
    for name, model in sorted(files.items()):
        if name not in by_name:
            problems.append(f"role '{name}' (.claude/agents/{name}.md, model: {model}) is "
                            "MISSING from the assignments table in docs/MODELS.md - every "
                            "role must have a written assignment")
            continue
        path, tier, table_model = by_name[name]
        if table_model != model:
            problems.append(f"role '{name}': {path} says model: {model}, docs/MODELS.md "
                            f"says {table_model} - the file and the policy must agree")
    for name, (_path, tier, model) in sorted(by_name.items()):
        if tier not in tiers:
            problems.append(f"role '{name}': tier {tier!r} is not in the {VENDOR} adapter "
                            f"table ({', '.join(sorted(tiers))})")
        elif tiers[tier] != model:
            problems.append(f"role '{name}': the {VENDOR} adapter maps tier {tier} to "
                            f"{tiers[tier]}, but the assignments table says {model}")
    for key in REQUIRED_PANEL:
        if key not in table_panel:
            problems.append(f"panel row '{key}' is missing from docs/MODELS.md - the panel "
                            "surfaces are declared by the policy page alone, so a missing "
                            "row means the ledger cannot state what the panel ran on")
    # Panel rows get the SAME adapter-existence check as role rows. They did not once, and
    # the asymmetry was the whole bug: `tier in tiers and ...` silently passes a tier the
    # adapter has never heard of, so a typo in a panel row stamped a configuration naming a
    # tier that does not exist — and every ledger line written afterwards recorded it, while
    # `--check` stayed green. A checker that validates one table and not its twin is a
    # checker that fails open on exactly the half nobody is watching.
    for key, (tier, model) in sorted(table_panel.items()):
        if tier not in tiers:
            problems.append(f"panel '{key}': tier {tier!r} is not in the {VENDOR} adapter "
                            f"table ({', '.join(sorted(tiers))})")
        elif tiers[tier] != model:
            problems.append(f"panel '{key}': the {VENDOR} adapter maps tier {tier} to "
                            f"{tiers[tier]}, but the assignments table says {model}")
    if problems:
        raise PolicyError("\n".join(problems))

    return {
        "panel": {k: {"model": m, "tier": t} for k, (t, m) in sorted(table_panel.items())},
        "roles": {n: {"model": files[n], "tier": by_name[n][1]} for n in sorted(files)},
        "vendor": VENDOR,
    }


def canonical(config: dict) -> str:
    """The bytes that go in a ledger line: sorted keys, compact, newline-free."""
    return json.dumps(config, sort_keys=True, separators=(",", ":"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="verify the role files and docs/MODELS.md agree; print nothing else")
    ap.add_argument("--indent", type=int, default=None,
                    help="pretty-print with this indent (the ledger uses the compact form)")
    args = ap.parse_args(argv)
    try:
        config = stamp()
    except PolicyError as e:
        print(f"model policy: FAILED\n{e}", file=sys.stderr)
        return 1
    if args.check:
        print(f"model policy: {len(config['roles'])} role(s) and {len(config['panel'])} "
              "panel surface(s) agree with docs/MODELS.md")
        return 0
    print(json.dumps(config, sort_keys=True, indent=args.indent)
          if args.indent is not None else canonical(config))
    return 0


if __name__ == "__main__":
    sys.exit(main())
