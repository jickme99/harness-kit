"""Phase 2 — the one page the owner (and anyone they forward it to) actually read (2026-09-10).

This is the job summary written to `$GITHUB_STEP_SUMMARY` on EVERY run, including the quiet ones —
it is the heartbeat that makes "no news" mean "checked, clean" rather than "nobody looked" (security
lens F3). Fictional digests, packages and CVE ids throughout.

Three properties it is worth pinning here, because all three are the kind that rot silently:

  * every section present on every run — a summary missing its findings table on the day there were
    findings is worse than no summary, because the run is still green;
  * the MONITORED-ONLY marker on `example-job` and `example-mcp` rows (failure lens F4);
  * no raw 64-character digest inside the table. The table is read on a phone and pasted into a mail;
    a full digest per row makes it unreadable, and the full base digest is recorded
    once, in its own section, where it is an audit record rather than noise.
"""
import os
os.environ.setdefault("FRESHNESS_MONITORED_ONLY", "example-job,example-mcp")  # the kit ships no roster
import pytest
import re

from infra.freshness.findings import Finding, LiveImage, classify
from infra.freshness.decide import DRY, FULL, decide
from infra.freshness.inventory import IDENTICAL, INCONCLUSIVE, MOVED, Verdict, Vulnerability
from infra.freshness.summary import render


def digest(seed):
    return "sha256:" + (f"{seed:02x}" * 32)


APP_LIVE, APP_OLD, JOB_LIVE, JOB_OLD, MCP_LIVE, MCP_OLD = (digest(s) for s in (0x11, 0x22, 0x99, 0x44, 0x88, 0x77))
BASE_DIGEST = digest(0xBE)

LIVE = {
    "example-app": LiveImage("example-app", "abcd1234", APP_LIVE, frozenset({APP_LIVE, APP_OLD})),
    "example-job": LiveImage("example-job", "v40", JOB_LIVE, frozenset({JOB_LIVE, JOB_OLD})),
    "example-mcp": LiveImage("example-mcp", "v2", MCP_LIVE, frozenset({MCP_LIVE, MCP_OLD})),
}

FINDINGS = [
    Finding("example-app", APP_OLD, "flimsy-tls", "1.2.3-1.azl3", "1.2.4-1.azl3", ("CVE-2026-90001",), 8.7),
    Finding("example-job", JOB_OLD, "packwright", "3.0.0", "4.0.0", ("CVE-2026-90002",), 7.1),
    Finding("example-mcp", MCP_OLD, "flimsy-tls", "1.2.3-1", "1.2.4-1", ("CVE-2026-90001",), 8.7),
]

ROWS = classify(FINDINGS, LIVE)
PATCHED = Verdict(MOVED, moved=(("flimsy-tls", "1.2.3-1.azl3", "1.2.4-1.azl3"),))
PROMOTION = decide(PATCHED, [], "", FULL, tag="4bb50595-cand-20260910")

SECTIONS = ("Defender findings", "Package comparison", "Decision", "Base image")


def summary(**kw):
    """The full call, with every argument the workflow passes, overridable per test."""
    kw.setdefault("date", "2026-09-10")
    kw.setdefault("mode", FULL)
    kw.setdefault("rows", ROWS)
    kw.setdefault("checked", True)
    kw.setdefault("verdict", PATCHED)
    kw.setdefault("decision", PROMOTION)
    kw.setdefault("base_digest", BASE_DIGEST)
    return render(**kw)


def table_lines(out):
    return [ln for ln in out.splitlines() if ln.startswith("|")]


def test_every_section_is_present_on_every_run():
    """A run that cannot render one of its four sections has failed, whatever its exit code says."""
    out = summary()

    for section in SECTIONS:
        assert section in out, section


def test_the_heartbeat_line_carries_the_date_and_the_mode():
    """The dead man's switch: the maintainer's close-out reads this line and the date on it.

    Fails if the date or the mode drops out — a stale summary from three days ago would then be
    indistinguishable from today's, which is the whole failure the heartbeat exists to prevent.
    """
    out = summary(date="2026-09-11", mode=DRY)

    heartbeat = next(ln for ln in out.splitlines() if "eartbeat" in ln)
    assert "2026-09-11" in heartbeat
    assert "dry" in heartbeat


def test_each_finding_gets_its_own_row_labelled_with_its_state():
    """One row per finding per digest — never one sample per recommendation (failure lens F3)."""
    out = summary()
    rows = [ln for ln in table_lines(out) if "flimsy-tls" in ln or "packwright" in ln]

    assert len(rows) == 3
    assert sum(1 for ln in rows if "STALE" in ln) == 3


def test_the_other_two_repositories_are_marked_monitored_only_and_ours_is_not():
    """Failure lens F4, in the artefact the owner actually reads.

    Fails if the marker is dropped or applied to everything: a row that cleans itself up tonight
    would read exactly like one that needs a person to go and delete an image by hand.
    """
    out = summary()

    for line in table_lines(out):
        if "example-job" in line or "example-mcp" in line:
            assert "MONITORED-ONLY" in line
        if "example-app" in line and "flimsy-tls" in line:
            assert "MONITORED-ONLY" not in line
    assert "built elsewhere" in out                      # and the marker is explained once, below the table


def test_no_raw_digest_longer_than_nineteen_characters_reaches_the_table():
    """`sha256:` plus twelve hex is enough to identify a manifest and short enough to read."""
    for line in table_lines(summary()):
        assert re.search(r"sha256:[0-9a-f]{13,}", line) is None, line


def test_the_base_image_digest_is_recorded_in_full_once():
    """Security lens F11: the floating base tag leaves no record of what it resolved to. This is it.

    Fails if the base digest is shortened along with the table's — a twelve-hex prefix is a label,
    not the record you would use to prove months later which base a build was made from.
    """
    out = summary()

    assert BASE_DIGEST in out
    assert out.count(BASE_DIGEST) == 1


def test_nothing_found_and_checked_says_checked_clean():
    """The sentence that makes silence mean something. Security lens F3, stated in words."""
    out = summary(rows=[], checked=True, verdict=Verdict(IDENTICAL), decision=decide(
        Verdict(IDENTICAL), [], "", FULL, tag="4bb50595-cand-20260910"))

    assert "checked, clean" in out.lower()


def test_a_read_that_did_not_complete_never_says_clean():
    """The third state in the summary: no findings AND not checked is the broken day, not a good one.

    Fails if `checked` is ignored — the worst possible summary, because it is green, empty and wrong
    on exactly the day the read fell over.
    """
    out = summary(rows=[], checked=False, verdict=Verdict(INCONCLUSIVE, reason="the read failed"))

    assert "checked, clean" not in out.lower()
    assert "NOT CHECKED" in out


def test_the_comparison_verdict_is_spelled_out_with_the_packages_that_moved():
    """"Packages moved" is the sentence on the approval screen; it has to name them."""
    out = summary()

    assert "flimsy-tls" in out
    assert "1.2.3-1.azl3" in out and "1.2.4-1.azl3" in out


def test_an_inconclusive_comparison_shows_its_reason_and_not_a_verdict():
    out = summary(verdict=Verdict(INCONCLUSIVE, reason="the deployed image's inventory could not be read"),
                  decision=decide(Verdict(INCONCLUSIVE, reason="the deployed image's inventory could not be read"),
                                  [], "", FULL, tag="4bb50595-cand-20260910"))

    assert "INCONCLUSIVE" in out
    assert "could not be read" in out
    assert "IDENTICAL" not in out


def test_a_day_with_no_rebuild_says_so_rather_than_calling_itself_inconclusive():
    """Six days out of seven there is no rebuild: the page must not read as a broken one.

    "INCONCLUSIVE" is the word for a comparison that FAILED. A Tuesday with nothing fixable open
    never ran a comparison at all, and printing the failure word on the ordinary day is how a daily
    page trains its reader to ignore it — which costs the heartbeat its entire purpose.
    """
    out = summary(rebuilt=False, verdict=Verdict(INCONCLUSIVE, reason="no rebuild ran this run"),
                  decision=decide(Verdict(INCONCLUSIVE, reason="no rebuild ran this run"), [], "",
                                  FULL, tag="4bb50595-cand-20260910"),
                  base_digest="")

    assert "No rebuild ran" in out
    assert "INCONCLUSIVE" not in out
    for section in SECTIONS:
        assert section in out, section


def test_the_decision_is_stated_in_the_summary_in_the_words_the_decision_used():
    """One decision, one sentence, rendered from the Decision itself — never re-derived here."""
    assert PROMOTION.sentence() in summary()


def test_a_dry_run_says_would_promote_rather_than_promote():
    """The mode has to be legible from the page, not only from the workflow's inputs."""
    dry = decide(PATCHED, [], "", DRY, tag="4bb50595-cand-20260910")

    out = summary(mode=DRY, decision=dry)

    assert "would promote" in out


def test_accepted_cves_appear_as_known_accepted_rather_than_disappearing():
    """Failure lens F10: an accepted finding is shown, with its CVE, every run. Never dropped."""
    accepted = (Vulnerability("CVE-2026-90006", "sheafy", "0.11.2", "0.12.0", "HIGH"),)

    out = summary(accepted=accepted)

    assert "CVE-2026-90006" in out
    assert "known, accepted" in out


def test_the_retention_outcome_rides_in_the_same_summary():
    """The prune step is `continue-on-error`, so its outcome only exists if the summary carries it."""
    out = summary(retention="Registry retention: FAILED (exit 2) — run it by hand.")

    assert "Registry retention: FAILED (exit 2)" in out


def test_the_policy_section_names_the_offending_image():
    """Layer three of the no-pip guard: the page shows every live image's verdict and says POLICY RED
    when one carries a package manager. Fails if the table or the verdict line is missing."""
    out = render(date="2026-09-11", mode=FULL, rows=[], checked=True, verdict=Verdict(IDENTICAL),
                 decision=decide(Verdict(IDENTICAL), [], "", FULL, tag="abcd1234-cand-20260911"),
                 policy=[("example-app", "abcd1234", "CLEAN"), ("example-job", "v41", "VIOLATION: pip is importable")])
    assert "no package manager in a running image" in out
    assert "| `example-job` | `v41` | VIOLATION: pip is importable |" in out
    assert "POLICY RED" in out


def test_a_run_without_the_policy_table_says_not_checked():
    """The third state again: no table is 'not checked', never 'clean'."""
    out = render(date="2026-09-11", mode=FULL, rows=[], checked=True, verdict=Verdict(IDENTICAL),
                 decision=decide(Verdict(IDENTICAL), [], "", FULL, tag="abcd1234-cand-20260911"), policy=None)
    assert "Policy" in out and "not checked" in out.lower()
    assert "All live images clean" not in out


@pytest.fixture(autouse=True)
def _monitored_only_roster(monkeypatch):
    """The kit's default MONITORED-ONLY roster is EMPTY (a template must not name one project's
    registries); these tests exercise the marker, so they name two example repositories the way a
    project would — through the environment."""
    monkeypatch.setenv("FRESHNESS_MONITORED_ONLY", "example-job,example-mcp")
