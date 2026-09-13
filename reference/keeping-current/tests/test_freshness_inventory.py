"""Phase 2 — the package inventory both sides of the compare are read from (2026-09-10).

Fictional throughout: `flimsy-tls`, `packwright` and `gnarl` are not real packages and the CVE ids
are invented. The Trivy JSON shape is real (`--format json`: `Results[].Packages[]` for the
inventory, `Results[].Vulnerabilities[]` for the findings).

What these tests are defending, from the plan's review panel:

  * failure lens F6 — "the deployed image's package list" had no mechanism and no failure path. The
    mechanism is Trivy on BOTH digests, one tool, one code path; the failure path is a THIRD state.
    A side that could not be read is INCONCLUSIVE. It is never IDENTICAL, which would be a green
    day invented out of a broken scan, and never MOVED, which would dispatch prod off bad data.
  * failure lens F7 — a naive diff cries wolf on build metadata. The compared unit is
    `{name: version-release}` lifted out of Trivy's own package list, so timestamps, layer digests
    and image config cannot reach the comparison by construction: there is no code path that reads
    them.
  * failure lens F10 — a CVE the owner has already accepted must be sayable as "known, accepted"
    and must never become a silent drop.
"""
import pytest

from infra.freshness.inventory import (
    IDENTICAL,
    INCONCLUSIVE,
    MOVED,
    InventoryRefused,
    compare,
    load_accepted,
    packages,
    split_accepted,
    vulnerabilities,
)

OS_TARGET = "exampleacr.azurecr.io/example-app@sha256:aa (azurelinux 3.0)"
PY_TARGET = "Python"


def trivy(os_packages=(), py_packages=(), vulns=(), created="2026-09-10T06:00:00Z", layer="sha256:dead"):
    """Trivy's `--format json` output, with the metadata a naive diff would trip over included."""
    return {
        "SchemaVersion": 2,
        "ArtifactName": "exampleacr.azurecr.io/example-app@sha256:aa",
        "Metadata": {
            "ImageConfig": {"created": created, "rootfs": {"diff_ids": [layer]}},
            "RepoDigests": ["exampleacr.azurecr.io/example-app@sha256:aa"],
        },
        "Results": [
            {
                "Target": OS_TARGET, "Class": "os-pkgs", "Type": "azurelinux",
                "Packages": [
                    dict(p, Layer={"Digest": layer, "DiffID": layer}) for p in os_packages
                ],
                "Vulnerabilities": list(vulns),
            },
            {
                "Target": PY_TARGET, "Class": "lang-pkgs", "Type": "python-pkg",
                "Packages": list(py_packages),
            },
        ],
    }


BUILD_A = trivy(
    os_packages=[{"Name": "flimsy-tls", "Version": "1.2.3", "Release": "1.azl3"},
                 {"Name": "gnarl", "Version": "9.9", "Release": "4.azl3"}],
    py_packages=[{"Name": "packwright", "Version": "3.0.0"},
                 {"Name": "sheafy", "Version": "0.11.2"}],
)


# --------------------------------------------------------------------------------------------------
# packages() — what the comparison is allowed to see
# --------------------------------------------------------------------------------------------------

def test_os_and_python_packages_are_merged_into_one_mapping():
    """Both halves of the image in one dict, version and release joined the way an RPM names itself.

    Fails if either Result class is skipped: the OS half is where the base image's patches land, the
    Python half is where a dependency floor moves, and the design needs to see both move.
    """
    assert packages(BUILD_A) == {
        "flimsy-tls": "1.2.3-1.azl3",
        "gnarl": "9.9-4.azl3",
        "packwright": "3.0.0",
        "sheafy": "0.11.2",
    }


def test_nothing_but_a_package_name_and_version_can_reach_the_inventory():
    """Two builds that differ ONLY in metadata produce the same inventory — F7, by construction.

    Fails the moment the extraction reads anything richer than Name/Version/Release: the created
    timestamp and the layer digests differ between these two builds, and every weekly rebuild would
    report "packages moved" for reasons that are not a patch.
    """
    b = trivy(
        os_packages=[{"Name": "flimsy-tls", "Version": "1.2.3", "Release": "1.azl3"},
                     {"Name": "gnarl", "Version": "9.9", "Release": "4.azl3"}],
        py_packages=[{"Name": "packwright", "Version": "3.0.0"},
                     {"Name": "sheafy", "Version": "0.11.2"}],
        created="2026-09-17T06:02:11Z", layer="sha256:beef",
    )

    assert packages(b) == packages(BUILD_A)
    assert compare(packages(BUILD_A), packages(b)).kind == IDENTICAL


def test_a_package_present_in_two_targets_keeps_both_versions():
    """`pip`-shaped case: the OS ships it and the Python layer ships another. Neither may be lost.

    DECIDED 2026-09-10: the first occurrence in Trivy's own order keeps the bare name; a later
    occurrence of a name already seen is keyed `name@<target>`. Fails if the second write overwrites
    the first (one version vanishes and a real move on the survivor is invisible) or if the duplicate
    is dropped (the same, quietly).
    """
    both = trivy(
        os_packages=[{"Name": "packwright", "Version": "2.0.0", "Release": "1.azl3"}],
        py_packages=[{"Name": "packwright", "Version": "3.0.0"}],
    )

    inv = packages(both)

    assert inv["packwright"] == "2.0.0-1.azl3"
    assert inv[f"packwright@{PY_TARGET}"] == "3.0.0"
    assert len(inv) == 2


def test_a_duplicate_that_is_not_a_duplicate_version_still_moves_on_its_own_key():
    """Once a name is split by target, each side moves independently and says which side moved."""
    old = trivy(os_packages=[{"Name": "packwright", "Version": "2.0.0", "Release": "1.azl3"}],
                py_packages=[{"Name": "packwright", "Version": "3.0.0"}])
    new = trivy(os_packages=[{"Name": "packwright", "Version": "2.0.0", "Release": "1.azl3"}],
                py_packages=[{"Name": "packwright", "Version": "3.1.0"}])

    v = compare(packages(old), packages(new))

    assert v.kind == MOVED
    assert v.moved == ((f"packwright@{PY_TARGET}", "3.0.0", "3.1.0"),)


def test_a_package_with_no_name_refuses_rather_than_being_skipped():
    """A row we cannot name is a broken scan, not a smaller image. Reject, never truncate."""
    with pytest.raises(InventoryRefused):
        packages(trivy(os_packages=[{"Version": "1.2.3", "Release": "1.azl3"}]))


def test_output_that_is_not_trivys_is_refused():
    """An error page, an empty file or a half-written JSON must never read as "no packages found"."""
    with pytest.raises(InventoryRefused):
        packages({"error": "could not pull image"})


def test_a_results_list_that_is_null_is_an_empty_inventory_not_a_crash():
    """Trivy writes `"Results": null` when it found no target; that is empty, and compare judges it."""
    assert packages({"SchemaVersion": 2, "Results": None}) == {}


# --------------------------------------------------------------------------------------------------
# compare() — three states, and the one that must never be reachable by accident
# --------------------------------------------------------------------------------------------------

def test_two_builds_of_the_same_commit_are_identical():
    """The no-op rebuild is the case that has to be quiet, or the gate click becomes a rubber stamp."""
    v = compare(packages(BUILD_A), packages(BUILD_A))

    assert v.kind == IDENTICAL
    assert v.moved == ()


def test_one_os_patch_moved_is_reported_as_that_one_package():
    """The expat-shaped case, fictional: one OS package, old and new versions both named."""
    patched = trivy(
        os_packages=[{"Name": "flimsy-tls", "Version": "1.2.4", "Release": "1.azl3"},
                     {"Name": "gnarl", "Version": "9.9", "Release": "4.azl3"}],
        py_packages=[{"Name": "packwright", "Version": "3.0.0"},
                     {"Name": "sheafy", "Version": "0.11.2"}],
    )

    v = compare(packages(BUILD_A), packages(patched))

    assert v.kind == MOVED
    assert v.moved == (("flimsy-tls", "1.2.3-1.azl3", "1.2.4-1.azl3"),)


def test_a_python_floor_moved_is_reported_the_same_way():
    """Every dependency in pyproject.toml is a `>=` floor, so a rebuild re-resolves them."""
    bumped = trivy(
        os_packages=[{"Name": "flimsy-tls", "Version": "1.2.3", "Release": "1.azl3"},
                     {"Name": "gnarl", "Version": "9.9", "Release": "4.azl3"}],
        py_packages=[{"Name": "packwright", "Version": "3.0.0"},
                     {"Name": "sheafy", "Version": "0.12.0"}],
    )

    v = compare(packages(BUILD_A), packages(bumped))

    assert v.kind == MOVED
    assert v.moved == (("sheafy", "0.11.2", "0.12.0"),)


def test_a_package_that_appeared_or_vanished_is_a_move_with_a_named_empty_side():
    """An added or removed package is a real change and is shown as one, not silently equal."""
    grew = trivy(
        os_packages=[{"Name": "flimsy-tls", "Version": "1.2.3", "Release": "1.azl3"}],
        py_packages=[{"Name": "packwright", "Version": "3.0.0"},
                     {"Name": "sheafy", "Version": "0.11.2"}],
    )

    v = compare(packages(BUILD_A), packages(grew))

    assert v.kind == MOVED
    assert v.moved == (("gnarl", "9.9-4.azl3", None),)


def test_a_missing_side_is_inconclusive_never_identical():
    """THE rule. A read that did not happen is a third state — not a green day, not a trigger.

    Fails if `compare` takes the two sides at face value: `None`/`None` and `{}`/`{}` both compare
    equal under any ordinary dict comparison, so a scan that failed on both sides would report
    IDENTICAL — silent, green, and completely uninformed. That is failure lens F6 exactly.
    """
    deployed = packages(BUILD_A)

    assert compare(None, deployed).kind == INCONCLUSIVE
    assert compare(deployed, None).kind == INCONCLUSIVE
    assert compare(None, None).kind == INCONCLUSIVE
    assert compare({}, deployed).kind == INCONCLUSIVE
    assert compare(deployed, {}).kind == INCONCLUSIVE
    assert compare({}, {}).kind == INCONCLUSIVE


def test_an_inconclusive_verdict_says_which_side_could_not_be_read():
    """The summary has to be able to tell the maintainer where to look; "inconclusive" alone cannot."""
    assert "deployed" in compare(None, packages(BUILD_A)).reason.lower()
    assert "candidate" in compare(packages(BUILD_A), None).reason.lower()


def test_an_empty_inventory_is_never_a_clean_bill_of_health():
    """Restated as a property over both arms, because this is the one that fails silently."""
    for a, b in ((None, None), ({}, {}), (None, {}), ({}, None)):
        assert compare(a, b).kind != IDENTICAL
        assert compare(a, b).kind != MOVED


# --------------------------------------------------------------------------------------------------
# the accepted-CVE allowlist — "known, accepted", never a silent drop
# --------------------------------------------------------------------------------------------------

VULNS = [
    {"VulnerabilityID": "CVE-2026-90001", "PkgName": "flimsy-tls", "InstalledVersion": "1.2.3-1.azl3",
     "FixedVersion": "1.2.4-1.azl3", "Severity": "HIGH"},
    {"VulnerabilityID": "CVE-2026-90005", "PkgName": "gnarl", "InstalledVersion": "9.9-4.azl3",
     "FixedVersion": "", "Severity": "CRITICAL"},
    {"VulnerabilityID": "CVE-2026-90006", "PkgName": "sheafy", "InstalledVersion": "0.11.2",
     "FixedVersion": "0.12.0", "Severity": "HIGH"},
]


def test_vulnerabilities_are_read_with_the_package_and_the_fix():
    """RED has to be able to name the package AND the version that fixes it — that is the whole ask."""
    got = vulnerabilities(trivy(vulns=VULNS))

    assert [(v.cve, v.package, v.fixed) for v in got] == [
        ("CVE-2026-90001", "flimsy-tls", "1.2.4-1.azl3"),
        ("CVE-2026-90005", "gnarl", ""),
        ("CVE-2026-90006", "sheafy", "0.12.0"),
    ]
    assert got[0].fixable is True and got[1].fixable is False


def test_the_allowlist_file_is_read_as_cve_then_package():
    """One `CVE-… <package>` per line, `#` comments and blank lines ignored."""
    text = "# accepted, see the findings log\n\nCVE-2026-90006 sheafy\n"

    assert load_accepted(text) == frozenset({("CVE-2026-90006", "sheafy")})


def test_a_malformed_allowlist_line_is_refused_rather_than_ignored():
    """A typo in this file must not quietly widen or narrow what is suppressed."""
    with pytest.raises(InventoryRefused):
        load_accepted("CVE-2026-90006\n")


def test_an_accepted_cve_becomes_known_accepted_and_never_a_silent_drop():
    """It leaves the actionable list and arrives, by name, in the accepted one. Nothing evaporates.

    Fails if the allowlist filters rather than splits: the finding would vanish from the summary
    entirely, and next quarter nobody could say what had been accepted or when.
    """
    split = split_accepted(vulnerabilities(trivy(vulns=VULNS)),
                           load_accepted("CVE-2026-90006 sheafy\n"))

    assert [v.cve for v in split.actionable] == ["CVE-2026-90001", "CVE-2026-90005"]
    assert [v.cve for v in split.accepted] == ["CVE-2026-90006"]
    assert len(split.actionable) + len(split.accepted) == len(VULNS)


def test_the_allowlist_matches_on_the_package_too_not_just_the_cve():
    """The same CVE id against a different package is a different finding and stays actionable."""
    split = split_accepted(vulnerabilities(trivy(vulns=VULNS)),
                           load_accepted("CVE-2026-90006 packwright\n"))

    assert [v.cve for v in split.actionable] == [v["VulnerabilityID"] for v in VULNS]
    assert split.accepted == ()


def test_an_empty_allowlist_suppresses_nothing():
    """The file ships empty with a header comment; it must behave as "nothing is accepted yet"."""
    split = split_accepted(vulnerabilities(trivy(vulns=VULNS)),
                           load_accepted("# nothing accepted yet\n"))

    assert len(split.actionable) == 3 and split.accepted == ()


def test_vulnerabilities_carry_the_target_and_the_package_path():
    """The RED line has to say WHERE. The first live run (2026-09-11) named "msgpack 1.1.2" and it took
    a probe of the running container to learn it was pip's vendored copy — Trivy had the path all along.
    Fails if Target/PkgPath are dropped on the floor."""
    vulns = [dict(VULNS[0]), dict(VULNS[2], PkgPath="usr/lib/python3.12/site-packages/pip/_vendor/msgpack")]
    got = vulnerabilities(trivy(vulns=vulns))
    assert [v.target for v in got] == [OS_TARGET, OS_TARGET]     # the helper files them under the OS result
    assert got[0].path == ""                                       # Trivy gave no path: none is invented
    assert got[1].path == "usr/lib/python3.12/site-packages/pip/_vendor/msgpack"
