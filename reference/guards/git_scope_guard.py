# harness-kit 2026.09 — reference guard, proven in the origin project's Claude Code harness.
"""PreToolUse guard: a git command that can destroy work must NAME the repository.

Born 2026-08-31, from three incidents in one hour on this workstation — the
hooks-by-evidence threshold is 2:

  1. A `git diff` believed to be reading the engine repo actually read HQ, because the `cd`
     that set the directory was in an earlier segment of a DIFFERENT tool call. A confident
     wrong conclusion followed, and was one step from being acted on.
  2. A ledger commit landed on local `main` instead of its branch, and had to be
     cherry-picked back.
  3. A `git reset --hard origin/main` intended for `main` ran inside a branch worktree and
     destroyed two commits. Recovered only because the reflog held them and the remote
     still had one.

THE GENERALISED SHAPE: a command whose meaning depends on ambient state nobody restated.
This venture is TWO repositories with worktrees under each, and the shell's working
directory persists between some tool calls and silently resets between others — so `cd X &&
cmd` in one call and `cmd` in the next are not the same context, and nothing announces the
difference. `git diff` in the wrong ambient directory gives a wrong answer; `git reset
--hard` in the wrong one destroys work.

THE RULE: a git command that can destroy, discard, rewrite, relocate or delete work must
state the repository it acts on — `git -C <absolute path>` or `--git-dir=<absolute path>`.
Ordinary safe git is untouched, with or without `-C`.

WHY THE SAFE SET IS THE ENUMERATED ONE, and not the destructive set. The defect class this
repository has hand-fixed eight times is an enumeration that fails OPEN: a finite list
stands in for an infinite one, and the value that is not in the list is treated as safe. A
list of DESTRUCTIVE subcommands has exactly that shape — `git filter-branch` missing from
it is a silent hole, and git grows subcommands. So the inversion, the same one
`scripts/az_guard.py` records: enumerate the members this guard can PROVE are safe and
require the rest to name their repository. A subcommand nobody listed, a global option this
guard cannot read, a command it cannot parse — each lands on the DENY side.

FAIL-CLOSED, STATED PRECISELY so the promise is true rather than decorative:

  * A subcommand outside `_READ_ONLY` and `_CONDITIONALLY_SAFE` — including one that does
    not exist yet — requires a stated repository.
  * A global option before the subcommand that this guard does not recognise is refused
    outright, because the subcommand cannot then be located and every classification below
    would be a guess.
  * A `-C` whose path is RELATIVE (`.`, `..`, `../engine`) or unexpanded (`$REPO`,
    `%CD%`) does not count as stated: the whole point is to name something ambient state
    does not already decide. This is the guard enforcing the venture's own standing rule,
    which says `git -C <abs path>`, not merely `-C`.
  * Text that mentions `git` as a WORD and cannot be parsed is DENIED, with a reason that
    says parsing failed. Unparseable text WITHOUT such a mention is passed over in silence —
    refusing `echo don't` is the usability failure that gets a guard switched off.
  * A shell payload this guard cannot read (`-EncodedCommand`, `-File`, a flag nobody has
    thought of) is refused without requiring `git` to be visible: absence of the string
    proves nothing inside base64.
  * If the shell parser this guard borrows cannot be loaded at all, every command mentioning
    `git` is refused. A guard that cannot parse is a guard that must not decide.

WHY DENIALS HERE ARE CHEAPER THAN THE AZ GUARD'S, which is what makes the inversion
affordable: this guard's refusal is not "you may not do that", it is "say which repository".
The remedy is one flag, always available and always correct, and it is what the venture's
own lesson already asks for. A false denial therefore costs a restated command, not a
blocked operation. That is the ONLY reason the safe set may be the enumerated half here
while the az guard had to enumerate its local-only groups instead.

Usability is still a security property, and the priced costs are named at their sites:
`git config`, `git switch`, `git stash push` and `git merge` all require a stated repository
and none of them destroys anything on a good day. Ordinary safe git — `status`, `log`,
`diff`, `show`, `add`, `commit`, `push` without force, `fetch`, `pull --ff-only`, `branch`
listing, `stash list`, `worktree list` — passes untouched, because a guard that blocks
routine work gets switched off and a switched-off guard protects nothing.

WHAT THIS DELIBERATELY DOES NOT DO. It is not the force-push gate: `git -C <abs> push
--force` passes here, because this guard asks one question and answers it. Force-pushing and
history rewriting are governed by the commit protocol ("never auto"), which is a different
promise and belongs in a different instrument. Nor is it a sandbox: `$GIT_BIN reset --hard`,
a script in a file it cannot read, and `ssh host 'git ...'` all defeat it. It is a
mistake-preventer for an agent that is trying to comply.

HOW IT PARSES. It does not enumerate the ways a command can be wrapped — that list has no
end and every missing entry fails open. It borrows the shell parser from
`scripts/az_guard.py` (its sibling, and the file that paid for that parser four times over):
here-doc bodies lifted out first and judged by what CONSUMES them, command substitutions
lifted quote-aware, `shlex` in POSIX mode with punctuation split out, shell `-c` payloads and
`eval` arguments followed to any depth, pipelines into a shell treated as code. Command
position is decided the same way too: a `git` token counts as an invocation when it is first
in a simple command or when the token after it looks like a git argument, so `sudo git`,
`timeout 30 git`, `xargs git` and every wrapper nobody has named are caught with no list to
maintain, while `rg git docs/`, `grep git README.md` and `find . -name git` are left alone.

GUARD-CONTRACT: registered in `tests/guard_registry.py`; the safe verdict is DENY.

Reads the hook JSON on stdin; silent (exit 0, no output) for anything it does not refuse.
A crash would be an ALLOW, so nothing escapes `main()` and the error path DENIES.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import sys


def _load_shell_parser():
    """`scripts/az_guard.py`, loaded by path for its shell parser, or `(None, reason)`.

    Borrowed rather than copied. The parser is ~250 lines of quote-aware substitution
    lifting, here-doc consumer classification and payload-flag inversion, every line of
    which was paid for by a bypass in that guard; a second copy here would be a second copy
    to drift, and "two parallel rules where one is strict and one is loose is the same bug
    wearing a symmetry" is this repository's own recorded lesson.

    The coupling is real and is stated rather than hidden: the two guards ship as twins in
    both repositories and this one cannot decide anything without that one's parser. Losing
    it is therefore not a shrug — `offending_segments` refuses everything that mentions git
    and says why, which is loud, immediate and fixable, and is the only direction a guard is
    allowed to fail in.
    """
    path = pathlib.Path(__file__).resolve().parent / "az_guard.py"
    try:
        spec = importlib.util.spec_from_file_location("_git_scope_guard_shell", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as exc:                                # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"
    missing = [name for name in ("_lift_heredocs", "_parse", "_stages", "_shell_payloads",
                                "_executes_stdin", "_pipelines", "_basename", "_MAX_DEPTH")
               if not hasattr(module, name)]
    if missing:
        return None, f"{path.name} no longer provides {', '.join(missing)}"
    return module, ""


_SHELL, _SHELL_ERROR = _load_shell_parser()

#: The program, matched against a token's BASENAME with any executable suffix removed, so
#: `git`, `./git`, `/usr/bin/git` and `C:\Program Files\Git\bin\git.exe` are all the CLI.
_GIT_NAMES = frozenset({"git"})

#: Wrappers that APPEND arguments from stdin, so a TRAILING `git` really is an invocation:
#: `echo 'reset --hard' | xargs git` runs it. Same list, same known limitation, as the az
#: guard: a name missing here falls back to the position rule, whose answer for a trailing
#: `git` is allow.
_ARG_APPENDERS = frozenset({"xargs", "parallel"})

#: `git` as a WORD. A substring test fires on `github`, `.gitignore`, `digit` and `legit`,
#: which matters on the refusal paths: an unparseable command containing `.gitignore` would
#: otherwise become a denial.
_GIT_MENTION = re.compile(r"(?<![0-9a-z_])git(?![0-9a-z_])", re.IGNORECASE)

#: What a git command line looks like just after the program name: a bare lowercase
#: subcommand (`status`, `reset`), a `--long-flag` with or without an attached value
#: (`--git-dir=/x`), or a `-x` single-letter flag (`-C`). Anything else — a path, a
#: capitalised filename, `-type` — says the `git` before it was a search term, not a program.
#:
#: The `=value` half was added after the guard-contract generator found it missing:
#: `timeout 30 git --work-tree=/x reset --hard` put an attached-value option straight after
#: `git`, the pattern did not match it, and the invocation was never recognised at all. The
#: priced cost is that `rg git --color=never docs/` now refuses — but note that
#: `rg git --color never docs/` ALREADY refused, because the bare `--long-flag` was always
#: matched here. Adding `=value` made the rule consistent rather than adding a new class of
#: false denial, and `main()`'s refusal names the other way out.
_GIT_ARGUMENT = re.compile(r"[a-z][a-z0-9-]*\Z|--[a-z][a-z0-9-]*(?:=.*)?\Z|-[a-z]\Z",
                           re.IGNORECASE | re.DOTALL)

# ---------------------------------------------------------------- what "stated" means

#: A path that names a repository rather than pointing at whatever is ambient. Windows
#: drive-qualified paths are accepted WITHOUT their separator (`D:example-repo`) because
#: POSIX `shlex` eats the backslashes of an unquoted `D:\example-repo`, and refusing the
#: single most common correctly-scoped command on this workstation would be the false denial
#: that gets the guard switched off. A drive letter is a statement of intent either way.
_ABSOLUTE = re.compile(r"\A(?:[A-Za-z]:|[\\/]{2}[^\\/]|/|~[\\/])")


def _is_stated_path(path: str | None) -> bool:
    """Whether this `-C`/`--git-dir` value names a repository ambient state does not decide.

    `.`, `..` and `../engine` are refused deliberately: a relative `-C` restates nothing —
    it is the same ambient directory with a decoration, and accepting it would let the guard
    be satisfied without the mistake being prevented. So is `$REPO` / `%CD%`: an unexpanded
    variable is EXACTLY the ambient state that nobody restated, which is the thing this
    guard exists to refuse.
    """
    if not path or "$" in path or "%" in path or "`" in path:
        return False
    return bool(_ABSOLUTE.match(path))


#: Global options that take a VALUE, so the token after them is not the subcommand. An
#: option missing from both this set and `_GLOBAL_BOOLEANS` is refused rather than guessed
#: past: skipping the wrong number of tokens would mis-identify the subcommand, and a
#: mis-identified subcommand is a classification made up.
_GLOBAL_VALUE_OPTIONS = frozenset({
    "-C", "-c", "--git-dir", "--work-tree", "--namespace", "--super-prefix",
    "--config-env", "--attr-source",
})

_GLOBAL_BOOLEANS = frozenset({
    "-p", "--paginate", "-P", "--no-pager", "--bare", "--no-replace-objects",
    "--replace-objects", "--literal-pathspecs", "--glob-pathspecs", "--noglob-pathspecs",
    "--icase-pathspecs", "--no-optional-locks", "--optional-locks", "--exec-path",
    "--html-path", "--man-path", "--info-path", "--version", "-v", "--help", "-h",
    "--no-lazy-fetch", "--no-advice",
})

#: The options that STATE a repository. `--work-tree` alone is not one: it says where the
#: files are, not which repository's history is being rewritten.
_SCOPE_OPTIONS = frozenset({"-C", "--git-dir"})

# ---------------------------------------------------------------- the proven-safe half

#: Subcommands that cannot modify a repository at all, so no flag on them can make the
#: ambient directory matter for anything but the ANSWER. Incident 1 was exactly that — a
#: wrong answer from `git diff` — and it is deliberately NOT refused here: gating reads would
#: mean `git status` and `git log` demanding a flag, which is the routine work whose refusal
#: gets a guard switched off. The wrong ANSWER is guarded one step later, where the action it
#: implies (`git checkout -- <path>`, `git reset --hard`) does have to name its repository.
_READ_ONLY = frozenset({
    "status", "log", "diff", "show", "blame", "annotate", "shortlog", "describe",
    "rev-parse", "rev-list", "ls-files", "ls-tree", "ls-remote", "cat-file", "grep",
    "whatchanged", "name-rev", "merge-base", "cherry", "count-objects", "diff-tree",
    "diff-files", "diff-index", "for-each-ref", "show-ref", "show-branch", "verify-commit",
    "verify-tag", "verify-pack", "check-ignore", "check-attr", "check-mailmap", "var",
    "version", "help", "range-diff", "fsck",
})


def _flag_name(token: str) -> str:
    """The option's name, without an attached `=value`."""
    return token.split("=", 1)[0]


def _flags(args: list[str]) -> list[str]:
    return [_flag_name(a) for a in args if a.startswith("-") and a not in {"-", "--"}]


def _words(args: list[str]) -> list[str]:
    """Non-flag arguments, stopping at `--`: the sub-subcommand lives in the first one."""
    out = []
    for arg in args:
        if arg == "--":
            break
        if not arg.startswith("-"):
            out.append(arg)
    return out


def _first_word(args: list[str]) -> str:
    words = _words(args)
    return words[0].lower() if words else ""


#: `git branch` flags that only LIST or CREATE. Everything else — `-d`, `-D`, `--delete`,
#: `-m`, `-M`, `--move`, `-f`, `--force`, `-u`, `--set-upstream-to`, `--unset-upstream`, and
#: any spelling nobody has thought of — falls through to requiring a stated repository.
_BRANCH_SAFE_FLAGS = frozenset({
    "-a", "--all", "-r", "--remotes", "-v", "-vv", "--verbose", "-l", "--list", "--color",
    "--no-color", "--show-current", "-q", "--quiet", "-i", "--ignore-case", "--merged",
    "--no-merged", "--contains", "--no-contains", "--points-at", "--sort", "--format",
    "--column", "--no-column", "--abbrev", "--no-abbrev", "-t", "--track", "--no-track",
})

#: `git tag` flags that only LIST or CREATE. `-d`, `--delete`, `-f` and `--force` are not
#: here, so they require a stated repository.
_TAG_SAFE_FLAGS = frozenset({
    "-l", "--list", "--contains", "--no-contains", "--merged", "--no-merged", "--points-at",
    "--sort", "--format", "--color", "-a", "--annotate", "-m", "--message", "-s", "--sign",
    "-u", "--local-user", "-F", "--file", "--cleanup", "-e", "--edit", "--column",
    "--no-column", "-i", "--ignore-case",
})

#: `git push` arguments that make it something other than a fast-forward publish. The
#: refspec form `+main:main` is a force push spelled without a flag, which is why the
#: predicate below tests for a leading `+` as well as for these.
_PUSH_UNSAFE_FLAGS = frozenset({
    "-f", "--force", "--force-with-lease", "--force-if-includes", "-d", "--delete",
    "--mirror", "--prune",
})


def _safe_commit(args: list[str]) -> bool:
    """`--amend` rewrites the ambient branch's last commit, which is history rewriting —
    the thing this venture's commit protocol says is never automatic — and it is
    unrecoverable through anything but the reflog. Every other `commit` only ever adds."""
    return "--amend" not in _flags(args)


def _safe_fetch(args: list[str]) -> bool:
    """A bare `fetch` only ever adds remote-tracking refs. A REFSPEC (`origin main:main`)
    writes a local branch, and a leading `+` or `--force` writes it non-fast-forward — which
    is incident 3 wearing a different hat."""
    if {"-f", "--force"} & set(_flags(args)):
        return False
    return not any(":" in word or word.startswith("+") for word in _words(args))


def _safe_push(args: list[str]) -> bool:
    return not (_PUSH_UNSAFE_FLAGS & set(_flags(args))
                or any(word.startswith("+") for word in _words(args)))


def _safe_pull(args: list[str]) -> bool:
    """Inverted, not filtered: `pull` is safe only in the ONE form proven not to rewrite or
    merge into whatever branch is ambient. A bare `git pull` is a merge (or, configured
    differently, a rebase) onto a branch nobody named."""
    return "--ff-only" in _flags(args)


def _safe_branch(args: list[str]) -> bool:
    return all(flag in _BRANCH_SAFE_FLAGS for flag in _flags(args))


def _safe_tag(args: list[str]) -> bool:
    return all(flag in _TAG_SAFE_FLAGS or re.fullmatch(r"-n\d*", flag)
               for flag in _flags(args))


def _only_subcommands(*safe: str):
    """A predicate for a subcommand whose FIRST WORD selects between reading and writing —
    `stash list` versus `stash drop`, `worktree list` versus `worktree remove`."""
    allowed = frozenset(safe)

    def predicate(args: list[str]) -> bool:
        return _first_word(args) in allowed
    return predicate


#: Subcommands that are safe only in a proven form. The predicate returns True for the form
#: this guard can prove adds or reads and nothing else; anything else needs a stated
#: repository. `clone` and `init` are absent from every table on purpose — see `_classify`.
_CONDITIONALLY_SAFE = {
    "add": lambda args: True,          # staging only ever adds; no flag on it destroys
    "commit": _safe_commit,
    "fetch": _safe_fetch,
    "push": _safe_push,
    "pull": _safe_pull,
    "branch": _safe_branch,
    "tag": _safe_tag,
    "stash": _only_subcommands("list", "show"),
    "worktree": _only_subcommands("list"),
    "remote": _only_subcommands("", "show", "get-url"),
    "submodule": _only_subcommands("status", "summary"),
    "notes": _only_subcommands("list", "show"),
    "reflog": _only_subcommands("", "show"),
    "bisect": _only_subcommands("log", "view", "visualize"),
}

#: Subcommands that CREATE a repository at a path they name themselves, so there is no
#: ambient repository for them to act on wrongly.
_CREATES_ITS_OWN = frozenset({"clone", "init"})

#: What to say about the ones this guard knows are dangerous. This dict is NOT the gate —
#: the gate is "not provably safe" — it only makes the refusal actionable. A subcommand
#: missing from here still requires a stated repository; it just gets the generic sentence.
_WHY = {
    "reset": "discards commits and, with --hard, uncommitted work",
    "checkout": "switches branches or overwrites files from the index",
    "restore": "overwrites working-tree files from the index or a commit",
    "switch": "moves the working tree to another branch",
    "clean": "DELETES UNTRACKED FILES, which no reflog can return",
    "branch": "deletes, force-moves or re-points a branch",
    "tag": "deletes or force-moves a tag",
    "push": "publishes non-fast-forward, deletes remote refs, or mirrors",
    "commit": "--amend rewrites the ambient branch's last commit",
    "rebase": "rewrites the ambient branch's history",
    "merge": "writes a merge into whatever branch is ambient",
    "cherry-pick": "applies commits onto whatever branch is ambient",
    "revert": "writes a revert onto whatever branch is ambient",
    "am": "applies patches onto whatever branch is ambient",
    "apply": "overwrites working-tree files",
    "stash": "moves, drops or clears uncommitted work",
    "rm": "deletes tracked files",
    "mv": "moves tracked files",
    "worktree": "adds, removes or prunes a working tree",
    "remote": "adds, removes or re-points a remote",
    "submodule": "checks out or resets submodule working trees",
    "gc": "prunes unreachable objects",
    "prune": "prunes unreachable objects",
    "reflog": "expire/delete destroys the safety net that made these incidents recoverable",
    "filter-branch": "rewrites every commit in the ambient repository",
    "filter-repo": "rewrites every commit in the ambient repository",
    "update-ref": "writes or deletes a ref directly",
    "symbolic-ref": "re-points HEAD",
    "replace": "rewrites what a commit resolves to",
    "sparse-checkout": "removes files from the working tree",
    "config": "writes configuration into whichever repository is ambient",
    "fetch": "a refspec writes local refs, and `+`/--force writes them non-fast-forward",
    "pull": "merges or rebases into whatever branch is ambient",
    "notes": "edits or removes notes",
    "bisect": "checks the working tree out at other commits",
    "maintenance": "runs repacking and pruning tasks",
    "repack": "rewrites the object store",
}

_GENERIC_WHY = ("this guard cannot prove it is safe, so it must say which repository it "
                "acts on")


def _mentions_git(text: str) -> bool:
    return _GIT_MENTION.search(text) is not None


def _split_global_options(args: list[str]) -> tuple[bool, list[str], str | None]:
    """`(repository_is_stated, the subcommand and its arguments, refusal or None)`.

    The refusal is for a global option this guard cannot read: it cannot then say which
    token is the subcommand, and every judgement after that would be invented.
    """
    stated = False
    index = 0
    while index < len(args):
        token = args[index]
        if token in {"-", "--"} or not token.startswith("-"):
            break
        name = _flag_name(token)
        attached = "=" in token
        if name in _GLOBAL_VALUE_OPTIONS:
            if attached:
                value: str | None = token.split("=", 1)[1]
                index += 1
            else:
                value = args[index + 1] if index + 1 < len(args) else None
                index += 2
            if name in _SCOPE_OPTIONS and _is_stated_path(value):
                stated = True
        elif name in _GLOBAL_BOOLEANS and not attached:
            index += 1
        else:
            return stated, args[index:], (
                f"a global option this guard cannot read ({token}), so it cannot tell "
                f"which token is the subcommand")
    return stated, args[index:], None


def _classify(args: list[str], appends_args: bool) -> str | None:
    """Why this git invocation must be refused, or None if it may proceed.

    THE INVERSION, in five lines: read-only subcommands pass, provably-additive ones pass,
    repository-creating ones pass, anything with a stated repository passes, and everything
    else — including a subcommand written after this guard was — is refused.
    """
    stated, rest, problem = _split_global_options(args)
    if problem is not None:
        return problem
    if not rest:
        if appends_args:
            # `xargs git` runs `git <whatever stdin says>`. The subcommand is not in the
            # command at all, so it cannot be classified and must not be guessed at.
            return "the subcommand arrives on stdin, so this guard cannot classify it"
        return None                                 # bare `git`, or `git --version`
    subcommand = rest[0].lower()
    tail = rest[1:]
    if subcommand in _READ_ONLY or subcommand in _CREATES_ITS_OWN:
        return None
    predicate = _CONDITIONALLY_SAFE.get(subcommand)
    if predicate is not None and predicate(tail):
        return None
    if stated:
        return None
    return _WHY.get(subcommand, _GENERIC_WHY)


def _looks_like_git_arguments(token: str) -> bool:
    """Whether this token says the `git` before it was a program rather than a search term."""
    return bool(_GIT_ARGUMENT.fullmatch(token))


def _executes_stdin_anywhere(command: str, depth: int) -> bool:
    """Whether anything in `command` — at this level or inside a command substitution — runs
    the text that is fed to it. It decides whether here-doc bodies are CODE or TEXT.

    The az guard asks this of the top-level stages only, and the metamorphic control found
    what that misses: in

        echo $(bash <<'EOF'
        git clean -fd
        EOF
        )

    the shell that runs the body sits inside a substitution, so a top-level scan sees only
    `echo`, calls the body text, and the payload runs anyway. The same shape hides
    `{ cat <<'EOF' ... } | bash` one level down. What CONSUMES the body decides — and the
    consumer need not be at the outermost level any more than it needs to share a line.

    Anything unparseable or nested past the cap returns True: this cannot then prove the
    body inert, and the unprovable case lands on the deny side, as everywhere else here.
    """
    if depth > _SHELL._MAX_DEPTH:
        return True
    try:
        tokens, substitutions = _SHELL._parse(command)
    except ValueError:
        return True
    if any(_SHELL._executes_stdin(group) for _operator, group in _SHELL._stages(tokens)):
        return True
    return any(_executes_stdin_anywhere(text, depth + 1) for text in substitutions)


def _unscoped_in_simple_command(tokens: list[str]) -> list[str]:
    """Git invocations in this simple command that do not state the repository they act on.

    Command position WITHOUT a wrapper whitelist, exactly as the az guard decides it: the
    first token, or a `git` whose next token looks like a git argument. That catches `sudo
    git`, `timeout 30 git`, `xargs git`, `if git ...` and wrappers nobody has named, while
    leaving `rg git docs/`, `grep git README.md`, `which git` and `find . -name git` alone —
    the single-word search for `git` is the common case, and it is precisely the search
    someone runs to audit this guard.
    """
    appends_args = any(_SHELL._basename(t) in _ARG_APPENDERS for t in tokens)
    starts = [
        i for i, token in enumerate(tokens)
        if _SHELL._basename(token) in _GIT_NAMES
        and (i == 0 or appends_args
             or (i + 1 < len(tokens) and _looks_like_git_arguments(tokens[i + 1])))
    ]
    offenders: list[str] = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(tokens)
        why = _classify(tokens[start + 1:end], appends_args)
        if why is not None:
            offenders.append(f"{' '.join(tokens[start:end])}  <- {why}")
    return offenders


def _analyse(command: str, depth: int, protect: bool) -> list[str]:
    """The same walk the az guard makes, over the same parser, asking a different question.

    `protect` carries the DIALECT down: when on, backslashes are doubled before lexing so
    Windows paths survive as one token. It is threaded through the recursion rather than
    applied once at the top, because `shlex` undoes the doubling inside double quotes.
    """
    if not command.strip():
        return []
    # Here-doc bodies come out FIRST, before quotes, substitutions or tokens are read, and
    # are judged by their CONSUMER: a body fed to `cat` or `git commit -F-` is text this
    # guard never reads, a body fed to a shell is code. Every wiki entry in this venture is
    # written with a here-doc whose prose discusses commands like `git reset --hard`, so
    # reading bodies as code would refuse the operator's most routine write — which is
    # precisely what the az guard's first live act did.
    skeleton, bodies = _SHELL._lift_heredocs(command)
    text = skeleton.replace("\\", "\\\\") if protect else skeleton
    try:
        parsed: tuple[list[str], list[str]] | None = _SHELL._parse(text)
    except ValueError:
        parsed = None
    stages = _SHELL._stages(parsed[0]) if parsed is not None else None
    # `stages is None` means the command could not be parsed, so nothing about it can be
    # proved and the bodies are read as code — the deny side.
    runs_input = stages is None or (
        any(_SHELL._executes_stdin(group) for _operator, group in stages)
        or any(_executes_stdin_anywhere(text, depth + 1) for text in parsed[1]))
    scripts = bodies if bodies and runs_input else []
    mentions = _mentions_git(skeleton) or any(_mentions_git(s) for s in scripts)
    if depth > _SHELL._MAX_DEPTH:
        # Refuse rather than abandon: giving up on depth is a fail-open.
        return [f"<nested deeper than this guard will follow: {command}>"] if mentions else []

    offenders: list[str] = []
    for script in scripts:
        offenders.extend(_analyse(script, depth + 1, protect))
    if stages is None:
        # THE FAIL-CLOSED PROMISE, and its exact limit. The test is on the SKELETON: a `git`
        # that appears only in a here-doc body has already been judged by what consumes it,
        # and must not be dragged back in by a parse failure on the line that wrote it down.
        if _mentions_git(skeleton):
            offenders.append(f"<could not be parsed, so it is refused: {command}>")
        return offenders

    for index, (operator, group) in enumerate(stages):
        payloads, refusals = _SHELL._shell_payloads(group)
        offenders.extend(refusals)
        offenders.extend(_unscoped_in_simple_command(group))
        # A here-STRING feeding a shell is that shell's script. Here-DOCS never reach here:
        # their bodies and their `<<DELIM` operators were lifted above.
        if "<" in operator and index and _SHELL._executes_stdin(stages[index - 1][1]):
            payloads.extend(group)
        for payload in payloads:
            offenders.extend(_analyse(payload, depth + 1, protect))

    # A shell receiving a pipeline executes whatever the left side produced, so every other
    # stage of that pipeline is a source of code: `echo 'git clean -fd' | bash`.
    for pipeline in _SHELL._pipelines(stages):
        if not any(_SHELL._executes_stdin(group) for group in pipeline):
            continue
        for group in pipeline:
            if _SHELL._executes_stdin(group):
                continue
            for token in group:
                offenders.extend(_analyse(token, depth + 1, protect))

    for substitution in parsed[1]:
        offenders.extend(_analyse(substitution, depth + 1, protect))
    return offenders


def offending_segments(command: str) -> list[str]:
    """Every git invocation in `command` that can destroy work without saying where.

    Empty means allow. Each entry names the invocation at fault and why, so the refusal is
    actionable rather than a wall.

    Parsed twice when — and only when — the command contains `\\git`. This hook gates the
    PowerShell tool as well as Bash, and the two disagree about the backslash: POSIX treats
    it as an escape, so `C:\\tools\\git.exe clean -fd` lexes to the harmless
    `C:toolsgit.exe` and slips through, while PowerShell runs it. Gated on that substring
    rather than run always because doubling backslashes changes how `\\"` lexes, which would
    start refusing ordinary commit messages containing escaped quotes — a false denial of
    exactly the kind that gets a guard switched off. `\\git` is the only thing the second
    pass can newly catch, so the gate costs nothing.
    """
    if _SHELL is None:
        if not _mentions_git(command):
            return []
        return [f"<this guard's shell parser could not be loaded ({_SHELL_ERROR}), so it "
                f"cannot read this command and refuses it: {command}>"]
    found = _analyse(command, 0, protect=False)
    if "\\git" in command.lower():
        seen = set(found)
        for item in _analyse(command, 0, protect=True):
            item = item.replace("\\\\", "\\")
            if item not in seen:
                seen.add(item)
                found.append(item)
    return found


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": f"git-scope-guard: {reason}",
    }}))
    sys.exit(0)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:                                   # noqa: BLE001
        return                                          # not a hook payload; stay silent
    try:
        if not isinstance(payload, dict):
            return
        tool_input = payload.get("tool_input")
        if not isinstance(tool_input, dict):
            # The harness treats a failed hook as NO DECISION, so a crash is an ALLOW — the
            # one failure mode this guard must never have. A payload shaped in a way it
            # cannot read is refused rather than guessed at.
            if tool_input is None:
                return
            deny("the hook payload's tool_input is not an object, so the command could not "
                 "be read. Refusing rather than guessing.")
        command = tool_input.get("command") or ""
        if not isinstance(command, str):
            return                                      # nothing to say about this call
        bad = offending_segments(command)
    except SystemExit:
        raise
    except Exception as exc:                            # noqa: BLE001
        deny(f"the guard itself failed on this command ({type(exc).__name__}), and a guard "
             f"that errors would otherwise let the call through. Refusing.")
    if not bad:
        return
    first = bad[0]
    shown = first if len(first) <= 200 else first[:197] + "..."
    deny(f"{len(bad)} git command(s) in this call do not say which repository they act on "
         f"— the first is: {shown!r}. This workstation holds TWO repositories with "
         f"worktrees under each, and the shell's working directory persists between some "
         f"tool calls and silently resets between others, so a command whose target is "
         f"ambient is a command nobody stated: a `git reset --hard origin/main` meant for "
         f"main ran in a branch worktree here and destroyed two commits. Re-issue it as "
         f"`git -C <ABSOLUTE path> ...` (or --git-dir=<absolute path>). A relative `-C .` "
         f"or an unexpanded `$VAR` does not count — it restates nothing. If this is not a "
         f"git command at all — a search whose PATTERN happens to be `git` with a flag "
         f"after it — put the flag IN FRONT of the pattern; quoting the pattern will not "
         f"help, because the tokenizer strips the quotes before this guard sees it.")


if __name__ == "__main__":
    main()
