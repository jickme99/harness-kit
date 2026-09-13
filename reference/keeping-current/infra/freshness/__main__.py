"""`python -m infra.freshness <command>` — the thin door the workflow's shell calls.

Four commands, one per pure module: `classify`, `compare`, `decide`, `summary`. Everything else
arrives in the ENVIRONMENT — no flags anywhere, the same convention
`infra/registry_retention_plan.py` uses for `$WORK`, and the one the maintainer's guarded shell
requires (it refuses an opaque script invocation carrying options).

Nothing here reaches Azure, the registry or GitHub. Those calls stay in the workflow's `run:` blocks
where the log shows them. This module only reads files, decides, and writes files.

The exit code is the contract, and the workflow depends on it:

    0   the step did its work (INCONCLUSIVE included — it is a state, not a crash)
    1   REFUSED or RED — the step fails loudly, which is what fires the issue step
    2   called wrong (unknown command)
"""
import json
import os
import pathlib
import sys

from infra.freshness import decide as decide_mod
from infra.freshness import findings as findings_mod
from infra.freshness import inventory as inventory_mod
from infra.freshness import summary as summary_mod
from infra.freshness import range_rule as range_mod

COMMANDS = ("classify", "compare", "decide", "summary", "range")


def _say(text, stream=None):
    """Write UTF-8 BYTES, not console-encoded text.

    The summary carries em dashes and arrows, and a Windows console is cp1252 by default: the plain
    `print()` of this page dies with UnicodeEncodeError on the maintainer's own workstation while
    working perfectly on the ubuntu runner (measured 2026-09-10, building this). The runner's
    redirect into `$GITHUB_STEP_SUMMARY` wants UTF-8 either way, so write it explicitly and let no
    locale decide what the owner's page says.
    """
    stream = stream or sys.stdout
    raw = getattr(stream, "buffer", None)
    if raw is None:
        print(text, file=stream)
        return
    raw.write((text + "\n").encode("utf-8"))
    raw.flush()


def _warn(text):
    _say(text, sys.stderr)


def _out(env):
    return pathlib.Path(env.get("OUT") or ".")


def _read_json(path):
    """A file that is absent or unreadable is NOT an empty answer — it is `None`, the third state."""
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None


def _write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def _row_json(r):
    f = r.finding
    return {"repository": r.repository, "digest": r.digest, "state": r.state,
            "monitored_only": r.monitored_only, "needs_a_hand": r.needs_a_hand,
            "software": f.software, "detected": f.detected, "fixed": f.fixed,
            "cves": list(f.cves), "cvss": f.cvss, "first_seen": f.first_seen}


def _row_from_json(d):
    f = findings_mod.Finding(d["repository"], d["digest"], d.get("software", ""),
                             d.get("detected", ""), d.get("fixed", ""), tuple(d.get("cves") or ()),
                             d.get("cvss"), d.get("first_seen", ""))
    return findings_mod.Row(f, d["state"], monitored_only=bool(d.get("monitored_only")))


def _inventory(path, side):
    """One side of the compare: its packages, or None when the scan did not leave a readable file."""
    raw = _read_json(path)
    if raw is None:
        return None
    try:
        return inventory_mod.packages(raw)
    except inventory_mod.InventoryRefused as e:
        _warn(f"{side}: {e}")
        return None


def cmd_classify(env):
    pages = _read_json(env.get("GRAPH_PAGES"))
    live_raw = _read_json(env.get("LIVE_IMAGES"))
    if pages is None or live_raw is None:
        _warn("REFUSED: the Resource Graph pages or the live-image read could not be loaded.")
        return 1
    live = {k: findings_mod.LiveImage(k, v.get("tag", ""), v.get("digest", ""),
                                      frozenset(v.get("registry_digests") or ()))
            for k, v in live_raw.items()}
    try:
        found = findings_mod.parse_resource_graph(pages)
        rows = findings_mod.classify(found, live)
    except findings_mod.FreshnessRefused as e:
        _warn(str(e))
        return 1
    _write_json(_out(env) / "classified.json",
                {"checked": found.checked, "total_records": found.total_records,
                 "rows": [_row_json(r) for r in rows]})
    _say(f"findings {len(rows)} of {found.total_records} rows; "
         f"needs-a-hand {sum(1 for r in rows if r.needs_a_hand)}")
    return 0


def cmd_compare(env):
    deployed = _inventory(env.get("DEPLOYED_TRIVY"), "deployed")
    candidate = _inventory(env.get("CANDIDATE_TRIVY"), "candidate")
    verdict = inventory_mod.compare(deployed, candidate)
    _write_json(_out(env) / "verdict.json",
                {"kind": verdict.kind, "reason": verdict.reason,
                 "moved": [list(m) for m in verdict.moved]})
    _say(f"verdict {verdict.kind} {verdict.reason}".strip())
    return 0


def cmd_decide(env):
    raw = _read_json(_out(env) / "verdict.json") or {}
    verdict = inventory_mod.Verdict(
        raw.get("kind", inventory_mod.INCONCLUSIVE),
        moved=tuple(tuple(m) for m in raw.get("moved") or ()),
        reason=raw.get("reason", "no comparison was written by the compare step"))

    candidate = _read_json(env.get("CANDIDATE_TRIVY"))
    found = inventory_mod.vulnerabilities(candidate) if isinstance(candidate, dict) else []
    accepted_text = ""
    try:
        accepted_text = pathlib.Path(env["ACCEPTED"]).read_text(encoding="utf-8")
    except (OSError, KeyError, TypeError):
        pass                       # no allowlist file is "nothing accepted", which is the default
    try:
        split = inventory_mod.split_accepted(found, inventory_mod.load_accepted(accepted_text))
    except inventory_mod.InventoryRefused as e:
        _warn(str(e))
        return 1

    try:
        d = decide_mod.decide(verdict, split.actionable, env.get("PENDING_SINCE", "").strip(),
                              env.get("MODE", decide_mod.DRY), tag=env.get("TAG", ""),
                              held_by=env.get("HELD_BY", "").strip())
    except ValueError as e:
        _warn(f"REFUSED: {e}")
        return 1

    _write_json(_out(env) / "decision.json", {
        "kind": d.kind, "mode": d.mode, "promote": d.will_promote, "tag": d.tag,
        "package": d.package, "fix": d.fix, "installed": d.installed, "cve": d.cve,
        "reason": d.reason, "where": d.where, "sentence": d.sentence(), "moved": [list(m) for m in d.moved],
        "accepted": [{"cve": v.cve, "package": v.package, "installed": v.installed,
                      "fixed": v.fixed, "severity": v.severity} for v in split.accepted],
    })
    _say(f"decision {d.kind}\npromote {'1' if d.will_promote else '0'}")
    # RED exits non-zero on purpose: the job goes red, the issue step fires, the owner hears it here.
    return 1 if d.is_red else 0


def cmd_summary(env):
    out = _out(env)
    classified = _read_json(out / "classified.json") or {}
    rows = [_row_from_json(r) for r in classified.get("rows", [])]
    verdict_raw = _read_json(out / "verdict.json") or {}
    verdict = inventory_mod.Verdict(
        verdict_raw.get("kind", inventory_mod.INCONCLUSIVE),
        moved=tuple(tuple(m) for m in verdict_raw.get("moved") or ()),
        reason=verdict_raw.get("reason", "no rebuild ran this run, so there is nothing to compare"))
    decision_raw = _read_json(out / "decision.json") or {}
    decision = decide_mod.Decision(
        decision_raw.get("kind", inventory_mod.INCONCLUSIVE),
        mode=decision_raw.get("mode", env.get("MODE", decide_mod.DRY)),
        tag=decision_raw.get("tag", ""), package=decision_raw.get("package", ""),
        fix=decision_raw.get("fix", ""), installed=decision_raw.get("installed", ""),
        cve=decision_raw.get("cve", ""),
        reason=decision_raw.get("reason", "no decision was written by the decide step"),
        moved=tuple(tuple(m) for m in decision_raw.get("moved") or ()),
        # Every field the sentence reads has to survive the round trip through decision.json: the
        # first live RED (2026-09-11) lost its "found in Python" right here.
        where=decision_raw.get("where", ""))
    accepted = tuple(inventory_mod.Vulnerability(a.get("cve", ""), a.get("package", ""),
                                                 a.get("installed", ""), a.get("fixed", ""),
                                                 a.get("severity", ""))
                     for a in decision_raw.get("accepted") or ())
    policy_path = out / "policy.tsv"
    policy = None
    if policy_path.exists():
        policy = [tuple(line.split("\t", 2)) for line in policy_path.read_text(encoding="utf-8").splitlines()
                  if line.strip()]
        policy = [(r + ("", "", ""))[:3] for r in policy]     # a short row is still a row, never dropped
    _say(summary_mod.render(
        date=env.get("DATE", ""), mode=env.get("MODE", decide_mod.DRY), rows=rows, policy=policy,
        checked=bool(classified.get("checked")), verdict=verdict, decision=decision,
        base_digest=env.get("BASE_DIGEST", ""), retention=env.get("RETENTION", ""),
        accepted=accepted, run_url=env.get("RUN_URL", ""),
        repositories=[r.strip() for r in env.get("FRESHNESS_REPOSITORIES", "").split(",") if r.strip()],
        # No decision file means the rebuild half never ran — the ordinary weekday, not a failure.
        rebuilt=bool(decision_raw)))
    return 0


def cmd_range(env):
    """`range`: COMPARE (GitHub's compare answer, a file) -> $OUT/range.json; exit 0 = the routine lane may ship the
    head, 1 = it may not (the reason is in the file and on stderr). The rule that keeps the lanes apart."""
    compare = _read_json(env["COMPARE"]) if env.get("COMPARE") else None
    if compare is None:                # absent, unreadable or not JSON: the third state, never "routine"
        verdict = range_mod.RangeVerdict(False, f"the compare answer could not be read: {env.get('COMPARE') or 'COMPARE is unset'}")
    else:
        verdict = range_mod.judge(compare)
    _out(env).mkdir(parents=True, exist_ok=True)      # the routine job calls this before its canary made the folder
    _write_json(_out(env) / "range.json", {"routine": verdict.routine, "reason": verdict.reason,
                                            "count": verdict.count, "head": verdict.head})
    (_say if verdict.routine else _warn)(verdict.line())
    return 0 if verdict.routine else 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in COMMANDS:
        _warn(f"usage: python -m infra.freshness <{' | '.join(COMMANDS)}>  "
              "(inputs come from the environment: OUT, MODE, TAG, GRAPH_PAGES, LIVE_IMAGES, "
              "DEPLOYED_TRIVY, CANDIDATE_TRIVY, ACCEPTED, PENDING_SINCE, DATE, BASE_DIGEST, "
              "RETENTION, RUN_URL; `range`: COMPARE)")
        return 2
    return {"classify": cmd_classify, "compare": cmd_compare,
            "decide": cmd_decide, "summary": cmd_summary, "range": cmd_range}[argv[0]](os.environ)


if __name__ == "__main__":
    sys.exit(main())
