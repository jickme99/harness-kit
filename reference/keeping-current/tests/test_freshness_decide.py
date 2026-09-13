"""Phase 2 — the one decision the daily job makes, and the two things that may never happen (2026-09-10).

Five arms: GREEN_SILENT, PROMOTE, RED, HOLD, INCONCLUSIVE. Two modes: `dry` computes and prints the
decision and changes nothing; `full` is allowed to act. Fictional packages and CVE ids throughout.

The two rules with teeth, both straight out of the plan's review panel:

  * security F6 / failure F5 — NEVER dispatch prod while a prod approval is already waiting. Two
    pending "Review deployments" entries against the same environment is how a one-click gate turns
    into a pile nobody can tell apart, and approving the older of two queued runs ships the older
    image over the newer one.
  * the whole point of `dry` — a dry run may compute and print a promotion, and may not perform one.
    `will_promote` is the single flag the workflow's `if:` reads before it imports a digest, deletes
    a tag or dispatches `deploy.yml`, so `dry` has to be false there and nowhere else.
"""
import itertools

import pytest

from infra.freshness.decide import (
    DRY,
    FULL,
    GREEN_SILENT,
    HOLD,
    PROMOTE,
    RED,
    decide,
)
from infra.freshness.inventory import IDENTICAL, INCONCLUSIVE, MOVED, Verdict, Vulnerability

SAME = Verdict(IDENTICAL)
PATCHED = Verdict(MOVED, moved=(("flimsy-tls", "1.2.3-1.azl3", "1.2.4-1.azl3"),))
UNREADABLE = Verdict(INCONCLUSIVE, reason="the deployed image's inventory could not be read")

FIXABLE = Vulnerability("CVE-2026-90001", "flimsy-tls", "1.2.3-1.azl3", "1.2.4-1.azl3", "HIGH")
WORSE = Vulnerability("CVE-2026-90007", "packwright", "3.0.0", "4.0.0", "CRITICAL")
NO_FIX = Vulnerability("CVE-2026-90005", "gnarl", "9.9-4.azl3", "", "CRITICAL")

TAG = "4bb50595-cand-20260910"


def test_nothing_moved_and_nothing_found_is_green_and_silent():
    """The ordinary weekday. No click, no issue, no noise — but the summary still posts (heartbeat)."""
    d = decide(SAME, [], "", FULL, tag=TAG)

    assert d.kind == GREEN_SILENT
    assert d.will_promote is False
    assert d.is_red is False


def test_packages_moved_and_clean_promotes_the_scanned_tag():
    """The design's happy path: the bytes that were scanned are the bytes offered to the gate."""
    d = decide(PATCHED, [], "", FULL, tag=TAG)

    assert d.kind == PROMOTE
    assert d.tag == TAG
    assert d.will_promote is True
    assert d.moved == PATCHED.moved
    assert "flimsy-tls" in d.sentence()


def test_a_dry_run_computes_the_promotion_and_refuses_to_perform_it():
    """`dry` is the mode the maintainer runs first, by hand, before ever arming the real one.

    Fails if `will_promote` forgets the mode: a dry run would then import a digest into the prod
    registry and dispatch a prod approval — the exact opposite of what the word dry promises, and
    the failure would be discovered by the owner receiving an approval request he did not ask for.
    """
    d = decide(PATCHED, [], "", DRY, tag=TAG)

    assert d.kind == PROMOTE                 # the decision is computed...
    assert d.will_promote is False           # ...and is not permitted to act
    assert d.sentence().startswith("would promote")


def test_a_fixable_cve_the_rebuild_did_not_fix_is_red_with_the_package_and_the_fix():
    """RED is the owner's early warning — it has to say what and to what version, not just "red"."""
    d = decide(PATCHED, [FIXABLE], "", FULL, tag=TAG)

    assert d.kind == RED
    assert d.package == "flimsy-tls"
    assert d.fix == "1.2.4-1.azl3"
    assert d.is_red is True
    assert d.will_promote is False
    assert "flimsy-tls" in d.sentence() and "1.2.4-1.azl3" in d.sentence()


def test_a_finding_with_no_fix_anywhere_is_not_red():
    """"No fix yet" is reported in the summary and is not an action. Fails if RED fires on it —
    the job would be red every night, forever, for something nobody can do anything about, which is
    how a red light stops meaning anything."""
    assert decide(SAME, [NO_FIX], "", FULL, tag=TAG).kind == GREEN_SILENT
    assert decide(PATCHED, [NO_FIX], "", FULL, tag=TAG).kind == PROMOTE


def test_the_worst_fixable_finding_is_the_one_red_names():
    """One line has to carry the worst news, not the alphabetically first."""
    d = decide(SAME, [FIXABLE, WORSE], "", FULL, tag=TAG)

    assert (d.package, d.fix) == ("packwright", "4.0.0")


def test_a_comparison_that_could_not_be_read_is_inconclusive_and_carries_its_reason():
    """The third state reaches the decision unchanged: neither green nor a trigger."""
    d = decide(UNREADABLE, [], "", FULL, tag=TAG)

    assert d.kind == INCONCLUSIVE
    assert d.will_promote is False
    assert "could not be read" in d.reason


def test_a_prod_approval_already_waiting_holds_instead_of_filing_a_second_one():
    """F5/F6: one thing waiting for the owner at a time, and the summary says since when."""
    d = decide(PATCHED, [], "2026-09-09T14:03:00Z", FULL, tag=TAG)

    assert d.kind == HOLD
    assert d.will_promote is False
    assert "2026-09-09T14:03:00Z" in d.reason
    assert "already waiting" in d.reason


def test_a_pending_dispatch_never_yields_promote_in_any_combination():
    """The property, stated over the whole matrix rather than the one arm that happens to hit it.

    Fails if the pending check is dropped, inverted, or moved below the PROMOTE arm — each of which
    is a one-line edit that no single-case test would necessarily catch.
    """
    verdicts = [SAME, PATCHED, UNREADABLE]
    findings = [[], [FIXABLE], [NO_FIX], [FIXABLE, WORSE]]

    for verdict, found, mode in itertools.product(verdicts, findings, (DRY, FULL)):
        d = decide(verdict, found, "2026-09-09T14:03:00Z", mode, tag=TAG)
        assert d.kind != PROMOTE, (verdict.kind, [f.cve for f in found], mode)
        assert d.will_promote is False


def test_red_is_not_hidden_by_a_waiting_gate_or_by_an_unreadable_compare():
    """A pending click means "do not add a second one"; it does not mean "say nothing today"."""
    assert decide(PATCHED, [FIXABLE], "2026-09-09T14:03:00Z", FULL, tag=TAG).kind == RED
    assert decide(UNREADABLE, [FIXABLE], "", FULL, tag=TAG).kind == RED


def test_every_arm_is_reachable_in_both_modes_and_only_full_ever_acts():
    """`dry` changes what may HAPPEN, never what is DECIDED — the two must not drift apart."""
    cases = [(SAME, [], "", GREEN_SILENT), (PATCHED, [], "", PROMOTE), (SAME, [FIXABLE], "", RED),
             (PATCHED, [], "2026-09-09T14:03:00Z", HOLD), (UNREADABLE, [], "", INCONCLUSIVE)]

    for verdict, found, pending, expected in cases:
        dry, full = (decide(verdict, found, pending, m, tag=TAG) for m in (DRY, FULL))
        assert dry.kind == full.kind == expected
        assert dry.will_promote is False
        assert full.will_promote is (expected == PROMOTE)


def test_an_unknown_mode_is_refused():
    """Anything but `dry` or `full` is a typo in the workflow input, and a typo must not act."""
    with pytest.raises(ValueError):
        decide(PATCHED, [], "", "FULL", tag=TAG)
    with pytest.raises(ValueError):
        decide(PATCHED, [], "", "", tag=TAG)


def test_a_promotion_with_no_candidate_tag_is_refused():
    """PROMOTE names the tag that will be imported; an empty one would retag nothing, or everything."""
    with pytest.raises(ValueError):
        decide(PATCHED, [], "", FULL, tag="")


def test_red_says_where_the_package_lives_when_the_scan_knows():
    """"msgpack 1.1.2 is fixable" is a riddle; "found in Python: .../pip/_vendor/msgpack" is an answer.
    Fails if the location is not carried into the sentence — and if a location is invented when the
    scan gave none."""
    vendored = Vulnerability("GHSA-0000-0000-0000", "msgpack", "1.1.2", "1.2.1", "HIGH",
                             target="Python", path="usr/lib/python3.12/site-packages/pip/_vendor/msgpack")
    d = decide(SAME, [vendored], "", FULL, tag=TAG)
    assert d.kind == RED
    assert d.where == "Python: usr/lib/python3.12/site-packages/pip/_vendor/msgpack"
    assert "found in Python: usr/lib/python3.12/site-packages/pip/_vendor/msgpack" in d.sentence()
    assert "found in" not in decide(SAME, [FIXABLE], "", FULL, tag=TAG).sentence()


def test_an_open_deploy_issue_holds_a_promotion_and_never_hides_red():
    """Phase C (spec/keeping-current.md C): the routine lane refuses while a `deploy` issue is open, so
    a promotion is HELD with the issue named — in words the summary can print — instead of dispatching
    a run that would only say no. RED still wins, and a green day is still green: the hold applies to
    the one arm that would act."""
    held = "deploy issue #12 is open (since 2026-09-11T02:00:00Z)"
    d = decide(PATCHED, [], "", FULL, tag=TAG, held_by=held)
    assert d.kind == HOLD and d.will_promote is False
    assert held in d.reason and "closed until a person closes it" in d.reason
    assert held in d.sentence()
    assert decide(PATCHED, [FIXABLE], "", FULL, tag=TAG, held_by=held).kind == RED
    assert decide(SAME, [], "", FULL, tag=TAG, held_by=held).kind == GREEN_SILENT
    # Both holds at once: the waiting approval is named first (F5/F6 is the older rule).
    both = decide(PATCHED, [], "2026-09-09T14:03:00Z", FULL, tag=TAG, held_by=held)
    assert both.kind == HOLD and "already waiting" in both.reason
