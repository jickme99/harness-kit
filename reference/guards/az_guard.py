# harness-kit 2026.09 — reference guard, proven in the origin project's Claude Code harness.
"""PreToolUse guard: every `az` invocation must pin `--subscription` explicitly.

Born 2026-08-29 (the machine default may point at an unrelated tenant, and this venture
shares a workstation with day-job subscriptions). Rewritten repeatedly, because every
version until this one reasoned about the command as TEXT, or reasoned about it as
structure but recognised the pieces by SPELLING.

  v1 asked whether `--subscription` appeared anywhere in the whole string, so
  `az account show --subscription X && az group list` passed while the second command ran
  against the machine default.

  v2 split the string on shell separators with a regex, and was broken in both directions
  at once: it failed OPEN through `bash -c`, `$(...)`, backticks, subshells, `xargs`,
  `timeout` and `if`, and failed CLOSED on prose that merely MENTIONS az, refusing
  `git commit -m "...az group list"` and `grep 'az ...' docs/`.

  v3 parsed properly but kept three enumerations-by-spelling, and each one leaked:
  `eval` was recognised only at token 0 (`time eval "az ..."` walked straight past it),
  shell payload flags were matched by a pattern anchored at the wrong end (`bash -cx`
  passed, `bash -xc` did not — same flags, different order), and `{` was not punctuation,
  so `if ($true) {az group list}` allowed while the space-separated twin denied. The
  verdict flipped on a single space.

  v4 (this one, plus the here-document rule below) went live and its FIRST live act was a
  false denial of a routine `cat >> wiki/log.md <<'EOF'` whose PROSE mentioned the CLI.
  A here-doc body cannot be quoted, so the "a quoted argument is text" escape did not
  reach it and every wiki entry in this venture is written that way. The lesson, recorded
  because an adversarial review had filed this as `later`: A FALSE DENIAL'S SEVERITY IS
  HOW OFTEN THE BLOCKED THING IS DONE, NOT HOW EXOTIC THE CONSTRUCT LOOKS.

THE RULE THIS FILE NOW FOLLOWS: where a class must be recognised, enumerate the members
this guard can PROVE IT HANDLES and refuse the rest, rather than listing the members it
knows are dangerous and allowing the rest. A missing spelling must land on the deny side.
Both halves matter — a guard that refuses routine work gets switched off, and a
switched-off guard protects nothing, so usability is a SECURITY property here.

How it works:

  1. Command substitutions — `$(...)` and backticks — are lifted out first, quote-aware,
     and analysed as their own commands. Done before tokenizing because substitutions run
     inside double quotes and NOT inside single quotes, a distinction no tokenizer
     preserves once quotes are stripped.
  2. What remains is tokenized with `shlex` in POSIX mode with punctuation characters
     enabled, so `;`, `|`, `&`, `(`, `)`, `<`, `>`, `{` and `}` become their own tokens
     and quoted runs collapse into ONE token. That is what separates code from text: in
     `git commit -m "az group list"` the message is one token and cannot be in command
     position, while in `{az group list}` the braces are operators and `az` is.
  3. Each simple command is scanned for `az` in COMMAND position, and each invocation
     must carry its OWN `--subscription`, up to the next `az`. Per invocation rather than
     per segment, because `shlex` folds the newline that separates two commands into
     whitespace.
  4. Code reached indirectly is followed to any depth: shell `-c` payloads, `eval`/`iex`
     arguments, and anything piped or here-stringed into a shell that is reading stdin.

Here-documents, and the tension they sit in. A here-doc body is the one argument a shell
offers that CANNOT be quoted, so the "a quoted argument is text" rule that keeps
`git commit -m "az ..."` working does not reach it, and reading every body as code denied
the routine `cat >> wiki/log.md <<'EOF'` that writes this venture's wiki. Reading every
body as TEXT is the opposite error and is a real execution vector: `bash <<< 'az ...'` and
`bash <<'EOF'` genuinely run their payload. WHAT CONSUMES THE BODY DECIDES, never what the
body looks like — a body fed to a shell or to `eval` is code and is followed; a body fed to
`cat`, `git commit -F-`, `gh pr create --body-file -` or a plain file redirect is text and
is not read at all. An introducer line this guard cannot parse cannot prove the body inert,
so that body is read as code: the unprovable case lands on the deny side, as everywhere
else here.

Command position, without a wrapper whitelist. An `az` token counts as an invocation when
it is the first token of a simple command, or when the token after it LOOKS LIKE an az
argument (a bare lowercase subcommand word, a `--long-flag`, or a `-x` single-letter
flag). That catches `xargs az …`, `timeout 30 az …`, `sudo az …`, `if az …` and every
wrapper nobody has thought of yet, with no list to maintain, while leaving `rg az docs/`,
`grep az README.md` and `find . -name az -type f` alone — the single-word search for `az`
is the common case, and it is precisely the search someone runs to AUDIT this guard.

Fail-closed, stated precisely so the promise is true: a command that mentions `az` as a
WORD and cannot be parsed is DENIED, with a reason that says parsing failed. Unparseable
input without such a mention is passed over in silence — refusing `echo don't` would be
the same usability failure as v2. The mention test is a word test, not a substring test,
because `azure\\`, `hazard` and `blaze` are not the CLI, and `D:\\...\\azure\\` is
everyday PowerShell here.

Two shells, not one. The hook's matcher is `Bash|PowerShell`, so both dialects arrive.
Parsing is POSIX, which is right for Bash and close enough for PowerShell's separators,
pipes, braces and `$(...)`; the one place they diverge dangerously is the backslash,
handled by a second pass whose dialect is carried through every level of recursion.

Not a sandbox. Deliberate obfuscation defeats it (`$AZ_BIN group list`, a script in a file
it cannot read, `ssh host 'az ...'` on another machine). It is a mistake-preventer for an
agent that is trying to comply, and the residual holes are named at their sites below.

Reads the hook JSON on stdin; silent (exit 0, no output) for anything it does not refuse.
A crash would be an ALLOW, so nothing escapes `main()` and the error path DENIES.
"""
from __future__ import annotations

import itertools
import json
import re
import shlex
import sys

#: How far to follow nested shells, pipelines and substitutions before refusing. Nothing
#: legitimate on this workstation nests ten deep; anything that does is refused.
_MAX_DEPTH = 10

#: The CLI's own name. Compared against the token's BASENAME with any executable suffix
#: removed, so `az`, `./az`, `/usr/bin/az` and `C:\...\az.cmd` are all the CLI.
_AZ_NAMES = frozenset({"az"})

#: Stripped before a name is matched, so the Windows spellings of the CLI, the shells and
#: the wrappers resolve to the same program as their bare names. Deliberately short:
#: stripping more would start eating real filenames (`azure.md` must stay `azure.md`).
_EXECUTABLE_SUFFIXES = (".exe", ".cmd", ".bat", ".ps1", ".com")

#: Programs whose argument is SHELL CODE. A name missing from this set is the documented
#: fail-open in the design: its payload is read as inert text. The alternative — treating
#: every `-c` argument as code — refuses `grep -c 'az group list' docs/`, and a guard that
#: blocks grep gets switched off.
_SHELLS = frozenset({
    "sh", "bash", "zsh", "dash", "ksh", "mksh", "ash", "busybox", "csh", "tcsh", "fish",
    "nu", "xonsh", "elvish", "pwsh", "powershell", "cmd", "command",
})

#: Programs that execute their ORDINARY ARGUMENTS as shell code, with no flag marking
#: which one. `eval "az group list"` is as wide a hole as `bash -c` and looks nothing like
#: it; `iex` is PowerShell's spelling. Scanned at EVERY token position, exactly as
#: `_SHELLS` is: checking only token 0 meant anything in front of `eval` demoted it out of
#: position and past the rule (`time eval "az ..."`, `then eval "az ..."`).
_CODE_TAKING_PROGRAMS = frozenset({"eval", "iex", "invoke-expression"})

#: Wrappers that APPEND arguments from stdin, which defeats the "a trailing `az` is only
#: being named" rule: `echo 'group list' | xargs az` really does run `az group list`.
#: NOTE FOR THE NEXT READER: this list is NOT safe to leave short. A name missing from it
#: falls back to the generic position rule, whose answer is ALLOW for a trailing `az` — so
#: an unlisted arg-appender fails OPEN, same as any other enumeration here.
_ARG_APPENDERS = frozenset({"xargs", "parallel"})

#: Arguments that cannot reach a tenant, so cannot reach the WRONG tenant.
_TENANTLESS_FLAGS = frozenset({"--help", "-h", "--version"})

#: `--help` anywhere in the argument list, at any depth of subcommand, reaches no tenant —
#: it prints usage and exits. Kept separate from `_TENANTLESS_FLAGS` (which must be the
#: ONLY arguments present) because `az account list --help` is how an operator finds out
#: which flags a subcommand takes, and refusing it shuts the way out of a refusal.
_HELP_FLAGS = frozenset({"--help", "-h"})

#: az subcommands that operate on the LOCAL CLI installation or the local credential
#: cache and never on a subscription's resources. Verified against `az <cmd> --help`:
#: these have no `--subscription` flag at all, so the guard's demand is impossible to
#: satisfy and the refusal is pure obstruction. `az account list` matters most — it is how
#: you discover the subscription id you are meant to pin, so refusing it closes the door
#: and eats the key.
#:
#: This IS an enumeration, and deliberately one that fails toward DENIAL: a missing entry
#: is a false denial (annoying, reported, fixable), while a wrong entry — something that
#: does accept `--subscription` — would be a hole. Entries are admitted only on the
#: principle above: local installation or credential state, never tenant resources.
_LOCAL_ONLY_GROUPS = frozenset({
    "login", "logout", "version", "upgrade", "feedback", "find", "interactive",
    "self-test", "survey", "extension", "config", "cache", "bicep", "init",
})
_LOCAL_ONLY_PAIRS = frozenset({("account", "list"), ("account", "clear")})

#: The pin, in both spellings. `-s` is NOT accepted: it is the short flag for other things
#: on some az subcommands, and a guard that guesses is a guard that can be argued into a
#: wrong tenant.
_PIN = "--subscription"

#: Stands in for a lifted-out `$(...)` / backtick run, so the surrounding command still
#: tokenizes with its original structure.
_SUBST = "__azguard_substitution__"

#: `{` and `}` are in here because PowerShell script blocks are ordinary style, not
#: obfuscation: `if ($true) {az group list}` must not read as one token `{az`.
_SHELL_PUNCTUATION = "();<>|&{}"

#: `az` as a WORD. A substring test fires on `azure`, `hazard` and `blaze`, which matters
#: on the refusal paths below: `ls D:\example-repo\azure\` has a trailing backslash that
#: POSIX `shlex` cannot parse, and a substring test would turn that into a denial.
_AZ_MENTION = re.compile(r"(?<![0-9a-z_])az(?![0-9a-z_])", re.IGNORECASE)

#: What an az command line looks like just after the program name: a bare lowercase
#: subcommand (`group`, `account`, `storage`), a `--long-flag`, or a `-x` single-letter
#: flag. Anything else — a path, a capitalised filename, `.`, `--`, `-type` — says the
#: `az` before it was a search term, not a program.
_AZ_ARGUMENT = re.compile(r"[a-z][a-z0-9-]*\Z|--[a-z][a-z0-9-]*\Z|-[a-z]\Z",
                          re.IGNORECASE)


def _basename(token: str) -> str:
    """The program name a token would resolve to, lowercased and without its executable
    suffix. Path- and extension-insensitive on purpose: `/usr/bin/az group list` and
    `az.cmd group list` are every bit the CLI that `az group list` is, and `bash.exe -c`
    is every bit the shell that `bash -c` is."""
    name = re.split(r"[\\/]", token)[-1].lower()
    for suffix in _EXECUTABLE_SUFFIXES:
        if name.endswith(suffix):
            return name[:-len(suffix)]
    return name


def _mentions_az(text: str) -> bool:
    return _AZ_MENTION.search(text) is not None


def _is_flag(token: str) -> bool:
    """A switch or option, as opposed to a value. `-` and `--` alone are neither."""
    if token in {"-", "--"}:
        return False
    return token.startswith("-") or bool(re.fullmatch(r"/[A-Za-z]{1,12}", token))


def _reads_payload(token: str) -> bool:
    """Whether this guard can PROVE it reads what follows this flag as shell code.

    The inversion. v3 asked the opposite question — does this flag look like `-c`? — with
    a pattern anchored at one end, so `bash -xc` matched and `bash -cx` did not, though
    both run. Worse, `-ec` matched, and PowerShell's `-EncodedCommand` payload is base64:
    reading it as shell code "proved" it contained no `az` and waved it through, which is
    strictly worse than not looking. Anything this returns False for is treated as a flag
    whose value cannot be read, and the invocation carrying it is refused.
    """
    low = token.lower()
    if low in {"/c", "/k"}:
        return True
    if low.startswith("--"):
        name, clustered = low[2:], False
    elif low.startswith("-"):
        name, clustered = low[1:], True
    else:
        return False
    if not name:
        return False
    # PowerShell accepts any unambiguous prefix of -Command: -Com, -Comm, -Comma, ...
    if name[0] == "c" and "command".startswith(name):
        return True
    # A POSIX short-flag cluster containing `c`, in ANY order: -c, -lc, -cx, -xc, -cv.
    # `e` and `f` are excluded because they mark payload forms this cannot read —
    # -EncodedCommand's base64 and -File's path — and a cluster is ambiguous between the
    # dialects. `bash -euxc '...'` is therefore refused rather than read; that is the
    # priced cost of not letting `-ec` through.
    return (clustered and bool(re.fullmatch(r"[a-z]+", name))
            and "c" in name and "e" not in name and "f" not in name)


def _read_delimited(text: str, start: int, opener: str, closer: str) -> tuple[str, int]:
    """Read a `$(...)`-style run beginning at `text[start] == opener`.

    Returns the inner text and the index just past the closer. Quote state is tracked so a
    `)` inside a quoted argument does not close the substitution early, and nesting is
    counted so `$(a $(b))` is lifted as one run (the recursion re-parses it). Raises
    ValueError if it never closes — which the caller turns into a DENIAL.
    """
    depth = 0
    in_single = in_double = False
    i = start
    while i < len(text):
        ch = text[i]
        if in_single:
            in_single = ch != "'"
        elif ch == "\\" and i + 1 < len(text):
            i += 1                                  # escaped char, whatever it is
        elif ch == "'" and not in_double:
            in_single = True
        elif ch == '"':
            in_double = not in_double
        elif not in_double:
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    return text[start + 1:i], i + 1
        i += 1
    raise ValueError(f"unterminated {opener}{closer}")


def _read_backticks(text: str, start: int) -> tuple[str, int]:
    """Read a backtick substitution beginning at ``text[start] == '`'``."""
    i = start + 1
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text):
            i += 2
            continue
        if text[i] == "`":
            return text[start + 1:i], i + 1
        i += 1
    raise ValueError("unterminated backtick substitution")


def _lift_substitutions(command: str) -> tuple[str, list[str]]:
    """Replace every command substitution with a placeholder; return the skeleton and the
    substituted commands.

    Done before tokenizing because quote CONTEXT decides whether a substitution runs, and
    tokenizing throws that context away: `"$(az ...)"` executes, `'$(az ...)'` does not.
    Raises ValueError on unbalanced quotes or an unterminated substitution.
    """
    inner: list[str] = []
    out: list[str] = []
    in_single = in_double = False
    i = 0
    while i < len(command):
        ch = command[i]
        if in_single:
            out.append(ch)
            if ch == "'":
                in_single = False
            i += 1
        elif ch == "\\" and i + 1 < len(command):
            out.append(command[i:i + 2])            # keep the escape for shlex to resolve
            i += 2
        elif ch == "'" and not in_double:
            in_single = True
            out.append(ch)
            i += 1
        elif ch == '"':
            in_double = not in_double
            out.append(ch)
            i += 1
        elif ch == "$" and command[i + 1:i + 2] == "(":
            text, i = _read_delimited(command, i + 1, "(", ")")
            inner.append(text)
            out.append(_SUBST)
        elif ch == "`":
            text, i = _read_backticks(command, i)
            inner.append(text)
            out.append(_SUBST)
        else:
            out.append(ch)
            i += 1
    if in_single or in_double:
        raise ValueError("unbalanced quotes")
    return "".join(out), inner


def _read_heredoc_delimiter(line: str, i: int) -> tuple[str | None, int]:
    """The here-doc delimiter word beginning at `line[i]`, and the index just past it.

    All four spellings — `EOF`, `'EOF'`, `"EOF"`, `\\EOF` — yield the same delimiter: the
    quoting decides only whether the body is parameter-expanded, which this guard does not
    model.

    A bare word that does not START with a letter or `_` is NOT read as a delimiter, and
    that guard is load-bearing rather than cosmetic: `$(( 1 << 2 ))` is an arithmetic
    shift, and reading its `2))` as a here-doc delimiter would swallow the remainder of
    the command as inert text. That is a fail-OPEN, which is the one direction this
    function is not allowed to be wrong in.
    """
    if i < len(line) and line[i] in "'\"":
        quote = line[i]
        end = line.find(quote, i + 1)
        if end == -1:
            return None, i
        return (line[i + 1:end] or None), end + 1
    j = i + 1 if line[i:i + 1] == "\\" else i
    start = j
    while j < len(line) and (line[j].isalnum() or line[j] in "_-."):
        j += 1
    word = line[start:j]
    if not word or not (word[0].isalpha() or word[0] == "_"):
        return None, i
    return word, j


def _heredoc_openers(line: str) -> list[tuple[str, bool, int, int]]:
    """`(delimiter, strips_leading_tabs, start, end)` for each here-doc opened on `line`.

    Quote-aware, for the same reason `_lift_substitutions` is: the `<<` in
    `git commit -m "a << b"` is text, and a scan that could not tell would turn ordinary
    messages into refusals. `<<<` is stepped over rather than matched — a here-STRING
    carries its payload on the same line, and `_stages` already treats it as an operator.
    """
    out: list[tuple[str, bool, int, int]] = []
    in_single = in_double = False
    i = 0
    while i < len(line):
        ch = line[i]
        if in_single:
            in_single = ch != "'"
            i += 1
        elif ch == "\\" and i + 1 < len(line):
            i += 2
        elif ch == "'" and not in_double:
            in_single = True
            i += 1
        elif ch == '"':
            in_double = not in_double
            i += 1
        elif not in_double and ch == "<" and line[i + 1:i + 2] == "<":
            if line[i + 2:i + 3] == "<":
                i += 3                                  # a here-STRING, not a here-doc
                continue
            j = i + 2
            strips = line[j:j + 1] == "-"
            j += 1 if strips else 0
            while j < len(line) and line[j] in " \t":
                j += 1
            delimiter, j = _read_heredoc_delimiter(line, j)
            if delimiter is None:
                i += 2
                continue
            out.append((delimiter, strips, i, j))
            i = j
        else:
            i += 1
    return out


def _lift_heredocs(command: str) -> tuple[str, list[str]]:
    """Strip every here-document BODY out of `command`.

    Returns the skeleton — the command with both the bodies and the `<<DELIM` operators
    removed, so it tokenizes as the command it actually is — and the bodies, in the order
    the shell reads them.

    Done before tokenizing, exactly like `_lift_substitutions`, and for the same reason:
    the structure that decides whether the text is code is destroyed by the tokenizer. Once
    `cat >> wiki/log.md <<'EOF'` and its body have been flattened into one token stream,
    the prose is indistinguishable from a simple command, and `az guard was enabled today`
    reads as an unpinned invocation. It did, on this guard's first live call.
    """
    if "<<" not in command:
        return command, []
    lines = command.split("\n")
    skeleton: list[str] = []
    bodies: list[str] = []
    i = 0
    while i < len(lines):
        raw = lines[i]
        i += 1
        openers = _heredoc_openers(raw)
        cleaned, last = "", 0
        for _delimiter, _strips, start, end in openers:
            cleaned += raw[last:start]
            last = end
        skeleton.append(cleaned + raw[last:])
        for delimiter, strips, _start, _end in openers:
            body: list[str] = []
            while i < len(lines):
                candidate = lines[i]
                i += 1
                probe = candidate.rstrip("\r")
                if (probe.lstrip("\t") if strips else probe) == delimiter:
                    break
                body.append(candidate)
            # An UNTERMINATED body runs to the end of the input, which is what the shell
            # does with it too. No refusal is owed for that on its own: whether the text
            # matters at all is still decided by what consumes it.
            bodies.append("\n".join(body))
    return "\n".join(skeleton), bodies


def _runs_its_input(stages: list[tuple[str, list[str]]] | None) -> bool:
    """Whether anything in this command executes what is fed to it — the test that decides
    whether here-doc bodies are CODE or TEXT.

    Asked of the WHOLE command rather than of the line that opened the here-doc, and the
    difference is a bypass. The line-scoped version of this reads `cat` in

        { cat <<'EOF'
        az group list
        EOF
        } | bash

    calls the body text, and hands it to a shell three lines later. A here-doc's body and
    the thing that ends up running it need not share a line, so nothing narrower than the
    whole command can be trusted here.

    `None` means the command could not be parsed: this guard cannot then prove anything
    about it, so the bodies are read as code, which is the deny side.

    The priced cost, stated because it is a real false denial: a call that writes a wiki
    entry with a here-doc AND separately pipes something into a shell has its prose read as
    code. `bash -c '...'` does NOT trigger it — that stage already has its script — so the
    shape has to be a bare `| bash`, `| sh` or `| iex` sharing one tool call with a
    here-doc. That is worth the brace-group bypass above.
    """
    return stages is None or any(_executes_stdin(group) for _operator, group in stages)


def _tokenize(command: str) -> list[str]:
    """Tokens, with shell punctuation split out and quoted runs collapsed to one token."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=_SHELL_PUNCTUATION)
    lexer.whitespace_split = True
    return list(lexer)


def _parse(command: str) -> tuple[list[str], list[str]]:
    """Skeleton tokens plus lifted substitutions, or ValueError.

    Retries once with a dangling trailing backslash removed. POSIX `shlex` raises on one,
    which turned `ls D:\\example-repo\\azure\\` and a bash line continuation at the end
    of the string into refusals. A backslash with nothing after it cannot hide a command,
    so dropping it is safe in the only direction that matters.
    """
    try:
        skeleton, substitutions = _lift_substitutions(command)
        return _tokenize(skeleton), substitutions
    except ValueError:
        trimmed = re.sub(r"\\+\s*\Z", "", command)
        if trimmed == command:
            raise
        skeleton, substitutions = _lift_substitutions(trimmed)
        return _tokenize(skeleton), substitutions


def _stages(tokens: list[str]) -> list[tuple[str, list[str]]]:
    """Simple commands, each paired with the operator that PRECEDED it.

    The operator is kept because it carries meaning v3 discarded: a stage after `|` is fed
    by the one before it, and a stage after `<<<` is a here-string. Anything made only of
    shell punctuation is an operator: `;`, `&&`, `||`, `|`, `(`, `)`, `{`, `}`, `&{`, and
    redirections.
    """
    out: list[tuple[str, list[str]]] = []
    operator, current = "", []
    for token in tokens:
        if token and all(ch in _SHELL_PUNCTUATION for ch in token):
            out.append((operator, current))
            operator, current = token, []
        else:
            current.append(token)
    out.append((operator, current))
    return [(op, group) for op, group in out if group]


def _is_pin(token: str) -> bool:
    return token == _PIN or token.startswith(_PIN + "=")


def _shell_payloads(tokens: list[str]) -> tuple[list[str], list[str]]:
    """Payloads to analyse as shell code, and refusals for payloads that cannot be read."""
    payloads: list[str] = []
    refusals: list[str] = []

    # Code-takers are scanned at every position, exactly as shells are. The paired rules
    # having different position handling is what let `time eval "az group list"` and
    # `if true; then eval "az group list"; fi` through: anything in front of `eval`
    # demoted it out of token 0. The priced cost is `grep eval 'az group list'`, which
    # now refuses — one command, against a whole class of bypass.
    for index, token in enumerate(tokens):
        if _basename(token) in _CODE_TAKING_PROGRAMS:
            payloads.extend(tokens[index + 1:])
            break

    shell_at = next((i for i, t in enumerate(tokens) if _basename(t) in _SHELLS), None)
    if shell_at is None:
        return payloads, refusals

    index = shell_at + 1
    while index < len(tokens):
        token = tokens[index]
        if _reads_payload(token):
            if index + 1 < len(tokens):
                payloads.append(tokens[index + 1])
                index += 2
                continue
        elif _is_flag(token):
            following = tokens[index + 1] if index + 1 < len(tokens) else None
            if following is not None and not _is_flag(following):
                # A flag this cannot read, carrying a value. Whether it is
                # `-EncodedCommand <base64>`, `-File <path>` or a spelling nobody has
                # thought of, the shell will run something this guard has not seen.
                # Refused WITHOUT requiring `az` to be visible: an opaque payload is
                # exactly the case where absence of the string proves nothing. A flag
                # followed by another flag is a switch, so `pwsh -NoProfile -Command ...`
                # is not caught by this.
                refusals.append(f"<a shell payload this guard cannot read "
                                f"({token}): {' '.join(tokens)}>")
                break
        index += 1
    return payloads, refusals


def _executes_stdin(tokens: list[str]) -> bool:
    """Whether this stage runs whatever text is fed to it.

    A shell with no readable payload flag reads its script from stdin — `bash`, `bash -s`,
    `pwsh -` — and so does `iex` at the end of a pipeline. `bash -c '...'` does not: it
    already has its script.
    """
    if any(_basename(t) in _CODE_TAKING_PROGRAMS for t in tokens):
        return True
    return (any(_basename(t) in _SHELLS for t in tokens)
            and not any(_reads_payload(t) for t in tokens))


def _looks_like_az_arguments(token: str) -> bool:
    return bool(_AZ_ARGUMENT.fullmatch(token))


def _is_local_only(args: list[str]) -> bool:
    """An az subcommand that touches only the local install or credential cache."""
    words = [a for a in itertools.takewhile(lambda a: not a.startswith("-"), args)]
    if not words:
        return False
    if words[0].lower() in _LOCAL_ONLY_GROUPS:
        return True
    return len(words) >= 2 and (words[0].lower(), words[1].lower()) in _LOCAL_ONLY_PAIRS


def _unpinned_in_simple_command(tokens: list[str]) -> list[str]:
    """`az` invocations in this simple command that carry no `--subscription` of their own."""
    appends_args = any(_basename(t) in _ARG_APPENDERS for t in tokens)

    # Command position WITHOUT a wrapper whitelist: the first token, or an `az` whose next
    # token looks like an az argument. The second half catches `xargs`, `timeout`, `sudo`,
    # `if`, loop bodies and wrappers nobody has named, while leaving the single-word
    # search — `rg az docs/`, `grep az README.md`, `find . -name az -type f` — alone. v3
    # used "not the last token", which denied all of those; searching for `az` is the
    # first thing anyone auditing this guard does.
    starts = [
        i for i, token in enumerate(tokens)
        if _basename(token) in _AZ_NAMES
        and (i == 0 or appends_args
             or (i + 1 < len(tokens) and _looks_like_az_arguments(tokens[i + 1])))
    ]

    offenders: list[str] = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(tokens)
        args = tokens[start + 1:end]
        if any(a.lower() in _HELP_FLAGS for a in args):
            continue                                # usage text reaches no tenant
        if not args and not appends_args:
            continue                                # bare `az` prints usage
        if args and all(a.lower() in _TENANTLESS_FLAGS for a in args):
            continue
        if _is_local_only(args):
            continue                                # no --subscription flag exists to add
        if not any(_is_pin(a) for a in args):
            offenders.append(" ".join(tokens[start:end]))
    return offenders


def _analyse(command: str, depth: int, protect: bool) -> list[str]:
    """`protect` carries the DIALECT down. When on, backslashes are doubled before lexing
    so Windows paths survive as one token. It must be threaded through the recursion, not
    applied once at the top: `shlex` undoes the doubling inside double quotes, so
    `bash -c "C:\\tools\\az.exe group list"` was re-lexed as POSIX one level down and the
    path dissolved — the single-quoted twin denied while the double-quoted one allowed."""
    if not command.strip():
        return []
    # Here-doc bodies come out FIRST, before quotes, substitutions or tokens are read: a
    # body is not part of the command's syntax, and leaving it in is what made prose read
    # as code. Each body is then judged by its CONSUMER, not by its content.
    skeleton, bodies = _lift_heredocs(command)
    text = skeleton.replace("\\", "\\\\") if protect else skeleton
    try:
        parsed: tuple[list[str], list[str]] | None = _parse(text)
    except ValueError:
        parsed = None
    stages = _stages(parsed[0]) if parsed is not None else None
    scripts = bodies if bodies and _runs_its_input(stages) else []
    # The mention test runs on the CODE — the skeleton and any body that will be executed.
    # A body destined for `cat` is text this guard never reads, so an `az` inside it is no
    # more a mention than one inside a quoted commit message.
    mentions = _mentions_az(skeleton) or any(_mentions_az(s) for s in scripts)
    if depth > _MAX_DEPTH:
        # Refuse rather than abandon: giving up on depth is exactly the fail-open v2 had.
        return [f"<nested deeper than this guard will follow: {command}>"] if mentions \
            else []

    offenders: list[str] = []
    for script in scripts:
        offenders.extend(_analyse(script, depth + 1, protect))
    if stages is None:
        # THE FAIL-CLOSED PROMISE, and its exact limit: refuse what mentions az as a WORD
        # and cannot be parsed; stay silent on everything else, because denying
        # `echo don't` would get this guard switched off and it protects nothing off. The
        # test is on the SKELETON: an `az` that only ever appears in a here-doc body has
        # already been judged above by what consumes it, and must not be dragged back in
        # here by a parse failure on the line that wrote it down.
        if _mentions_az(skeleton):
            offenders.append(f"<could not be parsed, so it is refused: {command}>")
        return offenders
    substitutions = parsed[1]

    for index, (operator, group) in enumerate(stages):
        payloads, refusals = _shell_payloads(group)
        offenders.extend(refusals)
        offenders.extend(_unpinned_in_simple_command(group))

        # A here-STRING feeding a shell is that shell's script: `bash <<< 'az group list'`.
        # Here-DOCS never reach here — `_lift_heredocs` removed both their bodies and
        # their `<<DELIM` operators above, because a here-doc's body is on other lines and
        # this test can only see the tokens of one stage.
        if "<" in operator and index and _executes_stdin(stages[index - 1][1]):
            payloads.extend(group)

        for payload in payloads:
            offenders.extend(_analyse(payload, depth + 1, protect))

    # A shell or code-taker receiving a pipeline executes whatever the left side produced,
    # so every other stage of that pipeline is a source of code: `echo 'az group list' |
    # bash`, `'az group list' | iex`. Stages are grouped by the `|` operator only; `||` is
    # a different token and does not pipe.
    for pipeline in _pipelines(stages):
        if not any(_executes_stdin(group) for group in pipeline):
            continue
        for group in pipeline:
            if _executes_stdin(group):
                continue
            for token in group:
                offenders.extend(_analyse(token, depth + 1, protect))

    for substitution in substitutions:
        offenders.extend(_analyse(substitution, depth + 1, protect))
    return offenders


def _pipelines(stages: list[tuple[str, list[str]]]) -> list[list[list[str]]]:
    """Runs of stages joined by `|`."""
    out: list[list[list[str]]] = []
    current: list[list[str]] = []
    for operator, group in stages:
        if operator == "|" and current:
            current.append(group)
            continue
        if len(current) > 1:
            out.append(current)
        current = [group]
    if len(current) > 1:
        out.append(current)
    return out


def offending_segments(command: str) -> list[str]:
    """Every `az` invocation anywhere in `command` that lacks its own `--subscription`.

    Empty means allow. Each entry is rendered for the refusal message, so it names the
    invocation at fault rather than the whole line the operator already typed.

    Parsed twice when — and only when — the command contains `\\az`. This hook gates the
    PowerShell tool as well as Bash (matcher `Bash|PowerShell`), and the two disagree
    about the backslash: POSIX treats it as an escape, so `C:\\tools\\az.exe group list`
    lexes to the harmless `C:toolsaz.exe` and slips through, while PowerShell runs the
    CLI. The second pass protects backslashes so Windows paths survive as one token.

    Gated on the `\\az` substring rather than run always because doubling backslashes
    changes how `\\"` lexes, which would start refusing bash commands with escaped quotes
    inside a message — a false denial of exactly the kind that got v2 switched off. `\\az`
    is the only thing the second pass can newly catch, so the gate costs nothing.
    """
    found = _analyse(command, 0, protect=False)
    if "\\az" in command.lower():
        seen = set(found)
        for item in _analyse(command, 0, protect=True):
            # Undo the doubling before comparing and before showing it: inside single
            # quotes shlex leaves `\\` alone, so the same offence renders differently in
            # the two passes and would otherwise be counted twice in the refusal.
            item = item.replace("\\\\", "\\")
            if item not in seen:
                seen.add(item)
                found.append(item)
    return found


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": f"az-guard: {reason}",
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
            # `{"tool_input": ["az group list"]}` used to raise AttributeError and exit 1.
            # The harness treats a failed hook as no decision, so a crash is an ALLOW —
            # the one failure mode this guard must never have.
            if tool_input is None:
                return
            deny("the hook payload's tool_input is not an object, so the command could "
                 "not be read. Refusing rather than guessing.")
        command = tool_input.get("command") or ""
        if not isinstance(command, str):
            return                                      # nothing to say about this call
        bad = offending_segments(command)
    except SystemExit:
        raise
    except Exception as exc:                            # noqa: BLE001
        deny(f"the guard itself failed on this command ({type(exc).__name__}), and a "
             f"guard that errors would otherwise let the call through. Refusing.")
    if not bad:
        return
    first = bad[0]
    shown = first if len(first) <= 120 else first[:117] + "..."
    deny(f"{len(bad)} `az` command(s) in this call do not pin a subscription — the first "
         f"is: {shown!r}. The machine default may point at an unrelated tenant, so EVERY "
         f"az invocation carries its own --subscription, including ones chained after a "
         f"pinned command, inside $(...) or backticks, inside a `bash -c` payload or a "
         f"script block, piped into a shell, and after wrappers like xargs, timeout or "
         f"sudo. Add the flag to each and retry.")


if __name__ == "__main__":
    main()
