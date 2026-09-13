"""Phase F — the weekly note (spec/keeping-current.md, section E; 2026-09-12). RED-first, fictional data.

Fails if an empty week is silent, if a routine run is not marked machine-approved (or a gated one is), if a held
Dependabot update is not named, if a daily-job run without a kept decision is presented as a decision, if the last
drill is not found outside the window, or if an open red issue is not shown as closing the lane.
"""
import datetime
import json

import pytest

from infra.weekly_note import lane_of, last_drill, main, render

MON = datetime.date(2026, 9, 7)


def _empty_week(routine_lane=""):
    return render(week_start=MON, days=7, deploy_runs=[], freshness_runs=[], prs=[], issues=[],
                  decisions={}, routine_lane=routine_lane)


def run(id_, title, created, conclusion="success", mins=6):
    c = datetime.datetime.fromisoformat(created).replace(tzinfo=datetime.timezone.utc)
    u = c + datetime.timedelta(minutes=mins)
    return {"databaseId": id_, "displayTitle": title, "conclusion": conclusion, "status": "completed",
            "createdAt": c.isoformat().replace("+00:00", "Z"), "updatedAt": u.isoformat().replace("+00:00", "Z"),
            "url": f"https://example.test/runs/{id_}"}


def pr(n, title, state="OPEN", merged=None, closed=None, labels=()):
    return {"number": n, "title": title, "state": state, "mergedAt": merged, "closedAt": closed,
            "createdAt": "2026-09-08T10:00:00Z", "labels": [{"name": l} for l in labels], "url": f"https://example.test/pull/{n}"}


def issue(n, title, labels, state="OPEN"):
    return {"number": n, "title": title, "state": state, "createdAt": "2026-09-09T01:00:00Z",
            "labels": [{"name": l} for l in labels], "url": f"https://example.test/issues/{n}"}


def test_an_empty_week_says_so_in_words_and_names_the_lane_state():
    title, body = _empty_week()
    assert title == "shipped itself: week of 2026-09-07"
    assert "nothing shipped itself this week" in body
    assert "The routine lane is OFF" in body and "`unset`" in body
    assert "no run this week — that is the thing to chase" in body
    assert "Last drill: **never**" in body


@pytest.mark.parametrize("value", ["ON", "true", "1", "off", " yes "])
def test_anything_but_exact_on_is_the_lane_off(value):
    _, body = _empty_week(routine_lane=value)
    assert "The routine lane is OFF" in body


def test_routine_runs_are_machine_approved_and_gated_runs_are_the_owners_click():
    runs = [run(1, "Routine deploy promote `ab12cd34-r20260908` — flimsy-tls moved", "2026-09-08T06:20:00"),
            run(2, "Deploy the new intake screen", "2026-09-10T15:00:00"),
            run(3, "Routine deploy Phase C check", "2026-08-30T10:00:00")]        # last week: excluded
    _, body = render(week_start=MON, days=7, deploy_runs=runs, freshness_runs=[], prs=[], issues=[], decisions={}, routine_lane="on")
    assert "## Routine deploys — 1" in body and "machine-approved" in body and "6 min" in body
    assert "## Gated deploys — 1" in body and "the owner's click" in body
    assert "Phase C check" not in body
    assert "The routine lane is ON" in body
    assert lane_of(runs[0]) == "routine" and lane_of(runs[1]) == "gated" and lane_of({"displayTitle": "DRILL rehearsal"}) == "drill"


def test_dependabot_updates_are_sorted_into_merged_held_open_and_closed():
    prs = [pr(5, "bump a from 1 to 2", state="MERGED", merged="2026-09-08T22:46:00Z"),
           pr(6, "bump b from 3 to 4", labels=("needs-a-look",)),
           pr(7, "bump c from 1.0 to 1.1"),
           pr(8, "bump d from 9 to 10", state="CLOSED", closed="2026-09-09T00:20:00Z"),
           pr(9, "bump e", state="MERGED", merged="2026-08-20T00:00:00Z")]           # outside the window
    _, body = render(week_start=MON, days=7, deploy_runs=[], freshness_runs=[], prs=prs, issues=[], decisions={}, routine_lane="on")
    assert "merged 1, held for a look 1, open 1, closed without merge 1" in body
    assert "**held for a look**" in body and "#6" in body
    assert "closed without merging" in body and "#8" in body
    assert "#9" not in body


def test_daily_job_runs_show_their_kept_decision_or_say_no_rebuild_ran():
    fresh = [run(41, "freshness full", "2026-09-08T06:00:00"), run(42, "freshness full", "2026-09-09T06:00:00", conclusion="failure")]
    _, body = render(week_start=MON, days=7, deploy_runs=[], freshness_runs=fresh, prs=[], issues=[],
                     decisions={"41": "green — nothing moved and nothing fixable was found"}, routine_lane="on")
    assert "## The daily job — 2 runs" in body
    assert "green — nothing moved" in body
    assert "**failure** — checked; nothing fixable, no rebuild that day" in body


def test_the_last_drill_is_found_outside_the_window_and_a_stale_one_is_overdue():
    runs = [run(7, "DRILL quarterly", "2026-06-01T10:00:00"), run(8, "DRILL failed attempt", "2026-06-02T10:00:00", conclusion="failure")]
    assert last_drill(runs)["databaseId"] == 7
    _, body = render(week_start=MON, days=7, deploy_runs=runs, freshness_runs=[], prs=[], issues=[], decisions={}, routine_lane="on")
    assert "Last drill: 2026-06-01" in body and "next drill due by **2026-08-31**" in body and "OVERDUE" in body
    fresh_drill = [run(9, "DRILL rehearsal", "2026-09-05T10:00:00")]
    _, body = render(week_start=MON, days=7, deploy_runs=fresh_drill, freshness_runs=[], prs=[], issues=[], decisions={}, routine_lane="on")
    assert "OVERDUE" not in body and "2026-12-05" in body


def test_open_red_issues_close_the_lane_and_the_cli_writes_the_note(tmp_path):
    issues = [issue(6, "deploy: RED 2026-09-09 — routine example-app:ab12cd34-r20260909", ["deploy"]),
              issue(3, "freshness: RED (old, closed)", ["freshness"], state="CLOSED")]
    _, body = render(week_start=MON, days=7, deploy_runs=[], freshness_runs=[], prs=[], issues=issues, decisions={}, routine_lane="on")
    assert "Issues that close the routine lane — 1 open" in body and "#6" in body and "#3" not in body
    out = tmp_path
    (out / "deploy-runs.json").write_text(json.dumps([run(1, "Routine deploy x", "2026-09-08T06:20:00")]), encoding="utf-8")
    (out / "freshness-runs.json").write_text(json.dumps([run(41, "freshness full", "2026-09-08T06:00:00")]), encoding="utf-8")
    (out / "art" / "41").mkdir(parents=True)
    (out / "art" / "41" / "decision.json").write_text(json.dumps({"sentence": "promote `ab12cd34-r20260908`"}), encoding="utf-8")
    import os
    saved = dict(os.environ)
    try:
        os.environ.update({"OUT": str(out), "WEEK_START": "2026-09-07", "ROUTINE_LANE": "on", "RUN_URL": "https://example.test/runs/99"})
        assert main([]) == 0
        note = (out / "note.md").read_text(encoding="utf-8")
        assert "# shipped itself: week of 2026-09-07" in note and "promote `ab12cd34-r20260908`" in note and "runs/99" in note
        os.environ["WEEK_START"] = "not-a-date"
        assert main([]) == 2
    finally:
        os.environ.clear(); os.environ.update(saved)
