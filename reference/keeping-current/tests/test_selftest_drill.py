"""The drill lever (spec/keeping-current.md): a revision created with APP_SELFTEST_FAIL=1 reports one
deliberate failure, so the canary's rollback can be proven without breaking anything real. RED-first.

Fails if the lever is ignored (a drill revision would look healthy and the "rollback" would never be
exercised), if it fires on any value but "1" (a stray variable must not turn every deploy red), or if the
header stops naming the version the canary compares against.
"""
import io
import contextlib

from app import selftest
from infra.canary_rules import FAIL, PASS, decide, parse_selftest


def _run_selftest(monkeypatch, *, version, drill=False):
    monkeypatch.setenv("APP_VERSION", version)
    monkeypatch.setenv("ADAPTER_PROFILE", "local")
    monkeypatch.delenv("AZURE_CRED_MODE", raising=False)
    if drill:
        monkeypatch.setenv("APP_SELFTEST_FAIL", "1")
    else:
        monkeypatch.delenv("APP_SELFTEST_FAIL", raising=False)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = selftest.main([])
    return rc, out.getvalue()


def test_the_lever_reports_one_deliberate_failure_only_when_set_to_one():
    assert selftest._drill_lever({}) is None
    assert selftest._drill_lever({"APP_SELFTEST_FAIL": "0"}) is None
    assert selftest._drill_lever({"APP_SELFTEST_FAIL": ""}) is None
    row = selftest._drill_lever({"APP_SELFTEST_FAIL": "1"})
    assert row is not None
    name, ok, detail = row
    assert ok is False
    assert "drill" in name.lower() and "APP_SELFTEST_FAIL" in detail


def test_main_goes_red_on_the_lever_and_names_it_and_the_version(monkeypatch):
    """Product door: `python3 -m app.selftest` is what the canary runs inside the new revision. With no
    services configured every probe is SKIP, so the only thing that can fail is the lever — and it must."""
    rc, text = _run_selftest(monkeypatch, version="abcd1234-drill", drill=True)
    assert rc == 1
    assert "APP_VERSION = abcd1234-drill" in text
    assert any("drill" in ln.lower() and "FAIL" in ln for ln in text.splitlines())


def test_main_is_green_without_the_lever_in_a_bare_environment(monkeypatch):
    rc, text = _run_selftest(monkeypatch, version="abcd1234")
    assert rc == 0, text
    assert "APP_VERSION = abcd1234" in text


def test_selftest_stdout_is_what_the_canary_parses(monkeypatch):
    rc, text = _run_selftest(monkeypatch, version="abcd1234")
    assert rc == 0
    v = decide(parse_selftest(text), expected_version="abcd1234", drill=False)
    assert v.kind == PASS

    rc, text = _run_selftest(monkeypatch, version="abcd1234-drill", drill=True)
    assert rc == 1
    drilled = decide(parse_selftest(text), expected_version="abcd1234-drill", drill=True)
    assert drilled.kind == FAIL and drilled.drill_fired is True
