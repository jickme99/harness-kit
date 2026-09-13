"""The weekly note — what you read instead of clicking (spec/keeping-current.md, section E; Phase F).

One GitHub issue a week, `shipped itself: week of <Monday>`, assigned to the owner: every routine deploy (machine-
approved, no click), every gated deploy (the owner's click), every Dependabot update merged, held or closed, the
daily job's decisions, the issues that close the routine lane, the state of the kill switch, and the date of the
last drill. The shell in `.github/workflows/weekly-note.yml` gathers GitHub's own records as JSON files and this
module renders them; nothing here reaches GitHub or Azure, so `tests/test_weekly_note.py` can prove every line.

House rule: an empty week says so in words. Silence is never a report.

Inputs (all under $OUT): deploy-runs.json, freshness-runs.json, prs.json, issues.json (each the JSON `gh` prints),
art/<run id>/decision.json (the daily job's kept decision, when its rebuild half ran); environment WEEK_START
(ISO date, the first day of the window), DAYS (default 7), ROUTINE_LANE, RUN_URL.
"""
import datetime
import json
import os
import pathlib
import sys

DRILL_DUE_DAYS = 91          # "the flag drill again once a quarter"


def _dt(s):
    return datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00"))


def _read(path):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _in_window(item, key, start, end):
    v = item.get(key)
    return bool(v) and start <= _dt(v) < end


def _when(s):
    return _dt(s).strftime("%Y-%m-%d %H:%M UTC")


def _minutes(run):
    try:
        return round((_dt(run["updatedAt"]) - _dt(run["createdAt"])).total_seconds() / 60)
    except (KeyError, ValueError, TypeError):
        return None


def _run_line(run, tag):
    mins = _minutes(run)
    dur = f" — {mins} min" if mins is not None else ""
    return f"- {_when(run['createdAt'])} — {run.get('displayTitle', '?')} — **{run.get('conclusion') or run.get('status') or '?'}**{dur} — {tag} — {run.get('url', '')}"


def lane_of(run):
    """Routine or gated, from the run's own name: `run-name` in deploy.yml says which lane a run took."""
    title = str(run.get("displayTitle") or "")
    if title.startswith("Routine deploy"):
        return "routine"
    if title.startswith("DRILL"):
        return "drill"
    return "gated"


def last_drill(deploy_runs):
    """The newest SUCCESSFUL drill, whatever week it ran in; None when there has never been one."""
    drills = [r for r in deploy_runs if lane_of(r) == "drill" and r.get("conclusion") == "success" and r.get("createdAt")]
    if not drills:
        return None
    return max(drills, key=lambda r: _dt(r["createdAt"]))


def render(*, week_start, days, deploy_runs, freshness_runs, prs, issues, decisions, routine_lane, run_url=""):
    start = datetime.datetime.combine(week_start, datetime.time.min, tzinfo=datetime.timezone.utc)
    end = start + datetime.timedelta(days=days)
    out = []
    title = f"shipped itself: week of {week_start.isoformat()}"
    out.append(f"# {title}")
    out.append(f"The week {week_start.isoformat()} to {(end - datetime.timedelta(days=1)).date().isoformat()}, from GitHub's own "
               "records. **Machine-approved** = shipped by the routine lane with no click; **the owner's click** = the gated lane.")
    out.append("")
    on = str(routine_lane or "").strip() == "on"
    out.append(f"**The routine lane is {'ON' if on else 'OFF'}** (repository variable `ROUTINE_LANE` = `{routine_lane or 'unset'}`)"
               + ("" if on else " — everything waits for the owner's click while it is off."))
    out.append("")

    runs = [r for r in deploy_runs if _in_window(r, "createdAt", start, end)]
    routine = [r for r in runs if lane_of(r) == "routine"]
    gated = [r for r in runs if lane_of(r) == "gated"]
    drills = [r for r in runs if lane_of(r) == "drill"]
    out.append(f"## Routine deploys — {len(routine)}")
    out.extend(_run_line(r, "machine-approved") for r in routine) if routine else out.append("- none: nothing shipped itself this week.")
    out.append("")
    out.append(f"## Gated deploys — {len(gated)}")
    out.extend(_run_line(r, "the owner's click") for r in gated) if gated else out.append("- none this week.")
    if drills:
        out.append("")
        out.append(f"## Drills this week — {len(drills)}")
        out.extend(_run_line(r, "a drill: refused before traffic = pass") for r in drills)
    out.append("")

    merged = [p for p in prs if p.get("mergedAt") and _in_window(p, "mergedAt", start, end)]
    held = [p for p in prs if p.get("state") == "OPEN" and any(l.get("name") == "needs-a-look" for l in p.get("labels") or [])]
    waiting = [p for p in prs if p.get("state") == "OPEN" and p not in held]
    closed = [p for p in prs if p.get("state") == "CLOSED" and not p.get("mergedAt") and _in_window(p, "closedAt", start, end)]
    out.append(f"## Dependabot — merged {len(merged)}, held for a look {len(held)}, open {len(waiting)}, closed without merge {len(closed)}")
    for p in merged:
        out.append(f"- merged {_when(p['mergedAt'])}: #{p['number']} {p['title']} — {p.get('url', '')}")
    for p in held:
        out.append(f"- **held for a look** (label `needs-a-look`): #{p['number']} {p['title']} — a person merges it, or not — {p.get('url', '')}")
    for p in waiting:
        out.append(f"- open, waiting on its checks: #{p['number']} {p['title']} — {p.get('url', '')}")
    for p in closed:
        out.append(f"- closed without merging {_when(p['closedAt'])}: #{p['number']} {p['title']} — {p.get('url', '')}")
    if not (merged or held or waiting or closed):
        out.append("- nothing from Dependabot this week.")
    out.append("")

    fresh = [r for r in freshness_runs if _in_window(r, "createdAt", start, end)]
    out.append(f"## The daily job — {len(fresh)} run{'s' if len(fresh) != 1 else ''}")
    for r in sorted(fresh, key=lambda r: r["createdAt"]):
        sentence = decisions.get(str(r.get("databaseId")), "")
        what = sentence or "checked; nothing fixable, no rebuild that day"
        out.append(f"- {_when(r['createdAt'])} — **{r.get('conclusion') or r.get('status') or '?'}** — {what} — {r.get('url', '')}")
    if not fresh:
        out.append("- **no run this week — that is the thing to chase** (the schedule is daily).")
    out.append("")

    red = [i for i in issues if i.get("state") == "OPEN" and any(l.get("name") in ("deploy", "freshness") for l in i.get("labels") or [])]
    out.append(f"## Issues that close the routine lane — {len(red)} open")
    for i in red:
        out.append(f"- **#{i['number']} {i['title']}** (open since {_when(i['createdAt'])}) — the lane stays closed until a person closes it — {i.get('url', '')}")
    if not red:
        out.append("- none open.")
    out.append("")

    d = last_drill(deploy_runs)
    if d:
        when = _dt(d["createdAt"]).date()
        due = when + datetime.timedelta(days=DRILL_DUE_DAYS)
        overdue = due < end.date()
        out.append(f"## Last drill: {when.isoformat()} — {d.get('displayTitle', '')} — {d.get('url', '')}")
        out.append(f"- next drill due by **{due.isoformat()}**" + (" — **OVERDUE**: dispatch deploy.yml with `drill: yes`." if overdue else "."))
    else:
        out.append("## Last drill: **never** — dispatch deploy.yml with `drill: yes` before trusting the routine lane.")
    out.append("")
    if run_url:
        out.append(f"_Written by the weekly-note workflow: {run_url}_")
    return title, "\n".join(out) + "\n"


def main(argv=None):
    env = os.environ
    out = pathlib.Path(env.get("OUT") or ".")
    try:
        week_start = datetime.date.fromisoformat(env["WEEK_START"])
    except (KeyError, ValueError):
        print("REFUSED: WEEK_START must be an ISO date.", file=sys.stderr)
        return 2
    days = int(env.get("DAYS") or 7)
    deploy_runs = _read(out / "deploy-runs.json") or []
    freshness_runs = _read(out / "freshness-runs.json") or []
    prs = _read(out / "prs.json") or []
    issues = _read(out / "issues.json") or []
    decisions = {}
    for r in freshness_runs:
        d = _read(out / "art" / str(r.get("databaseId")) / "decision.json")
        if isinstance(d, dict) and d.get("sentence"):
            decisions[str(r.get("databaseId"))] = d["sentence"]
    title, body = render(week_start=week_start, days=days, deploy_runs=deploy_runs, freshness_runs=freshness_runs,
                         prs=prs, issues=issues, decisions=decisions, routine_lane=env.get("ROUTINE_LANE", ""),
                         run_url=env.get("RUN_URL", ""))
    (out / "note.md").write_text(body, encoding="utf-8")
    print(title)
    return 0


if __name__ == "__main__":
    sys.exit(main())
