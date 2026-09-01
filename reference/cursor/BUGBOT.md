<!-- harness-kit 2026.09 — the Bugbot review-policy pattern, copied faithfully from the origin project. The 'already doctrine here' list near the end is the origin's own house doctrine, kept as a worked EXAMPLE — replace those bullets with your project's. -->

# Review policy for this repository

**Read this first, because it changes how much weight the rest of the file carries.** There is
no severity filter to configure. Bugbot's findings carry severity in its output, but nothing at
the repository or project level filters or suppresses by severity or by finding type. This file
is **prose handed to a reviewer**, not a setting that enforces anything. Everything below is
guidance that will be followed imperfectly, and a policy that reads like a setting but is only a
suggestion is exactly the kind of thing that gets trusted too far.

It applies to the local pre-push review and to the pull-request review alike.

## What a must-fix is here

Three categories, and only three:

1. **Wrong behaviour** — the code does something other than what it says it does, for an input
   that can actually occur.
2. **Data integrity** — a figure that does not compute what its name claims; a source record
   mutated instead of overlaid; a key that collides across scopes; an ordering that inverts on a
   backfill; a published number whose lineage does not hold.
3. **Security** — secrets in code, config, logs, test fixtures or history; injection on anything
   user- or file-derived; data exposure through a public repository, a published page, or an
   error message; dependency and supply-chain risk.

## What to suppress

Style, formatting, naming taste, import ordering, "consider extracting this into a helper",
"this function is long", docstring wording, test organisation preferences, and alternative
idioms that are not more correct. These are not free to report: every one of them costs the
reader attention that the three categories above need, and a review that is mostly taste teaches
its reader to skim, which is how a real finding gets skimmed too.

## The evidence standard: a must-fix needs a reproduction

State the input, the path through the code, and the wrong result. **A plausible reading is not a
reproduction.** A finding that says "this could fail if X" without establishing that X occurs is
a `later` at best, and should say so about itself rather than arriving dressed as a defect.

This cuts both ways and the second direction is the one that gets missed: when a finding *is*
reproducible, show the reproduction rather than asserting the conclusion, because the reproduction
is what lets a reader disagree with you cheaply.

## Severity is about frequency, not exoticism

**A finding's severity depends on how often the affected thing is done, not on how unusual the
construct looks.** The failure this rule was written from: a guard in this repository had a false
denial — it blocked a legitimate, correct command. The construct looked exotic, so the finding
was labelled low priority. It blocked the most routine operation in the project's daily
workflow, within a minute of being merged.

So, before assigning severity, answer: *how often is the affected thing done?* A false denial on
a daily operation outranks a true positive on a path taken twice a year. Rare-but-catastrophic
still outranks both — the point is that "how weird does this look" is not the axis.

## The class to hunt: fail-open enumeration

**This is what an outside reviewer has been best at catching here, and it has been hand-fixed
nine times.** It survives internal review because every instance looks locally reasonable.

The shape: **a finite list standing in for an infinite one.** A membership test, enum, status
whitelist, allowlist, header case, or branch over a fixed vocabulary — where a value *not* in
the list is treated as fine. Real instances from this repository: a status whitelist that read an
unlisted `Degraded` as idle and let a deployment gate open; a validator that checked one category
of configuration and silently passed the second; a scan that read changed paths only from a
header the tool does not always emit; a guard that tested one string for a flag that every
chained command needs.

**How to review it.** For each such set, name a value that is *not* in it and say what happens to
that value. If the answer is "treated as fine", that is a must-fix. Ask additionally whether the
vocabulary is documented as extensible — an enum that can gain members, a header that may or may
not appear, a format that gains fields. If it is, **no exhaustive list can ever be correct** and
the defect is structural rather than a missing entry.

**The repair is inversion, not addition.** Adding the missing value fixes one instance and leaves
the class intact — the *next* unlisted value fails the same way. Invert the set: enumerate the
terminal or known-safe cases and let everything else fail closed. A patch that only adds the
value you found is itself a finding.

Two adjacent checks worth making in the same pass: **do both twins of a paired rule get the same
strictness**, and **can the fallback a docstring promises actually be reached?**

## What is already doctrine here — do not report it as a discovery, do report violations

- **Guards fail closed, loudly, and early** — before the destructive step, not after.
- **Every detector has a positive control**: a deliberately bad input that must trip it, as a
  test. A guard that cannot be shown to fire is decoration; a guard that cannot be shown to *not*
  over-fire gets deleted the first time it cries wolf.
- **Guards are scripts with tests**, never inline one-liners in configuration where nothing can
  exercise them.
- **Source data is never mutated.** Enrichment is a join-time overlay carrying provenance.
- **Freshness is derived from the artifact, never read back from the job that wrote it.** A guard
  that trusts a value the thing being judged supplied is a finding on its own.
- **This repository is on a public trajectory.** Anything that only resolves inside one
  subscription — registry paths, storage account names, resource names, identity assumptions — is
  a finding on the published surface.

## How findings are used

Findings are one input to a review package, alongside an internal multi-lens panel. A human lead
deduplicates against the panel's findings, buckets each as **must-fix / later / ignore**, and
works within a two-round cap. Bugbot's severity label is an input to that judgement, never the
judgement. Duplicated findings are counted once.
