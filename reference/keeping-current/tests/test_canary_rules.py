"""The canary's verdict on a self-test transcript — pure rules, RED-first (spec/keeping-current.md B3).

`az containerapp exec` returns 0 whatever the remote command did (measured 2026-09-11: "No module named
pip" came back with exit 0), so the transcript is the only evidence. Three outcomes, never two:
PASS, FAIL, and COULD_NOT_RUN — a transcript with no self-test header is a door that did not answer,
never a passing app and never a failing one. A drill run is a run that MUST fail on the lever.
"""
import pytest

from infra.canary_rules import COULD_NOT_RUN, FAIL, PASS, decide, health_body_ok, parse_selftest

GREEN = """INFO: Successfully connected to container: 'example-app-prod'. [ Revision: 'x', Replica: 'y']
AZURE_CRED_MODE = entra   (adapter profile: azure)
APP_VERSION = abcd1234
------------------------------------------------------------------------
cache (redis)          PASS  OK
database               PASS  query round-trip; server sees user 'example-app-prod'
------------------------------------------------------------------------
auth gate              PASS  the configured checks both decide correctly
------------------------------------------------------------------------
all 8 configured service(s) reachable under mode 'entra'.
INFO: received success status from cluster
"""
RED = GREEN.replace("database               PASS  query round-trip; server sees user 'example-app-prod'",
                    "database               FAIL  connection refused").replace(
    "all 8 configured service(s) reachable under mode 'entra'.", "1 service(s) FAILED under mode 'entra'.")
DRILL = GREEN.replace("all 8 configured service(s) reachable under mode 'entra'.",
                      "drill (APP_SELFTEST_FAIL) FAIL  the drill lever is set on this revision\n1 service(s) FAILED under mode 'entra'.")
DOOR_404 = """ERROR: The resource you are looking for has been removed, had its name changed, or is temporarily unavailable.
"""
DOOR_429 = "ERROR: (TooManyRequests) retry after 600 seconds\n"


def test_a_green_transcript_with_the_expected_version_passes():
    r = parse_selftest(GREEN)
    assert r.ran and r.version == "abcd1234" and r.passed and r.failed == ()
    v = decide(r, expected_version="abcd1234", drill=False)
    assert v.kind == PASS


def test_a_failing_service_fails_and_names_the_service():
    r = parse_selftest(RED)
    assert r.ran and not r.passed and r.failed == ("database",)
    v = decide(r, expected_version="abcd1234", drill=False)
    assert v.kind == FAIL and "database" in v.reason


def test_the_wrong_version_fails_even_when_every_service_passed():
    """The exec landed on the previous revision (or the new one inherited an old APP_VERSION): a green
    transcript from the wrong bytes is a FAIL, never a PASS."""
    v = decide(parse_selftest(GREEN), expected_version="ffff0000", drill=False)
    assert v.kind == FAIL and "abcd1234" in v.reason and "ffff0000" in v.reason


@pytest.mark.parametrize("transcript", [DOOR_404, DOOR_429, "", "INFO: Successfully connected\n"])
def test_a_door_that_did_not_answer_is_the_third_outcome(transcript):
    r = parse_selftest(transcript)
    assert not r.ran
    v = decide(r, expected_version="abcd1234", drill=False)
    assert v.kind == COULD_NOT_RUN
    assert "could not run" in v.reason.lower()


def test_a_drill_must_fail_on_the_lever_and_nothing_else():
    """The drill proves the rollback fires. A drill transcript that is green means the lever was not on
    the revision (the wiring is wrong), which is a FAIL of the drill; a drill that fails on a REAL service
    is a real failure and is reported as such, not as a successful drill."""
    ok = decide(parse_selftest(DRILL), expected_version="abcd1234", drill=True)
    assert ok.kind == FAIL and ok.drill_fired is True
    green_drill = decide(parse_selftest(GREEN), expected_version="abcd1234", drill=True)
    assert green_drill.kind == FAIL and green_drill.drill_fired is False and "lever" in green_drill.reason.lower()
    real = decide(parse_selftest(RED), expected_version="abcd1234", drill=True)
    assert real.kind == FAIL and real.drill_fired is False and "database" in real.reason


def test_the_lever_on_a_real_deploy_is_a_fail():
    v = decide(parse_selftest(DRILL), expected_version="abcd1234", drill=False)
    assert v.kind == FAIL and v.drill_fired is True
    assert "not a drill" in v.reason.lower()


def test_a_transcript_cut_short_fails_not_passes():
    cut = GREEN.split("all 8")[0]
    v = decide(parse_selftest(cut), expected_version="abcd1234", drill=False)
    assert v.kind == FAIL
    assert "closing line" in v.reason.lower()


@pytest.mark.parametrize("body, ok", [
    ('{"status":"ok","version":"x"}', True),
    ('{"status": "ok", "version": "x"}', True),
    ('{\n  "status" : "ok"\n}', True),
    ('{"status":"okay"}', False),
    ('{"status":"fail"}', False),
    ("", False),
])
def test_health_accepts_spaced_json_and_rejects_okay(body, ok):
    assert health_body_ok(body) is ok
