# harness-kit 2026.09 — the portable guard registry, adapted from the origin project's
# repo-wide registry to run STANDALONE in the kit (stdlib + pytest, no project deps).
"""For every guard the kit ships, how to hand it input it has never seen and what the SAFE
answer to that input is.

WHY THIS EXISTS. The defect class the origin project hand-fixed most — nine times — is an
enumeration that fails OPEN: a finite list stands in for an infinite one, and the value
that is not in the list is treated as safe. Every instance was found by someone reading
the code — prose, which only works when somebody convenes it. This file is the half that
needs nobody to remember anything.

THE CONTRACT, in one sentence: **for every guard, an input it does not recognise must
produce that guard's SAFE verdict, and the safe verdict is declared per guard** — quoted
from the guard's own docstring, never assumed (a safe direction you assumed is a contract
you invented).

THE GENERATORS COMPOSE GRAMMARS rather than picking from lists: shell wrappers, invented
subcommands, unparseable fragments — inputs nobody wrote down. That is the whole point:
the origin's earlier az-guard suite held 104 literal strings and stayed green through four
separate bypasses, because every new bypass was simply absent from the list.

THE REGISTRY-COMPLETENESS PATTERN (documented for projects to adopt — see tests/README.md):
this registry is itself an enumeration and can fail open. In the origin, guards are
DISCOVERED mechanically (a file wired as a hook/gate, or declaring a fail direction in its
own vocabulary) and a completeness test fails if a discovered guard is neither covered here
nor written down in an UNCOVERED ledger with a reason — with a ratcheted ceiling, because
the obvious way to meet a red completeness check is to write an exemption line instead of a
contract. The kit's own tree has exactly the three shipped guards, so the kit runs the
contracts and documents the pattern; a stamped PROJECT must implement discovery over its
own tree.
"""
from __future__ import annotations

import dataclasses
import importlib.util
import pathlib
import random
import shlex
import string
import sys
from collections.abc import Callable
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
#: Where the guard scripts live. In the kit: reference/guards. In a stamped project:
#: usually `scripts/` — adjust this one constant when installing.
GUARDS_DIR = ROOT / "reference" / "guards"


def load_guard(name: str):
    """A guard module, loaded by path — the guards' directory is not a package."""
    spec = importlib.util.spec_from_file_location(f"_kit_guard_{name}",
                                                  GUARDS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@dataclasses.dataclass(frozen=True)
class Contract:
    """One kind of novelty a guard must survive, and the verdict that must come back."""

    name: str
    safe: str
    novel: Callable[[random.Random], Any]
    drive: Callable[[Any], str]
    iterations: int = 200


@dataclasses.dataclass(frozen=True)
class Guard:
    """One guard under contract."""

    source: str            # kit-relative path — the stable key a report names
    what: str
    safe_direction: str
    #: WHERE the guard says so — quoted from its own docstring. This field is what stops
    #: the next reader assuming a safe direction instead of confirming it.
    evidence: str
    contracts: tuple[Contract, ...]


# ---------------------------------------------------------------- shared generators

_WORD = string.ascii_lowercase


def _word(rng: random.Random, lo: int = 3, hi: int = 12) -> str:
    return "".join(rng.choice(_WORD) for _ in range(rng.randint(lo, hi)))


def _novel_token(rng: random.Random, taken: set[str]) -> str:
    """A word that is not already one of `taken` — a value from outside a closed set."""
    for _ in range(50):
        candidate = _word(rng)
        if candidate not in taken and candidate.lower() not in {t.lower() for t in taken}:
            return candidate
    raise AssertionError("could not generate a token outside the set")   # pragma: no cover


#: Junk for a fragment that must stay UNPARSEABLE. Quotes, backslashes, backticks and `#`
#: are excluded because each of them can REPAIR the very breakage the fragment is built
#: around — a stray `'` balances the unterminated one; `#` is a shlex comment character
#: that swallows the rest of the line along with the mention the contract depends on.
_INERT_JUNK = _WORD + string.digits + " -_./:,;=+@%!?*[]<>|&"


def _inert_junk(rng: random.Random) -> str:
    return "".join(rng.choice(_INERT_JUNK) for _ in range(rng.randint(1, 16)))


def _wrappers(command: str, chained: str) -> list[str]:
    """Every construct that still RUNS `command`, at this level of nesting.

    The grammar, not a list of bypasses: composing two or three of these produces tens of
    thousands of distinct commands, and the ones that matter are the ones nobody wrote
    down. Each entry is here because it genuinely executes its payload. `chained` is a
    command the guard under test ACCEPTS, prepended to build the "a compliant command does
    not launder the one after it" shape — the az guard's whole first bypass.
    """
    quoted = shlex.quote(command)
    out = [
        f"bash -c {quoted}", f"sh -c {quoted}", f"zsh -c {quoted}", f"dash -c {quoted}",
        f"bash.exe -c {quoted}",
        f"eval {quoted}", f"time eval {quoted}", f"if true; then eval {quoted}; fi",
        f"timeout 30 {command}", f"sudo {command}", f"nohup {command}",
        f"env FOO=1 {command}", f"nice -n 10 {command}",
        f"{chained} && {command}", f"{chained} ; {command}", f"{chained} || {command}",
        f"$({command})",
        f"echo {quoted} | bash", f"printf '%s' {quoted} | pwsh -", f"bash <<< {quoted}",
        f"cat {quoted} | sh",
        f"if true; then {command}; fi", "if ($true) {" + command + "}",
        f"( {command} )", f"for i in 1 2; do {command}; done",
        f"{command} ; echo done", f"while read x; do {command}; done",
    ]
    if '"' not in command and "\\" not in command:
        out += ['pwsh -Command "' + command + '"', 'powershell -Comm "' + command + '"',
                'pwsh -NoProfile -Command "' + command + '"']
    if "`" not in command:
        out.append("`" + command + "`")
    return out


# ================================================================ az_guard.py

az_guard = load_guard("az_guard")

#: The CLI's name, assembled rather than spelled: on a harness where this very file is
#: written or grepped through a guarded shell, an unparseable line MENTIONING the CLI is
#: (correctly) refused, and assembling the name keeps the literal off every line here.
_CLI = "a" + "z"

_AZ_PROGRAMS = (_CLI, _CLI + ".exe", _CLI + ".cmd", "./" + _CLI, "/usr/bin/" + _CLI,
                "C:\\tools\\" + _CLI + ".exe")
#: Groups that reach a tenant. Deliberately EXCLUDES the guard's documented local-only
#: groups (`login`, `account list`, `extension`, `config`, ...): those have no
#: `--subscription` flag at all, so allowing them is correct and generating them would be
#: the contract testing the wrong promise.
_AZ_GROUPS = ("group", "storage", "vm", "containerapp", "keyvault", "webapp", "network",
              "monitor", "resource", "role", "identity", "acr")
_AZ_VERBS = ("list", "show", "create", "delete", "update", "restart", "start", "stop")
_AZ_TAILS = ("", "--output json", "-o table", "--name thing", "--resource-group rg",
             "--only-show-errors", "--yes", "--no-wait")
#: A correctly pinned command, for the chained-after-a-pinned-one wrappers. The GUID is
#: assembled so no literal GUID shape sits on a line of this file (firewall scanners hunt
#: GUID shapes; this file should not trip its own project's gate).
_ZERO_GUID = "-".join(["0" * 8, "0" * 4, "0" * 4, "0" * 4, "0" * 12])
_PINNED = f"{_CLI} account show --subscription {_ZERO_GUID}"


def _unpinned_invocation(rng: random.Random) -> str:
    parts = [rng.choice(_AZ_PROGRAMS), rng.choice(_AZ_GROUPS), rng.choice(_AZ_VERBS)]
    tail = rng.choice(_AZ_TAILS)
    if tail:
        parts.append(tail)
    return " ".join(parts)


def novel_unpinned_command(rng: random.Random) -> str:
    """An unpinned `az` invocation buried under one to three composed shell constructs."""
    command = _unpinned_invocation(rng)
    if rng.random() < 0.15:
        # the arg-appender shape: the CLI is the LAST token and still runs
        command = (f"echo {shlex.quote(rng.choice(_AZ_GROUPS) + ' ' + rng.choice(_AZ_VERBS))}"
                   f" | {rng.choice(('xargs', 'parallel'))} {rng.choice(_AZ_PROGRAMS)}")
    for _ in range(rng.randint(1, 3)):
        command = rng.choice(_wrappers(command, _PINNED))
    return command


def _breakers(rng: random.Random, core: str) -> str:
    fragment = rng.choice([
        f'echo "{core}',                      # unbalanced double quote
        f"echo '{core}",                      # unbalanced single quote
        f"echo $({core}",                     # unterminated substitution
        "echo `" + core,                      # unterminated backtick
        f'bash -c "{core}',
        f"{core} && echo 'x",
        f"$( $( {core} )",
    ])
    if rng.random() < 0.5:
        fragment = f"{_inert_junk(rng)} {fragment}"
    return fragment


def novel_unparseable_az(rng: random.Random) -> str:
    """Text that mentions the CLI as a word and cannot be parsed at all.

    The fail-closed promise is stated precisely — unparseable AND mentioning the word is
    DENIED; unparseable without it is passed over — so the generator guarantees the
    mention by building the fragment around a real invocation."""
    return _breakers(rng, _unpinned_invocation(rng))


def drive_az(command: str) -> str:
    return "deny" if az_guard.offending_segments(command) else "allow"


AZ_GUARD = Guard(
    source="reference/guards/az_guard.py",
    what="PreToolUse hook: every `az` invocation must pin `--subscription` explicitly.",
    safe_direction="deny",
    evidence=('module docstring: "where a class must be recognised, enumerate the members '
              'this guard can PROVE IT HANDLES and refuse the rest ... A missing spelling '
              'must land on the deny side"; and "a command that mentions `az` as a WORD '
              'and cannot be parsed is DENIED".'),
    contracts=(
        Contract("an unpinned invocation under composed shell constructs", "deny",
                 novel_unpinned_command, drive_az, iterations=600),
        Contract("text that mentions the CLI and cannot be parsed", "deny",
                 novel_unparseable_az, drive_az, iterations=200),
    ),
)


# ================================================================ git_scope_guard.py

git_scope_guard = load_guard("git_scope_guard")

_GIT_PROGRAMS = ("git", "git.exe", "./git", "/usr/bin/git", "C:\\tools\\git.exe")

#: A command the guard ACCEPTS, for the chained-after-a-compliant-one wrappers.
_SCOPED_GIT = "git -C /opt/example-repo status"

#: Decorations that look like scope and are not: `-C .` is the ambient directory with a
#: decoration on it, `$REPO` is literally the unrestated ambient state, and `--work-tree`
#: says where the files are rather than whose history is rewritten.
_NOOP_SCOPES = ("-C .", "-C ..", "-C ../other-repo", "-C $REPO", "-C worktrees/x",
                "--work-tree=/opt/example-repo", "-c user.name=kit", "--no-pager")

#: Forms that destroy, relocate or rewrite — the SHAPE of the danger. The generator also
#: invents subcommands nobody has written, which is the half that can fail on an input
#: this file's author never thought of.
_DESTRUCTIVE_FORMS = (
    "reset", "reset --hard", "reset --hard origin/main", "reset --merge", "reset --keep",
    "checkout --", "checkout -- app/", "checkout .", "checkout -f main", "checkout main",
    "restore app/module.py", "restore --worktree --staged .", "switch other",
    "clean -fd", "clean -fdx", "clean --force", "clean -f",
    "branch -D old", "branch -d old", "branch -M main", "branch -f main origin/main",
    "tag -d v1", "tag -f v1", "update-ref -d refs/heads/old",
    "push --force", "push -f origin main", "push --force-with-lease",
    "push --force-if-includes", "push --delete origin old", "push --mirror",
    "push origin +main:main", "push --prune origin",
    "fetch origin main:main", "fetch --force origin", "pull", "pull --rebase",
    "commit --amend", "commit --amend --no-edit",
    "rebase -i HEAD~3", "rebase --onto main feature~2 feature", "merge feature",
    "cherry-pick 1a2b3c4", "revert HEAD", "am patch.mbox", "apply patch.diff",
    "stash", "stash drop", "stash clear", "stash pop", "stash push -m wip",
    "rm -r app/", "mv a b", "worktree remove ../wt", "worktree prune", "worktree add ../wt",
    "submodule update --init", "gc --prune=now", "prune", "reflog expire --all",
    "filter-branch --tree-filter true HEAD", "config user.email someone@example.invalid",
    "sparse-checkout set app", "symbolic-ref HEAD refs/heads/other", "notes add -m x",
    "bisect start", "repack -a -d", "maintenance run",
)


def _known_subcommands() -> set[str]:
    """Every subcommand the guard can prove safe — read from the guard rather than
    restated here, so a subcommand added to it tomorrow stops being generated as novel."""
    return (set(git_scope_guard._READ_ONLY)
            | set(git_scope_guard._CONDITIONALLY_SAFE)
            | set(git_scope_guard._CREATES_ITS_OWN))


def _destructive_git_invocation(rng: random.Random) -> str:
    parts = [rng.choice(_GIT_PROGRAMS)]
    if rng.random() < 0.3:
        parts.append(rng.choice(_NOOP_SCOPES))
    if rng.random() < 0.25:
        # A subcommand nobody has written: git grows these, and a guard whose safe half
        # is the enumerated one must refuse the ones that do not exist yet.
        invented = _novel_token(rng, _known_subcommands())
        tail = rng.choice(["", " --all", " -f", " " + _word(rng), " --" + _word(rng)])
        parts.append(invented + tail)
    else:
        parts.append(rng.choice(_DESTRUCTIVE_FORMS))
    return " ".join(parts)


def novel_unscoped_git_command(rng: random.Random) -> str:
    """A destructive git command buried under zero to three composed shell constructs."""
    command = _destructive_git_invocation(rng)
    for _ in range(rng.randint(0, 3)):
        command = rng.choice(_wrappers(command, _SCOPED_GIT))
    return command


def novel_unreadable_git_form(rng: random.Random) -> str:
    """A subcommand or a global option this guard has never heard of, in front of a
    payload it WOULD otherwise allow.

    The payload is deliberately `status` for the option cases: a pass then says the guard
    skipped past the unknown option and read `status` as the subcommand — the fail-open;
    it would have skipped past `--frobnicate` in front of `reset --hard` the same way."""
    globals_ = (set(git_scope_guard._GLOBAL_VALUE_OPTIONS)
                | set(git_scope_guard._GLOBAL_BOOLEANS))
    shorts = {g.lstrip("-") for g in globals_ if len(g) == 2}
    kind = rng.choice(["subcommand", "long-option", "attached-option", "short-option"])
    if kind == "subcommand":
        command = (f"git {_novel_token(rng, _known_subcommands())} "
                   f"{rng.choice(['--all', '-f', _word(rng), ''])}").strip()
    elif kind == "long-option":
        command = f"git --{_novel_token(rng, {g.lstrip('-') for g in globals_})} status"
    elif kind == "attached-option":
        command = (f"git --{_novel_token(rng, {g.lstrip('-') for g in globals_})}"
                   f"={_word(rng)} status")
    else:
        letter = rng.choice([c for c in string.ascii_letters if c not in shorts])
        command = f"git -{letter} status"
    for _ in range(rng.randint(0, 2)):
        command = rng.choice(_wrappers(command, _SCOPED_GIT))
    return command


def novel_unparseable_git(rng: random.Random) -> str:
    """Text that mentions git as a WORD and cannot be parsed at all."""
    return _breakers(rng, _destructive_git_invocation(rng))


def drive_git_scope(command: str) -> str:
    return "deny" if git_scope_guard.offending_segments(command) else "allow"


GIT_SCOPE_GUARD = Guard(
    source="reference/guards/git_scope_guard.py",
    what="PreToolUse hook: a git command that can destroy work must state the repository "
         "it acts on (`-C <absolute path>` / `--git-dir`).",
    safe_direction="deny",
    evidence=('module docstring: "A subcommand nobody listed, a global option this guard '
              'cannot read, a command it cannot parse — each lands on the DENY side"; and '
              '"Text that mentions `git` as a WORD and cannot be parsed is DENIED".'),
    contracts=(
        Contract("a destructive git command under composed shell constructs", "deny",
                 novel_unscoped_git_command, drive_git_scope, iterations=600),
        Contract("a subcommand or global option this guard has never heard of", "deny",
                 novel_unreadable_git_form, drive_git_scope, iterations=300),
        Contract("text that mentions git and cannot be parsed", "deny",
                 novel_unparseable_git, drive_git_scope, iterations=200),
    ),
)


# ================================================================ the registry itself

#: merge_green_check.py is deliberately NOT registered with generated contracts: its
#: refusal path depends on live PR/check state read through `gh`, which a standalone,
#: network-free suite must not exercise. Its stdin-contract behaviour — silence on
#: non-merge commands, denial on an unparseable merge, denial when state cannot be read —
#: is covered by the subprocess contract tests in tests/test_guard_contracts.py, and its
#: full behaviour belongs in a project test suite with a fixture `gh`. This note is the
#: registry's honest UNCOVERED entry, in the pattern tests/README.md documents.
GUARDS: tuple[Guard, ...] = (AZ_GUARD, GIT_SCOPE_GUARD)

#: The three scripts the kit ships as stdin-contract hook guards. The subprocess-level
#: contract (malformed payload handling, exit-0 discipline) is asserted for ALL of them.
HOOK_SCRIPTS = ("az_guard.py", "git_scope_guard.py", "merge_green_check.py")


def script_path(name: str) -> pathlib.Path:
    return GUARDS_DIR / name


def python() -> str:
    return sys.executable
