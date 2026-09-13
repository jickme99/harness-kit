"""Phase 2 — the CLI the workflow's shell calls, so the shell stays thin (2026-09-10).

`python -m infra.freshness <command>` with everything else in the ENVIRONMENT: no flags anywhere,
matching `infra/registry_retention_plan.py`'s `$WORK` convention and the maintainer's guarded shell,
which refuses an opaque script invocation carrying options.

Four commands, one per pure module: `classify`, `compare`, `decide`, `summary`. Each reads files and
writes files; none of them reaches Azure, the registry or GitHub — that is the shell's job, where it
is visible in the workflow log. The exit code is the contract: 0 is "this step did its work", 1 is
"REFUSED / RED", 2 is "you called it wrong". Fictional data throughout.
"""
import os
os.environ.setdefault("FRESHNESS_MONITORED_ONLY", "example-job,example-mcp")  # the kit ships no roster
import json

import pytest

from infra.freshness.__main__ import main


def digest(seed):
    return "sha256:" + (f"{seed:02x}" * 32)


APP_LIVE, APP_OLD = digest(0x11), digest(0x22)


def write(path, obj):
    path.write_text(json.dumps(obj), encoding="utf-8")
    return str(path)


def assessment(repository, dig, software, fixed):
    return {"properties": {
        "displayName": f"Update {software}",
        "status": {"code": "Unhealthy", "firstEvaluationDate": "2026-08-28T04:11:02Z"},
        "resourceDetails": {"Id": f"{repository}-images-{dig}"},
        "additionalData": {"SoftwareName": software, "MaxCvssScore": "8.7", "ScannersDetails": {
            "mdvm": {"FixedVersion": fixed, "DetectedSoftwareVersions": ["1.2.3-1"],
                     "CvesIds": ["CVE-2026-90001"]}}},
    }}


def trivy(version="1.2.3", vulns=()):
    return {"SchemaVersion": 2, "Results": [
        {"Target": "image (azurelinux 3.0)", "Class": "os-pkgs", "Type": "azurelinux",
         "Packages": [{"Name": "flimsy-tls", "Version": version, "Release": "1.azl3"}],
         "Vulnerabilities": list(vulns)}]}


LIVE_IMAGES = {
    "example-app": {"tag": "abcd1234", "digest": APP_LIVE, "registry_digests": [APP_LIVE, APP_OLD]},
}


@pytest.fixture()
def work(tmp_path, monkeypatch):
    monkeypatch.setenv("OUT", str(tmp_path))
    monkeypatch.setenv("MODE", "full")
    monkeypatch.setenv("TAG", "abcd1234-cand-20260910")
    monkeypatch.setenv("PENDING_SINCE", "")
    return tmp_path


def test_classify_writes_the_rows_and_reports_the_count(work, monkeypatch, capsys):
    """The read's whole output lands in one file the later commands and the summary share."""
    monkeypatch.setenv("GRAPH_PAGES", write(work / "pages.json", [{
        "total_records": 1, "count": 1,
        "data": [assessment("example-app", APP_OLD, "flimsy-tls", "1.2.4-1.azl3")]}]))
    monkeypatch.setenv("LIVE_IMAGES", write(work / "live.json", LIVE_IMAGES))

    assert main(["classify"]) == 0

    got = json.loads((work / "classified.json").read_text(encoding="utf-8"))
    assert got["checked"] is True
    assert len(got["rows"]) == 1
    assert got["rows"][0]["state"] == "STALE"
    assert "1" in capsys.readouterr().out


def test_a_page_count_mismatch_exits_one_and_says_so(work, monkeypatch, capsys):
    """The refusal has to reach the workflow as a non-zero exit, not as an empty findings table."""
    monkeypatch.setenv("GRAPH_PAGES", write(work / "pages.json", [{
        "total_records": 4, "count": 1,
        "data": [assessment("example-app", APP_OLD, "flimsy-tls", "1.2.4-1.azl3")]}]))
    monkeypatch.setenv("LIVE_IMAGES", write(work / "live.json", LIVE_IMAGES))

    assert main(["classify"]) == 1
    assert "REFUSED" in capsys.readouterr().err
    assert not (work / "classified.json").exists()


def test_compare_of_a_side_that_was_never_written_is_inconclusive_not_a_crash(work, monkeypatch):
    """A Trivy step that failed leaves no file. That is the third state, and the job says so."""
    monkeypatch.setenv("DEPLOYED_TRIVY", write(work / "deployed.json", trivy()))
    monkeypatch.setenv("CANDIDATE_TRIVY", str(work / "does-not-exist.json"))

    assert main(["compare"]) == 0

    verdict = json.loads((work / "verdict.json").read_text(encoding="utf-8"))
    assert verdict["kind"] == "INCONCLUSIVE"
    assert "candidate" in verdict["reason"].lower()


def test_compare_then_decide_promotes_only_in_full_mode(work, monkeypatch):
    """The two commands chained exactly as the workflow chains them, in both modes."""
    monkeypatch.setenv("DEPLOYED_TRIVY", write(work / "deployed.json", trivy("1.2.3")))
    monkeypatch.setenv("CANDIDATE_TRIVY", write(work / "candidate.json", trivy("1.2.4")))
    monkeypatch.setenv("ACCEPTED", str(work / "accepted-cves.txt"))
    (work / "accepted-cves.txt").write_text("# nothing accepted yet\n", encoding="utf-8")
    assert main(["compare"]) == 0

    assert main(["decide"]) == 0
    assert json.loads((work / "decision.json").read_text(encoding="utf-8"))["promote"] is True

    monkeypatch.setenv("MODE", "dry")
    assert main(["decide"]) == 0
    assert json.loads((work / "decision.json").read_text(encoding="utf-8"))["promote"] is False


def test_decide_exits_one_on_red_so_the_step_goes_red(work, monkeypatch):
    """RED is a failed job by design — that is what fires the issue step and the owner's email."""
    vulns = [{"VulnerabilityID": "CVE-2026-90001", "PkgName": "flimsy-tls",
              "InstalledVersion": "1.2.3-1.azl3", "FixedVersion": "1.2.4-1.azl3", "Severity": "HIGH"}]
    monkeypatch.setenv("DEPLOYED_TRIVY", write(work / "deployed.json", trivy("1.2.3")))
    monkeypatch.setenv("CANDIDATE_TRIVY", write(work / "candidate.json", trivy("1.2.3", vulns)))
    monkeypatch.setenv("ACCEPTED", str(work / "accepted-cves.txt"))
    (work / "accepted-cves.txt").write_text("# nothing accepted yet\n", encoding="utf-8")
    main(["compare"])

    assert main(["decide"]) == 1

    decision = json.loads((work / "decision.json").read_text(encoding="utf-8"))
    assert decision["kind"] == "RED" and decision["package"] == "flimsy-tls"


def test_an_accepted_cve_does_not_turn_the_job_red(work, monkeypatch):
    """The allowlist's whole purpose, exercised through the door the workflow uses."""
    vulns = [{"VulnerabilityID": "CVE-2026-90001", "PkgName": "flimsy-tls",
              "InstalledVersion": "1.2.3-1.azl3", "FixedVersion": "1.2.4-1.azl3", "Severity": "HIGH"}]
    monkeypatch.setenv("DEPLOYED_TRIVY", write(work / "deployed.json", trivy("1.2.3")))
    monkeypatch.setenv("CANDIDATE_TRIVY", write(work / "candidate.json", trivy("1.2.3", vulns)))
    monkeypatch.setenv("ACCEPTED", str(work / "accepted-cves.txt"))
    (work / "accepted-cves.txt").write_text("CVE-2026-90001 flimsy-tls\n", encoding="utf-8")
    main(["compare"])

    assert main(["decide"]) == 0
    assert json.loads((work / "decision.json").read_text(encoding="utf-8"))["kind"] != "RED"


def test_summary_prints_a_page_even_when_the_earlier_steps_left_nothing(work, monkeypatch, capsys):
    """The heartbeat posts on every run — including the run where everything before it fell over.

    Fails if the summary needs its inputs to exist: a broken day would then post NO page at all,
    which is the silence the whole design refuses to allow.
    """
    monkeypatch.setenv("DATE", "2026-09-10")
    monkeypatch.setenv("BASE_DIGEST", digest(0xBE))

    assert main(["summary"]) == 0

    out = capsys.readouterr().out
    assert "2026-09-10" in out
    assert "NOT CHECKED" in out
    assert "Decision" in out


def test_an_unknown_command_exits_two_without_doing_anything(work):
    assert main(["rebuild-everything"]) == 2
    assert main([]) == 2


def test_the_summary_says_where_the_red_package_was_found(work, monkeypatch, capfd):
    """Product door: `decide` then `summary`, as the workflow runs them. The first live RED
    (2026-09-11) said "found in Python" in decision.json and nothing of the kind on
    the page, because the summary rebuilt the decision without its location. Fails if the page's RED
    line does not carry what decision.json carries."""
    scan = {"SchemaVersion": 2, "Results": [
        {"Target": "image (azurelinux 3.0)", "Class": "os-pkgs", "Type": "azurelinux",
         "Packages": [{"Name": "flimsy-tls", "Version": "1.2.3", "Release": "1.azl3"}], "Vulnerabilities": []},
        {"Target": "Python", "Class": "lang-pkgs", "Type": "python-pkg",
         "Packages": [{"Name": "vendored-thing", "Version": "1.1.2"}],
         "Vulnerabilities": [{"VulnerabilityID": "GHSA-0000-0000-0000", "PkgName": "vendored-thing",
                              "InstalledVersion": "1.1.2", "FixedVersion": "1.2.1", "Severity": "HIGH"}]}]}
    monkeypatch.setenv("DEPLOYED_TRIVY", write(work / "deployed.json", scan))
    monkeypatch.setenv("CANDIDATE_TRIVY", write(work / "candidate.json", scan))
    monkeypatch.setenv("ACCEPTED", str(work / "accepted-cves.txt"))
    (work / "accepted-cves.txt").write_text("# nothing accepted yet\n", encoding="utf-8")
    monkeypatch.setenv("DATE", "2026-09-11")
    main(["compare"])
    assert main(["decide"]) == 1
    assert json.loads((work / "decision.json").read_text(encoding="utf-8"))["where"] == "Python"
    capfd.readouterr()
    assert main(["summary"]) == 0
    page = capfd.readouterr().out
    red = [ln for ln in page.splitlines() if ln.startswith("RED")]
    assert red and "found in Python" in red[0], red


def test_summary_reads_the_policy_table(work, monkeypatch, capfd):
    """The workflow writes policy.tsv (repository, tag, verdict); the page must carry every row."""
    (work / "policy.tsv").write_text("example-app\tabcd1234\tCLEAN\nexample-job\tv41\tVIOLATION: pip is importable\n",
                                     encoding="utf-8")
    monkeypatch.setenv("DATE", "2026-09-11")
    capfd.readouterr()
    assert main(["summary"]) == 0
    page = capfd.readouterr().out
    assert "| `example-app` | `abcd1234` | CLEAN |" in page
    assert "| `example-job` | `v41` | VIOLATION: pip is importable |" in page
    assert "POLICY RED" in page


@pytest.fixture(autouse=True)
def _monitored_only_roster(monkeypatch):
    """The kit's default MONITORED-ONLY roster is EMPTY (a template must not name one project's
    registries); these tests exercise the marker, so they name two example repositories the way a
    project would — through the environment."""
    monkeypatch.setenv("FRESHNESS_MONITORED_ONLY", "example-job,example-mcp")
