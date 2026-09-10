# tests/ — the portable contract tests, and the pattern behind them

**Dependency floor: Python ≥ 3.10 and pytest. Nothing else** — no project code, no
network, no fixtures beyond the standard library. Run from the kit root:

```sh
python -m pytest tests/ -q
```

When stamping a project, copy this directory into the project's `tests/` and adjust
`GUARDS_DIR` at the top of `guard_registry.py` to where the guard scripts were installed
(usually `scripts/`). A re-implementation of a guard — any language, any harness — passes
the same stdin-contract tests by honoring the same contract (`spec/guards.md`); the
generated-input contracts drive the Python reference directly.

## The registry-completeness pattern (documented for projects to adopt)

The registry (`guard_registry.py`) is itself an enumeration, and an enumeration can fail
open: the guard someone adds next month and never registers is exactly the guard nothing
tests. The origin project closes that loop mechanically, and a stamped project should
implement the same three pieces over its own tree:

1. **Discovery.** Find guard files mechanically, on two axes: (a) anything wired as a
   gate — scripts referenced from the hook configuration (`.claude/settings.json` and its
   user-level twin) or invoked by a CI workflow as a check; (b) anything that declares a
   fail direction in its own source vocabulary ("fail closed", "safe verdict",
   "refuses", a `GUARD-CONTRACT` marker comment). Axis (a) catches a guard that states
   nothing; axis (b) catches one not yet wired.
2. **The completeness test.** Every discovered file must be either covered by a
   `Guard(...)` entry with contracts, or written down in an `UNCOVERED` ledger entry
   carrying a kind (`not-a-guard` / `guard-not-yet-driven`), a reason longer than a
   shrug, and a date. Anything discovered that is neither FAILS the build — adding a
   guard without registering it turns CI red, which is the point.
3. **The ratchet.** `UNCOVERED` has a literal ceiling asserted by a test, because the
   obvious way to meet a red completeness check is to write an exemption line instead of
   a contract. Raising the ceiling is a reviewed edit somebody has to defend. Positive
   controls apply to the completeness check itself: plant an imposter guard in a temp
   tree and prove discovery reports it — a completeness check nobody has watched fire is
   worth exactly as much as the enumeration it replaced.

The kit's own tree ships exactly the guards this registry covers, plus one honest
UNCOVERED note (the merge guard's gh-dependent paths — see the note in
`guard_registry.py`), so the kit runs the contracts and documents the pattern rather than
shipping a discovery pass over a tree that cannot grow. A project's tree CAN grow;
implement discovery there.

The Cursor bridge is not a Guard in this registry. `tests/test_cursor_bridge.py` watches
the recorded empty-stdin fail-open residual and the install path. `tests/test_guard_wiring_probe.py`
covers adapter-aware `guard_wiring` (Cursor-only stamps must not fail the Claude layer).
`tests/test_kit_manifest.py` and `tests/test_kit_poll.py` cover the stamper and the poll
(proposal-only; STANDUP is the path map).

## Two halves, neither sufficient alone

These contracts ask only *"does novel input land on the safe side"*. A guard that refused
EVERY input would pass every contract here and be worthless — usability is a security
property, because a guard that blocks routine work gets switched off. The other half is a
MUST_ALLOW suite in the project's own tests: the routine commands the guard must pass in
silence (the stdin-contract tests here carry a seed of that half; grow it with every
false denial the guard ever produces, so each one stays fixed).
