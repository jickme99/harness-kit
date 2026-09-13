"""The daily-job image refresh rules (infra/refresh_rules.py) — RED-first, fictional data. 2026-09-12."""
import pytest

from infra.refresh_rules import (base_tag, candidate_tag, execution_verdict, last_scheduled_verdict, rebuild_plan,
                                 refresh_tag, rollback_command)


def test_the_image_tag_names_a_git_tag_and_a_promoted_rebuild_still_does():
    assert base_tag("v41") == "v41"
    assert base_tag("v41-r20260912") == "v41"
    assert refresh_tag("v41", "20260915") == "v41-r20260915" and candidate_tag("v41-r20260912", "20260915") == "v41-cand-20260915"
    for bad in ("latest", "41", "v41-cand-20260912", "ab12cd34", "", None, "v41-r2026091"):
        with pytest.raises(ValueError):
            base_tag(bad)


def test_rebuild_days_and_an_open_issue_holds_everything():
    assert rebuild_plan(rebuild_input="auto", weekday=1, open_issue="").rebuild
    assert not rebuild_plan(rebuild_input="auto", weekday=3, open_issue="").rebuild
    assert rebuild_plan(rebuild_input="force", weekday=3, open_issue="").rebuild
    assert not rebuild_plan(rebuild_input="skip", weekday=1, open_issue="").rebuild
    held = rebuild_plan(rebuild_input="force", weekday=1, open_issue="7")
    assert not held.rebuild and "#7" in held.why


def test_an_execution_has_three_states_and_only_succeeded_switches():
    assert execution_verdict("Succeeded") == "SUCCEEDED"
    assert execution_verdict("Failed") == "FAILED" and execution_verdict("Stopped") == "FAILED"
    for s in ("Running", "Processing", "", None, "Unknown"):
        assert execution_verdict(s) == "UNKNOWN"


def test_the_latest_finished_execution_is_read_and_a_failure_names_the_refreshed_image():
    execs = [{"name": "a", "status": "Succeeded", "start": "2026-09-11T11:00:00+00:00"},
             {"name": "b", "status": "Failed", "start": "2026-09-12T11:00:00+00:00"},
             {"name": "c", "status": "Running", "start": "2026-09-13T11:00:00+00:00"}]
    v, name, sentence = last_scheduled_verdict(execs, refreshed_tag="v41-r20260912")
    assert v == "FAILED" and name == "b" and "v41-r20260912" in sentence
    v, name, _ = last_scheduled_verdict(execs[:1], refreshed_tag="")
    assert v == "SUCCEEDED" and name == "a"
    assert last_scheduled_verdict([], refreshed_tag="")[0] == "UNKNOWN"
    assert last_scheduled_verdict([execs[2]], refreshed_tag="")[0] == "UNKNOWN"


def test_the_rollback_command_is_the_previous_tag_on_the_job():
    cmd = rollback_command(registry="exampleacr.azurecr.io", repository="example-job", previous_tag="v41",
                           job="example-daily", resource_group="rg-example")
    assert cmd == "az containerapp job update -n example-daily -g rg-example --image exampleacr.azurecr.io/example-job:v41"
