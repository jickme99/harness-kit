"""Phase 2 — reading what Defender says, and saying which rows need a hand (2026-09-10).

Every row below is FICTIONAL: the digests are made-up hex, the packages and CVE ids are invented.
The SHAPES are real — they are the ones the findings log G3/G4 recorded on 2026-09-10,
and the page envelope is the one `az graph query` actually returns (checked read-only the same day:
the CLI spells the envelope `total_records` / `skip_token`, the REST API spells it `totalRecords` /
`$skipToken`, and both have to be readable or the truncation guard is guarding nothing).

The two rules these tests exist for, both from the plan's review panel:

  * the failure lens's F3 — the query on file collapses every recommendation to ONE sample resource
    and would truncate at a page boundary without saying so. So the read REFUSES when the rows it
    got back do not add up to the rows the service said existed. Reject, never truncate.
  * the failure lens's F4 — `example-job` and `example-mcp` get the daily read but no
    rebuild until Phase 3. A row that fixes itself tonight must never look like one that needs a
    hand, so every row from those two repositories carries MONITORED-ONLY.

EMPTY BEATS WRONG, and a failed read is a THIRD state: an empty result is empty AND `checked`, which
is what lets the summary say "checked, clean" rather than the silence that means nobody looked.
"""
import os
os.environ.setdefault("FRESHNESS_MONITORED_ONLY", "example-job,example-mcp")  # the kit ships no roster
import json

import pytest

from infra.freshness.findings import (
    DEPLOYED,
    GONE,
    STALE,
    Finding,
    FreshnessRefused,
    LiveImage,
    classify,
    parse_resource_graph,
)

# --------------------------------------------------------------------------------------------------
# fictional fixtures
# --------------------------------------------------------------------------------------------------

def digest(seed):
    """A fictional manifest digest: 64 hex characters, distinct in its first byte."""
    return "sha256:" + (f"{seed:02x}" * 32)


APP_LIVE = digest(0x11)          # what example-app-prod is running
APP_OLD = digest(0x22)           # a superseded example-app manifest still in the registry
APP_DELETED = digest(0x33)       # a digest the registry no longer holds
JOB_V1 = digest(0x44)            # example-job, superseded
JOB_V2 = digest(0x55)
JOB_V3 = digest(0x66)
MCP_V1 = digest(0x77)            # example-mcp, superseded
MCP_LIVE = digest(0x88)
JOB_LIVE = digest(0x99)


def assessment(repository, dig, software, detected, fixed, cves, cvss="7.1",
               first_seen="2026-08-28T04:11:02Z"):
    """One `microsoft.security/assessments` row in the shape the Resource Graph read projects."""
    return {
        "properties": {
            "displayName": f"Update {software}",
            "status": {"code": "Unhealthy", "firstEvaluationDate": first_seen},
            "resourceDetails": {"Id": f"{repository}-images-{dig}"},
            "additionalData": {
                "SoftwareName": software,
                "MaxCvssScore": cvss,
                "ScannersDetails": {
                    "mdvm": {
                        "FixedVersion": fixed,
                        "DetectedSoftwareVersions": [detected],
                        "CvesIds": list(cves),
                    }
                },
            },
        }
    }


def page(rows, total=None, skip_token=None):
    """The envelope `az graph query` returns, snake_case as the CLI prints it."""
    out = {"count": len(rows), "data": rows, "total_records": len(rows) if total is None else total}
    if skip_token:
        out["skip_token"] = skip_token
    return out


G4_ROWS = [
    # four digests in TWO OTHER repositories — the 2026-09-10 shape, fictional contents
    assessment("example-job", JOB_V1, "flimsy-tls", "1.2.3-1", "1.2.4-1", ["CVE-2026-90001"]),
    assessment("example-job", JOB_V2, "flimsy-tls", "1.2.3-1", "1.2.4-1", ["CVE-2026-90001"]),
    assessment("example-job", JOB_V3, "packwright", "3.0.0", "4.0.0", ["CVE-2026-90002"]),
    assessment("example-mcp", MCP_V1, "flimsy-tls", "1.2.3-1", "1.2.4-1", ["CVE-2026-90001"]),
]

LIVE = {
    # example-app's deployed image is CLEAN in the G4 shape: no finding names APP_LIVE at all
    "example-app": LiveImage("example-app", "abcd1234", APP_LIVE, frozenset({APP_LIVE, APP_OLD})),
    "example-job": LiveImage("example-job", "v40", JOB_LIVE,
                                frozenset({JOB_LIVE, JOB_V1, JOB_V2})),
    "example-mcp": LiveImage("example-mcp", "v2", MCP_LIVE,
                                     frozenset({MCP_LIVE, MCP_V1})),
}


# --------------------------------------------------------------------------------------------------
# parse_resource_graph — the read itself
# --------------------------------------------------------------------------------------------------

def test_the_g4_shape_resolves_every_row_to_its_own_repository_and_digest():
    """Four findings in two repositories, each resolved to ITS OWN digest — not one sample per group.

    Fails if the parse collapses rows that share a recommendation (the `any(rid)` shape the query on
    file had, failure lens F3): three of the four rows here share the software name `flimsy-tls`, and
    a collapsing read would return one of them and drop the rest silently.
    """
    found = parse_resource_graph([page(G4_ROWS)])

    assert len(found) == 4
    assert sorted(f.digest for f in found) == sorted([JOB_V1, JOB_V2, JOB_V3, MCP_V1])
    assert sorted({f.repository for f in found}) == sorted(["example-mcp", "example-job"])
    one = next(f for f in found if f.digest == JOB_V3)
    assert (one.software, one.detected, one.fixed) == ("packwright", "3.0.0", "4.0.0")
    assert one.cves == ("CVE-2026-90002",)
    assert one.cvss == 7.1
    assert one.first_seen == "2026-08-28T04:11:02Z"


def test_pages_are_read_in_full_and_concatenated():
    """A skip-token loop hands the parser several pages; every row in every page has to arrive.

    Fails if only the first (or last) page is read — the shape of a truncation that returns valid
    JSON and looks exactly like "fewer unhealthy things exist".
    """
    pages = [page(G4_ROWS[:2], total=4, skip_token="tok"), page(G4_ROWS[2:], total=4)]

    found = parse_resource_graph(pages)

    assert len(found) == 4
    assert found.total_records == 4


def test_a_page_count_mismatch_is_refused_not_truncated():
    """`totalRecords` says four, four minus one arrived: REFUSE. The whole read is a third state.

    Fails if a short read is accepted — the keep half of the job would then report "three findings"
    on a day when four exist, which reads like good news and is the F3 failure exactly.
    """
    with pytest.raises(FreshnessRefused) as e:
        parse_resource_graph([page(G4_ROWS[:3], total=4)])

    assert "4" in str(e.value) and "3" in str(e.value)


def test_more_rows_than_the_service_counted_is_refused_too():
    """The mismatch guard is an equality, not a floor: a page that over-delivers is also unexplained."""
    with pytest.raises(FreshnessRefused):
        parse_resource_graph([page(G4_ROWS, total=3)])


def test_pages_that_disagree_about_the_total_are_refused():
    """Two pages of the same query must agree on how many rows exist, or the read is not one read.

    Fails if the parser takes the last page's total (or the first's) and reconciles against that —
    a scan landing mid-pagination would then silently decide the count for us.
    """
    with pytest.raises(FreshnessRefused):
        parse_resource_graph([page(G4_ROWS[:2], total=4, skip_token="tok"),
                              page(G4_ROWS[2:], total=2)])


def test_an_empty_result_is_empty_and_checked_not_an_error():
    """Defender reporting nothing is GOOD NEWS and has to be sayable as such.

    Fails if an empty read raises (a clean day would turn the job red) or if it comes back without
    `checked` (the summary could then only print silence, which is the one thing "no news" must not
    be allowed to mean — security lens F3).
    """
    found = parse_resource_graph([page([], total=0)])

    assert len(found) == 0
    assert not found
    assert found.checked is True
    assert found.total_records == 0
    assert list(found) == []


def test_no_pages_at_all_is_a_failed_read_not_a_clean_one():
    """Zero PAGES is not zero FINDINGS: nobody answered. Refuse rather than report a clean day."""
    with pytest.raises(FreshnessRefused):
        parse_resource_graph([])


def test_a_page_with_no_total_is_refused():
    """Without the service's own count there is nothing to check the rows against."""
    with pytest.raises(FreshnessRefused):
        parse_resource_graph([{"data": G4_ROWS, "count": 4}])


def test_the_rest_spelling_of_the_envelope_is_understood():
    """`az graph query` prints `total_records`; the REST API returns `totalRecords`. Both are read.

    Fails if only one spelling is honoured — the other would land in the "no total" arm and refuse a
    perfectly good read, or (worse, if the guard were lenient) skip the count check entirely.
    """
    found = parse_resource_graph([{"totalRecords": 4, "count": 4, "data": G4_ROWS, "$skipToken": None}])

    assert len(found) == 4


def test_the_long_arm_resource_id_form_is_understood():
    """Defender also writes the image id as an ARM path; the repository and digest are the same two."""
    row = assessment("example-app", APP_OLD, "flimsy-tls", "1.2.3-1", "1.2.4-1", ["CVE-2026-90001"])
    row["properties"]["resourceDetails"]["Id"] = (
        "/subscriptions/00000000-0000-0000-0000-000000000000/resourcegroups/example-rg/providers/"
        "microsoft.containerregistry/registries/exampleacr/repositories/example-app/images/"
        + APP_OLD
    )

    found = parse_resource_graph([page([row])])

    assert (found[0].repository, found[0].digest) == ("example-app", APP_OLD)


def test_a_row_whose_resource_id_names_no_digest_is_refused_never_dropped():
    """A row we cannot resolve to an image is not a row we may quietly skip.

    Fails if unparseable rows are filtered out: the count guard would still pass (we counted them),
    and the findings table would be short by exactly the rows nobody could read.
    """
    row = assessment("example-app", APP_OLD, "flimsy-tls", "1.2.3-1", "1.2.4-1", ["CVE-2026-90001"])
    row["properties"]["resourceDetails"]["Id"] = "some-other-kind-of-resource"

    with pytest.raises(FreshnessRefused):
        parse_resource_graph([page([row])])


def test_scanner_details_that_arrive_as_a_json_string_are_read():
    """Defender's `additionalData` values are sometimes JSON-encoded strings rather than objects."""
    row = assessment("example-job", JOB_V1, "flimsy-tls", "1.2.3-1", "1.2.4-1",
                     ["CVE-2026-90001", "CVE-2026-90003"])
    ad = row["properties"]["additionalData"]
    ad["ScannersDetails"] = json.dumps(ad["ScannersDetails"])

    found = parse_resource_graph([page([row])])

    assert found[0].fixed == "1.2.4-1"
    assert found[0].cves == ("CVE-2026-90001", "CVE-2026-90003")


def test_a_finding_with_no_fix_anywhere_is_not_fixable():
    """"No fix yet" is a real state: it is reported, and it never triggers a rebuild.

    Fails if an empty `FixedVersion` reads as fixable — the job would rebuild every night chasing a
    patch that does not exist, and the rebuild's own scan would report it again.
    """
    row = assessment("example-app", APP_LIVE, "flimsy-tls", "1.2.3-1", "", ["CVE-2026-90004"])

    found = parse_resource_graph([page([row])])

    assert found[0].fixed == ""
    assert found[0].fixable is False


def test_a_cvss_that_is_not_a_number_is_none_rather_than_a_refusal():
    """The score decorates the table; it decides nothing. An unreadable one must not fail the read."""
    row = assessment("example-app", APP_LIVE, "flimsy-tls", "1.2.3-1", "1.2.4-1",
                     ["CVE-2026-90001"], cvss="n/a")

    assert parse_resource_graph([page([row])])[0].cvss is None


# --------------------------------------------------------------------------------------------------
# classify — DEPLOYED / STALE / GONE, and the MONITORED-ONLY marker
# --------------------------------------------------------------------------------------------------

def test_a_finding_on_the_running_image_is_deployed():
    """The one state that can mean "act today". Fails if the digest comparison goes."""
    f = Finding("example-app", APP_LIVE, "flimsy-tls", "1.2.3-1", "1.2.4-1", ("CVE-2026-90001",))

    assert classify([f], LIVE)[0].state == DEPLOYED


def test_a_finding_on_a_superseded_image_still_in_the_registry_is_stale():
    """G3's shape: the deployed image was already patched; the finding sat on an older manifest.

    Fails if STALE and DEPLOYED are conflated — every retention run's leftovers would then read as
    "prod is vulnerable", which is the false alarm this whole plan exists to remove.
    """
    f = Finding("example-app", APP_OLD, "flimsy-tls", "1.2.3-1", "1.2.4-1", ("CVE-2026-90001",))

    assert classify([f], LIVE)[0].state == STALE


def test_a_finding_on_a_digest_the_registry_no_longer_holds_is_gone():
    """Defender's view lags a delete; a row for an image that is already gone says so in the table.

    Fails if an absent digest falls into STALE — the summary would keep asking for a prune that has
    already happened, every day, until Defender's next scan.
    """
    f = Finding("example-app", APP_DELETED, "flimsy-tls", "1.2.3-1", "1.2.4-1", ("CVE-2026-90001",))

    assert classify([f], LIVE)[0].state == GONE


def test_the_g4_shape_is_four_monitored_only_rows_beside_a_clean_deployed_image():
    """The whole 2026-09-10 picture in one assertion: nothing here is example-app's to fix.

    Fails if the MONITORED-ONLY marker is dropped (failure lens F4): four rows that a human has to
    go and delete by hand would then be presented exactly like rows the robot cleans up tonight.
    """
    rows = classify(parse_resource_graph([page(G4_ROWS)]), LIVE)

    assert len(rows) == 4
    assert all(r.monitored_only for r in rows)
    assert all(r.marker() == "MONITORED-ONLY" for r in rows)
    assert not any(r.repository == "example-app" for r in rows)
    assert not any(r.needs_a_hand for r in rows)


def test_ma_deal_app_rows_are_never_monitored_only():
    """The marker is the difference between the two halves of the design; it must not spread.

    Fails if the marker is applied to every row — the one repository the job CAN fix would look
    unfixable, and the rebuild half would read as dead code.
    """
    f = Finding("example-app", APP_LIVE, "flimsy-tls", "1.2.3-1", "1.2.4-1", ("CVE-2026-90001",))
    row = classify([f], LIVE)[0]

    assert row.monitored_only is False
    assert row.marker() == ""


def test_a_deployed_and_fixable_ma_deal_app_row_is_the_one_that_needs_a_hand():
    """This flag IS the same-day rebuild trigger, so its three conditions are pinned together."""
    fixable = Finding("example-app", APP_LIVE, "flimsy-tls", "1.2.3-1", "1.2.4-1", ("CVE-2026-90001",))
    no_fix = Finding("example-app", APP_LIVE, "gnarl", "9.9", "", ("CVE-2026-90004",))
    stale = Finding("example-app", APP_OLD, "flimsy-tls", "1.2.3-1", "1.2.4-1", ("CVE-2026-90001",))
    other = Finding("example-job", JOB_LIVE, "flimsy-tls", "1.2.3-1", "1.2.4-1", ("CVE-2026-90001",))

    hands = {f"{r.software}/{r.repository}/{r.state}": r.needs_a_hand
             for r in classify([fixable, no_fix, stale, other], LIVE)}

    assert hands["flimsy-tls/example-app/DEPLOYED"] is True      # deployed, fixable, ours
    assert hands["gnarl/example-app/DEPLOYED"] is False          # no fix exists
    assert hands["flimsy-tls/example-app/STALE"] is False        # retention's problem, not a rebuild's
    assert hands["flimsy-tls/example-job/DEPLOYED"] is False  # fixable, NOT ours until Phase 3
    assert sum(1 for v in hands.values() if v) == 1


def test_a_finding_for_a_repository_with_no_live_read_is_refused():
    """We cannot say DEPLOYED or STALE about a repository nobody read. Refuse; do not guess.

    Fails if an unknown repository is defaulted to STALE or dropped — either invents a state for an
    image that might be the one serving traffic.
    """
    f = Finding("some-other-repo", digest(0xAB), "flimsy-tls", "1.2.3-1", "1.2.4-1", ("CVE-2026-90001",))

    with pytest.raises(FreshnessRefused):
        classify([f], LIVE)


def test_classifying_nothing_gives_nothing_and_does_not_raise():
    """The clean day has to walk all the way through the pipeline, not just through the read."""
    assert classify(parse_resource_graph([page([], total=0)]), LIVE) == []


def test_rows_come_back_grouped_by_repository_with_the_deployed_ones_first():
    """The table is read top-down by a human; the row that might need action sorts to the top.

    Fails if the order follows Defender's arbitrary row order — two runs on the same data would
    print two different tables, and nothing in a diff of them would mean anything.
    """
    findings = [
        Finding("example-job", JOB_V1, "flimsy-tls", "1.2.3-1", "1.2.4-1", ("CVE-2026-90001",)),
        Finding("example-app", APP_OLD, "packwright", "3.0.0", "4.0.0", ("CVE-2026-90002",)),
        Finding("example-app", APP_LIVE, "flimsy-tls", "1.2.3-1", "1.2.4-1", ("CVE-2026-90001",)),
        Finding("example-job", JOB_LIVE, "packwright", "3.0.0", "4.0.0", ("CVE-2026-90002",)),
    ]

    rows = classify(findings, LIVE)

    assert [(r.repository, r.state) for r in rows] == [
        ("example-app", DEPLOYED), ("example-app", STALE),
        ("example-job", DEPLOYED), ("example-job", STALE),
    ]
    assert classify(findings, LIVE) == rows          # and it is stable run to run


@pytest.fixture(autouse=True)
def _monitored_only_roster(monkeypatch):
    """The kit's default MONITORED-ONLY roster is EMPTY (a template must not name one project's
    registries); these tests exercise the marker, so they name two example repositories the way a
    project would — through the environment."""
    monkeypatch.setenv("FRESHNESS_MONITORED_ONLY", "example-job,example-mcp")
