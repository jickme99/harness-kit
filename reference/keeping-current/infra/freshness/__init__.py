"""The daily image-freshness job's rules, lifted out of the workflow so tests can reach them.

Phase 2 of `spec/keeping-current.md`. The shell in `.github/workflows/freshness.yml` stays the
thin part — it runs `az`, Trivy and `gh`, and it does the acting. Everything that DECIDES lives here:

    findings.py    what Defender currently says, resolved to digests and classified
                   DEPLOYED / STALE / GONE, with MONITORED-ONLY on repositories the project
                   listed as watched-not-rebuilt
    inventory.py   Trivy's package list for one image, and the comparison of two of them
    decide.py      the one decision: GREEN_SILENT / PROMOTE / RED / HOLD / INCONCLUSIVE
    summary.py     the page the owner actually reads
    __main__.py    `python -m infra.freshness <command>`, inputs from the environment, no flags

The house rules, inherited from Phase 1 and repeated in each module for the person who arrives at one
of them cold: REJECT, NEVER TRUNCATE. EMPTY BEATS WRONG. A failed read is a THIRD state — never green
and never a trigger.
"""
