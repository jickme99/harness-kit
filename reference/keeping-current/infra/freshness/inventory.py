"""The package inventory of an image, and the comparison of two of them.

Phase 2 of `spec/keeping-current.md` (design B, step 4). ONE tool reads both sides — Trivy, by
digest, on the candidate and on the deployed image — so the two lists are produced by the same code
path and a difference between them is a real difference, not a difference of method.

What the rules here are defending, all from the plan's review panel:

  * F7, cry wolf. The compared unit is `{name: version-release}` lifted out of Trivy's own package
    list. Timestamps, layer digests, buildhost strings and image config CANNOT reach the comparison,
    because nothing here reads them — that is what "excluded by construction" has to mean if a
    weekly no-op rebuild is ever going to report "identical".
  * F6, the third state. A side that could not be read is INCONCLUSIVE: never IDENTICAL, which would
    invent a green day out of a broken scan, and never MOVED, which would dispatch prod on nothing.
    An EMPTY inventory counts as unread — two failed scans compare equal to each other, and that is
    exactly the trap.
  * F10, accepted findings. A CVE the owner has already declined to chase is SPLIT OUT and reported
    as "known, accepted", never filtered away. A suppression nobody can see is how the next person
    re-litigates a settled decision.
"""
import dataclasses

IDENTICAL, MOVED, INCONCLUSIVE = "IDENTICAL", "MOVED", "INCONCLUSIVE"

# Worst first, so the one line RED gets to print carries the worst news.
_SEVERITY = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}


class InventoryRefused(Exception):
    """Output we cannot read as Trivy's. Nothing is returned; the caller fails the step."""


@dataclasses.dataclass(frozen=True)
class Verdict:
    kind: str
    moved: tuple = ()          # ((name, old, new), ...) — None on a side where the package is absent
    reason: str = ""


@dataclasses.dataclass(frozen=True)
class Vulnerability:
    cve: str
    package: str
    installed: str = ""
    fixed: str = ""
    severity: str = ""
    target: str = ""           # Trivy's result target: the OS line, or "Python" for site-packages
    path: str = ""             # Trivy's PkgPath — the file the package was read from, when it says

    @property
    def fixable(self):
        """Trivy names a version that fixes it. Without one, nothing a rebuild does can help."""
        return bool(self.fixed)


@dataclasses.dataclass(frozen=True)
class Split:
    """The findings, divided — never reduced. `actionable + accepted` is always the whole input."""
    actionable: tuple = ()
    accepted: tuple = ()


def _refuse(message):
    raise InventoryRefused(message)


def _results(trivy_json):
    if isinstance(trivy_json, str):
        _refuse("REFUSED: the Trivy output was handed over as text, not parsed JSON.")
    if not isinstance(trivy_json, dict) or "Results" not in trivy_json:
        _refuse("REFUSED: this is not Trivy `--format json` output (no `Results` key) — an error "
                "page or a half-written file must never read as an image with no packages.")
    return trivy_json.get("Results") or []


def packages(trivy_json):
    """`{name: version-release}` over the OS and language results merged.

    DUPLICATES, decided 2026-09-10: the first occurrence in Trivy's own order keeps the bare name;
    a later occurrence of a name already seen is keyed `name@<target>`. Both versions survive, so a
    package the OS ships and the Python layer also ships moves on its own key and neither side's
    version is silently overwritten by the other's.
    """
    out = {}
    for result in _results(trivy_json):
        target = str(result.get("Target") or "")
        for p in (result.get("Packages") or []):
            name = str(p.get("Name") or "").strip()
            # A package row with no name is a broken scan, not a smaller image.
            if not name:
                _refuse(f"REFUSED: a package in target {target!r} has no name.")
            version = str(p.get("Version") or "")
            release = str(p.get("Release") or "")
            value = f"{version}-{release}" if release else version
            key = name if name not in out else f"{name}@{target}"
            while key in out and out[key] != value:
                key += "#"       # same name twice in the SAME target: keep both, never overwrite
            out[key] = value
    return out


def compare(deployed, candidate):
    """IDENTICAL / MOVED / INCONCLUSIVE over two inventories. Pure: two dicts in, a Verdict out."""
    # THE rule. `None` is a read that failed; `{}` is a scan that returned nothing, which is the same
    # thing wearing a friendlier face — and `{} == {}` is True, so a naive equality would call two
    # broken scans a clean day. Neither is ever IDENTICAL and neither is ever a trigger.
    if not deployed or not candidate: return Verdict(INCONCLUSIVE, reason=_unread(deployed, candidate))

    moved = tuple((name, deployed.get(name), candidate.get(name))
                  for name in sorted(set(deployed) | set(candidate))
                  if deployed.get(name) != candidate.get(name))
    return Verdict(MOVED, moved=moved) if moved else Verdict(IDENTICAL)


def _unread(deployed, candidate):
    missing = [side for side, inv in (("deployed", deployed), ("candidate", candidate)) if not inv]
    return (f"comparison inconclusive — the {' and the '.join(missing)} image's package inventory "
            "could not be read. An empty inventory is a failed scan, never a match.")


def vulnerabilities(trivy_json):
    """Trivy's findings, flattened: the CVE, the package, what is installed and what fixes it."""
    out = []
    for result in _results(trivy_json):
        target = str(result.get("Target") or "")
        for v in (result.get("Vulnerabilities") or []):
            out.append(Vulnerability(
                cve=str(v.get("VulnerabilityID") or ""),
                package=str(v.get("PkgName") or ""),
                installed=str(v.get("InstalledVersion") or ""),
                fixed=str(v.get("FixedVersion") or ""),
                severity=str(v.get("Severity") or "UNKNOWN").upper(),
                target=target,
                path=str(v.get("PkgPath") or ""),
            ))
    return out


def worst_first(findings):
    """CRITICAL before HIGH before the rest, then by package, so "the one to name" is deterministic."""
    return sorted(findings, key=lambda f: (_SEVERITY.get(f.severity, 9), f.package, f.cve))


def load_accepted(text):
    """`infra/freshness/accepted-cves.txt`: one `CVE-… <package>` per line, `#` comments ignored.

    A malformed line REFUSES rather than being skipped: a typo here silently widens or narrows what
    is suppressed, and a suppression list nobody validates is worse than none.
    """
    out = set()
    for n, raw in enumerate(text.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 2 or not parts[0].upper().startswith("CVE-"):
            _refuse(f"REFUSED: accepted-cves line {n} is not `CVE-… <package>`: {raw.strip()!r}")
        out.add((parts[0].upper(), parts[1]))
    return frozenset(out)


def split_accepted(findings, accepted):
    """Divide the findings into the ones that still count and the ones already accepted, by NAME.

    The match is (CVE, package): the same CVE id against a different package is a different finding.
    Nothing is dropped — the accepted half is carried into the summary as "known, accepted".
    """
    findings = list(findings)
    keep = tuple(f for f in findings if (f.cve.upper(), f.package) not in accepted)
    seen = tuple(f for f in findings if (f.cve.upper(), f.package) in accepted)
    return Split(actionable=keep, accepted=seen)
