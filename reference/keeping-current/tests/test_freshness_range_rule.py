"""Phase D — the rule that keeps the lanes apart (spec/keeping-current.md D; 2026-09-11).

A deploy of `main` may take the routine lane only if every commit since the deployed commit is one GitHub records
as authored by `dependabot[bot]` (id 49699333) AND marks verified. The input is GitHub's compare answer, never a
local log. One human commit, one unsigned commit, one unnamed author, an empty range, a diverged `main`, or a
truncated answer, and the verdict is NOT ROUTINE with the reason named. Fictional shas throughout.
"""
import json

import pytest

from infra.freshness.__main__ import main
from infra.freshness.range_rule import DEPENDABOT_ID, judge

MAINTAINER = {"login": "someone", "id": 1234}


def commit(sha, author, verified=True, reason="valid"):
    return {"sha": sha, "author": author,
            "commit": {"verification": {"verified": verified, "reason": reason},
                       "author": {"name": "x", "email": "x@example.com"}, "message": "build(deps): bump"}}


def bot(sha, verified=True, reason="valid"):
    return commit(sha, {"login": "dependabot[bot]", "id": DEPENDABOT_ID}, verified, reason)


def compare(commits, status="ahead", total=None):
    return {"status": status, "ahead_by": len(commits), "behind_by": 0,
            "total_commits": len(commits) if total is None else total, "commits": commits}


def test_a_range_of_only_verified_dependabot_commits_is_routine():
    v = judge(compare([bot("a" * 40), bot("b" * 40), bot("c" * 40)]))
    assert v.routine and v.count == 3 and v.head == "c" * 40
    assert "every one authored by dependabot[bot] and verified by GitHub" in v.reason
    assert v.line().startswith("ROUTINE — ")


def test_one_human_commit_anywhere_in_the_range_makes_it_the_judgement_lanes():
    for where in range(3):
        commits = [bot("a" * 40), bot("b" * 40), bot("c" * 40)]
        commits[where] = commit("d" * 40, MAINTAINER)
        v = judge(compare(commits))
        assert not v.routine and "ddddddd is by someone" in v.reason and "judgement lane" in v.reason


def test_an_author_github_cannot_name_is_refused():
    """A commit pushed from a workstation whose email is not linked to a GitHub user comes back with `author: null`
    — exactly what the maintainer's own commits look like (measured 2026-09-11). Not a bot, not routine."""
    v = judge(compare([bot("a" * 40), commit("e" * 40, None)]))
    assert not v.routine and "an author GitHub does not name" in v.reason


def test_an_unverified_dependabot_commit_is_refused_with_githubs_reason():
    v = judge(compare([bot("a" * 40, verified=False, reason="unsigned")]))
    assert not v.routine and "does not mark it verified (unsigned)" in v.reason


def test_an_identical_range_is_nothing_to_ship_and_a_diverged_or_behind_main_is_refused():
    assert not judge({"status": "identical", "total_commits": 0, "commits": []}).routine
    assert "nothing to ship" in judge({"status": "identical", "total_commits": 0, "commits": []}).reason
    for status in ("behind", "diverged", None):
        v = judge(compare([bot("a" * 40)], status=status))
        assert not v.routine and "must be an ancestor of main" in v.reason


def test_a_truncated_answer_is_refused_never_judged_on_half():
    v = judge(compare([bot("a" * 40), bot("b" * 40)], total=300))
    assert not v.routine and "lists 2 of 300 commits" in v.reason


def test_an_empty_or_malformed_answer_is_refused():
    assert not judge(compare([])).routine
    assert not judge({"status": "ahead", "total_commits": 1}).routine
    assert not judge("nonsense").routine
    assert not judge({"status": "ahead", "total_commits": 1, "commits": ["not an object"]}).routine


def test_the_cli_writes_range_json_and_its_exit_code_is_the_verdict(tmp_path, capsys):
    good = tmp_path / "good.json"; good.write_text(json.dumps(compare([bot("a" * 40)])), encoding="utf-8")
    bad = tmp_path / "bad.json"; bad.write_text(json.dumps(compare([commit("d" * 40, MAINTAINER)])), encoding="utf-8")
    out = tmp_path / "out"

    import os
    saved = dict(os.environ)
    try:
        os.environ.update({"COMPARE": str(good), "OUT": str(out)})
        assert main(["range"]) == 0
        d = json.loads((out / "range.json").read_text(encoding="utf-8"))
        assert d["routine"] is True and d["count"] == 1 and d["head"] == "a" * 40
        os.environ.update({"COMPARE": str(bad), "OUT": str(out)})
        assert main(["range"]) == 1
        d = json.loads((out / "range.json").read_text(encoding="utf-8"))
        assert d["routine"] is False and "ddddddd is by someone" in d["reason"]
        os.environ.update({"COMPARE": str(tmp_path / "missing.json"), "OUT": str(out)})
        assert main(["range"]) == 1
        assert "could not be read" in json.loads((out / "range.json").read_text(encoding="utf-8"))["reason"]
    finally:
        os.environ.clear(); os.environ.update(saved)


def test_the_workflows_strip_a_promotion_tag_to_its_commit_and_call_the_range_rule(read_chassis):
    """Lesson #188: the first promoted `<sha8>-rYYYYMMDD` tag reached prod on 2026-09-11 and the daily job's rebuild
    step still demanded a bare 8-character tag. Both readers of the deployed tag now strip the suffix, and both
    lanes' shells call this module rather than judging a range themselves."""
    fresh = read_chassis("templates", "freshness.yml")
    assert 'LIVE_SHA8="${TAG%%-*}"' in fresh and "python3 -m infra.freshness range" in fresh
    assert "-f lane=routine" in fresh and 'SHA8="${BUILD_SHA8:-}"' in fresh
    assert "not an 8-character commit sha" in fresh          # the refusal stays, on the stripped value
    deploy = read_chassis("templates", "deploy.yml", optional=True)
    assert 'LIVE_SHA8="${LIVE_SHA8%%-*}"' in deploy and "python3 -m infra.freshness range" in deploy
