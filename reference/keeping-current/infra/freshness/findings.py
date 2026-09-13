"""What Defender currently says about the estate's images, resolved to digests and classified.

Phase 2 of `spec/keeping-current.md` (design B, step 2). The workflow's shell runs the Resource
Graph query and hands the RAW PAGES here; everything that decides lives in this module, where
`tests/test_freshness_findings.py` can reach it — the same split Phase 1 made for retention.

Three rules earned this file its own tests, all three from the plan's review panel:

  * REJECT, NEVER TRUNCATE (failure lens F3). The query on file collapsed every recommendation to
    one sample resource with `any(rid)`, and a per-resource query hits Resource Graph's page cap
    silently: valid JSON, fewer rows, indistinguishable from "fewer unhealthy things exist". So the
    read refuses unless the rows it received add up to the `totalRecords` the service reported. A
    row that cannot be resolved to a repository and a digest is likewise a refusal, never a skip.
  * MONITORED-ONLY (failure lens F4). Repositories on the watched-not-rebuilt roster get the
    daily read and the pruning, and their rebuild later. Tests use `example-job` and
    `example-mcp` as stand-ins. A row that fixes itself tonight must never look like a row
    that needs a person.
  * EMPTY BEATS WRONG, and a failed read is a THIRD state (security lens F3). Nothing found is
    reported as nothing found AND `checked`, which is what lets the summary say "checked, clean"
    instead of the silence that means nobody looked.
"""
import dataclasses
import json
import os
import re

DEPLOYED, STALE, GONE = "DEPLOYED", "STALE", "GONE"

# The repositories this job READS AND PRUNES but does not rebuild — images built elsewhere (another
# repository, another team). Every row of theirs carries the marker so the summary cannot present it
# as covered. Named PER PROJECT through the environment (`FRESHNESS_MONITORED_ONLY="repo-a,repo-b"`)
# and EMPTY by default: a template that names one project's registries is how the next project
# prunes the wrong one (kit audit 2026-08-23, finding #13).
MONITORED_ONLY = frozenset()


def monitored_only_from_env(env=None):
    """The MONITORED-ONLY roster from `FRESHNESS_MONITORED_ONLY` (comma-separated), else the default."""
    raw = (os.environ if env is None else env).get("FRESHNESS_MONITORED_ONLY", "")
    return frozenset(r.strip() for r in raw.split(",") if r.strip()) or MONITORED_ONLY

_STATE_ORDER = {DEPLOYED: 0, STALE: 1, GONE: 2}
_DIGEST = re.compile(r"^sha256:[0-9a-f]{32,}$")
# Defender writes the image's resource id either as an ARM path or in the short form Resource Graph
# returns for a registry image. Both name the same two things: a repository and a manifest digest.
_ARM = re.compile(r"/repositories/(?P<repository>[^/]+)/images/(?P<digest>sha256:[0-9a-f]+)", re.I)
_SHORT = "-images-"


class FreshnessRefused(Exception):
    """A read could not be proven whole. Nothing is reported; the caller fails the job."""


@dataclasses.dataclass(frozen=True)
class Finding:
    """One Defender assessment, resolved to the image it is actually about."""
    repository: str
    digest: str
    software: str
    detected: str = ""
    fixed: str = ""
    cves: tuple = ()
    cvss: float = None
    first_seen: str = ""

    @property
    def fixable(self):
        """A fix version exists somewhere. Without one, a rebuild cannot help and RED would lie."""
        return bool(self.fixed)


@dataclasses.dataclass(frozen=True)
class LiveImage:
    """What a repository's workload is running right now, read live — never assumed.

    `registry_digests` is every manifest digest the repository currently holds, which is the only
    way to tell a superseded image that is still there (STALE, prunable) from one that has already
    been deleted (GONE, nothing left to do but wait for Defender's next scan).
    """
    repository: str
    tag: str
    digest: str
    registry_digests: frozenset = frozenset()


@dataclasses.dataclass(frozen=True)
class Row:
    """A finding plus the one thing the finding cannot know: whether anything can deploy it."""
    finding: Finding
    state: str
    monitored_only: bool = False

    @property
    def repository(self):
        return self.finding.repository

    @property
    def digest(self):
        return self.finding.digest

    @property
    def software(self):
        return self.finding.software

    @property
    def needs_a_hand(self):
        """The same-day rebuild trigger: a fixable finding, on the running image, in OUR repository.

        All three conditions matter. Not deployed -> retention handles it. No fix -> a rebuild cannot
        help. Not ours -> Phase 3; a rebuild here would push an image that repository does not own.
        """
        return self.state == DEPLOYED and self.finding.fixable and not self.monitored_only

    def marker(self):
        return "MONITORED-ONLY" if self.monitored_only else ""


@dataclasses.dataclass(frozen=True)
class Findings:
    """The read's whole answer. Iterable like a list, and it remembers that it HAPPENED."""
    findings: tuple = ()
    total_records: int = 0
    checked: bool = True

    def __iter__(self):
        return iter(self.findings)

    def __len__(self):
        return len(self.findings)

    def __getitem__(self, i):
        return self.findings[i]

    def __bool__(self):
        return bool(self.findings)


def _guard(ok, message):
    if not ok:
        raise FreshnessRefused(message)


def _maybe_json(value):
    """`additionalData` values arrive as objects on some rows and as JSON strings on others."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return {}
    return value or {}


def _as_list(value):
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value]
    if value in (None, ""):
        return []
    return [v.strip() for v in str(value).split(",") if v.strip()]


def _image(resource_id):
    """(repository, digest) from Defender's resource id, in either of the two forms it writes."""
    rid = str(resource_id or "")
    m = _ARM.search(rid)
    if m:
        return m.group("repository"), m.group("digest").lower()
    if _SHORT in rid:
        repository, digest = rid.rsplit(_SHORT, 1)
        return repository, digest.lower()
    return "", ""


def _total(page):
    """The service's own row count — `total_records` from the CLI, `totalRecords` from REST."""
    for key in ("totalRecords", "total_records"):
        if key in page:
            return page[key]
    return None


def parse_resource_graph(pages):
    """Every row of every page, resolved to a Finding — or a refusal. Never a partial answer.

    `pages` is the list of raw `az graph query` answers collected by the skip-token loop. The guard
    that matters is the last one: the rows we received must equal the rows the service said exist.
    """
    pages = [pages] if isinstance(pages, dict) else list(pages)
    _guard(pages, "REFUSED: the Resource Graph read returned no pages at all — nobody answered. "
                  "Zero PAGES is not zero FINDINGS.")

    totals, rows = set(), []
    for page in pages:
        total = _total(page)
        _guard(total is not None,
               "REFUSED: a Resource Graph page carried no totalRecords, so its rows cannot be "
               "checked for truncation.")
        totals.add(int(total))
        data = page.get("data")
        _guard(isinstance(data, list), "REFUSED: a Resource Graph page carried no `data` list.")
        rows.extend(data)

    _guard(len(totals) == 1,
           f"REFUSED: the pages disagree about how many rows exist {sorted(totals)} — a scan landed "
           "mid-pagination and this is not one read.")
    total = totals.pop()
    # F3, the whole reason this module exists: a short read is valid JSON and reads like good news.
    _guard(total == len(rows),
           f"REFUSED: Resource Graph reported {total} rows and {len(rows)} arrived. Reject, never "
           "truncate — raise the page size or fix the skip-token loop before trusting this.")

    found = []
    for row in rows:
        props = row.get("properties", row) or {}
        repository, digest = _image((props.get("resourceDetails") or {}).get("Id"))
        # A row nobody can resolve to an image is not a row we may quietly drop: the count guard
        # above would still pass (we counted it) and the table would be short by exactly that row.
        _guard(repository and _DIGEST.match(digest),
               f"REFUSED: an assessment row names no container image: "
               f"{(props.get('resourceDetails') or {}).get('Id')!r}")
        ad = _maybe_json(props.get("additionalData"))
        mdvm = _maybe_json(_maybe_json(ad.get("ScannersDetails")).get("mdvm"))
        try:
            cvss = float(ad.get("MaxCvssScore"))
        except (TypeError, ValueError):
            cvss = None          # the score decorates the table and decides nothing
        found.append(Finding(
            repository=repository,
            digest=digest,
            software=str(ad.get("SoftwareName") or "").strip(),
            detected=", ".join(_as_list(mdvm.get("DetectedSoftwareVersions"))),
            fixed=str(mdvm.get("FixedVersion") or "").strip(),
            cves=tuple(_as_list(mdvm.get("CvesIds"))),
            cvss=cvss,
            first_seen=str((props.get("status") or {}).get("firstEvaluationDate") or ""),
        ))

    # checked=True even when nothing was found. That is the flag the summary turns into the sentence
    # "checked, clean", and it is the only thing separating a clean day from a day nobody looked.
    return Findings(tuple(found), total_records=total, checked=True)


def classify(findings, live_images, *, monitored_only=None):
    """Label every finding DEPLOYED / STALE / GONE against the live read, and mark the two we watch.

    `live_images` maps repository -> LiveImage, read live by the shell. A finding naming a repository
    that was not read is a REFUSAL: we cannot say whether that digest is the one serving traffic, and
    guessing either way is how a running image ends up in a delete set or a live CVE reads as stale.
    """
    rows = []
    for f in findings:
        live = live_images.get(f.repository)
        _guard(live is not None,
               f"REFUSED: a finding names repository {f.repository!r}, which no live read covered — "
               "nothing can be said about whether that image is deployed.")
        if f.digest == live.digest:
            state = DEPLOYED
        elif f.digest in live.registry_digests:
            state = STALE
        else:
            state = GONE
        roster = monitored_only_from_env() if monitored_only is None else monitored_only
        rows.append(Row(f, state, monitored_only=f.repository in roster))

    # Stable, grouped, worst first: two runs over the same data print the same table, so a diff of
    # two days' summaries means something.
    rows.sort(key=lambda r: (r.repository, _STATE_ORDER.get(r.state, 9), r.software, r.digest))
    return rows
