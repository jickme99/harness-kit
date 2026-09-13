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

You (the agent) stand up their project. They answer questions in plain English.
They do not run stamp, poll, harvest, or pytest — you do.

1. Read `STANDUP.md` and follow it into a **new** directory (default: a sibling
   of this clone). Never copy product files into *this* tree.
2. Ask, without kit jargon:
   - Will any of this ever be public, or shared beyond the owner?
   - Will any tool send the repo to a third party (for example an external PR
     reviewer)?
   - Does this ship a container image (an app or a scheduled job) that has to
     stay current by itself?
   - What are we building, and what should the new folder be called?
3. Stamp with `--kit` pointed at **this** clone. Run the gate.
4. When the gate passes, give them the new path and say: close this folder,
   open that one, continue there.

## Paste this if the tool did not read the folder

Use this in ChatGPT in the browser, or in any agent that did not load
`CLAUDE.md` / `AGENTS.md`:

> This folder is harness-kit, not my project. Read START-HERE.md and STANDUP.md.
> Stand up a new project for me in a sibling folder. Ask me the STANDUP
> questions in plain English, then ask what I am building and what to name the
> folder. Do every copy, fill-in, stamp, and gate yourself — do not ask me to
> run terminal commands. When the gate passes, tell me the folder path and that
> I should open that folder and continue there.

## Kit version

`kit-manifest.json` field `kit_version`. This repo is the kit source, not a
consumer stamp.

## What is not in this repo

Consumer projects, their wikis, their product code. Those live in the folder
you create.
