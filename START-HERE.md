# Start here

**This folder is harness-kit, not a product.** Do not add app code here. Do not
rename this clone into a project.

A new project is a **separate folder**. This clone stays the factory. After
stand-up, the human opens the **new** folder and works there.

## Which tool is this?

| Tool | What it reads here without being asked |
|---|---|
| Claude Code | `CLAUDE.md` |
| Cursor | `AGENTS.md` |
| ChatGPT Codex (the coding agent) | `AGENTS.md` |
| ChatGPT in the browser | nothing — paste the prompt below |

The stand-up is the same on all three. After the gate, **enforcement** is not:
Claude is proven, Cursor hooks are verified, ChatGPT/Codex is doctrine-only until
a real cold start (`adapters/codex.md`). That does not change this front door.

## If someone just opened this repo to start work

You (the agent) stand up their project, or send them to the folder they already
have. They answer in plain English. They do not run stamp, poll, harvest, or
pytest — you do.

1. Read `STANDUP.md`. Never copy product files into *this* tree.
2. Ask only:
   - Is this a new folder, or one that already exists?
   - What is it about?
   - What are we doing?
   Do not ask how it will be hosted, whether it will be public, or whether
   anything will be sent out. A folder that already has the harness is not
   stood up again: tell them to open it.
3. For a new folder, or an existing folder with no harness: copy the core only
   (guards, wiki, stamp). Stamp with `--kit` pointed at **this** clone. Run
   the gate.
4. When the gate passes, give them the path and say: close this folder, open
   that one, continue there. Pieces beyond the core are copied later, when the
   work needs them (`STANDUP.md`).

## Paste this if the tool did not read the folder

Use this in ChatGPT in the browser, or in any agent that did not load
`CLAUDE.md` / `AGENTS.md`:

> This folder is harness-kit, not my project. Read START-HERE.md and STANDUP.md.
> Ask only whether this is a new folder or an existing one, what it is about,
> and what we are doing. Do not ask me how it will be hosted. If the folder
> already has the harness, tell me to open that folder. Otherwise stand up the
> core in the right folder. Do every copy, fill-in, stamp, and gate yourself —
> do not ask me to run terminal commands. When the gate passes, tell me the
> folder path and that I should open that folder and continue there.

## Kit version

`kit-manifest.json` field `kit_version`. This repo is the kit source, not a
consumer stamp.

## What is not in this repo

Consumer projects, their wikis, their product code. Those live in the folder
you create.
