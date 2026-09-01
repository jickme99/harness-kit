# reference/claude — the Claude Code wiring, as shipped by harness-kit 2026.09

Copied from the origin project's working harness. JSON cannot carry comments, so this README
is the header comment for `settings.json`:

- **`settings.json`** — the PROJECT-level hook wiring sample, verbatim from the origin. It
  wires all three guards as PreToolUse hooks on `Bash|PowerShell` via
  `${CLAUDE_PROJECT_DIR}` paths, so it travels with every clone. Install it as
  `.claude/settings.json` in the project, with the guard scripts under `scripts/`. The
  origin ALSO wires the same three scripts in `~/.claude/settings.json` with
  machine-absolute paths — deliberate defense-in-depth, because a project-level file lives
  in the checked-out COMMIT and a worktree branched before it landed is silently unguarded
  (that gap is how a guard once sat inert through 23 commands). The guards are read-only
  and idempotent; a doubled denial costs nothing. See `spec/guards.md`.
- **`role-template.md`** — the worker role-file template, distilled from the origin's
  role roster (`.claude/agents/*.md`). The `fence:` frontmatter is the machine-readable
  contract; the prose is the human explanation. One parser reads the whole roster.
- **`harness-auditor.md`** / **`version-steward.md`** — the two standing FUNCTION-role
  patterns (as opposed to product roles): the reader of the harness's own instruments, and
  the reader of dependency/runtime currency. Copied faithfully as patterns — they carry
  origin-project path names and instrument names as worked examples; replace those with
  your project's own at install time. See `spec/operating-model.md` and
  `spec/versioning.md` for what must survive the adaptation.
