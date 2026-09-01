# harness-kit 2026.09 — reference tool, proven in the origin project's harness.
"""Catch and escape rates per tier-configuration era, read off the review ledger.

The model policy (`docs/MODELS.md`) admits exactly two reasons to move an assignment, and both
are counting arguments. This is the counter. It groups `reviews/ledger.jsonl` by the
configuration each line was stamped under — an **era** is one distinct configuration, dated
from its first line to its last — and prints, per era:

    reviews          how many panel runs ran under it
    must-fix         findings the panel raised as blocking
    verified         of those, how many survived the lead's verify pass as real
    missed           escapes attributed to it whose introducing commit WAS reviewed
    catch            verified / (verified + missed)
    escapes/review   missed / reviews

    python scripts/review_rates.py                 # the table
    python scripts/review_rates.py --json          # the same numbers, machine-readable
    python scripts/review_rates.py path/to/ledger  # a fixture, for tests

Deterministic: the era key is a hash of the canonical configuration bytes, so the same ledger
always yields the same eras in the same order (first-seen date, then key). Two habits it is
built to resist — a line whose type nobody recognises is an ERROR rather than a skipped row
(a typo must not quietly leave a review out of the denominator), and an escape attributed to a
configuration that never appears in a review still gets its own row rather than vanishing.

An unrecorded count (`null`, only legal in a back-filled line) is never added in as a zero —
not the must-fix count, not the verified count. Each is tallied in its own "unrecorded"
counter and shown beside the column it belongs to, so a review whose numbers nobody wrote down
reads as unknown rather than as a review that found nothing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
LEDGER = ROOT / "reviews" / "ledger.jsonl"


class LedgerError(RuntimeError):
    """The ledger cannot be read as the record it claims to be."""


def config_key(config: dict) -> str:
    body = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]


def config_label(config: dict) -> str:
    """A short human summary of a configuration — what changed between eras, at a glance."""
    roles = sorted({str(v.get("model")) for v in (config.get("roles") or {}).values()})
    panel = config.get("panel") or {}

    def one(key: str) -> str:
        return str((panel.get(key) or {}).get("model", "?"))

    parts = [f"roles {'+'.join(roles) or '?'}",
             f"lens {one('review-panel-lens')}",
             f"lead {one('panel-lead-verify')}"]
    if config.get("source"):
        parts.append(str(config["source"]))
    return ", ".join(parts)


def read(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        raise LedgerError(f"{path} does not exist")
    lines = []
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as e:
            raise LedgerError(f"{path}:{n}: not valid JSON ({e})") from None
        kind = obj.get("type")
        if kind not in ("review", "escape"):
            raise LedgerError(f"{path}:{n}: unknown line type {kind!r} - an unrecognised "
                              "line would silently leave a review out of the numbers")
        required = (("pr", "date", "config", "findings", "verified_surviving")
                    if kind == "review"
                    else ("fix_pr", "introducing_commit", "reviewed_and_missed",
                          "attributed_config"))
        missing = [f for f in required if f not in obj]
        if missing:
            raise LedgerError(f"{path}:{n}: {kind} line is missing {', '.join(missing)}")
        lines.append(obj)
    return lines


def eras(entries: list[dict]) -> list[dict]:
    out: dict[str, dict] = {}

    def era(config: dict) -> dict:
        key = config_key(config)
        return out.setdefault(key, {"key": key, "label": config_label(config),
                                    "first_seen": None, "last_seen": None,
                                    "reviews": 0, "must_fix": 0, "uncounted": 0,
                                    "verified": 0, "unverified": 0,
                                    "missed": 0, "not_reviewed": 0})

    for obj in entries:
        if obj["type"] == "review":
            e = era(obj["config"])
            date = str(obj["date"])
            e["first_seen"] = date if e["first_seen"] is None else min(e["first_seen"], date)
            e["last_seen"] = date if e["last_seen"] is None else max(e["last_seen"], date)
            e["reviews"] += 1
            # `or 0` here would have been the exact sin this module's docstring forbids:
            # a back-filled line whose must-fix count was never recorded would have
            # displayed as a review that found nothing. Unknown gets its own counter, the
            # same way an unverified count does.
            must_fix = (obj.get("findings") or {}).get("must_fix")
            if must_fix is None:
                e["uncounted"] += 1
            else:
                e["must_fix"] += int(must_fix)
            verified = obj.get("verified_surviving")
            if verified is None:
                e["unverified"] += 1
            else:
                e["verified"] += int(verified)
        else:
            e = era(obj["attributed_config"])
            if obj["reviewed_and_missed"]:
                e["missed"] += 1
            else:
                e["not_reviewed"] += 1

    rows = sorted(out.values(), key=lambda r: (r["first_seen"] or "", r["key"]))
    for r in rows:
        caught = r["verified"] + r["missed"]
        r["catch_rate"] = (r["verified"] / caught) if caught else None
        r["escapes_per_review"] = (r["missed"] / r["reviews"]) if r["reviews"] else None
    return rows


def table(rows: list[dict]) -> str:
    head = ("era", "dates", "reviews", "must-fix", "verified", "missed", "catch",
            "escapes/review")

    # ASCII only: this prints to whatever console the operator has, and a Windows cp1252
    # terminal raises UnicodeEncodeError on an em dash rather than degrading the glyph.
    def fmt(r: dict) -> tuple[str, ...]:
        dates = f"{r['first_seen'] or '?'}..{r['last_seen'] or '?'}"
        catch = "n/a" if r["catch_rate"] is None else f"{r['catch_rate'] * 100:.0f}%"
        esc = "n/a" if r["escapes_per_review"] is None else f"{r['escapes_per_review']:.2f}"
        def counted(total: int, unknown: int) -> str:
            return str(total) + (f" (+{unknown} unrecorded)" if unknown else "")

        return (r["key"], dates, str(r["reviews"]),
                counted(r["must_fix"], r["uncounted"]),
                counted(r["verified"], r["unverified"]),
                str(r["missed"]), catch, esc)

    body = [fmt(r) for r in rows]
    widths = [max(len(h), *(len(b[i]) for b in body)) if body else len(h)
              for i, h in enumerate(head)]
    out = ["  ".join(h.ljust(w) for h, w in zip(head, widths, strict=True)).rstrip(),
           "  ".join("-" * w for w in widths)]
    out += ["  ".join(c.ljust(w) for c, w in zip(b, widths, strict=True)).rstrip() for b in body]
    out += [""] + [f"{r['key']}  {r['label']}" for r in rows]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ledger", nargs="?", default=str(LEDGER))
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args(argv)
    try:
        rows = eras(read(pathlib.Path(args.ledger)))
    except LedgerError as e:
        print(f"review ledger: {e}", file=sys.stderr)
        return 1
    if not rows:
        print("review ledger: no lines yet - no rates to compute")
        return 0
    print(json.dumps(rows, sort_keys=True, indent=1) if args.as_json else table(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
