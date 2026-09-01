# harness-kit 2026.09 — the portable contract tests: the kit's TEETH.
"""Novel input must land on each guard's SAFE side — on any harness, in any port.

Adapted from the origin project's suite to run standalone (stdlib + pytest, no project
dependencies). Three kinds of test:

1. **The contracts** — every registered contract over hundreds of GENERATED inputs
   (composed shell grammars, invented subcommands, unparseable fragments). Inputs nobody
   wrote down: a literal-string suite once stayed green through four separate bypasses
   because each new bypass was simply absent from the list.
2. **The positive controls** — each guard's own HISTORICAL defect is re-created by
   monkeypatch and the contract above must go red. A contract that has never been seen to
   fail is decoration.
3. **The stdin contract** — the guards as the hook actually runs them: a subprocess fed
   JSON on stdin. Exit code 0 ALWAYS (a crashed hook is an ALLOW in Claude Code, so a
   guard must never signal through exit codes); deny = JSON on stdout; allow = silence;
   an unreadable payload lands on the deny side.

A failure in (1) or (3) is a fail-open finding about the GUARD (or about a port of it);
the fix is in the guard, never in the contract. Determinism: seeds derive from the
contract's own name, so a failure reproduces exactly. Set KIT_GUARD_CONTRACT_SEED to soak
a wider space locally.
"""
from __future__ import annotations

import json
import os
import random
import subprocess
import zlib

import pytest

import guard_registry as reg

SEED_OFFSET = int(os.environ.get("KIT_GUARD_CONTRACT_SEED", "0"))


def _seed(guard: reg.Guard, contract: reg.Contract) -> int:
    """Stable per-contract seed — `hash()` is salted per process and would make a failing
    input unreproducible from the report of it."""
    return zlib.crc32(f"{guard.source}::{contract.name}".encode()) + SEED_OFFSET


def _run_contract(guard: reg.Guard, contract: reg.Contract,
                  iterations: int | None = None) -> list[tuple[object, str]]:
    """Every generated input whose verdict was NOT the declared safe one. Returns rather
    than asserts, so the same machinery serves the contract test (must be empty) and the
    sabotage control (must NOT be empty)."""
    rng = random.Random(_seed(guard, contract))
    bad: list[tuple[object, str]] = []
    for _ in range(iterations or contract.iterations):
        payload = contract.novel(rng)
        verdict = contract.drive(payload)
        if verdict != contract.safe:
            bad.append((payload, verdict))
    return bad


CONTRACTS = [(g, c) for g in reg.GUARDS for c in g.contracts]
IDS = [f"{g.source}::{c.name}" for g, c in CONTRACTS]


# ---------------------------------------------------------------- 1. the contracts

@pytest.mark.parametrize(("guard", "contract"), CONTRACTS, ids=IDS)
def test_novel_input_lands_on_the_safe_side(guard: reg.Guard, contract: reg.Contract):
    bad = _run_contract(guard, contract)
    if bad:
        payload, verdict = bad[0]
        pytest.fail(
            f"{guard.source} — {contract.name}\n"
            f"  {len(bad)} of {contract.iterations} generated input(s) did NOT produce "
            f"the safe verdict {contract.safe!r}.\n"
            f"  Safe direction: {guard.safe_direction}\n"
            f"  Evidence: {guard.evidence}\n"
            f"  First offender returned {verdict!r} for:\n{payload!r}\n"
            f"  Reproduce with seed {_seed(guard, contract)}.")


# ---------------------------------------------------------------- 2. positive controls

def _sabotage_az_whole_string(monkeypatch):
    """The az guard's v1 bypass, restored: ask whether the pin appears ANYWHERE in the
    whole string — so a chained second command inherits a flag it never carried."""
    def whole_string_test(command: str) -> list[str]:
        return [] if "--subscription" in command else ["<unpinned>"]
    monkeypatch.setattr(reg.az_guard, "offending_segments", whole_string_test)


def _sabotage_az_unparseable(monkeypatch):
    """The v2 shrug: what the guard could not parse, it let through."""
    original = reg.az_guard.offending_segments

    def shrug(command: str) -> list[str]:
        try:
            reg.az_guard._parse(command)
        except ValueError:
            return []
        return original(command)
    monkeypatch.setattr(reg.az_guard, "offending_segments", shrug)


def _sabotage_git_denylist(monkeypatch):
    """The implementation the git guard was deliberately NOT given: enumerate the
    destructive subcommands the incident report named and treat everything else as safe —
    the fail-open enumeration; `stash drop`, `filter-branch` and every subcommand git
    grows next year are simply absent from the list, so they pass."""
    named = {"reset", "checkout", "clean"}

    def denylist_classify(args, appends_args):
        stated, rest, _problem = reg.git_scope_guard._split_global_options(args)
        if not rest or stated:
            return None
        return "destructive" if rest[0].lower() in named else None
    monkeypatch.setattr(reg.git_scope_guard, "_classify", denylist_classify)


class _EverythingIsSafe(frozenset):
    """Keeps the real members — generators read them to build values from OUTSIDE the
    set — but says yes to everything: 'what I do not recognise, I wave past'."""

    def __contains__(self, item):                                   # noqa: D105
        return True


def _sabotage_git_unknown_is_safe(monkeypatch):
    """One defect at both of its sites: an unknown subcommand reads as read-only, and a
    global option the guard cannot read is skipped rather than refused."""
    monkeypatch.setattr(reg.git_scope_guard, "_READ_ONLY",
                        _EverythingIsSafe(reg.git_scope_guard._READ_ONLY))
    original = reg.git_scope_guard._split_global_options

    def wave_past(args):
        stated, rest, _problem = original(args)
        return stated, rest, None
    monkeypatch.setattr(reg.git_scope_guard, "_split_global_options", wave_past)


def _sabotage_git_unparseable(monkeypatch):
    """The az guard's v2 shrug, put back in its sibling."""
    original = reg.git_scope_guard.offending_segments

    def shrug(command: str) -> list[str]:
        try:
            reg.git_scope_guard._SHELL._parse(command)
        except ValueError:
            return []
        return original(command)
    monkeypatch.setattr(reg.git_scope_guard, "offending_segments", shrug)


SABOTAGES = {
    "reference/guards/az_guard.py::an unpinned invocation under composed shell constructs":
        _sabotage_az_whole_string,
    "reference/guards/az_guard.py::text that mentions the CLI and cannot be parsed":
        _sabotage_az_unparseable,
    "reference/guards/git_scope_guard.py::a destructive git command under composed shell "
    "constructs": _sabotage_git_denylist,
    "reference/guards/git_scope_guard.py::a subcommand or global option this guard has "
    "never heard of": _sabotage_git_unknown_is_safe,
    "reference/guards/git_scope_guard.py::text that mentions git and cannot be parsed":
        _sabotage_git_unparseable,
}


@pytest.mark.parametrize(("guard", "contract"),
                         [(g, c) for g, c in CONTRACTS
                          if f"{g.source}::{c.name}" in SABOTAGES],
                         ids=[i for i in IDS if i in SABOTAGES])
def test_a_sabotaged_guard_makes_its_own_contract_fail(guard, contract, monkeypatch):
    """Break the guard's safe direction, and the contract above must go red. The sabotage
    re-creates that guard's own historical defect — not a synthetic tripwire: the previous
    bug, put back."""
    clean = _run_contract(guard, contract)
    assert not clean, "the contract is already failing; fix that before reading this control"
    SABOTAGES[f"{guard.source}::{contract.name}"](monkeypatch)
    broken = _run_contract(guard, contract)
    assert broken, (
        f"{guard.source} — {contract.name}: the guard's safe direction was sabotaged and "
        "the contract still passed. The contract does not test what it claims to.")


def test_every_contract_has_a_positive_control():
    """A registered contract with no sabotage is a contract nobody has proved can fail."""
    missing = sorted(i for i in IDS if i not in SABOTAGES)
    assert missing == [], f"contracts without a positive control: {missing}"


# ---------------------------------------------------------------- 3. the stdin contract

def _invoke(script: str, stdin_text: str) -> tuple[int, str, str]:
    r = subprocess.run([reg.python(), str(reg.script_path(script))],
                       input=stdin_text, capture_output=True, text=True, timeout=60)
    return r.returncode, r.stdout, r.stderr


def _payload(command) -> str:
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})


def _is_deny(stdout: str) -> bool:
    if not stdout.strip():
        return False
    doc = json.loads(stdout)
    return doc["hookSpecificOutput"]["permissionDecision"] == "deny"


@pytest.mark.parametrize("script", reg.HOOK_SCRIPTS)
def test_malformed_json_is_silent_and_exits_zero(script):
    """Not a hook payload at all: stay silent, exit 0. Refusing arbitrary stdin noise
    would fire on every non-hook use of the script; crashing (nonzero) is worse — a
    crashed hook is an ALLOW, so the exit code must never carry the verdict."""
    code, out, _err = _invoke(script, "this is not json {")
    assert code == 0
    assert out.strip() == ""


@pytest.mark.parametrize("script", ("az_guard.py", "git_scope_guard.py"))
def test_tool_input_that_is_not_an_object_is_denied(script):
    """`{"tool_input": ["az group list"]}` once raised AttributeError and exited 1 — and
    the harness treats a failed hook as no decision, i.e. an ALLOW. The guards now refuse
    a payload shaped in a way they cannot read, at exit 0."""
    code, out, _err = _invoke(script, json.dumps({"tool_name": "Bash",
                                                  "tool_input": ["az group list"]}))
    assert code == 0
    assert _is_deny(out)


@pytest.mark.parametrize(("script", "command"), [
    ("az_guard.py", "echo hello"),
    ("az_guard.py", "az account show --subscription " + "-".join(
        ["0" * 8, "0" * 4, "0" * 4, "0" * 4, "0" * 12])),
    ("git_scope_guard.py", "git status"),
    ("git_scope_guard.py", "git -C /opt/example-repo reset --hard"),
    ("merge_green_check.py", "ls -la"),
    ("merge_green_check.py", "gh pr view 12"),
])
def test_compliant_commands_pass_in_silence(script, command):
    """The other half of every guard's promise: a guard that refuses routine work gets
    switched off, and a switched-off guard protects nothing."""
    code, out, _err = _invoke(script, _payload(command))
    assert code == 0
    assert out.strip() == "", f"{script} refused compliant {command!r}: {out}"


@pytest.mark.parametrize(("script", "command"), [
    ("az_guard.py", "az group list"),
    ("az_guard.py", "az account show --subscription X && az group list"),
    ("git_scope_guard.py", "git reset --hard origin/main"),
    ("git_scope_guard.py", "git -C . clean -fd"),
    # merge with no parseable PR selector: denied BEFORE any gh call, so this stays
    # network-free. The green-path behaviour needs live PR state and belongs in a project
    # suite with a fixture gh — see the registry's UNCOVERED note.
    ("merge_green_check.py", "gh pr merge --squash"),
])
def test_offending_commands_are_denied_with_json_at_exit_zero(script, command):
    code, out, _err = _invoke(script, _payload(command))
    assert code == 0, f"{script} exited {code} — the deny path must be JSON, never a crash"
    assert _is_deny(out), f"{script} did not deny {command!r}; stdout: {out!r}"
    reason = json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]
    assert reason.strip(), "a refusal with no reason is a wall, not a guard"


@pytest.mark.xfail(
    strict=True,
    reason="RECORDED FAIL-OPEN, found by this suite at kit extraction (2026-09-01): the "
           "merge guard's regex requires text AFTER `gh pr merge`, so a BARE `gh pr "
           "merge` — which gh resolves from the current branch and merges — matches "
           "nothing and passes in silence. The fix belongs in the guard, upstream first "
           "(see TODO.md); strict xfail means this entry goes RED the day someone fixes "
           "it, so the record is deleted rather than left to rot green.")
def test_a_bare_merge_with_no_selector_is_denied():
    code, out, _err = _invoke("merge_green_check.py", _payload("gh pr merge"))
    assert code == 0
    assert _is_deny(out)


@pytest.mark.parametrize("script", ("az_guard.py", "git_scope_guard.py"))
def test_non_string_command_is_silent(script):
    """Nothing to say about a call whose command is not text."""
    code, out, _err = _invoke(script, json.dumps({"tool_name": "Bash",
                                                  "tool_input": {"command": 42}}))
    assert code == 0
    assert out.strip() == ""
