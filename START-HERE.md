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
2. Ask about today, in plain English. A guess about later is not an answer.
   If they do not want the quiz, use the defaults (this computer, repository
   not shared, no outside reviewer, the product does not send data out yet)
   and write that down. The questions:
   - Is this repository public today, or shared with anyone besides you?
     A page you might publish later is not a yes. Yes installs a second
     repository.
   - Are you turning on a tool now that sends this repository to someone else
     (for example an outside reviewer)? Later is not a yes. Default: no.
     This does not install the tool.
   - Where does this run today? Default: this computer. A deployment stack is
     copied only when a container file is already in the project. "It will be
     a website" is not a yes.
   - Does the thing you are building send information to anyone but you?
     This is not the reviewer question. Default: no, until a spec says
     otherwise.
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
