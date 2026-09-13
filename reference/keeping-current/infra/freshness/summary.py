"""The one page a human reads: the job summary, written on EVERY run.

Phase 2 of `spec/keeping-current.md` (design B, steps 6 and 7). This is the heartbeat — the
thing that makes "no news" mean "checked, clean" rather than "nobody looked" (security lens F3) — and
it is the text the owner can paste when a scanner-of-record alert arrives, because that team often
cannot open a private repository's Actions page (operations lens 10).

Three properties it holds on purpose:

  * every section renders on every run, including the run where everything before it fell over;
  * `MONITORED-ONLY` on every watched-not-rebuilt row, explained once under the
    table (failure lens F4) — a row that fixes itself tonight must not look like one that needs a
    person; tests use `example-job` / `example-mcp` as stand-ins;
  * no raw 64-character digest inside the table. Twelve hex is enough to identify a manifest and
    short enough to read on a phone; the BASE image's digest is recorded in full, once, in its own
    section, where it is an audit record of what the floating base tag resolved to (security F11).
"""
SHORT = 19          # `sha256:` + 12 hex — the same truncation infra/registry_retention_plan.py uses

_COLUMNS = ("repository", "image", "state", "software", "detected", "fixed", "CVEs", "note")


def short(digest):
    return str(digest or "")[:SHORT]


def _row(row):
    return "| " + " | ".join((
        row.repository,
        f"`{short(row.digest)}`",
        row.state,
        row.software or "—",
        row.finding.detected or "—",
        row.finding.fixed or "no fix yet",
        ", ".join(row.finding.cves) or "—",
        row.marker(),
    )) + " |"


def render(*, date, mode, rows, checked, verdict, decision, base_digest="", retention="",
           accepted=(), run_url="", rebuilt=True, policy=None, repositories=()):
    """The whole page as Markdown for `$GITHUB_STEP_SUMMARY`. Pure: no reads, no clock, no I/O."""
    rows = list(rows)
    out = [f"## Image freshness — {date} · mode `{mode}`", ""]

    # --- the heartbeat ---------------------------------------------------------------------------
    beat = (f"**Heartbeat:** this job ran on **{date}** in `{mode}` mode"
            + (f" ([run]({run_url}))" if run_url else "")
            + ". A page older than yesterday means the job did not run — that is the thing to chase.")
    out += [beat, ""]

    # --- what Defender currently says ---------------------------------------------------------
    out += ["### Defender findings", ""]
    if rows:
        out.append("| " + " | ".join(_COLUMNS) + " |")
        out.append("|" + "---|" * len(_COLUMNS))
        out += [_row(r) for r in rows]
        out.append("")
    if not checked:
        # The third state. Not green, not clean, and it must not be sayable as either.
        out.append("**NOT CHECKED** — the Defender read did not complete, so this page says nothing "
                   "about today's findings. Treat it as unknown, not as clear.")
    elif not rows:
        names = ", ".join(f"`{r}`" for r in repositories) or "the repositories read"
        out.append(f"**Checked, clean** — the scanner reports nothing against {names} today. The read "
                   "completed; this is good news rather than silence.")
    if any(r.monitored_only for r in rows):
        out.append("")
        out.append("`MONITORED-ONLY` — read and pruned, never rebuilt here: these images are built "
                   "elsewhere. A row marked this way does not fix itself; it needs a person.")
    out.append("")

    # --- the compare ------------------------------------------------------------------------------
    out += ["### Package comparison", ""]
    if not rebuilt:
        # Six days in seven. INCONCLUSIVE is the word for a comparison that FAILED; a day that never
        # ran one must not borrow it, or the daily page trains its reader to ignore the word that
        # matters on the day it does fail.
        out.append("**No rebuild ran this run** — the read above and the prune are the whole of "
                   "today's work. A rebuild happens on Mondays, on a fixable finding against the "
                   "DEPLOYED image, or on a dispatch with `rebuild: force`.")
    elif verdict.kind == "MOVED":
        out.append("**MOVED** — the rebuild changed these packages:")
        out += [f"- `{name}` {old or '(absent)'} → {new or '(absent)'}" for name, old, new in verdict.moved]
    elif verdict.kind == "INCONCLUSIVE":
        out.append(f"**INCONCLUSIVE** — {verdict.reason}")
    else:
        out.append("**IDENTICAL** — the rebuild resolved the same package versions as the deployed "
                   "image. Nothing to ship.")
    if accepted:
        out.append("")
        out.append("Findings the owner has already accepted are reported here as known, accepted, "
                   "and are never dropped:")
        out += [f"- `{v.cve}` {v.package} {v.installed} (fix {v.fixed or 'none'}) — known, accepted"
                for v in accepted]
    out.append("")

    # --- the decision -----------------------------------------------------------------------------
    out += ["### Decision", "",
            "No rebuild ran, so there was nothing to decide." if not rebuilt else decision.sentence(),
            ""]

    # --- the record -------------------------------------------------------------------------------
    # Layer three of the no-pip guard: every live image, checked inside the image itself. `None` is
    # a run that did not check — the third state, never presented as clean.
    out.append("### Policy — no package manager in a running image")
    out.append("")
    if policy is None:
        out.append("**Not checked this run** — the policy step wrote no table. Treat as unknown, not as clean.")
    else:
        out.append("| Repository | Deployed tag | Result |")
        out.append("|---|---|---|")
        out += [f"| `{repo}` | `{tag}` | {verdict} |" for repo, tag, verdict in policy]
        out.append("")
        if any(not str(verdict).startswith("CLEAN") for _, _, verdict in policy):
            out.append("**POLICY RED** — a running image carries a package manager, or could not be checked. The fix "
                       "is the Dockerfile block (`spec/keeping-current.md` in the kit); the run stays red until "
                       "every live image is clean.")
        else:
            out.append("All live images clean: pip is neither importable nor on PATH in any of them.")
    out.append("")
    out += ["### Base image", ""]
    out.append(f"Resolved base digest: `{base_digest}`" if base_digest else
               "Resolved base digest: not recorded — no rebuild ran this run.")
    if retention:
        out += ["", "### Registry retention", "", retention]
    return "\n".join(out) + "\n"
